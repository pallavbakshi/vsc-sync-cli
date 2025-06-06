"""Implementation of the init command."""

import logging
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..config import ConfigManager
from ..core.app_manager import AppManager
from ..core.git_ops import GitOperations
from ..exceptions import GitOperationError, VscSyncError
from ..models import AppDetails, VscSyncConfig
from ..utils import resolve_path

logger = logging.getLogger(__name__)
console = Console()


class InitCommand:
    """Handles the initialization process for vsc-sync."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def run(
        self, repo: Optional[str] = None, config_file: Optional[str] = None
    ) -> None:
        """Execute the init command."""
        console.print("[bold blue]Initializing vsc-sync...[/bold blue]")

        # Handle reinitialization
        if self.config_manager.is_initialized():
            console.print("[yellow]vsc-sync is already initialized.[/yellow]")
            if not Confirm.ask(
                "Do you want to reinitialize? This will overwrite your current configuration"
            ):
                console.print("Initialization cancelled.")
                return

        try:
            # Step 1: Set up configuration file path
            config_path = self._setup_config_path(config_file)
            console.print(
                f"Configuration will be stored at: [cyan]{config_path}[/cyan]"
            )

            # Step 2: Set up vscode-configs repository
            vscode_configs_path = self._setup_vscode_configs_repo(repo)

            # Step 3: Auto-discover applications
            managed_apps = self._setup_managed_apps()

            # Step 4: Create and save configuration
            config = VscSyncConfig(
                vscode_configs_path=vscode_configs_path, managed_apps=managed_apps
            )

            # Update config manager with new path if provided
            if config_file:
                self.config_manager.config_path = resolve_path(config_file)

            self.config_manager.save_config(config)

            # Step 5: Success message and next steps
            self._show_success_message(config)

        except Exception as e:
            console.print(f"[red]Initialization failed:[/red] {e}")
            logger.exception("Initialization failed")
            raise VscSyncError(f"Initialization failed: {e}")

    def _setup_config_path(self, config_file: Optional[str]) -> Path:
        """Set up the configuration file path."""
        if config_file:
            return resolve_path(config_file)
        return self.config_manager.config_path

    def _setup_vscode_configs_repo(self, repo: Optional[str]) -> Path:
        """Set up the vscode-configs repository."""
        console.print("\n[bold]Setting up vscode-configs repository...[/bold]")

        if repo:
            return self._handle_repo_argument(repo)
        else:
            return self._prompt_for_repo()

    def _handle_repo_argument(self, repo: str) -> Path:
        """Handle the --repo argument."""
        # Check if it's a URL or local path
        if repo.startswith(("http://", "https://", "git@")):
            return self._clone_repository(repo)
        else:
            return self._verify_local_repo(repo)

    def _clone_repository(self, repo_url: str) -> Path:
        """Clone a remote repository."""
        if not GitOperations.is_git_available():
            raise VscSyncError(
                "Git support is not available. Please install GitPython: pip install gitpython"
            )

        # Default clone location
        default_path = Path.home() / "vscode-configs"

        clone_path = Prompt.ask(
            f"Where should the repository be cloned?", default=str(default_path)
        )

        clone_path = resolve_path(clone_path)

        if clone_path.exists():
            if not Confirm.ask(
                f"Directory {clone_path} already exists. Remove it and clone fresh?"
            ):
                raise VscSyncError("Cannot clone to existing directory")

            import shutil

            shutil.rmtree(clone_path)

        console.print(f"Cloning repository to [cyan]{clone_path}[/cyan]...")

        try:
            GitOperations.clone_repository(repo_url, clone_path)
            console.print("[green]Repository cloned successfully![/green]")
            return clone_path

        except GitOperationError as e:
            raise VscSyncError(f"Failed to clone repository: {e}")

    def _verify_local_repo(self, repo_path: str) -> Path:
        """Verify and use a local repository path."""
        path = resolve_path(repo_path)

        if not path.exists():
            raise VscSyncError(f"Local path does not exist: {path}")

        if not path.is_dir():
            raise VscSyncError(f"Path is not a directory: {path}")

        # Check if it looks like a vscode-configs repository
        expected_dirs = ["base", "apps", "stacks"]
        missing_dirs = [d for d in expected_dirs if not (path / d).exists()]

        if missing_dirs:
            console.print(
                f"[yellow]Warning: Directory structure looks incomplete.[/yellow]"
            )
            console.print(f"Missing directories: {', '.join(missing_dirs)}")

            if not Confirm.ask("Continue anyway?"):
                raise VscSyncError("Repository verification failed")

        console.print(f"Using local repository: [cyan]{path}[/cyan]")
        return path

    def _prompt_for_repo(self) -> Path:
        """Prompt user for repository location."""
        console.print("Please specify your vscode-configs repository:")
        console.print("1. Git URL (will be cloned)")
        console.print("2. Local directory path")
        console.print("3. Create new repository at default location")

        choice = Prompt.ask("Choose an option", choices=["1", "2", "3"], default="3")

        if choice == "1":
            repo_url = Prompt.ask("Enter Git repository URL")
            return self._clone_repository(repo_url)

        elif choice == "2":
            repo_path = Prompt.ask("Enter local directory path")
            return self._verify_local_repo(repo_path)

        else:  # choice == "3"
            return self._create_new_repo()

    def _create_new_repo(self) -> Path:
        """Create a new vscode-configs repository."""
        default_path = Path.home() / "vscode-configs"

        repo_path = Prompt.ask(
            "Where should the new repository be created?", default=str(default_path)
        )

        repo_path = resolve_path(repo_path)

        if repo_path.exists():
            if not Confirm.ask(f"Directory {repo_path} already exists. Use it anyway?"):
                raise VscSyncError("Cannot create repository at existing location")

        console.print(
            f"Creating new repository structure at [cyan]{repo_path}[/cyan]..."
        )

        # Create directory structure
        self._create_repo_structure(repo_path)

        console.print("[green]Repository structure created successfully![/green]")
        console.print(f"[yellow]Tip:[/yellow] Initialize this as a Git repository:")
        console.print(f"  cd {repo_path}")
        console.print(f"  git init")
        console.print(f"  git add .")
        console.print(f'  git commit -m "Initial vscode-configs repository"')

        return repo_path

    def _create_repo_structure(self, repo_path: Path) -> None:
        """Create the basic repository structure."""
        from ..core.file_ops import FileOperations

        # Create directories
        directories = ["base", "apps", "stacks", "projects", "base/snippets"]

        for dir_name in directories:
            dir_path = repo_path / dir_name
            FileOperations.ensure_directory(dir_path)

        # Create basic files
        base_settings = {
            "editor.fontSize": 14,
            "editor.tabSize": 2,
            "editor.insertSpaces": True,
            "files.autoSave": "onFocusChange",
        }

        base_extensions = {"recommendations": []}

        base_keybindings = []

        FileOperations.write_json_file(
            repo_path / "base" / "settings.json", base_settings
        )
        FileOperations.write_json_file(
            repo_path / "base" / "extensions.json", base_extensions
        )
        FileOperations.write_json_file(
            repo_path / "base" / "keybindings.json", base_keybindings
        )

        # Create README
        readme_content = """# VSCode Configurations
        
