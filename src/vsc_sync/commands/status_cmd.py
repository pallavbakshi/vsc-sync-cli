"""Implementation of the status command."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
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


class StatusCommand:
    """Handles checking configuration status for VSCode-like applications."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.load_config()
        self.layer_manager = LayerConfigManager(self.config.vscode_configs_path)

    def _generate_edit_suggestions(self, app_alias: str, stacks: List[str] = None) -> Dict[str, str]:
        """Generate edit command suggestions for different file types."""
        suggestions = {
            "live_settings": f"vsc-sync edit live {app_alias}",
            "live_keybindings": f"vsc-sync edit live {app_alias} --file-type keybindings", 
            "live_snippets": f"vsc-sync edit live {app_alias} --file-type snippets",
            "live_extensions": f"vsc-sync edit live {app_alias} --file-type extensions",
            "app_settings": f"vsc-sync edit app {app_alias}",
            "app_keybindings": f"vsc-sync edit app {app_alias} --file-type keybindings",
            "base_settings": "vsc-sync edit base",
            "base_keybindings": "vsc-sync edit base --file-type keybindings",
        }
        
        # Add stack-specific suggestions if stacks are provided
        if stacks:
            for stack in stacks:
                suggestions[f"stack_{stack}_settings"] = f"vsc-sync edit stack {stack}"
                suggestions[f"stack_{stack}_keybindings"] = f"vsc-sync edit stack {stack} --file-type keybindings"
        
        return suggestions

    def run(
        self,
        app_alias: Optional[str] = None,
        stacks: Optional[List[str]] = None,
    ) -> None:
        """Execute the status command."""
        try:
            if app_alias:
                # Check status for specific app
                self._check_app_status(app_alias, stacks or [])
            else:
                # Check status for all registered apps
                self._check_all_apps_status()

        except Exception as e:
            console.print(f"[red]Status check failed:[/red] {e}")
            logger.exception("Status command failed")
            raise VscSyncError(f"Status check failed: {e}")

    def _check_all_apps_status(self) -> None:
        """Check status for all registered applications."""
        console.print("[bold blue]Checking status for all registered applications...[/bold blue]")

        if not self.config.managed_apps:
            console.print("No applications registered yet.")
            console.print(
                "Use 'vsc-sync add-app' to register applications or 'vsc-sync init' to auto-discover."
            )
            return

        # Create summary table
        table = Table(title="Configuration Status Summary")
        table.add_column("App", style="cyan")
        table.add_column("Settings", style="green")
        table.add_column("Keybindings", style="yellow")
        table.add_column("Snippets", style="blue")
        table.add_column("Extensions", style="magenta")
        table.add_column("Overall", style="bold")

        for app_alias in self.config.managed_apps:
            try:
                app_details = self._validate_app(app_alias)
                status_result = self._get_app_status_summary(app_details, [])
                
                table.add_row(
                    app_alias,
                    status_result["settings"],
                    status_result["keybindings"],
                    status_result["snippets"],
                    status_result["extensions"],
                    status_result["overall"],
                )
            except Exception as e:
                table.add_row(
                    app_alias,
                    "[red]ERROR[/red]",
                    "[red]ERROR[/red]", 
                    "[red]ERROR[/red]",
                    "[red]ERROR[/red]",
                    "[red]ERROR[/red]",
                )

        console.print(table)
        console.print("\n[dim]Use 'vsc-sync status <app>' for detailed information about a specific app.[/dim]")

    def _check_app_status(self, app_alias: str, stacks: List[str]) -> None:
        """Check status for a specific application."""
        console.print(f"[bold blue]Checking status for {app_alias}...[/bold blue]")

        # Validate app and get details
        app_details = self._validate_app(app_alias)

        # Get what configuration would be applied
        merge_result = self.layer_manager.merge_layers(
            app_alias=app_alias, stacks=stacks
        )

        # Show layers that would be applied
        self._show_active_layers(merge_result, stacks)

        # Compare current vs target configurations
        self._compare_configurations(app_details, merge_result, stacks)

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

    def _get_app_status_summary(self, app_details: AppDetails, stacks: List[str]) -> Dict[str, str]:
        """Get a summary status for an app (for the overview table)."""
        try:
            merge_result = self.layer_manager.merge_layers(
                app_alias=app_details.alias, stacks=stacks
            )

            settings_status = self._get_settings_status(app_details, merge_result.merged_settings)
            keybindings_status = self._get_keybindings_status(app_details, merge_result.keybindings_source)
            snippets_status = self._get_snippets_status(app_details, merge_result.snippets_paths)
            extensions_status = self._get_extensions_status(app_details, merge_result.extensions)

            # Determine overall status
            statuses = [settings_status, keybindings_status, snippets_status, extensions_status]
            if any("OUT OF SYNC" in status for status in statuses):
                overall_status = "[red]OUT OF SYNC[/red]"
            elif any("UNKNOWN" in status for status in statuses):
                overall_status = "[yellow]UNKNOWN[/yellow]"
            elif all("IN SYNC" in status for status in statuses):
                overall_status = "[green]IN SYNC[/green]"
            else:
                overall_status = "[yellow]PARTIAL[/yellow]"

            return {
                "settings": settings_status,
                "keybindings": keybindings_status,
                "snippets": snippets_status,
                "extensions": extensions_status,
                "overall": overall_status,
            }

        except Exception:
            return {
                "settings": "[red]ERROR[/red]",
                "keybindings": "[red]ERROR[/red]",
                "snippets": "[red]ERROR[/red]",
                "extensions": "[red]ERROR[/red]",
                "overall": "[red]ERROR[/red]",
            }

    def _show_active_layers(self, merge_result: MergeResult, stacks: List[str]) -> None:
        """Show which layers would be applied."""
        console.print("\n[bold]Active configuration layers:[/bold]")

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

    def _compare_configurations(self, app_details: AppDetails, merge_result: MergeResult, stacks: List[str]) -> None:
        """Compare current configuration with target configuration."""
        console.print("\n[bold]Configuration Status:[/bold]")

        # Check settings.json
        self._compare_settings(app_details, merge_result.merged_settings, stacks)

        # Check keybindings.json
        self._compare_keybindings(app_details, merge_result.keybindings_source, stacks)

        # Check snippets
        self._compare_snippets(app_details, merge_result.snippets_paths, stacks)

        # Check extensions
        self._compare_extensions(app_details, merge_result.extensions, stacks)

    def _compare_settings(self, app_details: AppDetails, target_settings: Dict, stacks: List[str] = None) -> None:
        """Compare current settings.json with target."""
        console.print("\n[bold cyan]Settings.json:[/bold cyan]")

        current_settings_file = app_details.config_path / "settings.json"
        current_settings = FileOperations.read_json_file(current_settings_file)

        if current_settings == target_settings:
            console.print("[green]✓ IN SYNC[/green] - Settings match target configuration")
        else:
            console.print("[red]✗ OUT OF SYNC[/red] - Settings differ from target configuration")
            
            # Show detailed differences
            self._show_setting_differences(current_settings, target_settings)
            
            # Show edit suggestions
            self._show_edit_suggestions_for_settings(app_details.alias, stacks or [])

    def _show_setting_differences(self, current: Dict, target: Dict) -> None:
        """Show detailed setting differences."""
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
        target_flat = flatten_dict(target)

        added = set(target_flat.keys()) - set(current_flat.keys())
        removed = set(current_flat.keys()) - set(target_flat.keys())
        modified = {
            k
            for k in current_flat.keys() & target_flat.keys()
            if current_flat[k] != target_flat[k]
        }

        differences_count = len(added) + len(removed) + len(modified)
        console.print(f"  [yellow]{differences_count} differences found:[/yellow]")

        if added:
            console.print(f"    [green]{len(added)} settings to add[/green]")
            for key in sorted(list(added)[:3]):  # Show first 3
                console.print(f"      + {key}")
            if len(added) > 3:
                console.print(f"      ... and {len(added) - 3} more")

        if modified:
            console.print(f"    [yellow]{len(modified)} settings to modify[/yellow]")
            for key in sorted(list(modified)[:3]):  # Show first 3
                console.print(f"      ~ {key}")
            if len(modified) > 3:
                console.print(f"      ... and {len(modified) - 3} more")

        if removed:
            console.print(f"    [red]{len(removed)} settings to remove[/red]")
            for key in sorted(list(removed)[:3]):  # Show first 3
                console.print(f"      - {key}")
            if len(removed) > 3:
                console.print(f"      ... and {len(removed) - 3} more")

    def _show_edit_suggestions_for_settings(self, app_alias: str, stacks: List[str]) -> None:
        """Show edit command suggestions for settings."""
        suggestions = self._generate_edit_suggestions(app_alias, stacks)
        
        console.print(f"\n  [bold blue]💡 Quick fixes:[/bold blue]")
        console.print(f"    Edit live app config:  [cyan]{suggestions['live_settings']}[/cyan]")
        console.print(f"    Edit app layer:        [cyan]{suggestions['app_settings']}[/cyan]")
        console.print(f"    Edit base layer:       [cyan]{suggestions['base_settings']}[/cyan]")
        
        # Show stack suggestions if available
        for stack in stacks:
            stack_key = f"stack_{stack}_settings"
            if stack_key in suggestions:
                console.print(f"    Edit {stack} stack:       [cyan]{suggestions[stack_key]}[/cyan]")

    def _compare_keybindings(self, app_details: AppDetails, target_keybindings_source: Optional[Path], stacks: List[str] = None) -> None:
        """Compare current keybindings.json with target."""
        console.print("\n[bold yellow]Keybindings.json:[/bold yellow]")

        current_keybindings_file = app_details.config_path / "keybindings.json"
        out_of_sync = False

        if target_keybindings_source:
            if current_keybindings_file.exists():
                current_content = current_keybindings_file.read_text()
                target_content = target_keybindings_source.read_text()

                if current_content.strip() == target_content.strip():
                    console.print("[green]✓ IN SYNC[/green] - Keybindings match target configuration")
                else:
                    console.print("[red]✗ OUT OF SYNC[/red] - Keybindings differ from target configuration")
                    console.print(f"  Target source: {target_keybindings_source}")
                    out_of_sync = True
            else:
                console.print("[red]✗ MISSING[/red] - Target keybindings exist but current file is missing")
                console.print(f"  Target source: {target_keybindings_source}")
                out_of_sync = True
        else:
            if current_keybindings_file.exists():
                console.print("[yellow]⚠ EXTRA[/yellow] - Current keybindings exist but no target configuration")
                out_of_sync = True
            else:
                console.print("[green]✓ IN SYNC[/green] - No keybindings configuration")

        # Show edit suggestions if out of sync
        if out_of_sync:
            self._show_edit_suggestions_for_keybindings(app_details.alias, stacks or [])

    def _show_edit_suggestions_for_keybindings(self, app_alias: str, stacks: List[str]) -> None:
        """Show edit command suggestions for keybindings."""
        suggestions = self._generate_edit_suggestions(app_alias, stacks)
        
        console.print(f"\n  [bold blue]💡 Quick fixes:[/bold blue]")
        console.print(f"    Edit live app config:  [cyan]{suggestions['live_keybindings']}[/cyan]")
        console.print(f"    Edit app layer:        [cyan]{suggestions['app_keybindings']}[/cyan]")
        console.print(f"    Edit base layer:       [cyan]{suggestions['base_keybindings']}[/cyan]")
        
        # Show stack suggestions if available
        for stack in stacks:
            stack_key = f"stack_{stack}_keybindings"
            if stack_key in suggestions:
                console.print(f"    Edit {stack} stack:       [cyan]{suggestions[stack_key]}[/cyan]")

    def _compare_snippets(self, app_details: AppDetails, target_snippets_paths: List[Path], stacks: List[str] = None) -> None:
        """Compare current snippets with target."""
        console.print("\n[bold blue]Snippets:[/bold blue]")

        app_snippets_dir = app_details.config_path / "snippets"
        out_of_sync = False

        if not target_snippets_paths:
            if app_snippets_dir.exists() and list(app_snippets_dir.glob("*.code-snippets")):
                console.print("[yellow]⚠ EXTRA[/yellow] - Current snippets exist but no target configuration")
                out_of_sync = True
            else:
                console.print("[green]✓ IN SYNC[/green] - No snippets configuration")
            if out_of_sync:
                self._show_edit_suggestions_for_snippets(app_details.alias, stacks or [])
            return

        # Collect all target snippet files
        target_snippet_files = {}
        for snippets_path in target_snippets_paths:
            if snippets_path.is_dir():
                for snippet_file in snippets_path.glob("*.code-snippets"):
                    target_snippet_files[snippet_file.name] = snippet_file

        # Check current snippets
        current_snippet_files = {}
        if app_snippets_dir.exists():
            for snippet_file in app_snippets_dir.glob("*.code-snippets"):
                current_snippet_files[snippet_file.name] = snippet_file

        # Compare
        missing_files = set(target_snippet_files.keys()) - set(current_snippet_files.keys())
        extra_files = set(current_snippet_files.keys()) - set(target_snippet_files.keys())
        
        different_files = []
        for filename in set(target_snippet_files.keys()) & set(current_snippet_files.keys()):
            current_content = current_snippet_files[filename].read_text()
            target_content = target_snippet_files[filename].read_text()
            if current_content.strip() != target_content.strip():
                different_files.append(filename)

        if not missing_files and not extra_files and not different_files:
            console.print("[green]✓ IN SYNC[/green] - All snippets match target configuration")
        else:
            console.print("[red]✗ OUT OF SYNC[/red] - Snippets differ from target configuration")
            
            if missing_files:
                console.print(f"  [red]{len(missing_files)} missing files[/red]: {', '.join(sorted(missing_files))}")
            
            if different_files:
                console.print(f"  [yellow]{len(different_files)} modified files[/yellow]: {', '.join(sorted(different_files))}")
            
            if extra_files:
                console.print(f"  [blue]{len(extra_files)} extra files[/blue]: {', '.join(sorted(extra_files))}")
                
            # Show edit suggestions
            self._show_edit_suggestions_for_snippets(app_details.alias, stacks or [])

    def _compare_extensions(self, app_details: AppDetails, target_extensions: List[str], stacks: List[str] = None) -> None:
        """Compare current extensions with target."""
        console.print("\n[bold magenta]Extensions:[/bold magenta]")

        if not target_extensions:
            console.print("[green]✓ IN SYNC[/green] - No extensions configuration")
            return

        try:
            current_extensions = set(AppManager.get_installed_extensions(app_details))
        except ExtensionError as e:
            console.print(f"[red]✗ ERROR[/red] - Cannot check current extensions: {e}")
            return

        target_extensions_set = set(target_extensions)

        missing_extensions = target_extensions_set - current_extensions
        extra_extensions = current_extensions - target_extensions_set
        
        if not missing_extensions and not extra_extensions:
            console.print("[green]✓ IN SYNC[/green] - All extensions match target configuration")
        else:
            console.print("[red]✗ OUT OF SYNC[/red] - Extensions differ from target configuration")
            
            if missing_extensions:
                console.print(f"  [red]{len(missing_extensions)} missing extensions[/red]:")
                for ext in sorted(list(missing_extensions)[:5]):  # Show first 5
                    console.print(f"    - {ext}")
                if len(missing_extensions) > 5:
                    console.print(f"    ... and {len(missing_extensions) - 5} more")
            
            if extra_extensions:
                console.print(f"  [blue]{len(extra_extensions)} extra extensions[/blue]:")
                for ext in sorted(list(extra_extensions)[:5]):  # Show first 5
                    console.print(f"    + {ext}")
                if len(extra_extensions) > 5:
                    console.print(f"    ... and {len(extra_extensions) - 5} more")
                    
            # Show edit suggestions
            self._show_edit_suggestions_for_extensions(app_details.alias, stacks or [])

    def _show_edit_suggestions_for_snippets(self, app_alias: str, stacks: List[str]) -> None:
        """Show edit command suggestions for snippets."""
        suggestions = self._generate_edit_suggestions(app_alias, stacks)
        
        console.print(f"\n  [bold blue]💡 Quick fixes:[/bold blue]")
        console.print(f"    Edit live app snippets: [cyan]{suggestions['live_snippets']}[/cyan]")
        console.print(f"    Edit base snippets:     [cyan]vsc-sync edit base --file-type snippets[/cyan]")
        
        # Show stack suggestions if available
        for stack in stacks:
            console.print(f"    Edit {stack} snippets:     [cyan]vsc-sync edit stack {stack} --file-type snippets[/cyan]")

    def _show_edit_suggestions_for_extensions(self, app_alias: str, stacks: List[str]) -> None:
        """Show edit command suggestions for extensions."""
        suggestions = self._generate_edit_suggestions(app_alias, stacks)
        
        console.print(f"\n  [bold blue]💡 Quick fixes:[/bold blue]")
        console.print(f"    Edit live app config:   [cyan]{suggestions['live_extensions']}[/cyan]")
        console.print(f"    Edit app layer:         [cyan]vsc-sync edit app {app_alias} --file-type extensions[/cyan]")
        console.print(f"    Edit base layer:        [cyan]vsc-sync edit base --file-type extensions[/cyan]")
        
        # Show stack suggestions if available
        for stack in stacks:
            console.print(f"    Edit {stack} stack:        [cyan]vsc-sync edit stack {stack} --file-type extensions[/cyan]")

    def _get_settings_status(self, app_details: AppDetails, target_settings: Dict) -> str:
        """Get settings status for summary table."""
        current_settings_file = app_details.config_path / "settings.json"
        current_settings = FileOperations.read_json_file(current_settings_file)
        
        if current_settings == target_settings:
            return "[green]IN SYNC[/green]"
        else:
            return "[red]OUT OF SYNC[/red]"

    def _get_keybindings_status(self, app_details: AppDetails, target_keybindings_source: Optional[Path]) -> str:
        """Get keybindings status for summary table."""
        current_keybindings_file = app_details.config_path / "keybindings.json"
        
        if target_keybindings_source:
            if current_keybindings_file.exists():
                current_content = current_keybindings_file.read_text()
                target_content = target_keybindings_source.read_text()
                
                if current_content.strip() == target_content.strip():
                    return "[green]IN SYNC[/green]"
                else:
                    return "[red]OUT OF SYNC[/red]"
            else:
                return "[red]MISSING[/red]"
        else:
            if current_keybindings_file.exists():
                return "[yellow]EXTRA[/yellow]"
            else:
                return "[green]IN SYNC[/green]"

    def _get_snippets_status(self, app_details: AppDetails, target_snippets_paths: List[Path]) -> str:
        """Get snippets status for summary table."""
        app_snippets_dir = app_details.config_path / "snippets"
        
        if not target_snippets_paths:
            if app_snippets_dir.exists() and list(app_snippets_dir.glob("*.code-snippets")):
                return "[yellow]EXTRA[/yellow]"
            else:
                return "[green]IN SYNC[/green]"
        
        # Quick check for snippets sync
        target_snippet_files = set()
        for snippets_path in target_snippets_paths:
            if snippets_path.is_dir():
                for snippet_file in snippets_path.glob("*.code-snippets"):
                    target_snippet_files.add(snippet_file.name)
        
        current_snippet_files = set()
        if app_snippets_dir.exists():
            for snippet_file in app_snippets_dir.glob("*.code-snippets"):
                current_snippet_files.add(snippet_file.name)
        
        if target_snippet_files == current_snippet_files:
            return "[green]IN SYNC[/green]"
        else:
            return "[red]OUT OF SYNC[/red]"

    def _get_extensions_status(self, app_details: AppDetails, target_extensions: List[str]) -> str:
        """Get extensions status for summary table."""
        if not target_extensions:
            return "[green]IN SYNC[/green]"
        
        try:
            current_extensions = set(AppManager.get_installed_extensions(app_details))
            target_extensions_set = set(target_extensions)
            
            if current_extensions == target_extensions_set:
                return "[green]IN SYNC[/green]"
            else:
                return "[red]OUT OF SYNC[/red]"
        except ExtensionError:
            return "[yellow]UNKNOWN[/yellow]"