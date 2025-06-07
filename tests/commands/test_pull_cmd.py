"""Tests for the pull command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from vsc_sync.commands.pull_cmd import PullCommand
from vsc_sync.config import ConfigManager
from vsc_sync.exceptions import AppConfigPathError, VscSyncError
from vsc_sync.models import AppDetails, VscSyncConfig


class TestPullCommand:
    """Test cases for PullCommand."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as app_config_dir, tempfile.TemporaryDirectory() as vscode_configs_dir:
            yield {
                "app_config": Path(app_config_dir),
                "vscode_configs": Path(vscode_configs_dir),
            }

    @pytest.fixture
    def mock_config_manager(self, temp_dirs):
        """Create a mock config manager with test data."""
        config = VscSyncConfig(
            vscode_configs_path=temp_dirs["vscode_configs"],
            managed_apps={
                "test-app": AppDetails(
                    alias="test-app",
                    config_path=temp_dirs["app_config"],
                    executable_path=Path("/usr/bin/test-app"),
                )
            },
        )

        manager = Mock(spec=ConfigManager)
        manager.load_config.return_value = config
        return manager

    @pytest.fixture
    def pull_command(self, mock_config_manager):
        """Create a PullCommand instance for testing."""
        return PullCommand(mock_config_manager)

    def test_validate_app_success(self, pull_command, temp_dirs):
        """Test successful app validation."""
        # Create the app config directory
        temp_dirs["app_config"].mkdir(exist_ok=True)

        app_details = pull_command._validate_app("test-app")
        assert app_details.alias == "test-app"
        assert app_details.config_path == temp_dirs["app_config"]

    def test_validate_app_not_registered(self, pull_command):
        """Test validation of unregistered app."""
        with pytest.raises(VscSyncError, match="App 'nonexistent' is not registered"):
            pull_command._validate_app("nonexistent")

    def test_validate_app_config_path_not_exists(self, temp_dirs):
        """Test validation when app config path doesn't exist."""
        # Create a config with a non-existent path
        config = VscSyncConfig(
            vscode_configs_path=temp_dirs["vscode_configs"],
            managed_apps={
                "test-app": AppDetails(
                    alias="test-app",
                    config_path=temp_dirs["app_config"]
                    / "nonexistent",  # This doesn't exist
                    executable_path=Path("/usr/bin/test-app"),
                )
            },
        )

        manager = Mock(spec=ConfigManager)
        manager.load_config.return_value = config
        pull_command = PullCommand(manager)

        with pytest.raises(
            AppConfigPathError, match="App config directory does not exist"
        ):
            pull_command._validate_app("test-app")

    def test_resolve_target_layer_path_base(self, pull_command, temp_dirs):
        """Test resolving base layer path."""
        target_path = pull_command._resolve_target_layer_path("base", None, "test-app")
        expected_path = temp_dirs["vscode_configs"] / "base"
        assert target_path == expected_path
        assert target_path.exists()  # Should be created

    def test_resolve_target_layer_path_app(self, pull_command, temp_dirs):
        """Test resolving app layer path."""
        target_path = pull_command._resolve_target_layer_path("app", None, "test-app")
        expected_path = temp_dirs["vscode_configs"] / "apps" / "test-app"
        assert target_path == expected_path
        assert target_path.exists()  # Should be created

    def test_resolve_target_layer_path_app_with_custom_name(
        self, pull_command, temp_dirs
    ):
        """Test resolving app layer path with custom name."""
        target_path = pull_command._resolve_target_layer_path(
            "app", "custom-name", "test-app"
        )
        expected_path = temp_dirs["vscode_configs"] / "apps" / "custom-name"
        assert target_path == expected_path
        assert target_path.exists()  # Should be created

    def test_resolve_target_layer_path_stack(self, pull_command, temp_dirs):
        """Test resolving stack layer path."""
        target_path = pull_command._resolve_target_layer_path(
            "stack", "python", "test-app"
        )
        expected_path = temp_dirs["vscode_configs"] / "stacks" / "python"
        assert target_path == expected_path
        assert target_path.exists()  # Should be created

    def test_resolve_target_layer_path_stack_no_name(self, pull_command):
        """Test resolving stack layer path without name."""
        with pytest.raises(
            VscSyncError, match="Layer name is required for stack layer type"
        ):
            pull_command._resolve_target_layer_path("stack", None, "test-app")

    def test_resolve_target_layer_path_invalid_type(self, pull_command):
        """Test resolving invalid layer type."""
        with pytest.raises(VscSyncError, match="Invalid layer type 'invalid'"):
            pull_command._resolve_target_layer_path("invalid", None, "test-app")

    def test_pull_settings_success(self, pull_command, temp_dirs):
        """Test successful settings pull."""
        # Create source settings.json
        source_settings = {"editor.fontSize": 14}
        source_file = temp_dirs["app_config"] / "settings.json"
        source_file.write_text(json.dumps(source_settings, indent=2))

        # Create target directory
        target_dir = temp_dirs["vscode_configs"] / "base"
        target_dir.mkdir(parents=True)

        # Pull settings
        pull_command._pull_settings(
            AppDetails(alias="test-app", config_path=temp_dirs["app_config"]),
            target_dir,
            overwrite=True,
        )

        # Verify target file was created with correct content
        target_file = target_dir / "settings.json"
        assert target_file.exists()

        target_content = json.loads(target_file.read_text())
        assert target_content == source_settings

    def test_pull_settings_source_not_exists(self, pull_command, temp_dirs, capsys):
        """Test pulling settings when source doesn't exist."""
        target_dir = temp_dirs["vscode_configs"] / "base"
        target_dir.mkdir(parents=True)

        pull_command._pull_settings(
            AppDetails(alias="test-app", config_path=temp_dirs["app_config"]),
            target_dir,
            overwrite=True,
        )

        # Should print warning and not create target file
        captured = capsys.readouterr()
        assert "Source settings.json does not exist - skipping" in captured.out
        assert not (target_dir / "settings.json").exists()

    @patch("vsc_sync.commands.pull_cmd.AppManager.get_installed_extensions")
    def test_pull_extensions_success(
        self, mock_get_extensions, pull_command, temp_dirs
    ):
        """Test successful extensions pull."""
        # Mock installed extensions
        mock_get_extensions.return_value = [
            "ms-python.python",
            "ms-vscode.vscode-typescript-next",
        ]

        # Create target directory
        target_dir = temp_dirs["vscode_configs"] / "base"
        target_dir.mkdir(parents=True)

        # Pull extensions
        pull_command._pull_extensions(
            AppDetails(
                alias="test-app",
                config_path=temp_dirs["app_config"],
                executable_path=Path("/usr/bin/test-app"),
            ),
            target_dir,
            overwrite=True,
        )

        # Verify target file was created with correct content
        target_file = target_dir / "extensions.json"
        assert target_file.exists()

        target_content = json.loads(target_file.read_text())
        expected_content = {
            "recommendations": ["ms-python.python", "ms-vscode.vscode-typescript-next"]
        }
        assert target_content == expected_content

    def test_pull_extensions_no_executable(self, pull_command, temp_dirs, capsys):
        """Test pulling extensions when no executable is configured."""
        target_dir = temp_dirs["vscode_configs"] / "base"
        target_dir.mkdir(parents=True)

        pull_command._pull_extensions(
            AppDetails(alias="test-app", config_path=temp_dirs["app_config"]),
            target_dir,
            overwrite=True,
        )

        # Should print warning and not create target file
        captured = capsys.readouterr()
        assert "No executable path configured - skipping extensions" in captured.out
        assert not (target_dir / "extensions.json").exists()

    @pytest.mark.parametrize("dry_run", [True, False])
    @patch("vsc_sync.commands.pull_cmd.console")
    def test_run_dry_run_vs_actual(
        self, mock_console, pull_command, temp_dirs, dry_run
    ):
        """Test that dry run doesn't make changes while actual run does."""
        # Create app config directory and settings
        temp_dirs["app_config"].mkdir(exist_ok=True)
        source_settings = {"editor.fontSize": 14}
        source_file = temp_dirs["app_config"] / "settings.json"
        source_file.write_text(json.dumps(source_settings, indent=2))

        # Create vscode configs base directory
        base_dir = temp_dirs["vscode_configs"] / "base"
        base_dir.mkdir(parents=True)

        with patch.object(pull_command, "_confirm_pull", return_value=True):
            pull_command.run(
                app_alias="test-app",
                layer_type="base",
                layer_name=None,
                include_extensions=False,
                include_keybindings=False,
                include_snippets=False,
                overwrite=True,
                dry_run=dry_run,
            )

        target_file = base_dir / "settings.json"

        if dry_run:
            # Dry run should not create the file
            assert not target_file.exists()
        else:
            # Actual run should create the file
            assert target_file.exists()
            target_content = json.loads(target_file.read_text())
            assert target_content == source_settings

    @pytest.fixture
    def app_details(self, temp_dirs):
        """Create an AppDetails instance for testing."""
        return AppDetails(
            alias="test-app",
            config_path=temp_dirs["app_config"],
            executable_path=Path("/usr/bin/test-app"),
        )

    def test_pull_keybindings_success(self, pull_command, temp_dirs, app_details):
        """Test successful keybindings pull."""
        # Create source keybindings.json
        keybindings_content = (
            '[{"key": "ctrl+shift+p", "command": "workbench.action.showCommands"}]'
        )
        source_file = temp_dirs["app_config"] / "keybindings.json"
        source_file.write_text(keybindings_content)

        # Create target directory
        target_dir = temp_dirs["vscode_configs"] / "base"
        target_dir.mkdir(parents=True)

        # Pull keybindings
        pull_command._pull_keybindings(app_details, target_dir, overwrite=True)

        # Verify target file was created with correct content
        target_file = target_dir / "keybindings.json"
        assert target_file.exists()
        assert target_file.read_text() == keybindings_content

    def test_pull_snippets_success(self, pull_command, temp_dirs, app_details):
        """Test successful snippets pull."""
        # Create source snippets directory with files
        source_snippets_dir = temp_dirs["app_config"] / "snippets"
        source_snippets_dir.mkdir(parents=True)

        snippet_content = (
            '{"test": {"prefix": "test", "body": "console.log(\\"test\\");"}}'
        )
        (source_snippets_dir / "javascript.code-snippets").write_text(snippet_content)

        # Create target directory
        target_dir = temp_dirs["vscode_configs"] / "base"
        target_dir.mkdir(parents=True)

        # Pull snippets
        pull_command._pull_snippets(app_details, target_dir, overwrite=True)

        # Verify target files were created
        target_snippets_dir = target_dir / "snippets"
        assert target_snippets_dir.exists()

        target_file = target_snippets_dir / "javascript.code-snippets"
        assert target_file.exists()
        assert target_file.read_text() == snippet_content

    @pytest.mark.parametrize("overwrite", [True, False])
    @patch("vsc_sync.commands.pull_cmd.Confirm.ask")
    def test_pull_settings_overwrite_behavior(
        self, mock_confirm, pull_command, temp_dirs, app_details, overwrite
    ):
        """Test overwrite behavior for settings pull."""
        # Create source settings.json
        source_settings = {"editor.fontSize": 14}
        source_file = temp_dirs["app_config"] / "settings.json"
        source_file.write_text(json.dumps(source_settings, indent=2))

        # Create target directory with existing settings
        target_dir = temp_dirs["vscode_configs"] / "base"
        target_dir.mkdir(parents=True)
        target_file = target_dir / "settings.json"
        target_file.write_text('{"existing": "content"}')

        # Configure mock: when overwrite=False, simulate user declining
        mock_confirm.return_value = False  # User says no to overwrite

        # Pull settings
        pull_command._pull_settings(app_details, target_dir, overwrite=overwrite)

        if overwrite:
            # File should be overwritten without asking user
            target_content = json.loads(target_file.read_text())
            assert target_content == source_settings
            mock_confirm.assert_not_called()
        else:
            # User was asked and said no, file should not be overwritten
            target_content = json.loads(target_file.read_text())
            assert target_content == {"existing": "content"}
            mock_confirm.assert_called_once()

    @pytest.mark.parametrize(
        "layer_type,layer_name,expected_path",
        [
            ("base", None, "base"),
            ("app", None, "apps/test-app"),
            ("app", "custom", "apps/custom"),
            ("stack", "python", "stacks/python"),
            ("project", None, "projects/test-app"),
            ("project", "custom-project", "projects/custom-project"),
        ],
    )
    def test_resolve_target_layer_paths(
        self, pull_command, temp_dirs, layer_type, layer_name, expected_path
    ):
        """Test various layer path resolutions."""
        if layer_type == "stack" and layer_name is None:
            with pytest.raises(VscSyncError):
                pull_command._resolve_target_layer_path(
                    layer_type, layer_name, "test-app"
                )
        else:
            target_path = pull_command._resolve_target_layer_path(
                layer_type, layer_name, "test-app"
            )
            expected_full_path = temp_dirs["vscode_configs"] / expected_path
            assert target_path == expected_full_path
            assert target_path.exists()  # Should be created

    def test_validate_project_success(self, pull_command, temp_dirs):
        """Test successful project validation."""
        # Create a project directory with .vscode
        project_dir = temp_dirs["app_config"] / "test-project"
        project_dir.mkdir()
        vscode_dir = project_dir / ".vscode"
        vscode_dir.mkdir()

        project_details = pull_command._validate_project(project_dir)
        assert project_details.alias == "test-project"
        assert project_details.config_path == vscode_dir
        assert (
            project_details.executable_path is None
        )  # Projects don't have executables

    def test_validate_project_not_exists(self, pull_command, temp_dirs):
        """Test validation when project directory doesn't exist."""
        nonexistent_project = temp_dirs["app_config"] / "nonexistent"

        with pytest.raises(VscSyncError, match="Project directory does not exist"):
            pull_command._validate_project(nonexistent_project)

    def test_validate_project_no_vscode_dir(self, pull_command, temp_dirs):
        """Test validation when project has no .vscode directory."""
        project_dir = temp_dirs["app_config"] / "test-project"
        project_dir.mkdir()

        with pytest.raises(
            VscSyncError, match="Project does not have a .vscode directory"
        ):
            pull_command._validate_project(project_dir)

    def test_validate_project_vscode_is_file(self, pull_command, temp_dirs):
        """Test validation when .vscode is a file instead of directory."""
        project_dir = temp_dirs["app_config"] / "test-project"
        project_dir.mkdir()
        vscode_file = project_dir / ".vscode"
        vscode_file.write_text("not a directory")

        with pytest.raises(VscSyncError, match=".vscode path is not a directory"):
            pull_command._validate_project(project_dir)

    @patch("vsc_sync.commands.pull_cmd.console")
    def test_run_project_mode(self, mock_console, pull_command, temp_dirs):
        """Test running pull command in project mode."""
        # Create a project with .vscode directory and settings
        project_dir = temp_dirs["app_config"] / "test-project"
        project_dir.mkdir()
        vscode_dir = project_dir / ".vscode"
        vscode_dir.mkdir()

        # Create some settings in the project
        settings_file = vscode_dir / "settings.json"
        settings_content = {"editor.fontSize": 16, "workbench.colorTheme": "Dark+"}
        settings_file.write_text(json.dumps(settings_content, indent=2))

        # Create target directory structure
        target_dir = temp_dirs["vscode_configs"] / "projects" / "test-project"
        target_dir.mkdir(parents=True)

        with patch.object(pull_command, "_confirm_pull", return_value=True):
            pull_command.run(
                app_alias=None,
                layer_type="project",
                layer_name=None,
                project_path=project_dir,
                include_extensions=False,  # Should be ignored in project mode
                include_keybindings=False,
                include_snippets=False,
                overwrite=True,
                dry_run=False,
            )

        # Verify the settings were pulled
        target_settings_file = target_dir / "settings.json"
        assert target_settings_file.exists()

        pulled_settings = json.loads(target_settings_file.read_text())
        assert pulled_settings == settings_content

    def test_run_project_mode_dry_run(self, pull_command, temp_dirs, capsys):
        """Test running pull command in project mode with dry run."""
        # Create a project with .vscode directory and settings
        project_dir = temp_dirs["app_config"] / "test-project"
        project_dir.mkdir()
        vscode_dir = project_dir / ".vscode"
        vscode_dir.mkdir()

        # Create some settings in the project
        settings_file = vscode_dir / "settings.json"
        settings_content = {"editor.fontSize": 16}
        settings_file.write_text(json.dumps(settings_content, indent=2))

        pull_command.run(
            app_alias=None,
            layer_type="project",
            layer_name=None,
            project_path=project_dir,
            include_extensions=False,
            include_keybindings=False,
                include_snippets=False,
            overwrite=True,
            dry_run=True,
        )

        # In dry run mode, no files should be created
        target_dir = temp_dirs["vscode_configs"] / "projects" / "test-project"
        if target_dir.exists():
            target_settings_file = target_dir / "settings.json"
            assert not target_settings_file.exists()

    def test_run_requires_app_alias_or_project_path(self, pull_command):
        """Test that run method requires either app_alias or project_path."""
        with pytest.raises(
            VscSyncError, match="app_alias is required when not pulling from a project"
        ):
            pull_command.run(
                app_alias=None,
                layer_type="base",
                layer_name=None,
                project_path=None,
            # include_settings default True
                overwrite=True,
                dry_run=True,
            )

    def test_full_preview_mode(self, pull_command, temp_dirs):
        """Test full preview mode functionality."""
        # Create app config directory and settings
        temp_dirs["app_config"].mkdir(exist_ok=True)
        source_settings = {"editor.fontSize": 16, "editor.tabSize": 4}
        source_file = temp_dirs["app_config"] / "settings.json"
        source_file.write_text(json.dumps(source_settings, indent=2))

        # Create vscode configs base directory
        base_dir = temp_dirs["vscode_configs"] / "base"
        base_dir.mkdir(parents=True)

        # Test full preview with no_pager=True
        with patch.object(pull_command, "_show_content_with_pager") as mock_pager:
            pull_command._show_settings_pull_preview(
                AppDetails(alias="test-app", config_path=temp_dirs["app_config"]),
                base_dir,
                full_preview=True,
                no_pager=True,
            )

            # Verify pager was called with correct parameters
            mock_pager.assert_called_once()
            args, kwargs = mock_pager.call_args
            assert "Full settings.json content" in args[1]  # title
            assert (
                kwargs.get("use_pager") is False
            )  # no_pager=True means use_pager=False

    def test_show_content_with_pager_no_pager(self, pull_command):
        """Test content display without pager."""
        test_content = '{"test": "content"}'

        with patch("vsc_sync.commands.pull_cmd.console") as mock_console:
            pull_command._show_content_with_pager(
                test_content, "Test Content", use_pager=False
            )

            # Should print title and use Syntax for content
            assert mock_console.print.call_count >= 2

    @patch("vsc_sync.commands.pull_cmd.subprocess.run")
    @patch("vsc_sync.commands.pull_cmd.tempfile.NamedTemporaryFile")
    def test_show_content_with_pager_with_pager(
        self, mock_tempfile, mock_subprocess, pull_command
    ):
        """Test content display with pager."""
        test_content = '{"test": "content"}'

        # Mock tempfile
        mock_file = Mock()
        mock_file.name = "/tmp/test_file.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        # Mock subprocess success
        mock_subprocess.return_value = None

        with patch("vsc_sync.commands.pull_cmd.console") as mock_console, patch(
            "vsc_sync.commands.pull_cmd.os.unlink"
        ):

            pull_command._show_content_with_pager(
                test_content, "Test Content", use_pager=True
            )

            # Should call subprocess with less command
            mock_subprocess.assert_called_once()
            cmd_args = mock_subprocess.call_args[0][0]
            assert cmd_args[0] == "less"
            assert "/tmp/test_file.json" in cmd_args

    @patch("typer.prompt")
    def test_prompt_for_full_content(self, mock_prompt, pull_command):
        """Test interactive prompt for full content."""
        # Test different responses
        test_cases = [
            ("y", "pager"),
            ("yes", "pager"),
            ("d", "direct"),
            ("direct", "direct"),
            ("n", "no"),
            ("no", "no"),
            ("anything_else", "no"),
        ]

        for input_val, expected in test_cases:
            mock_prompt.return_value = input_val
            result = pull_command._prompt_for_full_content("test content")
            assert result == expected
