# For developers

This page explains how to set up a development environment for **VSC Sync CLI**, run the test-suite, lint the code and contribute patches.

---

## 1 · Clone the repository

```bash
git clone https://github.com/your-org/vsc-sync-cli.git
cd vsc-sync-cli
```

## 2 · Create a virtual environment (uv)

We use [uv](https://github.com/astral-sh/uv) for blister-fast dependency installs, but regular `python -m venv` works as well.

```bash
uv venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install runtime + dev dependencies
uv pip install -r requirements.txt        # if provided
uv pip install -r requirements-dev.txt    # linting / tests

# Or, if lock-files are not present
uv pip install -e .[dev]                  # editable install with extras
```

## 3 · Run the test-suite

```bash
pytest -q        # run all tests
pytest -q tests/core/test_config_manager.py  # single module
```

Coverage report:

```bash
pytest --cov=vsc_sync --cov-report=term-missing --cov-report=html
open htmlcov/index.html
```

## 4 · Code quality tooling

The project uses *ruff* for linting/formatting and *pre-commit* to make sure checks pass before each commit.

```bash
# one-off setup
pre-commit install

# run everything against the entire repo
pre-commit run --all-files
```

## 5 · Building the docs locally

Instructions live in [Installation](installation.md) → Option B (uv).  Once the tool-chain is installed:

```bash
mkdocs serve
# http://127.0.0.1:8000
```

## 6 · Release checklist (maintainers)

1. Bump version in `src/vsc_sync/__init__.py` and `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. `tox -e build` or `python -m build`.
4. `twine upload dist/*`.
5. `git tag vX.Y.Z && git push --tags`.
6. `mkdocs gh-deploy --force` to publish updated docs.

---

### Useful tox environments

| Command           | Purpose                       |
|-------------------|-------------------------------|
| `tox -e py311`    | Run unit tests on Python 3.11 |
| `tox -e lint`     | Ruff + mypy + import-sort     |
| `tox -e docs`     | Ensure docs build cleanly     |