This repository contains your synchronized VSCode-like editor configurations.

## Structure

- `base/`: Base configurations applied to all editors
- `apps/`: Editor-specific configurations  
- `stacks/`: Technology stack-specific configurations
- `projects/`: Project template configurations

## Usage

Use the `vsc-sync` CLI tool to apply these configurations to your editors.
"""

        (repo_path / "README.md").write_text(readme_content)

    def _setup_managed_apps(self) -> Dict[str, AppDetails]:
        """Set up managed applications through auto-discovery and user interaction."""
        console.print("\n[bold]Discovering VSCode-like applications...[/bold]")

        # Auto-discover applications
        discovered_apps = AppManager.auto_discover_apps()

        if not discovered_apps:
            console.print("No VSCode-like applications found automatically.")
            return self._manually_add_apps({})

        # Show discovered applications
        self._show_discovered_apps(discovered_apps)

        # Let user review and modify the list
        return self._review_discovered_apps(discovered_apps)

    def _show_discovered_apps(self, discovered_apps: Dict[str, AppDetails]) -> None:
        """Display discovered applications in a table."""
        table = Table(title="Discovered Applications")
        table.add_column("Alias", style="cyan")
        table.add_column("Config Path", style="green")
        table.add_column("Executable", style="yellow")
        table.add_column("Status", style="magenta")

        for alias, app_details in discovered_apps.items():
            config_status = "✓" if app_details.config_path.exists() else "✗"
            exec_status = (
                "✓"
                if (
                    app_details.executable_path and app_details.executable_path.exists()
                )
                else "✗"
            )
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

    def _review_discovered_apps(
        self, discovered_apps: Dict[str, AppDetails]
    ) -> Dict[str, AppDetails]:
        """Let user review and modify the discovered applications."""
        console.print("\n[bold]Review discovered applications:[/bold]")

        if not Confirm.ask(
            "Do you want to review each application individually?", default=False
        ):
            # Use all discovered apps as-is
            selected_apps = {
                alias: app
                for alias, app in discovered_apps.items()
                if app.config_path.exists()
            }

            if selected_apps != discovered_apps:
                console.print(
                    "Only including applications with existing config directories."
                )

            return self._maybe_add_more_apps(selected_apps)

        # Review each app individually
        selected_apps = {}

        for alias, app_details in discovered_apps.items():
            console.print(f"\n[cyan]Application: {alias}[/cyan]")
            console.print(f"Config Path: {app_details.config_path}")
            console.print(f"Executable: {app_details.executable_path or 'Not found'}")

            if not app_details.config_path.exists():
                console.print(
                    "[yellow]Warning: Config directory doesn't exist[/yellow]"
                )

            action = Prompt.ask(
                "Action",
                choices=["include", "skip", "modify", "quit"],
                default="include" if app_details.config_path.exists() else "skip",
            )

            if action == "quit":
                break
            elif action == "skip":
                continue
            elif action == "include":
                selected_apps[alias] = app_details
            elif action == "modify":
                modified_app = self._modify_app_details(alias, app_details)
                if modified_app:
                    selected_apps[alias] = modified_app

        return self._maybe_add_more_apps(selected_apps)

    def _modify_app_details(
        self, alias: str, app_details: AppDetails
    ) -> Optional[AppDetails]:
        """Allow user to modify application details."""
        console.print(f"Modifying application: {alias}")

        new_alias = Prompt.ask("Alias", default=alias)
        new_config_path = Prompt.ask(
            "Config Path", default=str(app_details.config_path)
        )
        new_executable = Prompt.ask(
            "Executable Path (press Enter for none)",
            default=(
                str(app_details.executable_path) if app_details.executable_path else ""
            ),
        )

        try:
            config_path = resolve_path(new_config_path)
            executable_path = resolve_path(new_executable) if new_executable else None

            if not AppManager.validate_app_config_path(config_path):
                console.print(
                    "[yellow]Warning: Path doesn't look like a VSCode config directory[/yellow]"
                )
                if not Confirm.ask("Continue anyway?"):
                    return None

            return AppDetails(
                alias=new_alias,
                config_path=config_path,
                executable_path=executable_path,
            )

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def _maybe_add_more_apps(
        self, selected_apps: Dict[str, AppDetails]
    ) -> Dict[str, AppDetails]:
        """Ask if user wants to add more applications manually."""
        if Confirm.ask(
            "Do you want to add any additional applications manually?", default=False
        ):
            return self._manually_add_apps(selected_apps)

        return selected_apps

    def _manually_add_apps(
        self, existing_apps: Dict[str, AppDetails]
    ) -> Dict[str, AppDetails]:
        """Manually add applications."""
        apps = existing_apps.copy()

        while True:
            console.print("\nAdding new application:")

            alias = Prompt.ask("Application alias (e.g., 'my-editor')")

            if alias in apps:
                console.print(f"[red]Alias '{alias}' already exists[/red]")
                continue

            config_path_str = Prompt.ask("Config directory path")
            executable_path_str = Prompt.ask(
                "Executable path (press Enter for none)", default=""
            )

            try:
                config_path = resolve_path(config_path_str)
                executable_path = (
                    resolve_path(executable_path_str) if executable_path_str else None
                )

                if not config_path.exists():
                    console.print(
                        "[yellow]Warning: Config directory doesn't exist[/yellow]"
                    )
                    if not Confirm.ask("Continue anyway?"):
                        continue

                apps[alias] = AppDetails(
                    alias=alias,
                    config_path=config_path,
                    executable_path=executable_path,
                )

                console.print(f"[green]Added application '{alias}'[/green]")

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

            if not Confirm.ask("Add another application?", default=False):
                break

        return apps

    def _show_success_message(self, config: VscSyncConfig) -> None:
        """Show success message and next steps."""
        console.print("\n[bold green]✓ vsc-sync initialization completed![/bold green]")

        console.print(
            f"\n[bold]Configuration saved to:[/bold] [cyan]{self.config_manager.config_path}[/cyan]"
        )
        console.print(
            f"[bold]VSCode configs repository:[/bold] [cyan]{config.vscode_configs_path}[/cyan]"
        )
        console.print(f"[bold]Managed applications:[/bold] {len(config.managed_apps)}")

        if config.managed_apps:
            console.print("\n[bold]Next steps:[/bold]")
            console.print(
                "• Use [cyan]vsc-sync list-apps[/cyan] to see your registered applications"
            )
            console.print(
                "• Use [cyan]vsc-sync apply <app> --stack <stack>[/cyan] to apply configurations"
            )
            console.print(
                "• Use [cyan]vsc-sync discover[/cyan] to find more applications"
            )

            # Show example commands
            first_app = next(iter(config.managed_apps.keys()))
            console.print(f"\n[bold]Example:[/bold]")
            console.print(f"  vsc-sync apply {first_app} --stack python")

        # Advice about version control
        if not self._is_in_dotfiles_location(self.config_manager.config_path):
            console.print(
                f"\n[yellow]Tip:[/yellow] Consider adding your configuration file to version control:"
            )
            console.print(f"  {self.config_manager.config_path}")

    def _is_in_dotfiles_location(self, config_path: Path) -> bool:
        """Check if config path is in a typical dotfiles location."""
        dotfiles_patterns = [".config", ".dotfiles", "dotfiles", ".vsc-sync"]

        for parent in config_path.parents:
            if any(pattern in parent.name for pattern in dotfiles_patterns):
                return True

        return False
