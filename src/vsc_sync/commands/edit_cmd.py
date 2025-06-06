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
    "extensions": "extensions.json",
    "snippets": "snippets"
}

LAYER_TYPE_PATHS = {
    "base": "base",
    "app": "apps",
    "stack": "stacks", 
    "project": "projects"
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
    ) -> None:
        """Execute the edit command."""
        try:
            console.print(f"[bold blue]Opening {layer_type} {file_type} for editing...[/bold blue]")

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

            # Step 4: Open file in editor
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
        if layer_type != "base" and not layer_name:
            raise VscSyncError(
                f"Layer name is required for layer type '{layer_type}'"
            )

        # Validate app layer names against registered apps
        if layer_type == "app" and layer_name not in self.config.managed_apps:
            available_apps = list(self.config.managed_apps.keys())
            raise VscSyncError(
                f"App '{layer_name}' is not registered. "
                f"Available apps: {', '.join(available_apps) if available_apps else 'none'}"
            )

    def _construct_file_path(
        self, layer_type: str, layer_name: Optional[str], file_type: str
    ) -> Path:
        """Construct the full path to the configuration file."""
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
            console.print(f"[yellow]Snippets directory doesn't exist:[/yellow] {file_path}")
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
        else:
            return "{}\n"

    def _open_file_in_editor(self, file_path: Path) -> None:
        """Open the file in the configured or system default editor."""
        editor = self._get_editor()
        
        try:
            if file_path.is_dir():
                # For snippets directory, open the directory
                console.print(f"[cyan]Opening directory in {editor}:[/cyan] {file_path}")
            else:
                console.print(f"[cyan]Opening file in {editor}:[/cyan] {file_path}")

            # Try to open with the editor
            result = subprocess.run(
                [editor, str(file_path)],
                check=True,
                capture_output=True,
                text=True
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
                    [editor, "--version"],
                    check=True,
                    capture_output=True,
                    text=True
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