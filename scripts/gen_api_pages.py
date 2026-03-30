"""Generate one Markdown stub per public Python module so mkdocstrings
can render API reference pages automatically.

The script is executed automatically by the *mkdocs-gen-files* plugin
when you run `mkdocs build` or `mkdocs serve`.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path


ROOT_PACKAGE = "vsc_sync"


def iter_modules(package_name: str):
    """Yield the given package and all its sub-modules recursively."""
    module = importlib.import_module(package_name)
    yield module.__name__

    # Packages (i.e. modules with a __path__) may contain sub-modules.
    if hasattr(module, "__path__"):
        for submodule in pkgutil.walk_packages(
            module.__path__, prefix=f"{package_name}."
        ):
            yield from iter_modules(submodule.name)


def main() -> None:
    docs_path = Path(__file__).resolve().parents[1]
    reference_root = docs_path / "reference"
    reference_root.mkdir(parents=True, exist_ok=True)

    for mod_name in iter_modules(ROOT_PACKAGE):
        out_file = reference_root / f"{mod_name}.md"
        out_file.write_text(f"::: {mod_name}\n")


if __name__ == "__main__":
    main()
