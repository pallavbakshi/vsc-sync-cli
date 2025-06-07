"""Main CLI application for vsc-sync."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import ConfigManager
from .core.app_manager import AppManager
from .core.config_manager import LayerConfigManager
from .exceptions import VscSyncError
from .utils import setup_logging

# Create the main Typer app
app = typer.Typer(
    name="vsc-sync",
    help="Synchronize VSCode-like configurations across multiple editors",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Show version information."""
    if value:
        console.print(f"vsc-sync version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, help="Show version"
    ),
) -> None:
    """vsc-sync: Synchronize VSCode-like configurations across multiple editors."""
    setup_logging(verbose)


@app.command()
def init(
    repo: Optional[str] = typer.Option(
        None, "--repo", help="Git URL or local path to vscode-configs repository"
    ),
    config_file: Optional[str] = typer.Option(
        None, "--config-file", help="Path to store vsc-sync configuration"
    ),
) -> None:
    """Initialize vsc-sync for first-time use."""
    try:
        from .commands.init_cmd import InitCommand

        config_manager = ConfigManager()
        init_command = InitCommand(config_manager)
        init_command.run(repo=repo, config_file=config_file)

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Initialization cancelled by user.[/yellow]")
        raise typer.Exit(1)


@app.command()
def add_app(
    alias: str = typer.Argument(..., help="Unique alias for the application"),
    config_path: str = typer.Argument(
        ..., help="Path to the app's user configuration directory"
    ),
    executable: Optional[str] = typer.Option(
        None, "--executable", help="Path to the app's executable"
    ),
) -> None:
    """Register a new VSCode-like application."""
    try:
        # TODO: Implement add-app logic
        console.print(f"[yellow]Add-app functionality coming soon![/yellow]")
        console.print(f"Will register app '{alias}' with config path: {config_path}")
        if executable:
            console.print(f"Executable: {executable}")

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def list_apps(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information"
    ),
) -> None:
    """List all registered applications."""
    try:
        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]"
            )
            raise typer.Exit(1)

        config = config_manager.load_config()

        if not config.managed_apps:
            console.print("No applications registered yet.")
            console.print(
                "Use 'vsc-sync add-app' to register applications or 'vsc-sync init' to auto-discover."
            )
            return

        table = Table(title="Registered Applications")
        table.add_column("Alias", style="cyan")
        table.add_column("Config Path", style="green")

        if verbose:
            table.add_column("Executable", style="yellow")
            table.add_column("Status", style="magenta")

        for alias, app_details in config.managed_apps.items():
            row = [alias, str(app_details.config_path)]

            if verbose:
                exec_path = (
                    str(app_details.executable_path)
                    if app_details.executable_path
                    else "Not set"
                )
                status = "✓" if app_details.config_path.exists() else "✗"
                row.extend([exec_path, status])

            table.add_row(*row)

        console.print(table)

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def apply(
    app_alias: str = typer.Argument(..., help="Alias of the target application"),
    stack: Optional[list[str]] = typer.Option(
        None, "--stack", help="Tech stack to apply (can be used multiple times)"
    ),
    backup: bool = typer.Option(
        True,
        "--backup/--no-backup",
        help="Create backup before applying (default: enabled)",
    ),
    backup_suffix: Optional[str] = typer.Option(
        None, "--backup-suffix", help="Custom backup suffix"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without applying"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force overwrite without prompting"
    ),
    prune_extensions: bool = typer.Option(
        False, "--prune-extensions", help="Uninstall extensions not in configuration"
    ),
    tasks: bool = typer.Option(
        True, "--tasks/--no-tasks", help="Sync tasks.json (default: yes)"
    ),
) -> None:
    """Apply configurations to an application."""
    try:
        from .commands.apply_cmd import ApplyCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]"
            )
            raise typer.Exit(1)

        apply_command = ApplyCommand(config_manager)
        apply_command.run(
            app_alias=app_alias,
            stacks=stack,
            backup=backup,
            backup_suffix=backup_suffix,
            dry_run=dry_run,
            force=force,
            prune_extensions=prune_extensions,
            tasks=tasks,
        )

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Apply cancelled by user.[/yellow]")
        raise typer.Exit(1)


@app.command()
def status(
    app_alias: Optional[str] = typer.Argument(
        None, help="App alias to check (if not provided, checks all)"
    ),
    stack: Optional[list[str]] = typer.Option(
        None, "--stack", help="Stacks to consider for comparison"
    ),
) -> None:
    """Show configuration status for applications."""
    try:
        from .commands.status_cmd import StatusCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]"
            )
            raise typer.Exit(1)

        status_command = StatusCommand(config_manager)
        status_command.run(app_alias=app_alias, stacks=stack)

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Status check cancelled by user.[/yellow]")
        raise typer.Exit(1)


@app.command()
def setup_project(
    project_path: str = typer.Argument(
        ".", help="Path to the project directory (defaults to current directory)"
    ),
    stack: Optional[list[str]] = typer.Option(
        None,
        "--stack",
        help="Tech stack(s) to use for project setup (can be used multiple times)",
    ),
    from_project_type: Optional[str] = typer.Option(
        None,
        "--from-project-type",
        help="Use predefined project type as base configuration",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .vscode files without prompting",
    ),
) -> None:
    """Set up .vscode/ configuration files for a project."""
    try:
        from pathlib import Path
        from .commands.setup_project_cmd import SetupProjectCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]"
            )
            raise typer.Exit(1)

        setup_command = SetupProjectCommand(config_manager)
        setup_command.run(
            project_path=Path(project_path),
            stacks=stack,
            from_project_type=from_project_type,
            force=force,
        )

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user.[/yellow]")
        raise typer.Exit(1)


