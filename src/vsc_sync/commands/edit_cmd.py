"""Implementation of the edit command."""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm

from ..config import ConfigManager
from ..exceptions import VscSyncError

logger = logging.getLogger(__name__)
console = Console()

FILE_TYPE_MAPPING = {
    "settings": "settings.json",
    "keybindings": "keybindings.json",
    "tasks": "tasks.json",
    "extensions": "extensions.json",
    "snippets": "snippets",
}

LAYER_TYPE_PATHS = {
    "base": "base",
    "app": "apps",
    "stack": "stacks",
    "project": "projects",
    "live": None,  # Special case for actual app configs
}


class EditCommand:
    """Handles opening configuration files for editing."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.load_config()

    def run(
        self,
        layer_type: str,
        layer_name: Optional[str] = None,
        file_type: str = "settings",
        sort: bool = False,
        yes: bool = False,
    ) -> None:
        """Execute the edit command."""
        try:
            console.print(
                f"[bold blue]Opening {layer_type} {file_type} for editing...[/bold blue]"
            )

            # Step 1: Validate inputs
            self._validate_inputs(layer_type, layer_name, file_type)

            # Step 2: Construct file path
            file_path = self._construct_file_path(layer_type, layer_name, file_type)

            # Step 3: Handle file creation if needed
            if not file_path.exists():
                if not self._prompt_create_file(file_path):
                    console.print("[yellow]Edit cancelled.[/yellow]")
                    return

                self._create_file_if_needed(file_path, file_type)

            # Step 4: Sort keybindings if requested
            if sort and file_type == "keybindings":
                self._sort_keybindings(file_path, yes=yes)

            # Step 5: Open file in editor
            self._open_file_in_editor(file_path)

        except Exception as e:
            console.print(f"[red]Edit failed:[/red] {e}")
            logger.exception("Edit command failed")
            raise VscSyncError(f"Edit failed: {e}")

    def _validate_inputs(
        self, layer_type: str, layer_name: Optional[str], file_type: str
    ) -> None:
        """Validate command inputs."""
        if layer_type not in LAYER_TYPE_PATHS:
            available_types = ", ".join(LAYER_TYPE_PATHS.keys())
            raise VscSyncError(
                f"Invalid layer type '{layer_type}'. Available: {available_types}"
            )

        if file_type not in FILE_TYPE_MAPPING:
            available_types = ", ".join(FILE_TYPE_MAPPING.keys())
            raise VscSyncError(
                f"Invalid file type '{file_type}'. Available: {available_types}"
            )

        # layer_name is required for non-base layers
        if layer_type not in ["base"] and not layer_name:
            raise VscSyncError(f"Layer name is required for layer type '{layer_type}'")

        # Validate app layer names against registered apps (for both 'app' and 'live')
        if layer_type in ["app", "live"] and layer_name not in self.config.managed_apps:
            available_apps = list(self.config.managed_apps.keys())
            raise VscSyncError(
                f"App '{layer_name}' is not registered. "
                f"Available apps: {', '.join(available_apps) if available_apps else 'none'}"
            )

    def _construct_file_path(
        self, layer_type: str, layer_name: Optional[str], file_type: str
    ) -> Path:
        """Construct the full path to the configuration file."""

        # Special handling for live app configs
        if layer_type == "live":
            app_details = self.config.managed_apps[layer_name]
            if file_type == "snippets":
                return app_details.config_path / FILE_TYPE_MAPPING[file_type]
            else:
                return app_details.config_path / FILE_TYPE_MAPPING[file_type]

        # Normal handling for vscode-configs repository files
        configs_path = self.config.vscode_configs_path

        if layer_type == "base":
            layer_path = configs_path / LAYER_TYPE_PATHS[layer_type]
        else:
            layer_path = configs_path / LAYER_TYPE_PATHS[layer_type] / layer_name

        # Handle special case for snippets directory
        if file_type == "snippets":
            return layer_path / FILE_TYPE_MAPPING[file_type]
        else:
            return layer_path / FILE_TYPE_MAPPING[file_type]

    def _prompt_create_file(self, file_path: Path) -> bool:
        """Ask user if they want to create the file if it doesn't exist."""
        if file_path.name == "snippets":
            console.print(
                f"[yellow]Snippets directory doesn't exist:[/yellow] {file_path}"
            )
            return Confirm.ask("Create snippets directory?", default=True)
        else:
            console.print(f"[yellow]File doesn't exist:[/yellow] {file_path}")
            return Confirm.ask("Create new file?", default=True)

    def _create_file_if_needed(self, file_path: Path, file_type: str) -> None:
        """Create file or directory with appropriate initial content."""
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_type == "snippets":
            # Create snippets directory
            file_path.mkdir(exist_ok=True)
            console.print(f"[green]✓[/green] Created snippets directory: {file_path}")
        else:
            # Create JSON file with appropriate initial content
            initial_content = self._get_initial_content(file_type)
            file_path.write_text(initial_content)
            console.print(f"[green]✓[/green] Created file: {file_path}")

    def _get_initial_content(self, file_type: str) -> str:
        """Get initial content for new configuration files."""
        if file_type == "settings":
            return "{\n}\n"
        elif file_type == "keybindings":
            return "[\n]\n"
        elif file_type == "extensions":
            return '{\n  "recommendations": [\n  ]\n}\n'
        elif file_type == "tasks":
            return '{\n  "version": "2.0.0",\n  "tasks": []\n}\n'
        else:
            return "{}\n"

    # ------------------------------------------------------------------
    # Keybindings sorting
    # ------------------------------------------------------------------

    def _sort_keybindings(self, file_path: Path, yes: bool = False) -> None:
        """Sort *keybindings.json* entries in-place according to the Product
        Requirements Document (PRD) for the *VS Code Keybinding Sorter*.

        The rules implemented below are a close match of the "best-effort" MVP
        specification in the PRD (v1.0 – 2023-10-26):

        1. Primary sort key  –  ``key`` (alphabetically, case-insensitive).
        2. Secondary key     –  bindings **without** a ``when`` clause come
           before bindings **with** a ``when`` clause.
        3. Tertiary key      –  heuristic specificity for the ``when`` clause
           (apparent *generality* → *specificity*):
              • First by the number of logical operators (``&&``, ``||``)
                – fewer operators are considered more general.
              • Then by the length of the ``when`` string – shorter is more
                general.
        4. Quaternary key    –  alphabetical order of the ``when`` string.
        5. Final tie-breaker –  alphabetical order of the ``command`` string.

        The routine **does not remove duplicates** (FR7 of the PRD – identical
        entries are simply placed next to each other after sorting).  A future
        CLI flag may enable deduplication but that is *out of scope* for the
        current MVP.
        """
        if not file_path.exists():
            console.print(f"[red]Cannot sort: {file_path} does not exist[/red]")
            return

        try:
            import json, re

            raw_text = file_path.read_text(encoding="utf-8")

            # -----------------------------------------------------------------
            # Best-effort comment stripping – VS Code allows // and /* */ comments
            # in *keybindings.json*.  We remove them so that a standard ``json``
            # parser can handle the file.
            # -----------------------------------------------------------------

            # 1. Line comments
            cleaned_lines = []
            for line in raw_text.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("//"):
                    continue
                cleaned_lines.append(line)

            cleaned = "\n".join(cleaned_lines)

            # 2. Block comments
            cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.S)

            # 3. Keep only the JSON array portion (everything between the first
            #    '[' and the last ']') – guards against trailing characters.
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start == -1 or end == -1:
                console.print("[red]Could not locate a JSON array inside the keybindings file.[/red]")
                return

            cleaned = cleaned[start : end + 1]

            try:
                bindings = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                console.print(f"[red]Failed to parse keybindings.json:[/red] {exc}")
                return

            if not isinstance(bindings, list):
                console.print("[red]keybindings.json must contain a top-level JSON array – aborting sort.[/red]")
                return

            # -----------------------------------------------------------------
            # Sorting helpers
            # -----------------------------------------------------------------

            def _num_logical_ops(when_clause: str) -> int:
                """Return how many logical operators are present in *when_clause*."""
                # Count occurrences of the two operator tokens.  Overlapping
                # tokens are impossible because they differ by the first char.
                return when_clause.count("&&") + when_clause.count("||")

            def _sort_tuple(item):
                """Build a tuple implementing the PRD ordering rules."""
                if not isinstance(item, dict):
                    # Non-dict items go to the top to avoid crashing; should not
                    # happen with valid VS Code keybindings.json.
                    return ("", 0, 0, 0, "", "")

                key_str = str(item.get("key", ""))

                when_raw = item.get("when")
                has_when = 1 if when_raw else 0  # 0 → *no* when, comes first

                when_str = when_raw if when_raw else ""

                # Heuristic specificity score: (number_of_ops, len_when)
                num_ops = _num_logical_ops(when_str)
                len_when = len(when_str)

                command_str = str(item.get("command", ""))

                return (
                    key_str.lower(),  # primary key (case-insensitive)
                    has_when,         # secondary – general before specific
                    num_ops,          # tertiary (part 1) – general before specific
                    len_when,         # tertiary (part 2)
                    when_str.lower(), # quaternary
                    command_str.lower(),  # tie-breaker
                )

            bindings.sort(key=_sort_tuple)

            # -----------------------------------------------------------------
            # Confirmation prompt (unless --yes/yes=True)
            # -----------------------------------------------------------------
            if not yes:
                console.print(
                    f"This will overwrite [bold]{file_path}[/bold] with a best-effort sorted list (entries: {len(bindings)})."
                )
                if not Confirm.ask("Proceed?", default=True):
                    console.print("[yellow]Sort cancelled.[/yellow]")
                    return

            # -----------------------------------------------------------------
            # Write the sorted array back to disk – pretty-printed JSON.
            # (Comment preservation is a known limitation; see PRD §5.1 FR8.)
            # -----------------------------------------------------------------

            file_path.write_text(
                json.dumps(bindings, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            console.print(f"[green]✓[/green] keybindings sorted")

        except Exception as exc:
            console.print(f"[red]Failed to sort keybindings:[/red] {exc}")

    def _open_file_in_editor(self, file_path: Path) -> None:
        """Open the file in the configured or system default editor."""
        editor = self._get_editor()

        try:
            if file_path.is_dir():
                # For snippets directory, open the directory
                console.print(
                    f"[cyan]Opening directory in {editor}:[/cyan] {file_path}"
                )
            else:
                console.print(f"[cyan]Opening file in {editor}:[/cyan] {file_path}")

            # Try to open with the editor
            result = subprocess.run(
                [editor, str(file_path)], check=True, capture_output=True, text=True
            )

            console.print(f"[green]✓[/green] Opened successfully")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to open with {editor}:[/red] {e}")
            console.print(f"[yellow]You can manually open:[/yellow] {file_path}")
        except FileNotFoundError:
            console.print(f"[red]Editor '{editor}' not found[/red]")
            console.print(f"[yellow]You can manually open:[/yellow] {file_path}")

    def _get_editor(self) -> str:
        """Get the editor to use for opening files."""
        # Check if user has configured a preferred editor
        # For now, we'll use a simple priority order

        # 1. Check for VSCode (most likely to be available)
        editors_to_try = ["code", "codium", "cursor"]

        for editor in editors_to_try:
            try:
                result = subprocess.run(
                    [editor, "--version"], check=True, capture_output=True, text=True
                )
                return editor
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        # 2. Fall back to system defaults based on platform
        if sys.platform == "darwin":  # macOS
            return "open"
        elif sys.platform == "win32":  # Windows
            return "start"
        else:  # Linux and others
            return "xdg-open"
