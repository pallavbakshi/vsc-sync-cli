"""Implementation of the pull command."""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from vsc_sync.config import ConfigManager
from vsc_sync.core.app_manager import AppManager
from vsc_sync.core.file_ops import FileOperations
from vsc_sync.exceptions import AppConfigPathError, ExtensionError, VscSyncError
from vsc_sync.models import AppDetails

logger = logging.getLogger(__name__)
console = Console()


class PullCommand:
    """Handles pulling configurations from VSCode-like applications to the repository."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.load_config()

    def run(
        self,
        app_alias: Optional[str] = None,
        layer_type: Optional[str] = None,
        layer_name: Optional[str] = None,
        project_path: Optional[Path] = None,
        include_settings: bool = True,
        include_keybindings: bool = False,
        include_extensions: bool = False,
        include_snippets: bool = False,
        overwrite: bool = False,
        dry_run: bool = False,
        full_preview: bool = False,
        no_pager: bool = False,
    ) -> None:
        """Execute the pull command."""
        try:
            # Determine pull mode: app or project
            if project_path:
                # Project mode: pull from .vscode directory
                source_name = project_path.name
                console.print(
                    f"[bold blue]Pulling configuration from project {source_name}...[/bold blue]",
                )

                # Step 1: Validate project and get details
                source_details = self._validate_project(project_path)

                # Step 2: Resolve target layer path for project
                if not layer_type:
                    raise VscSyncError(
                        "--to layer_type is required for project pulling"
                    )
                target_layer_path = self._resolve_target_layer_path(
                    layer_type, layer_name, source_name
                )
            else:
                # App mode: pull from app user directory
                if not app_alias:
                    raise VscSyncError(
                        "app_alias is required when not pulling from a project"
                    )
                if not layer_type:
                    raise VscSyncError("--to layer_type is required")

                console.print(
                    f"[bold blue]Pulling configuration from {app_alias}...[/bold blue]",
                )

                # Step 1: Validate app and get details
                source_details = self._validate_app(app_alias)

                # Step 2: Validate and resolve layer information
                target_layer_path = self._resolve_target_layer_path(
                    layer_type, layer_name, app_alias
                )

            pull_settings = include_settings

            # Step 4: Show what will be pulled
            self._show_pull_summary(
                source_details,
                target_layer_path,
                pull_settings,
                include_extensions,
                include_keybindings,
                include_snippets,
            )

            if dry_run:
                # Step 5a: Dry run - show what would be pulled
                self._show_dry_run_results(
                    source_details,
                target_layer_path,
                pull_settings,
                include_extensions,
                include_keybindings,
                include_snippets,
                    full_preview,
                    no_pager,
                )
            else:
                # Step 5b: Actually pull configurations
                if not overwrite and not self._confirm_pull(
                    source_details, target_layer_path
                ):
                    console.print("[yellow]Pull cancelled by user.[/yellow]")
                    return

                self._pull_configurations(
                    source_details,
                    target_layer_path,
                    pull_settings,
                    include_extensions,
                    include_keybindings,
                    include_snippets,
                    overwrite,
                )
                self._show_success_message(source_details, target_layer_path)

        except Exception as e:
            console.print(f"[red]Pull failed:[/red] {e}")
            logger.exception("Pull command failed")
            raise VscSyncError(f"Pull failed: {e}")

    def _validate_app(self, app_alias: str) -> AppDetails:
        """Validate that the app exists and is properly configured."""
        if app_alias not in self.config.managed_apps:
            available_apps = list(self.config.managed_apps.keys())
            raise VscSyncError(
                f"App '{app_alias}' is not registered. "
                f"Available apps: {', '.join(available_apps) if available_apps else 'none'}",
            )

        app_details = self.config.managed_apps[app_alias]

        if not app_details.config_path.exists():
            raise AppConfigPathError(
                f"App config directory does not exist: {app_details.config_path}",
            )

        return app_details

    def _validate_project(self, project_path: Path) -> AppDetails:
        """Validate that the project has a .vscode directory and return details."""
        if not project_path.exists():
            raise VscSyncError(f"Project directory does not exist: {project_path}")

        if not project_path.is_dir():
            raise VscSyncError(f"Project path is not a directory: {project_path}")

        vscode_dir = project_path / ".vscode"
        if not vscode_dir.exists():
            raise VscSyncError(
                f"Project does not have a .vscode directory: {vscode_dir}"
            )

        if not vscode_dir.is_dir():
            raise VscSyncError(f".vscode path is not a directory: {vscode_dir}")

        # Create a pseudo AppDetails for the project
        # Note: For projects, we don't have an executable_path since it's not an app
        return AppDetails(
            alias=project_path.name,
            config_path=vscode_dir,
            executable_path=None,
        )

    def _resolve_target_layer_path(
        self, layer_type: str, layer_name: Optional[str], source_name: str
    ) -> Path:
        """Resolve the target path in the vscode-configs repository."""
        valid_layer_types = ["base", "app", "stack", "project"]
        if layer_type not in valid_layer_types:
            raise VscSyncError(
                f"Invalid layer type '{layer_type}'. Must be one of: {', '.join(valid_layer_types)}",
            )

        vscode_configs_path = self.config.vscode_configs_path
        if not vscode_configs_path.exists():
            raise VscSyncError(
                f"vscode-configs repository not found at: {vscode_configs_path}"
            )

        if layer_type == "base":
            target_path = vscode_configs_path / "base"
        elif layer_type == "app":
            # Use source_name if layer_name is not provided
            name = layer_name or source_name
            target_path = vscode_configs_path / "apps" / name
        elif layer_type == "stack":
            if not layer_name:
                raise VscSyncError("Layer name is required for stack layer type")
            target_path = vscode_configs_path / "stacks" / layer_name
        elif layer_type == "project":
            # Use source_name if layer_name is not provided
            name = layer_name or source_name
            target_path = vscode_configs_path / "projects" / name

        # Ensure target directory exists
        if not target_path.exists():
            console.print(f"[yellow]Creating target directory:[/yellow] {target_path}")
            target_path.mkdir(parents=True, exist_ok=True)

        return target_path

    def _show_content_with_pager(
        self, content: str, title: str, use_pager: bool = True
    ) -> None:
        """Display content using a pager (like git diff) or direct output."""
        if not use_pager:
            # Direct output without pager
            console.print(f"\n[bold]{title}:[/bold]")
            console.print(Syntax(content, "json", line_numbers=True, theme="monokai"))
            return

        # Try to use system pager
        pager_cmd = os.environ.get("PAGER", "less")

        try:
            # Create temporary file with content
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            # Set up pager command
            if pager_cmd == "less":
                # Use less with good defaults for JSON
                cmd = ["less", "-R", "-S", "-F", "-X", tmp_file_path]
            else:
                cmd = [pager_cmd, tmp_file_path]

            console.print(f"\n[bold]{title}:[/bold]")
            console.print(f"[dim]Opening in pager... (Press 'q' to quit)[/dim]")

            # Run pager
            subprocess.run(cmd, check=False)

        except (subprocess.SubprocessError, FileNotFoundError):
            # Fallback to direct output if pager fails
            console.print(f"\n[yellow]Pager not available, showing directly:[/yellow]")
            console.print(f"\n[bold]{title}:[/bold]")
            console.print(Syntax(content, "json", line_numbers=True, theme="monokai"))
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except:
                pass

    def _prompt_for_full_content(self, content_type: str = "content") -> str:
        """Prompt user for how they want to see full content."""
        console.print(
            f"\n[yellow]Content truncated. Show full {content_type}?[/yellow]"
        )
        console.print("[dim]Options: y=pager, n=no, d=direct (no pager)[/dim]")

        try:
            import typer

            response = typer.prompt("Choice", default="n", show_default=False)
            response_lower = response.lower().strip()

            if response_lower in ["y", "yes"]:
                return "pager"
            elif response_lower in ["d", "direct"]:
                return "direct"
            else:
                return "no"
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Skipping full content display[/yellow]")
            return "no"

    def _show_pull_summary(
        self,
        app_details: AppDetails,
        target_layer_path: Path,
        pull_settings: bool,
        include_extensions: bool,
        include_keybindings: bool,
        include_snippets: bool,
    ) -> None:
        """Show a summary of what will be pulled."""
        console.print("\n[bold]Pull configuration summary:[/bold]")

        table = Table()
        table.add_column("Source", style="cyan")
        table.add_column("Target", style="green")
        table.add_column("Components", style="yellow")

        components = []
        if pull_settings:
            components.append("settings.json")
        if include_keybindings:
            components.append("keybindings.json")
        if include_snippets:
            components.append("snippets/")
        if include_extensions:
            components.append("extensions.json")

        table.add_row(
            str(app_details.config_path),
            str(target_layer_path),
            ", ".join(components) if components else "settings.json (default)",
        )

        console.print(table)

    def _show_dry_run_results(
        self,
        app_details: AppDetails,
        target_layer_path: Path,
        pull_settings: bool,
        include_extensions: bool,
        include_keybindings: bool,
        include_snippets: bool,
        full_preview: bool,
        no_pager: bool,
    ) -> None:
        """Show what would be pulled in a dry run."""
        console.print("\n[bold yellow]DRY RUN - No changes will be made[/bold yellow]")

        # Show settings.json changes
        if pull_settings:
            self._show_settings_pull_preview(
                app_details, target_layer_path, full_preview, no_pager
            )

        # Show keybindings.json changes
        if include_keybindings:
            self._show_keybindings_pull_preview(
                app_details, target_layer_path, full_preview, no_pager
            )

        # Show snippets changes
        if include_snippets:
            self._show_snippets_pull_preview(
                app_details, target_layer_path, full_preview, no_pager
            )

        # Show extensions changes
        if include_extensions:
            self._show_extensions_pull_preview(
                app_details, target_layer_path, full_preview, no_pager
            )

    def _show_settings_pull_preview(
        self,
        app_details: AppDetails,
        target_layer_path: Path,
        full_preview: bool = False,
        no_pager: bool = False,
    ) -> None:
        """Show preview of settings.json pull."""
        console.print("\n[bold]Settings.json pull preview:[/bold]")

        source_settings_file = app_details.config_path / "settings.json"
        target_settings_file = target_layer_path / "settings.json"

        if not source_settings_file.exists():
            console.print(
                "[yellow]Source settings.json does not exist - nothing to pull[/yellow]"
            )
            return

        source_settings = FileOperations.read_json_file(source_settings_file)

        if target_settings_file.exists():
            target_settings = FileOperations.read_json_file(target_settings_file)
            if source_settings == target_settings:
                console.print(
                    "[green]No changes needed - settings are identical[/green]"
                )
                return
            console.print(
                f"[yellow]Will overwrite existing settings.json in:[/yellow] {target_layer_path}"
            )
        else:
            console.print(
                f"[green]Will create new settings.json in:[/green] {target_layer_path}"
            )

        # Show content preview based on options
        settings_json = json.dumps(source_settings, indent=2, sort_keys=True)

        if full_preview:
            # Show full content with pager (unless disabled)
            self._show_content_with_pager(
                settings_json, "Full settings.json content", use_pager=not no_pager
            )
        else:
            # Show truncated preview with option to expand
            console.print("\n[dim]Content preview:[/dim]")
            if len(settings_json) > 500:
                console.print(
                    Syntax(
                        settings_json[:500] + "...",
                        "json",
                        line_numbers=False,
                        theme="monokai",
                    )
                )

                # Interactive prompt for full content
                choice = self._prompt_for_full_content("settings.json content")
                if choice == "pager":
                    self._show_content_with_pager(
                        settings_json, "Full settings.json content", use_pager=True
                    )
                elif choice == "direct":
                    self._show_content_with_pager(
                        settings_json, "Full settings.json content", use_pager=False
                    )
            else:
                # Content is short enough, show it all
                console.print(
                    Syntax(settings_json, "json", line_numbers=False, theme="monokai")
                )

    def _show_keybindings_pull_preview(
        self,
        app_details: AppDetails,
        target_layer_path: Path,
        full_preview: bool = False,
        no_pager: bool = False,
    ) -> None:
        """Show preview of keybindings.json pull."""
        console.print("\n[bold]Keybindings.json pull preview:[/bold]")

        source_keybindings_file = app_details.config_path / "keybindings.json"
        target_keybindings_file = target_layer_path / "keybindings.json"

        if not source_keybindings_file.exists():
            console.print(
                "[yellow]Source keybindings.json does not exist - nothing to pull[/yellow]"
            )
            return

        if target_keybindings_file.exists():
            console.print(
                f"[yellow]Will overwrite existing keybindings.json in:[/yellow] {target_layer_path}"
            )
        else:
            console.print(
                f"[green]Will create new keybindings.json in:[/green] {target_layer_path}"
            )

        # Show content preview for keybindings if requested
        if full_preview:
            try:
                keybindings_content = source_keybindings_file.read_text()
                self._show_content_with_pager(
                    keybindings_content,
                    "Full keybindings.json content",
                    use_pager=not no_pager,
                )
            except Exception as e:
                console.print(f"[red]Error reading keybindings file:[/red] {e}")
        else:
            # For keybindings, we could show a summary or offer to show full content
            try:
                keybindings_content = source_keybindings_file.read_text()
                if len(keybindings_content) > 200:
                    console.print(
                        f"[dim]Keybindings file size: {len(keybindings_content)} characters[/dim]"
                    )
                    choice = self._prompt_for_full_content("keybindings.json content")
                    if choice == "pager":
                        self._show_content_with_pager(
                            keybindings_content,
                            "Full keybindings.json content",
                            use_pager=True,
                        )
                    elif choice == "direct":
                        self._show_content_with_pager(
                            keybindings_content,
                            "Full keybindings.json content",
                            use_pager=False,
                        )
                else:
                    console.print(
                        Syntax(
                            keybindings_content,
                            "json",
                            line_numbers=False,
                            theme="monokai",
                        )
                    )
            except Exception:
                console.print("[dim]Unable to preview keybindings content[/dim]")

    def _show_snippets_pull_preview(
        self,
        app_details: AppDetails,
        target_layer_path: Path,
        full_preview: bool = False,
        no_pager: bool = False,
    ) -> None:
        """Show preview of snippets pull."""
        console.print("\n[bold]Snippets pull preview:[/bold]")

        source_snippets_dir = app_details.config_path / "snippets"
        target_snippets_dir = target_layer_path / "snippets"

        if not source_snippets_dir.exists():
            console.print(
                "[yellow]Source snippets directory does not exist - nothing to pull[/yellow]"
            )
            return

        snippet_files = list(source_snippets_dir.glob("*.code-snippets"))
        if not snippet_files:
            console.print("[yellow]No snippet files found in source directory[/yellow]")
            return

        console.print(
            f"[green]Will copy {len(snippet_files)} snippet files to:[/green] {target_snippets_dir}"
        )
        for snippet_file in snippet_files:
            target_file = target_snippets_dir / snippet_file.name
            status = "overwrite" if target_file.exists() else "create"
            console.print(
                f"  [{('yellow' if status == 'overwrite' else 'green')}]{status}:[/{('yellow' if status == 'overwrite' else 'green')}] {snippet_file.name}"
            )

        # Show snippet content preview if requested
        if full_preview and snippet_files:
            # Show all snippet files in pager
            combined_content = ""
            for snippet_file in snippet_files:
                try:
                    content = snippet_file.read_text()
                    combined_content += f"=== {snippet_file.name} ===\n{content}\n\n"
                except Exception:
                    combined_content += (
                        f"=== {snippet_file.name} ===\n[Error reading file]\n\n"
                    )

            self._show_content_with_pager(
                combined_content, "All snippet files content", use_pager=not no_pager
            )
        elif not full_preview and len(snippet_files) > 0:
            # Offer to show snippet content
            choice = self._prompt_for_full_content("snippet files content")
            if choice != "no":
                combined_content = ""
                for snippet_file in snippet_files:
                    try:
                        content = snippet_file.read_text()
                        combined_content += (
                            f"=== {snippet_file.name} ===\n{content}\n\n"
                        )
                    except Exception:
                        combined_content += (
                            f"=== {snippet_file.name} ===\n[Error reading file]\n\n"
                        )

                use_pager = choice == "pager"
                self._show_content_with_pager(
                    combined_content, "All snippet files content", use_pager=use_pager
                )

    def _show_extensions_pull_preview(
        self,
        app_details: AppDetails,
        target_layer_path: Path,
        full_preview: bool = False,
        no_pager: bool = False,
    ) -> None:
        """Show preview of extensions pull."""
        console.print("\n[bold]Extensions pull preview:[/bold]")

        if not app_details.executable_path:
            console.print(
                "[red]No executable path configured - cannot pull extensions[/red]"
            )
            return

        try:
            extensions = AppManager.get_installed_extensions(app_details)
        except ExtensionError as e:
            console.print(f"[red]Cannot get installed extensions:[/red] {e}")
            return

        if not extensions:
            console.print("[yellow]No extensions installed - nothing to pull[/yellow]")
            return

        target_extensions_file = target_layer_path / "extensions.json"
        status = "overwrite" if target_extensions_file.exists() else "create"

        console.print(
            f"[green]Will {status} extensions.json with {len(extensions)} extensions in:[/green] {target_layer_path}"
        )

        # Show extensions preview
        if full_preview:
            # Show full extensions list in pager
            extensions_content = json.dumps(
                {"recommendations": sorted(extensions)}, indent=2
            )
            self._show_content_with_pager(
                extensions_content,
                "Full extensions.json content",
                use_pager=not no_pager,
            )
        else:
            # Show a preview of extensions
            console.print("\n[dim]Extensions to be saved:[/dim]")
            preview_count = min(10, len(extensions))
            for ext in sorted(extensions[:preview_count]):
                console.print(f"  • {ext}")

            if len(extensions) > preview_count:
                console.print(f"  ... and {len(extensions) - preview_count} more")

                # Offer to show all extensions
                choice = self._prompt_for_full_content("complete extensions list")
                if choice != "no":
                    extensions_content = json.dumps(
                        {"recommendations": sorted(extensions)}, indent=2
                    )
                    use_pager = choice == "pager"
                    self._show_content_with_pager(
                        extensions_content,
                        "Full extensions.json content",
                        use_pager=use_pager,
                    )

    def _confirm_pull(self, app_details: AppDetails, target_layer_path: Path) -> bool:
        """Ask user to confirm pulling changes."""
        console.print(
            f"\n[bold]Ready to pull configuration from {app_details.alias}[/bold]",
        )
        console.print(f"Source directory: [cyan]{app_details.config_path}[/cyan]")
        console.print(f"Target directory: [cyan]{target_layer_path}[/cyan]")

        return Confirm.ask("Proceed with pulling configuration?", default=True)

    def _pull_configurations(
        self,
        app_details: AppDetails,
        target_layer_path: Path,
        pull_settings: bool,
        include_extensions: bool,
        include_keybindings: bool,
        include_snippets: bool,
        overwrite: bool,
    ) -> None:
        """Actually pull the configurations."""
        console.print("\n[bold]Pulling configurations...[/bold]")

        # Pull settings.json
        if pull_settings:
            self._pull_settings(app_details, target_layer_path, overwrite=overwrite)

        # Pull keybindings.json
        if include_keybindings:
            self._pull_keybindings(app_details, target_layer_path, overwrite=overwrite)

        # Pull snippets
        if include_snippets:
            self._pull_snippets(app_details, target_layer_path, overwrite=overwrite)

        # Pull extensions
        if include_extensions:
            self._pull_extensions(app_details, target_layer_path, overwrite=overwrite)

    def _pull_settings(
        self, app_details: AppDetails, target_layer_path: Path, *, overwrite: bool
    ) -> None:
        """Pull settings.json from app to repository."""
        source_file = app_details.config_path / "settings.json"
        target_file = target_layer_path / "settings.json"

        if not source_file.exists():
            console.print(
                "[yellow]Source settings.json does not exist - skipping[/yellow]"
            )
            return

        if (
            target_file.exists()
            and not overwrite
            and not Confirm.ask(
                f"Overwrite existing settings.json in {target_layer_path}?",
                default=False,
            )
        ):
            console.print(
                "[yellow]Skipping settings.json (user declined overwrite)[/yellow]"
            )
            return

        console.print("[cyan]Pulling settings.json...[/cyan]")
        FileOperations.copy_file(source_file, target_file)
        console.print("[green]✓[/green] Settings.json pulled")

    def _pull_keybindings(
        self, app_details: AppDetails, target_layer_path: Path, *, overwrite: bool
    ) -> None:
        """Pull keybindings.json from app to repository."""
        source_file = app_details.config_path / "keybindings.json"
        target_file = target_layer_path / "keybindings.json"

        if not source_file.exists():
            console.print(
                "[yellow]Source keybindings.json does not exist - skipping[/yellow]"
            )
            return

        if (
            target_file.exists()
            and not overwrite
            and not Confirm.ask(
                f"Overwrite existing keybindings.json in {target_layer_path}?",
                default=False,
            )
        ):
            console.print(
                "[yellow]Skipping keybindings.json (user declined overwrite)[/yellow]"
            )
            return

        console.print("[cyan]Pulling keybindings.json...[/cyan]")
        FileOperations.copy_file(source_file, target_file)
        console.print("[green]✓[/green] Keybindings.json pulled")

    def _pull_snippets(
        self, app_details: AppDetails, target_layer_path: Path, *, overwrite: bool
    ) -> None:
        """Pull snippets directory from app to repository."""
        source_dir = app_details.config_path / "snippets"
        target_dir = target_layer_path / "snippets"

        if not source_dir.exists():
            console.print(
                "[yellow]Source snippets directory does not exist - skipping[/yellow]"
            )
            return

        snippet_files = list(source_dir.glob("*.code-snippets"))
        if not snippet_files:
            console.print(
                "[yellow]No snippet files found in source directory - skipping[/yellow]"
            )
            return

        if (
            target_dir.exists()
            and not overwrite
            and not Confirm.ask(
                f"Overwrite existing snippets in {target_layer_path}?", default=False
            )
        ):
            console.print(
                "[yellow]Skipping snippets (user declined overwrite)[/yellow]"
            )
            return

        console.print("[cyan]Pulling snippets...[/cyan]")
        FileOperations.ensure_directory(target_dir)
        FileOperations.copy_directory_contents(
            source_dir, target_dir, overwrite_existing=True
        )

        # Count copied files
        copied_files = len(list(target_dir.glob("*.code-snippets")))
        console.print(f"[green]✓[/green] {copied_files} snippet files pulled")

    def _pull_extensions(
        self, app_details: AppDetails, target_layer_path: Path, *, overwrite: bool
    ) -> None:
        """Pull extensions list from app to repository."""
        target_file = target_layer_path / "extensions.json"

        if not app_details.executable_path:
            console.print(
                "[yellow]No executable path configured - skipping extensions[/yellow]"
            )
            return

        try:
            extensions = AppManager.get_installed_extensions(app_details)
        except ExtensionError as e:
            console.print(f"[red]Cannot get installed extensions:[/red] {e}")
            return

        if not extensions:
            console.print("[yellow]No extensions installed - skipping[/yellow]")
            return

        if (
            target_file.exists()
            and not overwrite
            and not Confirm.ask(
                f"Overwrite existing extensions.json in {target_layer_path}?",
                default=False,
            )
        ):
            console.print(
                "[yellow]Skipping extensions.json (user declined overwrite)[/yellow]"
            )
            return

        console.print("[cyan]Pulling extensions list...[/cyan]")

        extensions_data = {
            "recommendations": sorted(extensions),
        }

        FileOperations.write_json_file(target_file, extensions_data)
        console.print(f"[green]✓[/green] {len(extensions)} extensions pulled")

    def _show_success_message(
        self, app_details: AppDetails, target_layer_path: Path
    ) -> None:
        """Show success message after pulling configurations."""
        console.print(
            f"\n[bold green]✓ Configuration successfully pulled from {app_details.alias}![/bold green]",
        )
        console.print(f"Source: [cyan]{app_details.config_path}[/cyan]")
        console.print(f"Target: [cyan]{target_layer_path}[/cyan]")

        console.print(
            "\n[yellow]Next steps:[/yellow]",
        )
        console.print("1. Review the pulled configuration files")
        console.print("2. Commit and push changes to your vscode-configs repository")
        console.print(
            "3. Use [cyan]vsc-sync apply[/cyan] to apply configurations to other apps"
        )
