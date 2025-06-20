"""Main CLI application for vsc-sync."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import ConfigManager
from .core.app_manager import AppManager
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
        False, "--verbose", "-v", help="Enable verbose output",
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, help="Show version",
    ),
) -> None:
    """vsc-sync: Synchronize VSCode-like configurations across multiple editors."""
    setup_logging(verbose)


@app.command()
def init(
    repo: Optional[str] = typer.Option(
        None, "--repo", help="Git URL or local path to vscode-configs repository",
    ),
    config_file: Optional[str] = typer.Option(
        None, "--config-file", help="Path to store vsc-sync configuration",
    ),
) -> None:
    """Initialize vsc-sync for first-time use.
    
    This will:
    - Set up your vscode-configs repository
    - Auto-discover VSCode-like applications
    - Create TOML configuration for intelligent layer resolution
    - Enable you to use simple names like 'base', 'python', 'vscode'
    """
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
        ..., help="Path to the app's user configuration directory",
    ),
    executable: Optional[str] = typer.Option(
        None, "--executable", help="Path to the app's executable",
    ),
) -> None:
    """Register a new VSCode-like application."""
    try:
        # TODO: Implement add-app logic
        console.print("[yellow]Add-app functionality coming soon![/yellow]")
        console.print(f"Will register app '{alias}' with config path: {config_path}")
        if executable:
            console.print(f"Executable: {executable}")

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def list_apps(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information",
    ),
) -> None:
    """List all registered applications."""
    try:
        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]",
            )
            raise typer.Exit(1)

        config = config_manager.load_config()

        if not config.managed_apps:
            console.print("No applications registered yet.")
            console.print(
                "Use 'vsc-sync add-app' to register applications or 'vsc-sync init' to auto-discover.",
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
    stack: Optional[List[str]] = typer.Option(
        None, "--stack", help="Tech stack to apply (can be used multiple times)",
    ),
    backup: bool = typer.Option(
        True,
        "--backup/--no-backup",
        help="Create backup before applying (default: enabled)",
    ),
    backup_suffix: Optional[str] = typer.Option(
        None, "--backup-suffix", help="Custom backup suffix",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without applying",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force overwrite without prompting",
    ),

    # Component selection flags (opt-in)
    settings: bool = typer.Option(
        False, "--settings", help="Apply settings.json",
    ),
    keybindings: bool = typer.Option(
        False, "--keybindings", help="Apply keybindings.json",
    ),
    extensions: bool = typer.Option(
        False, "--extensions", help="Manage extensions",
    ),
    snippets: bool = typer.Option(
        False, "--snippets", help="Copy snippets",
    ),
    tasks: bool = typer.Option(
        False, "--tasks", help="Apply tasks.json",
    ),

    # Convenience flags
    all_components: bool = typer.Option(
        False, "--all", help="Apply all components (settings, keybindings, extensions, snippets, tasks)",
    ),
    config_only: bool = typer.Option(
        False, "--config", help="Apply config files only (settings, keybindings, tasks)",
    ),

    # Custom layer flags
    layer: Optional[List[str]] = typer.Option(
        None, "--layer", help="Layer path (file or directory) or alias. Can be used multiple times. First layer is base, subsequent layers stack on top. Later layers take precedence.",
    ),
    
    # Layer preset flag
    preset: Optional[str] = typer.Option(
        None, "--preset", help="Use a predefined layer preset from config.toml",
    ),

    # Extension-specific flags
    remove_extra: bool = typer.Option(
        False, "--remove-extra", help="Remove extensions not in configuration (requires --extensions)",
    ),
    replace_all: bool = typer.Option(
        False, "--replace-all", help="Remove ALL extensions and reinstall from scratch (requires --extensions)",
    ),
) -> None:
    """Apply configurations to an application."""
    try:
        from .commands.apply_cmd import ApplyCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]",
            )
            raise typer.Exit(1)

        # Validate flag combinations
        if all_components and any([settings, keybindings, extensions, snippets, tasks, config_only]):
            console.print(
                "[red]Error:[/red] Cannot use --all with individual component flags",
            )
            raise typer.Exit(1)

        if config_only and any([settings, keybindings, extensions, snippets, tasks, all_components]):
            console.print(
                "[red]Error:[/red] Cannot use --config with other component flags",
            )
            raise typer.Exit(1)

        if (remove_extra or replace_all) and not extensions and not all_components:
            console.print(
                "[red]Error:[/red] --remove-extra and --replace-all require --extensions or --all",
            )
            raise typer.Exit(1)

        # Load TOML config for layer resolution
        from .config_toml import TomlConfigManager
        toml_config_manager = TomlConfigManager()
        
        # Handle layer preset first
        if preset:
            if layer:
                console.print(
                    "[red]Error:[/red] Cannot use --preset with --layer flags. Use either --preset or individual --layer flags.",
                )
                raise typer.Exit(1)
            
            if stack:
                console.print(
                    "[red]Error:[/red] Cannot use --preset with --stack flags. Use either --preset or --stack.",
                )
                raise typer.Exit(1)
            
            # Resolve preset to paths
            preset_paths = toml_config_manager.resolve_layer_preset(preset)
            if preset_paths is None:
                console.print(f"[red]Error:[/red] Layer preset '{preset}' not found in config.toml")
                raise typer.Exit(1)
            
            custom_layers = [(i, path) for i, path in enumerate(preset_paths)]
        else:
            # Collect custom layers from --layer flags
            custom_layers = []
            if layer:
                for i, layer_spec in enumerate(layer):
                    # Use intelligent resolution: name -> alias -> path
                    resolved_path = toml_config_manager.resolve_layer_spec(layer_spec)
                    if resolved_path is not None:
                        custom_layers.append((i, resolved_path))
                    else:
                        # If all resolution strategies fail, still try as literal path
                        # This handles cases where the path doesn't exist yet but user wants to proceed
                        custom_layers.append((i, Path(layer_spec)))

        # Validate custom layers vs stack flags
        if custom_layers and stack:
            console.print(
                "[red]Error:[/red] Cannot use --layer/--preset flags with --stack flags. Use either standard layers (--stack) or custom layers (--layer or --preset).",
            )
            raise typer.Exit(1)

        # Determine which components to include
        if all_components:
            include_settings = True
            include_keybindings = True
            include_extensions = True
            include_snippets = True
            include_tasks = True
        elif config_only:
            include_settings = True
            include_keybindings = True
            include_extensions = False
            include_snippets = False
            include_tasks = True
        else:
            include_settings = settings
            include_keybindings = keybindings
            include_extensions = extensions
            include_snippets = snippets
            include_tasks = tasks

        # Check if at least one component was specified
        if not any([include_settings, include_keybindings, include_extensions, include_snippets, include_tasks]):
            console.print(
                "[red]Error:[/red] No components specified. Use --settings, --keybindings, --extensions, "
                "--snippets, --tasks, --config, or --all",
            )
            raise typer.Exit(1)

        apply_command = ApplyCommand(config_manager)
        apply_command.run(
            app_alias=app_alias,
            stacks=stack,
            custom_layers=custom_layers if custom_layers else None,
            backup=backup,
            backup_suffix=backup_suffix,
            dry_run=dry_run,
            force=force,
            prune_extensions=remove_extra,
            clean_extensions=replace_all,
            tasks=include_tasks,
            include_settings=include_settings,
            include_keybindings=include_keybindings,
            include_extensions=include_extensions,
            include_snippets=include_snippets,
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
        None, help="App alias to check (if not provided, checks all)",
    ),
    stack: Optional[List[str]] = typer.Option(
        None, "--stack", help="Stacks to consider for comparison",
    ),
) -> None:
    """Show configuration status for applications."""
    try:
        from .commands.status_cmd import StatusCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]",
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
        ".", help="Path to the project directory (defaults to current directory)",
    ),
    stack: Optional[List[str]] = typer.Option(
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
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]",
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


# --------------------------------------------------------------------------------------
# PULL COMMAND
# --------------------------------------------------------------------------------------

@app.command(help=(
    "Pull configurations from an application or project into the vscode-configs "
    "repository.  [bold red]⚠ Existing files in the target layer may be overwritten![/bold red]"
))
def pull(
    app_alias: Optional[str] = typer.Argument(
        None,
        help="Alias of the source application (required unless --from-project is used)",
    ),
    layer_type: str = typer.Option(
        ..., "--to", help="Target layer type: base, app, stack, project",
    ),
    layer_name: Optional[str] = typer.Argument(
        None, help="Layer name (required for stack, optional for app/project)",
    ),
    from_project: Optional[str] = typer.Option(
        None,
        "--from-project",
        help="Pull from project .vscode directory instead of app",
    ),
    settings: bool = typer.Option(
        True,
        "--settings/--no-settings",
        help="Include settings.json (default: yes)",
    ),
    keybindings: bool = typer.Option(
        False, "--keybindings", help="Include keybindings.json",
    ),
    extensions: bool = typer.Option(
        False, "--extensions", help="Include extensions list",
    ),
    snippets: bool = typer.Option(
        False, "--snippets", help="Include snippets directory",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="[dangerous] Overwrite existing files without prompting",
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
        False, "--no-pager", help="Disable pager for full preview output",
    ),
) -> None:
    """Pull configurations from an application or project to the repository."""
    try:
        from .commands.pull_cmd import PullCommand

        config_manager = ConfigManager()

        if not config_manager.is_initialized():
            console.print(
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]",
            )
            raise typer.Exit(1)

        # Validate arguments
        if from_project and app_alias:
            console.print(
                "[red]Error:[/red] Cannot specify both app_alias and --from-project",
            )
            raise typer.Exit(1)

        if not from_project and not app_alias:
            console.print(
                "[red]Error:[/red] Must specify either app_alias or --from-project",
            )
            raise typer.Exit(1)

        # Warn about extensions in project mode
        if from_project and extensions:
            console.print(
                "[yellow]Warning:[/yellow] --include-extensions is not available in project mode, ignoring",
            )
            extensions = False

        # Convert from_project to Path if provided
        project_path = Path(from_project) if from_project else None

        pull_command = PullCommand(config_manager)
        pull_command.run(
            app_alias=app_alias,
            layer_type=layer_type,
            layer_name=layer_name,
            project_path=project_path,
            include_settings=settings,
            include_keybindings=keybindings,
            include_extensions=extensions,
            include_snippets=snippets,
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
        ..., help="Layer type: base, app, stack, project, live",
    ),
    layer_name: Optional[str] = typer.Argument(
        None, help="Layer name (not needed for base)",
    ),
    # Mutually-exclusive file-type flags (default: settings)
    settings_flag: bool = typer.Option(
        False, "--settings", help="Edit settings.json",
    ),
    keybindings_flag: bool = typer.Option(
        False, "--keybindings", help="Edit keybindings.json",
    ),
    extensions_flag: bool = typer.Option(
        False, "--extensions", help="Edit extensions.json",
    ),
    snippets_flag: bool = typer.Option(
        False, "--snippets", help="Edit snippets directory",
    ),
    tasks_flag: bool = typer.Option(
        False, "--tasks", help="Edit tasks.json",
    ),
    sort: bool = typer.Option(
        False,
        "--sort",
        help="Sort keybindings.json (only when editing keybindings)",
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
                "[red]vsc-sync is not initialized. Run 'vsc-sync init' first.[/red]",
            )
            raise typer.Exit(1)

        edit_command = EditCommand(config_manager)
        # Determine chosen file type
        flag_map = {
            "settings": settings_flag,
            "keybindings": keybindings_flag,
            "extensions": extensions_flag,
            "snippets": snippets_flag,
            "tasks": tasks_flag,
        }

        chosen = [name for name, val in flag_map.items() if val]

        if len(chosen) > 1:
            console.print("[red]Error:[/red] Please specify only one of --settings/--keybindings/--extensions/--snippets/--tasks")
            raise typer.Exit(1)

        file_type = chosen[0] if chosen else "settings"

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
def config(
    init: bool = typer.Option(
        False, "--init", help="Initialize config.toml with example configuration",
    ),
    show: bool = typer.Option(
        False, "--show", help="Show current configuration",
    ),
    edit: bool = typer.Option(
        False, "--edit", help="Open config.toml in editor",
    ),
    path: bool = typer.Option(
        False, "--path", help="Show path to config.toml file",
    ),
) -> None:
    """Manage vsc-sync configuration file (config.toml)."""
    try:
        from .config_toml import TomlConfigManager
        
        toml_manager = TomlConfigManager()
        
        # Show path
        if path:
            console.print(f"Config file location: [cyan]{toml_manager.config_path}[/cyan]")
            return
        
        # Initialize config
        if init:
            if toml_manager.config_exists():
                console.print(f"[yellow]Config file already exists at {toml_manager.config_path}[/yellow]")
                if not typer.confirm("Overwrite existing config?"):
                    console.print("Cancelled.")
                    return
            
            example_config = toml_manager.create_example_config()
            toml_manager.save_config(example_config)
            console.print(f"[green]✓[/green] Created example config at [cyan]{toml_manager.config_path}[/cyan]")
            console.print("Edit the file to customize layer aliases and presets.")
            return
        
        # Show config
        if show:
            if not toml_manager.config_exists():
                console.print(f"[yellow]No config file found at {toml_manager.config_path}[/yellow]")
                console.print("Use 'vsc-sync config --init' to create one.")
                return
            
            config = toml_manager.load_config()
            
            console.print("[bold]vsc-sync Configuration[/bold]")
            console.print(f"File: [dim]{toml_manager.config_path}[/dim]")
            
            # Show vscode_configs_path
            if config.vscode_configs_path:
                console.print(f"\n[bold]VSCode Configs Path:[/bold]")
                console.print(f"  {config.vscode_configs_path}")
                console.print("  [dim](Used for intelligent layer name resolution)[/dim]")
            
            # Show defaults
            console.print("\n[bold]Defaults:[/bold]")
            console.print(f"  Components: {', '.join(config.defaults.components)}")
            console.print(f"  Backup: {config.defaults.backup}")
            console.print(f"  Extension mode: {config.defaults.extension_mode}")
            
            # Show layer aliases
            if config.layer_aliases:
                console.print("\n[bold]Layer Aliases:[/bold]")
                for name, alias in config.layer_aliases.items():
                    console.print(f"  [cyan]{name}[/cyan]: {alias.path}")
                    if alias.description:
                        console.print(f"    {alias.description}")
            
            # Show layer presets
            if config.layer_presets:
                console.print("\n[bold]Layer Presets:[/bold]")
                for name, layers in config.layer_presets.items():
                    console.print(f"  [cyan]{name}[/cyan]: {', '.join(layers)}")
            
            return
        
        # Edit config
        if edit:
            import subprocess
            import os
            
            if not toml_manager.config_exists():
                console.print(f"[yellow]No config file found at {toml_manager.config_path}[/yellow]")
                if typer.confirm("Create example config first?"):
                    example_config = toml_manager.create_example_config()
                    toml_manager.save_config(example_config)
                else:
                    return
            
            # Try to open in default editor
            editor = os.environ.get("EDITOR", "nano")
            try:
                subprocess.run([editor, str(toml_manager.config_path)], check=True)
            except subprocess.CalledProcessError:
                console.print(f"[red]Failed to open editor '{editor}'[/red]")
                console.print(f"Edit the file manually: {toml_manager.config_path}")
            except FileNotFoundError:
                console.print(f"[red]Editor '{editor}' not found[/red]")
                console.print(f"Edit the file manually: {toml_manager.config_path}")
            
            return
        
        # Default: show help
        console.print("Use one of: --init, --show, --edit, or --path")
        console.print("Example: vsc-sync config --init")

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def discover(
    add_found: bool = typer.Option(
        False, "--add", help="Automatically add discovered apps to configuration",
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
                "\nUse 'vsc-sync discover --add' to automatically add these to your configuration.",
            )
            console.print("Or use 'vsc-sync add-app' to add them individually.")

    except VscSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
