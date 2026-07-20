FROM ghcr.io/astral-sh/uv:0.11.29@sha256:eb2843a1e56fd9e30c7276ce1a52cba86e64c7b385f5e3279a0e08e02dd058fc AS uv

FROM python:3.12.12-slim-trixie@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c AS builder

COPY --from=uv /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

FROM python:3.12.12-slim-trixie@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c AS runtime

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --home-dir /tmp \
        --shell /usr/sbin/nologin app

ENV HOME=/tmp \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY .streamlit ./.streamlit
COPY src ./

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/stream/_stcore/health', timeout=3).read()"]

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.baseUrlPath=/stream"]
