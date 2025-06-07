# Installation

At the moment **VSC Sync CLI** is not yet published on PyPI or Homebrew.  Until the
first public release drops you can install it straight from the Git repository.

---

## 1 · Clone the repository

```bash
git clone https://github.com/your-org/vsc-sync-cli.git
cd vsc-sync-cli
```

## 2 · Create a virtual environment (optional but recommended)

Using the standard library:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

Or with the super-fast [uv](https://github.com/astral-sh/uv) tool:

```bash
uv venv .venv
source .venv/bin/activate
```

## 3 · Install the package in *editable* mode

Editable (`-e`) installs mean changes you make to the source code are picked up
immediately—perfect for contributing patches or running the latest main branch.

```bash
pip install -e .[cli]
# or, via uv
uv pip install -e .[cli]
```

> **Note**
> The `[cli]` extra brings in Typer, Rich and any runtime deps but deliberately
> excludes heavy dev-only tooling (pytest, ruff, etc.).  See
> [For Developers](for-developers.md) if you need those as well.

## 4 · Verify installation

```bash
$ vsc-sync --version
vsc-sync, version 0.3.0.dev (editable)
```

If a version string prints without errors you’re good to go.

---

## Keeping up to date

```bash
git pull                       # grab the latest commit
pip install -e . --upgrade     # update editable install in-place
```

---

### Roadmap to “pip install vsc-sync”

Once the API stabilises we’ll publish:

* **PyPI** wheels for Linux, macOS & Windows
* **Homebrew** formula for one-line macOS / Linux installs
* Stand-alone binaries via GitHub Releases

Stay tuned!  In the meantime the git-clone method above is the official way to
get the tool.