@app.command()
def pull(
    app_alias: Optional[str] = typer.Argument(
        None,
        help="Alias of the source application (required unless --from-project is used)",
    ),
    layer_type: str = typer.Option(
        ..., "--to", help="Target layer type: base, app, stack, project"
    ),
    layer_name: Optional[str] = typer.Argument(
        None, help="Layer name (required for stack, optional for app/project)"
    ),
    from_project: Optional[str] = typer.Option(
        None,
        "--from-project",
        help="Pull from project .vscode directory instead of app",
    ),
    include_extensions: bool = typer.Option(
        False,
        "--include-extensions",
        help="Pull installed extensions list (not available for project mode)",
    ),
    include_keybindings: bool = typer.Option(
        False, "--include-keybindings", help="Pull keybindings.json"
    ),
    include_snippets: bool = typer.Option(
        False, "--include-snippets", help="Pull snippets directory"
    ),
    settings_only: bool = typer.Option(
        False,
        "--settings-only",
        help="Only pull settings.json (default if no other flags specified)",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing files without prompting"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be pulled without making changes",
    ),
    full_preview: bool = typer.Option(
        False,
        "--full-preview",
        help="Show full content preview in pager (like git diff)",
    ),
    no_pager: bool = typer.Option(
        False, "--no-pager", help="Disable pager for full preview output"
    ),
) -> None:
    """Pull configurations from an application or project to the repository."""
    try:
        from .commands.pull_cmd import PullCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]"
            )
            raise typer.Exit(1)

        # Validate arguments
        if from_project and app_alias:
            console.print(
                "[red]Error:[/red] Cannot specify both app_alias and --from-project"
            )
            raise typer.Exit(1)

        if not from_project and not app_alias:
            console.print(
                "[red]Error:[/red] Must specify either app_alias or --from-project"
            )
            raise typer.Exit(1)

        # Warn about extensions in project mode
        if from_project and include_extensions:
            console.print(
                "[yellow]Warning:[/yellow] --include-extensions is not available in project mode, ignoring"
            )
            include_extensions = False

        # Convert from_project to Path if provided
        project_path = Path(from_project) if from_project else None

        pull_command = PullCommand(config_manager)
        pull_command.run(
            app_alias=app_alias,
            layer_type=layer_type,
            layer_name=layer_name,
            project_path=project_path,
            include_extensions=include_extensions,
            include_keybindings=include_keybindings,
            include_snippets=include_snippets,
            settings_only=settings_only,
            overwrite=overwrite,
            dry_run=dry_run,
            full_preview=full_preview,
            no_pager=no_pager,
        )

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Pull cancelled by user.[/yellow]")
        raise typer.Exit(1)


@app.command()
def edit(
    layer_type: str = typer.Argument(
        ..., help="Layer type: base, app, stack, project, live"
    ),
    layer_name: Optional[str] = typer.Argument(
        None, help="Layer name (not needed for base)"
    ),
    file_type: str = typer.Option(
        "settings",
        "--file-type",
        "-t",
        help="File type: settings, keybindings, extensions, snippets",
    ),
    sort: bool = typer.Option(
        False,
        "--sort",
        help="Sort keybindings.json (only valid when --file-type keybindings)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Assume yes for overwrite confirmation while sorting",
    ),
) -> None:
    """Open configuration files for editing."""
    try:
        from .commands.edit_cmd import EditCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]"
            )
            raise typer.Exit(1)

        edit_command = EditCommand(config_manager)
        edit_command.run(
            layer_type=layer_type,
            layer_name=layer_name,
            file_type=file_type,
            sort=sort,
            yes=yes,
        )

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Edit cancelled by user.[/yellow]")
        raise typer.Exit(1)


@app.command()
def discover(
    add_found: bool = typer.Option(
        False, "--add", help="Automatically add discovered apps to configuration"
    ),
) -> None:
    """Discover VSCode-like applications on the system."""
    try:
        console.print("Discovering VSCode-like applications...")

        discovered_apps = AppManager.auto_discover_apps()

        if not discovered_apps:
            console.print("No VSCode-like applications found.")
            return

        table = Table(title="Discovered Applications")
        table.add_column("Alias", style="cyan")
        table.add_column("Config Path", style="green")
        table.add_column("Executable", style="yellow")
        table.add_column("Status", style="magenta")

        for alias, app_details in discovered_apps.items():
            exec_status = (
                "✓"
                if (
                    app_details.executable_path and app_details.executable_path.exists()
                )
                else "✗"
            )
            config_status = "✓" if app_details.config_path.exists() else "✗"
            status = f"Config: {config_status} | Exec: {exec_status}"

            table.add_row(
                alias,
                str(app_details.config_path),
                (
                    str(app_details.executable_path)
                    if app_details.executable_path
                    else "Not found"
                ),
                status,
            )

        console.print(table)

        if add_found:
            console.print("[yellow]Auto-add functionality coming soon![/yellow]")
        else:
            console.print(
                "\nUse 'vsc-sync discover --add' to automatically add these to your configuration."
            )
            console.print("Or use 'vsc-sync add-app' to add them individually.")

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
