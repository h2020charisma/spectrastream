<h2 align="center">SpectraStream: the web-based spectra harmonization tool</h2>

SpectraStream is a [Streamlit](https://streamlit.io/)-powered tool for spectra harmonization that runs in your browser. As simple as that, as complex as you like.

## For developers

### Introduction

This project uses several tools to enhance developer collaboration and ensure high code quality.

- [Poetry](https://python-poetry.org/): Dependency and virtual environment management.
- [Black](https://github.com/psf/black): Enforces consistent code formatting.
  - Different developers may have different habits (or no habits at all!) in code formatting. This can not only lead to frustration, but also waste valuable time, especially with poorly formatted code. Blake solves this problem by applying a common formatting. It promises that any changes it makes will **not** change the resulting byte-code.
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

#### Windows

In PowerShell, install `pyenv-win` ([details](https://pyenv-win.github.io/pyenv-win/docs/installation.html)):

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
```

In PowerShell, install Scoop ([details](https://scoop.sh/)):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
```

In a command prompt, install `pipx` ([details](https://pipx.pypa.io/stable/installation/)):

```cmd
scoop install pipx
pipx ensurepath
```

In a command prompt, install Poetry ([details](https://python-poetry.org/docs/#installation)):

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

### Specific IDE/editor notes

For better integration with Visual Studio Code, you may set:
```sh
poetry config virtualenvs.in-project true
```

## Acknowledgements

🇪🇺 This project has received funding from the European Union’s Horizon 2020 research and innovation program under [grant agreement No. 952921](https://cordis.europa.eu/project/id/952921).
