<h2 align="center">SpectraStream: the web-based spectra harmonization tool</h2>

SpectraStream is a [Streamlit](https://streamlit.io/)-powered tool for spectra harmonization that runs in your browser. As simple as that, as complex as you like.

## For developers

### Introduction

This project uses several tools to enhance developer collaboration and ensure high code quality.

- [Poetry](https://python-poetry.org/): Dependency and virtual environment management.
- [Black](https://github.com/psf/black): Enforces consistent code formatting.
  - Different developers may have different habits (or no habits at all!) in code formatting. This can not only lead to frustration, but also waste valuable time, especially with poorly formatted code. Blake solves this problem by applying a common formatting. It promises that any changes it makes will **not** change the resulting byte-code.
- [µsort](https://github.com/facebook/usort): Safe, minimal import sorting for Python projects.
- [Flake8](https://flake8.pycqa.org/): Linter for identifying syntax and style errors.
  - Black will prevent linter errors related to formatting, but these are not all possible errors that a linter may catch.
- [Pre-commit](https://pre-commit.com/): Git hooks for automated code quality checks.
  - Git supports [hooks](https://git-scm.com/docs/githooks)—programs that can be run at specific points in the workflow, e.g., when `git commit` is used. The `pre-commit` hook is particularly useful for running programs like the ones above automatically. This not only helps to keep the commit history cleaner, but, most importantly, saves time by catching trivial mistakes early.

### Best practices

- Do not commit to `main` directly. Please use [feature branches](https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow) and [pull requests](https://help.github.com/articles/about-pull-requests/). Only urgent fixes that are small enough may be directly merged to `main` without a pull request.
- [Rebase](https://git-scm.com/docs/git-rebase) your feature branches often. Even when they are merged to `main` with a merge commit, regular rebases make sure that no significant merge conflicts accumulate over time.
- To avoid automatic merge commits on `git pull` that pollute the commit history and make it harder to follow, please run one of the following:
```sh
# For the current repo only
git config pull.rebase true

# For all Git repos on this system
git config --global pull.rebase true
```

### Tool requirements

You will need working Python and Poetry. For Python, the recommended way of handling different Python versions is [pyenv](https://github.com/pyenv/pyenv) on UNIX-like systems (Linux, BSD, macOS) and [pyenv-win](https://github.com/pyenv-win/pyenv-win) for Windows. For Poetry, the recommended way to install on both UNIX-like and Windows systems is [pipx](https://pipx.pypa.io/).

#### UNIX-like systems

Install `pyenv` and `pipx` through your package manager, e.g., on Arch Linux:

```sh
pacman -Syu pyenv python-pipx
```

Install Poetry through `pipx` ([details](https://python-poetry.org/docs/#installation)):

```sh
pipx install poetry
```

Install the Python version from `.python-version` in the project root, e.g.:

```sh
pyenv install 3.12
```

#### Windows

a) In PowerShell (non-admin), install `pyenv-win` ([details](https://pyenv-win.github.io/pyenv-win/docs/installation.html)):

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
```

**NB**: Do not install `pyenv-win` with Scoop. This installs an older version that doesn't support “latest” type Python versions, e.g., `3.12` that becomes `3.12.3` automatically.

b) In a Command Prompt, install the Python version from `.python-version` in the project root, e.g.:

```sh
pyenv install 3.12
```

c) In PowerShell (non-admin), install Scoop ([details](https://scoop.sh/)):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
```

d) In a Command Prompt, install `pipx` ([details](https://pipx.pypa.io/stable/installation/)):

```cmd
scoop install pipx
pipx ensurepath
```

e) In a Command Prompt, install Poetry ([details](https://python-poetry.org/docs/#installation)):

```cmd
pipx install poetry
```

### Start developing

```sh
git clone git@github.com:h2020charisma/spectrastream.git
cd spectrastream
poetry install
poetry run pre-commit install
```

### Run the application

```sh
# To run directly
poetry run streamlit run src/spectrastream/app.py

# Or, start a Poetry shell first
poetry shell
streamlit run src/spectrastream/app.py
# To exit the Poetry shell, type `exit`.
```

### Running the formatters & linters

**IMPORTANT**: This is run automatically against the changed files on `git commit`. If hooks like `usort` or `black` fail and change some files, review the changes with `git diff` and add the changed files with `git add`. Then either run `git commit` or `poetry run pre-commit` again, depending on what you were doing.

```sh
# Run against changed files
poetry run pre-commit

# Run against all files
poetry run pre-commit run --all-files
```

### Running the tests & coverage report

```sh
# Run tests
poetry run pytest

# Run tests with coverage report
poetry run pytest --cov
```

### Switching Python versions

Install the desired Python version with `pyenv`:

```sh
pyenv install 3.9
```

Switch the environment to the desired version:

```sh
pyenv shell 3.9 && poetry env use 3.9 && poetry install
```

**NB**: On Windows, run this compound command in a Command Prompt, not PowerShell (or, in PowerShell, execute the commands separated by `&&` independently, one after another).

### Specific IDE/editor notes

For better integration with Visual Studio Code, you may set:

```sh
poetry config virtualenvs.in-project true
```

You will need to run `poetry install` again after this.

## Acknowledgements

🇪🇺 This project has received funding from the European Union’s Horizon 2020 research and innovation program under [grant agreement No. 952921](https://cordis.europa.eu/project/id/952921).
