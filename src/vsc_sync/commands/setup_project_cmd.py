"""Implementation of the setup-project command."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from ..config import ConfigManager
from ..core.config_manager import LayerConfigManager
from ..core.file_ops import FileOperations
from ..exceptions import LayerNotFoundError, VscSyncError
from ..models import ExtensionsConfig, LayerInfo, MergeResult

logger = logging.getLogger(__name__)
console = Console()


class SetupProjectCommand:
    """Handles setting up .vscode/ files for projects."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.load_config()
        self.layer_manager = LayerConfigManager(self.config.vscode_configs_path)

    def run(
        self,
        project_path: Path,
        stacks: Optional[List[str]] = None,
        from_project_type: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Execute the setup-project command."""
        try:
            console.print(
                f"[bold blue]Setting up .vscode/ for project:[/bold blue] {project_path}"
            )

            # Step 1: Validate and resolve project path
            project_path = self._validate_project_path(project_path)

            # Step 2: Create .vscode directory if needed
            vscode_dir = self._ensure_vscode_directory(project_path)

            # Step 3: Merge configuration layers for project
            stacks = stacks or []
            merge_result = self._merge_project_layers(from_project_type, stacks)

            # Step 4: Show what will be created
            self._show_merge_summary(merge_result, from_project_type, stacks)

            # Step 5: Check for existing files and handle overwrites
            if not force:
                if not self._confirm_overwrite(vscode_dir, merge_result):
                    console.print("[yellow]Setup cancelled by user.[/yellow]")
                    return

            # Step 6: Write the project files
            self._write_project_files(vscode_dir, merge_result)
            self._show_success_message(project_path, merge_result)

        except Exception as e:
            console.print(f"[red]Setup failed:[/red] {e}")
            logger.exception("Setup-project command failed")
            raise VscSyncError(f"Setup failed: {e}")

    def _validate_project_path(self, project_path: Path) -> Path:
        """Validate and resolve the project path."""
        resolved_path = project_path.resolve()

        if not resolved_path.exists():
            raise VscSyncError(f"Project path does not exist: {project_path}")

        if not resolved_path.is_dir():
            raise VscSyncError(f"Project path is not a directory: {project_path}")

        return resolved_path

    def _ensure_vscode_directory(self, project_path: Path) -> Path:
        """Create .vscode directory if it doesn't exist."""
        vscode_dir = project_path / ".vscode"

        if not vscode_dir.exists():
            vscode_dir.mkdir()
            console.print(f"[green]Created:[/green] {vscode_dir}")
        else:
            console.print(f"[dim]Using existing:[/dim] {vscode_dir}")

        return vscode_dir

    def _merge_project_layers(
        self, from_project_type: Optional[str], stacks: List[str]
    ) -> MergeResult:
        """Merge configuration layers for project setup."""
        layers = []

        # Add project type layer if specified
        if from_project_type:
            if self.layer_manager.layer_exists("project", from_project_type):
                project_layer = LayerInfo(
                    layer_type="project",
                    layer_name=from_project_type,
                    path=self.layer_manager.get_layer_path(
                        "project", from_project_type
                    ),
                )
                layers.append(project_layer)
            else:
                raise LayerNotFoundError(
                    f"Project type '{from_project_type}' not found"
                )

        # Add stack layers
        for stack in stacks:
            if self.layer_manager.layer_exists("stack", stack):
                stack_layer = LayerInfo(
                    layer_type="stack",
                    layer_name=stack,
                    path=self.layer_manager.get_layer_path("stack", stack),
                )
                layers.append(stack_layer)
            else:
                raise LayerNotFoundError(f"Stack '{stack}' not found")

        if not layers:
            raise VscSyncError(
                "No layers specified. Use --from-project-type or --stack to specify configuration sources."
            )

        # Merge settings.json from all layers
        merged_settings = {}
        for layer in layers:
            settings_file = layer.path / "settings.json"
            if settings_file.exists():
                layer_settings = self.layer_manager.load_json_file(settings_file)
                merged_settings = self.layer_manager.deep_merge_dicts(
                    merged_settings, layer_settings
                )

        # Collect extensions from all layers
        extensions = self.layer_manager.collect_extensions(layers)

        # Note: We don't collect keybindings or snippets for project setup
        # Those are typically user-level configurations

        return MergeResult(
            merged_settings=merged_settings,
            keybindings_source=None,
            extensions=extensions,
            snippets_paths=[],
            layers_applied=layers,
        )

    def _show_merge_summary(
        self,
        merge_result: MergeResult,
        from_project_type: Optional[str],
        stacks: List[str],
    ) -> None:
        """Show a summary of what layers were merged."""
        console.print("\n[bold]Configuration sources:[/bold]")

        table = Table()
        table.add_column("Layer Type", style="cyan")
        table.add_column("Layer Name", style="green")
        table.add_column("Path", style="dim")

        for layer in merge_result.layers_applied:
            table.add_row(layer.layer_type, layer.layer_name, str(layer.path))

        console.print(table)

        # Show what will be generated
        files_to_create = []
        if merge_result.merged_settings:
            files_to_create.append("settings.json")
        if merge_result.extensions:
            files_to_create.append("extensions.json")

        if files_to_create:
            console.print(
                f"\n[bold]Files to create/update:[/bold] {', '.join(files_to_create)}"
            )

    def _confirm_overwrite(self, vscode_dir: Path, merge_result: MergeResult) -> bool:
        """Check for existing files and confirm overwrite."""
        existing_files = []

        settings_file = vscode_dir / "settings.json"
        if settings_file.exists() and merge_result.merged_settings:
            existing_files.append("settings.json")

        extensions_file = vscode_dir / "extensions.json"
        if extensions_file.exists() and merge_result.extensions:
            existing_files.append("extensions.json")

        if not existing_files:
            return True  # No conflicts, proceed

        console.print(
            f"\n[yellow]Existing files found:[/yellow] {', '.join(existing_files)}"
        )
        console.print("These files will be overwritten.")

        return Confirm.ask("Continue with setup?", default=True)

    def _write_project_files(self, vscode_dir: Path, merge_result: MergeResult) -> None:
        """Write the project configuration files."""
        console.print("\n[bold]Writing project files...[/bold]")

        # Write settings.json
        if merge_result.merged_settings:
            settings_file = vscode_dir / "settings.json"
            console.print(f"[cyan]Writing settings.json...[/cyan]")
            FileOperations.write_json_file(settings_file, merge_result.merged_settings)
            console.print(f"[green]✓[/green] Created {settings_file}")

        # Write extensions.json
        if merge_result.extensions:
            extensions_file = vscode_dir / "extensions.json"
            console.print(f"[cyan]Writing extensions.json...[/cyan]")

            extensions_config = {"recommendations": merge_result.extensions}
            FileOperations.write_json_file(extensions_file, extensions_config)
            console.print(f"[green]✓[/green] Created {extensions_file}")

    def _show_success_message(
        self, project_path: Path, merge_result: MergeResult
    ) -> None:
        """Show success message after setting up project."""
        console.print(f"\n[bold green]✓ Project setup completed![/bold green]")
        console.print(f"Project directory: [cyan]{project_path}[/cyan]")

        created_files = []
        if merge_result.merged_settings:
            created_files.append("settings.json")
        if merge_result.extensions:
            created_files.append("extensions.json")

        if created_files:
            console.print(f"Created: {', '.join(created_files)}")

        # Advise about git
        console.print(
            "\n[yellow]Recommendation:[/yellow] Commit the .vscode/ directory to your project's Git repository"
        )
        console.print("to share these settings with your team:")
        console.print("[dim]  git add .vscode/[/dim]")
        console.print("[dim]  git commit -m 'Add VSCode project configuration'[/dim]")
