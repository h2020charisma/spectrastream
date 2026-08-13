"""Browser-local persistence for instrument profiles.

Profiles live in the visitor's own browser, not on the server. That was a
deliberate choice: the deployment container has no writable volume, an
anonymous demo has nobody to attach server-side records to, and "it stays on
your machine" is a much easier promise to keep than a retention policy.

The bridge is a Custom Component v2 that owns one ``localStorage`` key. Python
sends the text it wants stored; JavaScript writes it and reports back what is
actually there. Both directions are needed -- there is no two-way binding.

Rerun discipline matters here: ``setStateValue`` triggers a rerun, so the
frontend only emits when the stored text has genuinely changed, or the app
would loop forever.
"""

import json

import streamlit as st

from spectrastream.profiles import ProfileLibrary

#: One key holds the whole library. Versioned so a future schema change can
#: migrate rather than silently misread.
STORAGE_KEY = "spectrastream.profiles.v1"

COMPONENT_KEY = "spectrastream_localstore"

#: Browsers give roughly 5 MB to localStorage. A JSON calibration model is a
#: few kB, so this is headroom, not a limit -- but it is worth saying out loud
#: rather than failing opaquely at some future profile count.
SOFT_LIMIT_BYTES = 3 * 1024 * 1024

_HTML = """<div data-spectrastream-localstore="1" style="display:none"></div>"""

_JS = """
export default function (component) {
  const { data, parentElement, setStateValue } = component
  const key = data?.key
  if (!key) return

  // Private-browsing modes and hardened settings can make localStorage throw
  // on access, not just on write -- probe before relying on it.
  let store = null
  try {
    store = window.localStorage
    const probe = "__spectrastream_probe__"
    store.setItem(probe, "1")
    store.removeItem(probe)
  } catch (err) {
    setStateValue("state", { available: false, text: null, error: String(err) })
    return
  }

  let error = null
  const write = data?.write
  if (write && typeof write.text === "string") {
    try {
      store.setItem(key, write.text)
    } catch (err) {
      // Most often the quota. Report it rather than pretending the save
      // succeeded, so Python can tell the user their work is not persisted.
      error = String(err)
    }
  } else if (write && write.clear) {
    try {
      store.removeItem(key)
    } catch (err) {
      error = String(err)
    }
  }

  let text = null
  try {
    text = store.getItem(key)
  } catch (err) {
    error = error || String(err)
  }

  // Emit only on a real change: setStateValue causes a rerun.
  const next = { available: true, text: text, error: error }
  const previous = parentElement.__spectrastreamLast
  if (
    !previous ||
    previous.text !== next.text ||
    previous.error !== next.error ||
    previous.available !== next.available
  ) {
    parentElement.__spectrastreamLast = next
    setStateValue("state", next)
  }
}
"""


def _register():
    return st.components.v2.component(COMPONENT_KEY, html=_HTML, js=_JS)


_COMPONENT = _register()


def _mount(data: dict):
    """Mount the bridge, re-registering if the runtime has forgotten it.

    Registration happens at import time and lives in the *runtime's* registry,
    but the module is cached in ``sys.modules``. A second runtime in the same
    process -- which is what every AppTest after the first one is -- therefore
    finds no component registered. Re-register on demand instead of failing.
    """
    global _COMPONENT
    try:
        return _COMPONENT(key=COMPONENT_KEY, data=data, on_state_change=lambda: None)
    except ValueError:
        _COMPONENT = _register()
        return _COMPONENT(key=COMPONENT_KEY, data=data, on_state_change=lambda: None)


class BrowserStoreResult:
    """What the browser reported back this run."""

    def __init__(self, raw: dict | None):
        raw = raw or {}
        self.answered = bool(raw)
        self.available = bool(raw.get("available", False))
        self.text = raw.get("text")
        self.error = raw.get("error")


def sync(pending_write: str | None = None, clear: bool = False) -> BrowserStoreResult:
    """Mount the bridge, optionally writing ``pending_write``.

    Returns whatever is currently in the browser's storage. On the very first
    run this has not answered yet -- callers must not treat "nothing yet" as
    "no profiles", or they will save an empty library over real data.
    """
    write: dict | None = None
    if clear:
        write = {"clear": True}
    elif pending_write is not None:
        write = {"text": pending_write}

    result = _mount({"key": STORAGE_KEY, "write": write})
    return BrowserStoreResult(getattr(result, "state", None))


def load_library(text: str | None) -> tuple[ProfileLibrary, str | None]:
    """Parse stored text into a library, reporting rather than raising."""
    if not text:
        return ProfileLibrary(), None
    try:
        return ProfileLibrary.from_json(text), None
    except (ValueError, json.JSONDecodeError) as err:
        return ProfileLibrary(), (
            f"Saved profiles could not be read ({err}). Starting with an empty "
            "library; the stored copy has been left untouched."
        )


def serialise(library: ProfileLibrary) -> str:
    return library.to_json()


def size_warning(text: str) -> str | None:
    size = len(text.encode("utf-8"))
    if size < SOFT_LIMIT_BYTES:
        return None
    return (
        f"Stored profiles now take {size / 1_048_576:.1f} MB, close to what a "
        "browser allows. Export and remove older calibrations to be safe."
    )
