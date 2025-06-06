"""Tests for the init command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from vsc_sync.commands.init_cmd import InitCommand
from vsc_sync.config import ConfigManager
from vsc_sync.exceptions import VscSyncError
from vsc_sync.models import AppDetails, VscSyncConfig


class TestInitCommand:
    """Test class for InitCommand functionality."""

    def test_init_command_creation(self, mock_config_manager):
        """Test creating an InitCommand instance."""
        init_cmd = InitCommand(mock_config_manager)
        assert init_cmd.config_manager == mock_config_manager

    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    def test_run_already_initialized_cancel(self, mock_confirm, temp_dir):
        """Test running init when already initialized and user cancels."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Create existing config to simulate initialized state
        config = VscSyncConfig(
            vscode_configs_path=temp_dir / "vscode-configs", managed_apps={}
        )
        config_manager.save_config(config)

        mock_confirm.return_value = False  # User cancels

        init_cmd = InitCommand(config_manager)

        # Should not raise exception, just return early
        init_cmd.run()

        # Config should remain unchanged
        loaded_config = config_manager.load_config()
        assert loaded_config.vscode_configs_path == temp_dir / "vscode-configs"

    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    @patch("vsc_sync.commands.init_cmd.Prompt.ask")
    @patch("vsc_sync.commands.init_cmd.AppManager.auto_discover_apps")
    def test_run_create_new_repo(
        self, mock_discover, mock_prompt, mock_confirm, temp_dir
    ):
        """Test running init with creating a new repository."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Mock user interactions
        mock_prompt.side_effect = [
            "3",  # Choose option 3 (create new repo)
            str(temp_dir / "new-vscode-configs"),  # Repository path
        ]
        mock_confirm.side_effect = [
            False,  # Don't review apps individually  
            False,  # Don't add more apps manually
            False,  # Additional confirm for any other prompts
        ]
        # Mock discovered apps to avoid forced manual addition
        mock_discover.return_value = {
            "vscode": AppDetails(
                alias="vscode",
                config_path=temp_dir / "vscode_config",
                executable_path=Path("/usr/bin/code"),
            )
        }

        init_cmd = InitCommand(config_manager)
        init_cmd.run()

        # Check that config was created
        assert config_manager.config_path.exists()
        config = config_manager.load_config()
        # Use resolve() to handle /private/var vs /var differences on macOS
        assert config.vscode_configs_path.resolve() == (temp_dir / "new-vscode-configs").resolve()

        # Check that repository structure was created
        repo_path = temp_dir / "new-vscode-configs"
        assert (repo_path / "base").exists()
        assert (repo_path / "apps").exists()
        assert (repo_path / "stacks").exists()
        assert (repo_path / "projects").exists()
        assert (repo_path / "base" / "settings.json").exists()
        assert (repo_path / "base" / "extensions.json").exists()
        assert (repo_path / "base" / "keybindings.json").exists()
        assert (repo_path / "README.md").exists()

    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    @patch("vsc_sync.commands.init_cmd.Prompt.ask")
    @patch("vsc_sync.commands.init_cmd.AppManager.auto_discover_apps")
    def test_run_local_repo(
        self,
        mock_discover,
        mock_prompt,
        mock_confirm,
        temp_dir,
        mock_vscode_configs_repo,
    ):
        """Test running init with existing local repository."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Mock user interactions
        mock_prompt.side_effect = [
            "2",  # Choose option 2 (local directory)
            str(mock_vscode_configs_repo),  # Repository path
        ]
        mock_confirm.side_effect = [
            False,  # Don't review apps individually
            False,  # Don't add more apps manually
            False,  # Additional confirm for any other prompts
        ]
        # Mock discovered apps to avoid forced manual addition  
        mock_discover.return_value = {
            "cursor": AppDetails(
                alias="cursor",
                config_path=temp_dir / "cursor_config", 
                executable_path=Path("/usr/bin/cursor"),
            )
        }

        init_cmd = InitCommand(config_manager)
        init_cmd.run()

        # Check that config was created with correct repo path
        config = config_manager.load_config()
        # Use resolve() to handle /private/var vs /var differences on macOS
        assert config.vscode_configs_path.resolve() == mock_vscode_configs_repo.resolve()

    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    @patch("vsc_sync.commands.init_cmd.Prompt.ask")
    @patch("vsc_sync.commands.init_cmd.AppManager.auto_discover_apps")
    def test_run_with_discovered_apps(
        self, mock_discover, mock_prompt, mock_confirm, temp_dir
    ):
        """Test running init with discovered applications."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Create mock app config directory
        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        (app_config_dir / "settings.json").write_text("{}")

        # Mock discovered apps
        mock_discover.return_value = {
            "vscode": AppDetails(
                alias="vscode",
                config_path=app_config_dir,
                executable_path=Path("/usr/bin/code"),
            )
        }

        # Mock user interactions
        mock_prompt.side_effect = [
            "3",  # Choose option 3 (create new repo)
            str(temp_dir / "new-vscode-configs"),  # Repository path
        ]
        mock_confirm.side_effect = [
            False,  # Don't review apps individually (use all)
            False,  # Don't add more apps manually
        ]

        init_cmd = InitCommand(config_manager)
        init_cmd.run()

        # Check that app was included
        config = config_manager.load_config()
        assert "vscode" in config.managed_apps
        # Use resolve() to handle /private/var vs /var differences on macOS
        assert config.managed_apps["vscode"].config_path.resolve() == app_config_dir.resolve()

    def test_setup_config_path_default(self, temp_dir):
        """Test setting up config path with default."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        path = init_cmd._setup_config_path(None)
        assert path == config_manager.config_path

    def test_setup_config_path_custom(self, temp_dir):
        """Test setting up config path with custom path."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        custom_path = str(temp_dir / "custom-config.json")
        path = init_cmd._setup_config_path(custom_path)
        # Use resolve() to handle /private/var vs /var differences on macOS
        assert path.resolve() == (temp_dir / "custom-config.json").resolve()

    def test_verify_local_repo_valid(self, temp_dir, mock_vscode_configs_repo):
        """Test verifying a valid local repository."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        path = init_cmd._verify_local_repo(str(mock_vscode_configs_repo))
        # Use resolve() to handle /private/var vs /var differences on macOS
        assert path.resolve() == mock_vscode_configs_repo.resolve()

    def test_verify_local_repo_nonexistent(self, temp_dir):
        """Test verifying a nonexistent local repository."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        with pytest.raises(VscSyncError, match="Local path does not exist"):
            init_cmd._verify_local_repo(str(temp_dir / "nonexistent"))

    def test_verify_local_repo_not_directory(self, temp_dir):
        """Test verifying a file instead of directory."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        # Create a file instead of directory
        file_path = temp_dir / "not-a-dir.txt"
        file_path.write_text("content")

        with pytest.raises(VscSyncError, match="Path is not a directory"):
            init_cmd._verify_local_repo(str(file_path))

    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    def test_verify_local_repo_incomplete_structure(self, mock_confirm, temp_dir):
        """Test verifying a repository with incomplete structure."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        # Create directory with missing subdirectories
        incomplete_repo = temp_dir / "incomplete-repo"
        incomplete_repo.mkdir()
        (incomplete_repo / "base").mkdir()  # Only create base, missing apps and stacks

        mock_confirm.return_value = True  # User confirms to continue

        path = init_cmd._verify_local_repo(str(incomplete_repo))
        # Use resolve() to handle /private/var vs /var differences on macOS
        assert path.resolve() == incomplete_repo.resolve()

    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    def test_verify_local_repo_incomplete_structure_cancel(
        self, mock_confirm, temp_dir
    ):
        """Test verifying a repository with incomplete structure and user cancels."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        # Create directory with missing subdirectories
        incomplete_repo = temp_dir / "incomplete-repo"
        incomplete_repo.mkdir()

        mock_confirm.return_value = False  # User cancels

        with pytest.raises(VscSyncError, match="Repository verification failed"):
            init_cmd._verify_local_repo(str(incomplete_repo))

    def test_create_repo_structure(self, temp_dir):
        """Test creating repository structure."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        repo_path = temp_dir / "new-repo"
        init_cmd._create_repo_structure(repo_path)

        # Check directory structure
        assert (repo_path / "base").exists()
        assert (repo_path / "apps").exists()
        assert (repo_path / "stacks").exists()
        assert (repo_path / "projects").exists()
        assert (repo_path / "base" / "snippets").exists()

        # Check files
        assert (repo_path / "base" / "settings.json").exists()
        assert (repo_path / "base" / "extensions.json").exists()
        assert (repo_path / "base" / "keybindings.json").exists()
        assert (repo_path / "README.md").exists()

        # Check file contents
        settings = json.loads((repo_path / "base" / "settings.json").read_text())
        assert "editor.fontSize" in settings

        extensions = json.loads((repo_path / "base" / "extensions.json").read_text())
        assert "recommendations" in extensions

    @patch("vsc_sync.commands.init_cmd.GitOperations.clone_repository")
    @patch("vsc_sync.commands.init_cmd.GitOperations.is_git_available")
    @patch("vsc_sync.commands.init_cmd.Prompt.ask")
    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    def test_clone_repository(
        self, mock_confirm, mock_prompt, mock_git_available, mock_clone, temp_dir
    ):
        """Test cloning a repository."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        mock_git_available.return_value = True
        mock_prompt.return_value = str(temp_dir / "cloned-repo")
        mock_confirm.return_value = (
            False  # Directory doesn't exist, no need to confirm removal
        )

        repo_url = "https://github.com/user/vscode-configs.git"
        path = init_cmd._clone_repository(repo_url)

        # Use resolve() to handle /private/var vs /var differences on macOS in assertion
        expected_path = (temp_dir / "cloned-repo").resolve()
        actual_call_path = mock_clone.call_args[0][1].resolve()
        assert actual_call_path == expected_path
        assert path.resolve() == expected_path

    @patch("vsc_sync.commands.init_cmd.GitOperations.is_git_available")
    def test_clone_repository_no_git(self, mock_git_available, temp_dir):
        """Test cloning when Git is not available."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        mock_git_available.return_value = False

        with pytest.raises(VscSyncError, match="Git support is not available"):
            init_cmd._clone_repository("https://github.com/user/repo.git")

    @patch("vsc_sync.commands.init_cmd.Prompt.ask")
    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    def test_modify_app_details(self, mock_confirm, mock_prompt, temp_dir):
        """Test modifying application details."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        # Create mock config directory
        config_dir = temp_dir / "app-config"
        config_dir.mkdir()
        (config_dir / "settings.json").write_text("{}")

        original_app = AppDetails(
            alias="old-alias",
            config_path=config_dir,
            executable_path=Path("/usr/bin/old-exec"),
        )

        # Mock user input
        mock_prompt.side_effect = [
            "new-alias",  # New alias
            str(config_dir),  # Keep same config path
            "/usr/bin/new-exec",  # New executable
        ]
        mock_confirm.return_value = True  # Continue despite validation warning

        result = init_cmd._modify_app_details("old-alias", original_app)

        assert result is not None
        assert result.alias == "new-alias"
        # Use resolve() to handle /private/var vs /var differences on macOS
        assert result.config_path.resolve() == config_dir.resolve()
        assert result.executable_path == Path("/usr/bin/new-exec")

    @patch("vsc_sync.commands.init_cmd.Prompt.ask")
    @patch("vsc_sync.commands.init_cmd.Confirm.ask")
    def test_modify_app_details_cancel(self, mock_confirm, mock_prompt, temp_dir):
        """Test modifying application details and cancelling."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        original_app = AppDetails(
            alias="test-app", config_path=temp_dir / "config", executable_path=None
        )

        # Mock user input with invalid path
        mock_prompt.side_effect = [
            "test-app",  # Same alias
            str(temp_dir / "nonexistent"),  # Invalid config path
            "",  # No executable
        ]
        mock_confirm.return_value = False  # Cancel when path doesn't validate

        result = init_cmd._modify_app_details("test-app", original_app)
        assert result is None

    def test_is_in_dotfiles_location(self, temp_dir):
        """Test checking if config is in dotfiles location."""
        config_manager = ConfigManager(temp_dir / "config.json")
        init_cmd = InitCommand(config_manager)

        # Test dotfiles location
        dotfiles_path = temp_dir / ".config" / "vsc-sync" / "config.json"
        assert init_cmd._is_in_dotfiles_location(dotfiles_path)

        # Test non-dotfiles location
        regular_path = temp_dir / "somewhere" / "config.json"
        assert not init_cmd._is_in_dotfiles_location(regular_path)


@pytest.fixture
def mock_console():
    """Mock console for testing."""
    return Mock(spec=Console)
