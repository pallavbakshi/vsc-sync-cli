"""Implementation of the apply command."""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..config import ConfigManager
from ..core.app_manager import AppManager
from ..core.config_manager import LayerConfigManager
from ..core.file_ops import FileOperations
from ..exceptions import AppConfigPathError, ExtensionError, VscSyncError
from ..models import AppDetails, MergeResult

logger = logging.getLogger(__name__)
console = Console()


class ApplyCommand:
    """Handles applying configurations to VSCode-like applications."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.load_config()
        self.layer_manager = LayerConfigManager(self.config.vscode_configs_path)

    def run(
        self,
        app_alias: str,
        stacks: Optional[List[str]] = None,
        backup: bool = True,
        backup_suffix: Optional[str] = None,
        dry_run: bool = False,
        force: bool = False,
        prune_extensions: bool = False,
        tasks: bool = True,
        include_settings: bool = True,
        include_keybindings: bool = True,
        include_extensions: bool = True,
        include_snippets: bool = True,
    ) -> None:
        """Execute the apply command."""
        try:
            console.print(
                f"[bold blue]Applying configuration to {app_alias}...[/bold blue]"
            )

            # Step 1: Validate app and get details
            app_details = self._validate_app(app_alias)

            # Step 2: Always create backup before cleaning (unless dry run)
            if not dry_run:
                self._create_backup(app_details, backup_suffix)

            # Step 3: Clean user directory for fresh start
            if not dry_run:
                self._clean_user_directory(
                    app_details,
                    include_settings,
                    include_keybindings,
                    include_snippets,
                    tasks,
                )

            # Step 4: Merge configuration layers
            stacks = stacks or []
            merge_result = self.layer_manager.merge_layers(
                app_alias=app_alias, stacks=stacks
            )

            # Step 5: Show what will be applied
            self._show_merge_summary(merge_result, stacks)

            if dry_run:
                # Step 6a: Dry run - show differences
                self._show_dry_run_results(
                    app_details,
                    merge_result,
                    prune_extensions,
                    tasks,
                    include_settings,
                    include_keybindings,
                    include_extensions,
                    include_snippets,
                )
            else:
                # Step 6b: Actually apply changes
                if not force and not self._confirm_apply(
                    app_details,
                    merge_result,
                    include_settings=include_settings,
                    include_keybindings=include_keybindings,
                    include_extensions=include_extensions,
                    include_snippets=include_snippets,
                ):
                    console.print("[yellow]Apply cancelled by user.[/yellow]")
                    return

                # Ask about extension cleaning
                clean_extensions = False
                if include_extensions:
                    clean_extensions = self._prompt_extension_cleaning(
                        app_details, merge_result
                    )

                self._apply_configurations(
                    app_details,
                    merge_result,
                    prune_extensions,
                    clean_extensions,
                    tasks,
                    include_settings,
                    include_keybindings,
                    include_extensions,
                    include_snippets,
                )
                self._show_success_message(
                    app_details,
                    merge_result,
                    include_settings=include_settings,
                    include_keybindings=include_keybindings,
                    include_extensions=include_extensions,
                    include_snippets=include_snippets,
                )

        except Exception as e:
            console.print(f"[red]Apply failed:[/red] {e}")
            logger.exception("Apply command failed")
            raise VscSyncError(f"Apply failed: {e}")

    def _validate_app(self, app_alias: str) -> AppDetails:
        """Validate that the app exists and is properly configured."""
        if app_alias not in self.config.managed_apps:
            available_apps = list(self.config.managed_apps.keys())
            raise VscSyncError(
                f"App '{app_alias}' is not registered. "
                f"Available apps: {', '.join(available_apps) if available_apps else 'none'}"
            )

        app_details = self.config.managed_apps[app_alias]

        if not app_details.config_path.exists():
            raise AppConfigPathError(
                f"App config directory does not exist: {app_details.config_path}"
            )

        return app_details

    def _create_backup(
        self, app_details: AppDetails, backup_suffix: Optional[str]
    ) -> Path:
        """Create a backup of the app's configuration directory."""
        if backup_suffix is None:
            timestamp = int(time.time())
            backup_suffix = f"bak.{timestamp}"

        console.print(f"Creating backup with suffix: {backup_suffix}")
        backup_path = FileOperations.backup_directory(
            app_details.config_path, backup_suffix
        )
        console.print(f"[green]Backup created:[/green] {backup_path}")
        return backup_path

    def _clean_user_directory(
        self,
        app_details: AppDetails,
        include_settings: bool,
        include_keybindings: bool,
        include_snippets: bool,
        tasks_enabled: bool,
    ) -> None:
        """Remove the files that will be overwritten (respect component flags)."""
        if not app_details.config_path.exists():
            # Create the directory if it doesn't exist
            app_details.config_path.mkdir(parents=True, exist_ok=True)
            console.print(
                f"[green]✓[/green] Created user directory: {app_details.config_path}"
            )
            return

        console.print(
            f"[yellow]Cleaning managed config files in:[/yellow] {app_details.config_path}"
        )

        managed_files: list[str] = []
        if include_settings:
            managed_files.append("settings.json")
        if include_keybindings:
            managed_files.append("keybindings.json")
        if tasks_enabled:
            managed_files.append("tasks.json")
        if include_snippets:
            managed_files.append("snippets")

        cleaned_count = 0
        for item_name in managed_files:
            item_path = app_details.config_path / item_name
            if item_path.exists():
                if item_path.is_file():
                    item_path.unlink()
                    console.print(f"[dim]  Removed file: {item_name}[/dim]")
                elif item_path.is_dir():
                    shutil.rmtree(item_path)
                    console.print(f"[dim]  Removed directory: {item_name}[/dim]")
                cleaned_count += 1

        # Preserve everything else:
        # - globalStorage/ (auth, licenses, app data)
        # - workspaceStorage/ (workspace-specific data)
        # - profiles/ (user's custom profiles)
        # - logs/ (application logs)
        # - extensions/ (extension metadata)
        # - Any other app-specific directories

        if cleaned_count > 0:
            console.print(
                f"[green]✓[/green] Cleaned {cleaned_count} managed config items"
            )
        else:
            console.print(f"[green]✓[/green] No managed config files to clean")

    def _show_merge_summary(self, merge_result: MergeResult, stacks: List[str]) -> None:
        """Show a summary of what layers were merged."""
        console.print("\n[bold]Configuration layers applied:[/bold]")

        table = Table()
        table.add_column("Layer Type", style="cyan")
        table.add_column("Layer Name", style="green")
        table.add_column("Path", style="dim")

        for layer in merge_result.layers_applied:
            layer_name = layer.layer_name or "base"
            table.add_row(layer.layer_type, layer_name, str(layer.path))

        console.print(table)

        if stacks:
            console.print(f"[bold]Stacks:[/bold] {', '.join(stacks)}")

    def _show_dry_run_results(
        self,
        app_details: AppDetails,
        merge_result: MergeResult,
        prune_extensions: bool,
        tasks_enabled: bool,
        include_settings: bool = True,
        include_keybindings: bool = True,
        include_extensions: bool = True,
        include_snippets: bool = True,
    ) -> None:
        """Show what would change in a dry run."""
        console.print("\n[bold yellow]DRY RUN - No changes will be made[/bold yellow]")

        if include_settings:
            self._show_settings_diff(app_details, merge_result.merged_settings)

        if include_keybindings:
            self._show_keybindings_diff(app_details, merge_result.keybindings_source)

        if include_snippets:
            self._show_snippets_diff(app_details, merge_result.snippets_paths)

        if tasks_enabled:
            self._show_tasks_diff(app_details, merge_result.tasks_source)

        # Show extension changes
        if include_extensions:
            self._show_extensions_diff(
                app_details, merge_result.extensions, prune_extensions
            )

    def _show_settings_diff(
        self, app_details: AppDetails, merged_settings: Dict
    ) -> None:
        """Show differences in settings.json."""
        console.print("\n[bold]Settings.json changes:[/bold]")

        current_settings_file = app_details.config_path / "settings.json"
        current_settings = FileOperations.read_json_file(current_settings_file)

        if current_settings == merged_settings:
            console.print("[green]No changes needed[/green]")
            return

        # Show current vs new settings
        if current_settings:
            console.print("[dim]Current settings:[/dim]")
            current_json = json.dumps(current_settings, indent=2, sort_keys=True)
            console.print(
                Syntax(current_json, "json", line_numbers=False, theme="monokai")
            )

        console.print("[dim]New settings:[/dim]")
        new_json = json.dumps(merged_settings, indent=2, sort_keys=True)
        console.print(Syntax(new_json, "json", line_numbers=False, theme="monokai"))

        # Show added/modified/removed keys
        self._show_setting_changes(current_settings, merged_settings)

    def _show_setting_changes(self, current: Dict, new: Dict) -> None:
        """Show detailed setting changes."""

        def flatten_dict(d: Dict, prefix: str = "") -> Dict[str, any]:
            """Flatten nested dictionary for comparison."""
            items = []
            for k, v in d.items():
                new_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        current_flat = flatten_dict(current)
        new_flat = flatten_dict(new)

        added = set(new_flat.keys()) - set(current_flat.keys())
        removed = set(current_flat.keys()) - set(new_flat.keys())
        modified = {
            k
            for k in current_flat.keys() & new_flat.keys()
            if current_flat[k] != new_flat[k]
        }

        if added:
            console.print(f"[green]Added settings ({len(added)}):[/green]")
            for key in sorted(added):
                console.print(f"  + {key}: {new_flat[key]}")

        if modified:
            console.print(f"[yellow]Modified settings ({len(modified)}):[/yellow]")
            for key in sorted(modified):
                console.print(f"  ~ {key}: {current_flat[key]} → {new_flat[key]}")

        if removed:
            console.print(f"[red]Removed settings ({len(removed)}):[/red]")
            for key in sorted(removed):
                console.print(f"  - {key}: {current_flat[key]}")

    def _show_keybindings_diff(
        self, app_details: AppDetails, keybindings_source: Optional[Path]
    ) -> None:
        """Show keybindings.json changes."""
        console.print("\n[bold]Keybindings.json changes:[/bold]")

        current_keybindings_file = app_details.config_path / "keybindings.json"

        if keybindings_source:
            if current_keybindings_file.exists():
                current_content = current_keybindings_file.read_text()
                new_content = keybindings_source.read_text()

                if current_content == new_content:
                    console.print("[green]No changes needed[/green]")
                else:
                    console.print(
                        f"[yellow]Will replace with:[/yellow] {keybindings_source}"
                    )
            else:
                console.print(f"[green]Will create from:[/green] {keybindings_source}")
        else:
            if current_keybindings_file.exists():
                console.print("[dim]Will keep existing keybindings.json[/dim]")
            else:
                console.print("[dim]No keybindings.json to apply[/dim]")

    def _show_tasks_diff(
        self, app_details: AppDetails, tasks_source: Optional[Path]
    ) -> None:
        """Show tasks.json changes during dry run."""
        console.print("\n[bold]Tasks.json changes:[/bold]")

        current_tasks_file = app_details.config_path / "tasks.json"

        if tasks_source:
            if current_tasks_file.exists():
                current_content = current_tasks_file.read_text()
                new_content = tasks_source.read_text()

                if current_content == new_content:
                    console.print("[green]No changes needed[/green]")
                else:
                    console.print(f"[yellow]Will replace with:[/yellow] {tasks_source}")
            else:
                console.print(f"[green]Will create from:[/green] {tasks_source}")
        else:
            if current_tasks_file.exists():
                console.print("[dim]Will keep existing tasks.json[/dim]")
            else:
                console.print("[dim]No tasks.json to apply[/dim]")

    def _show_snippets_diff(
        self, app_details: AppDetails, snippets_paths: List[Path]
    ) -> None:
        """Show snippets changes."""
        console.print("\n[bold]Snippets changes:[/bold]")

        if not snippets_paths:
            console.print("[dim]No snippets to apply[/dim]")
            return

        app_snippets_dir = app_details.config_path / "snippets"

        for snippets_path in snippets_paths:
            console.print(f"[green]Will copy snippets from:[/green] {snippets_path}")

            if snippets_path.is_dir():
                snippet_files = list(snippets_path.glob("*.code-snippets"))
                for snippet_file in snippet_files:
                    target_file = app_snippets_dir / snippet_file.name
                    if target_file.exists():
                        console.print(
                            f"  [yellow]Will overwrite:[/yellow] {snippet_file.name}"
                        )
                    else:
                        console.print(
                            f"  [green]Will create:[/green] {snippet_file.name}"
                        )

    def _show_extensions_diff(
        self,
        app_details: AppDetails,
        target_extensions: List[str],
        prune_extensions: bool,
    ) -> None:
        """Show extension changes."""
        console.print("\n[bold]Extensions changes:[/bold]")

        if not target_extensions:
            console.print("[dim]No extensions to manage[/dim]")
            return

        try:
            current_extensions = set(AppManager.get_installed_extensions(app_details))
        except ExtensionError as e:
            console.print(f"[red]Cannot check current extensions:[/red] {e}")
            console.print(f"[yellow]Would install these extensions:[/yellow]")
            for ext in target_extensions:
                console.print(f"  + {ext}")
            return

        target_extensions_set = set(target_extensions)

        to_install = target_extensions_set - current_extensions
        to_uninstall = (
            current_extensions - target_extensions_set if prune_extensions else set()
        )
        already_installed = target_extensions_set & current_extensions

        if to_install:
            console.print(f"[green]Extensions to install ({len(to_install)}):[/green]")
            for ext in sorted(to_install):
                console.print(f"  + {ext}")

        if to_uninstall:
            console.print(f"[red]Extensions to uninstall ({len(to_uninstall)}):[/red]")
            for ext in sorted(to_uninstall):
                console.print(f"  - {ext}")

        if already_installed:
            console.print(f"[dim]Already installed ({len(already_installed)}):[/dim]")
            for ext in sorted(already_installed):
                console.print(f"  ✓ {ext}")

        if not to_install and not to_uninstall:
            console.print("[green]No extension changes needed[/green]")

    def _confirm_apply(
        self,
        app_details: AppDetails,
        merge_result: MergeResult,
        *,
        include_settings: bool,
        include_keybindings: bool,
        include_extensions: bool,
        include_snippets: bool,
    ) -> bool:
        """Ask user to confirm applying changes."""
        console.print(
            f"\n[bold]Ready to apply configuration to {app_details.alias}[/bold]"
        )
        console.print(f"Target directory: [cyan]{app_details.config_path}[/cyan]")

        changes_summary: list[str] = []
        if include_settings and merge_result.merged_settings:
            changes_summary.append("settings.json")
        if include_keybindings and merge_result.keybindings_source:
            changes_summary.append("keybindings.json")
        if include_snippets and merge_result.snippets_paths:
            changes_summary.append("snippets")
        if include_extensions and merge_result.extensions:
            changes_summary.append("extensions")

        if changes_summary:
            console.print(f"Will modify: {', '.join(changes_summary)}")

        return Confirm.ask("Proceed with applying configuration?", default=True)

    def _prompt_extension_cleaning(
        self, app_details: AppDetails, merge_result: MergeResult
    ) -> bool:
        """Ask user if they want to clean extensions for a fresh start."""
        if not merge_result.extensions:
            return False  # No extensions to manage, skip cleaning

        extension_dir = AppManager.get_extension_directory(app_details.alias)

        if not extension_dir.exists():
            return False  # No existing extensions to clean

        console.print(
            f"\n[bold yellow]Extension Directory Found:[/bold yellow] {extension_dir}"
        )
        console.print(
            "Do you want to clean all existing extensions and install only the ones from your config?"
        )
        console.print(
            "[dim]This will remove all currently installed extensions and do a fresh install.[/dim]"
        )

        return Confirm.ask("Clean extensions directory?", default=False)

    def _apply_configurations(
        self,
        app_details: AppDetails,
        merge_result: MergeResult,
        prune_extensions: bool,
        clean_extensions: bool = False,
        tasks_enabled: bool = True,
        include_settings: bool = True,
        include_keybindings: bool = True,
        include_extensions: bool = True,
        include_snippets: bool = True,
    ) -> None:
        """Actually apply the configurations."""
        console.print("\n[bold]Applying configurations...[/bold]")

        # Apply settings.json
        if include_settings and merge_result.merged_settings:
            self._apply_settings(app_details, merge_result.merged_settings)

        # Apply keybindings.json
        if include_keybindings and merge_result.keybindings_source:
            self._apply_keybindings(app_details, merge_result.keybindings_source)

        # Apply tasks.json
        if tasks_enabled and merge_result.tasks_source:
            self._apply_tasks(app_details, merge_result.tasks_source)

        # Apply snippets
        if include_snippets and merge_result.snippets_paths:
            self._apply_snippets(app_details, merge_result.snippets_paths)

        # Clean extensions directory if requested
        if clean_extensions:
            self._clean_extensions_directory(app_details)

        # Apply extensions
        if include_extensions and merge_result.extensions:
            self._apply_extensions(
                app_details, merge_result.extensions, prune_extensions, clean_extensions
            )

    def _apply_tasks(self, app_details: AppDetails, tasks_source: Path) -> None:
        """Apply tasks.json from source layer."""
        tasks_file = app_details.config_path / "tasks.json"
        console.print(f"[cyan]Writing tasks.json...[/cyan]")

        FileOperations.copy_file(tasks_source, tasks_file)
        console.print(f"[green]✓[/green] Tasks applied")

    def _apply_settings(self, app_details: AppDetails, merged_settings: Dict) -> None:
        """Apply merged settings.json."""
        settings_file = app_details.config_path / "settings.json"
        console.print(f"[cyan]Writing settings.json...[/cyan]")

        FileOperations.write_json_file(settings_file, merged_settings)
        console.print(f"[green]✓[/green] Settings applied")

    def _apply_keybindings(
        self, app_details: AppDetails, keybindings_source: Path
    ) -> None:
        """Apply keybindings.json."""
        keybindings_file = app_details.config_path / "keybindings.json"
        console.print(f"[cyan]Writing keybindings.json...[/cyan]")

        FileOperations.copy_file(keybindings_source, keybindings_file)
        console.print(f"[green]✓[/green] Keybindings applied")

    def _apply_snippets(
        self, app_details: AppDetails, snippets_paths: List[Path]
    ) -> None:
        """Apply snippets from all layers."""
        app_snippets_dir = app_details.config_path / "snippets"
        console.print(f"[cyan]Copying snippets...[/cyan]")

        FileOperations.ensure_directory(app_snippets_dir)

        snippets_applied = 0
        for snippets_path in snippets_paths:
            if snippets_path.is_dir():
                FileOperations.copy_directory_contents(
                    snippets_path, app_snippets_dir, overwrite_existing=True
                )
                snippet_files = list(snippets_path.glob("*.code-snippets"))
                snippets_applied += len(snippet_files)

        console.print(f"[green]✓[/green] {snippets_applied} snippet files applied")

    def _clean_extensions_directory(self, app_details: AppDetails) -> None:
        """Clean the extensions directory for a fresh start."""
        extension_dir = AppManager.get_extension_directory(app_details.alias)

        if not extension_dir.exists():
            console.print(
                f"[dim]Extensions directory doesn't exist, skipping clean[/dim]"
            )
            return

        console.print(
            f"[yellow]Cleaning extensions directory:[/yellow] {extension_dir}"
        )

        try:
            shutil.rmtree(extension_dir)
            console.print(f"[green]✓[/green] Extensions directory cleaned")
        except Exception as e:
            console.print(f"[red]Failed to clean extensions directory:[/red] {e}")

    def _apply_extensions(
        self,
        app_details: AppDetails,
        target_extensions: List[str],
        prune_extensions: bool,
        clean_extensions: bool = False,
    ) -> None:
        """Apply extension changes."""
        console.print(f"[cyan]Managing extensions...[/cyan]")

        if not app_details.executable_path:
            console.print(
                "[yellow]No executable path configured, skipping extensions[/yellow]"
            )
            return

        try:
            if clean_extensions:
                # If we cleaned the directory, install all target extensions
                current_extensions = set()
                to_install = set(target_extensions)
                to_uninstall = set()
            else:
                # Normal case: check what's currently installed
                current_extensions = set(
                    AppManager.get_installed_extensions(app_details)
                )
                target_extensions_set = set(target_extensions)

                to_install = target_extensions_set - current_extensions
                to_uninstall = (
                    current_extensions - target_extensions_set
                    if prune_extensions
                    else set()
                )

            # Install extensions
            installed_count = 0
            for extension in to_install:
                console.print(f"Installing {extension}...")
                if AppManager.install_extension(app_details, extension):
                    installed_count += 1
                    console.print(f"[green]✓[/green] Installed {extension}")
                else:
                    console.print(f"[red]✗[/red] Failed to install {extension}")

            # Uninstall extensions (if prune_extensions is enabled)
            uninstalled_count = 0
            for extension in to_uninstall:
                console.print(f"Uninstalling {extension}...")
                if AppManager.uninstall_extension(app_details, extension):
                    uninstalled_count += 1
                    console.print(f"[green]✓[/green] Uninstalled {extension}")
                else:
                    console.print(f"[red]✗[/red] Failed to uninstall {extension}")

            if installed_count > 0 or uninstalled_count > 0:
                console.print(
                    f"[green]✓[/green] Extensions: {installed_count} installed, {uninstalled_count} uninstalled"
                )
            else:
                console.print(f"[green]✓[/green] No extension changes needed")

        except ExtensionError as e:
            console.print(f"[red]Extension management failed:[/red] {e}")

    def _show_success_message(
        self,
        app_details: AppDetails,
        merge_result: MergeResult,
        *,
        include_settings: bool,
        include_keybindings: bool,
        include_extensions: bool,
        include_snippets: bool,
    ) -> None:
        """Show success message after applying configurations."""
        console.print(
            f"\n[bold green]✓ Configuration successfully applied to {app_details.alias}![/bold green]"
        )

        applied_components: list[str] = []
        if include_settings and merge_result.merged_settings:
            applied_components.append("settings")
        if include_keybindings and merge_result.keybindings_source:
            applied_components.append("keybindings")
        if include_snippets and merge_result.snippets_paths:
            applied_components.append("snippets")
        if include_extensions and merge_result.extensions:
            applied_components.append("extensions")

        if applied_components:
            console.print(f"Applied: {', '.join(applied_components)}")

        console.print(
            f"Configuration directory: [cyan]{app_details.config_path}[/cyan]"
        )

        # Suggest restart if needed
        console.print(
            "\n[yellow]Note:[/yellow] Some changes may require restarting the application to take effect."
        )
        console.print(
            "Use [cyan]vsc-sync status[/cyan] to verify the configuration was applied correctly."
        )
