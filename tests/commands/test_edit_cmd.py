"""Tests for the edit command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.vsc_sync.commands.edit_cmd import EditCommand
from src.vsc_sync.config import ConfigManager
from src.vsc_sync.exceptions import VscSyncError
from src.vsc_sync.models import VscSyncConfig, AppDetails


class TestEditCommand:
    """Test cases for EditCommand."""

    @pytest.fixture
    def mock_config_manager(self, tmp_path):
        """Create a mock config manager."""
        config_manager = Mock(spec=ConfigManager)
        
        # Mock config with apps
        mock_config = VscSyncConfig(
            vscode_configs_path=tmp_path / "vscode-configs",
            managed_apps={
                "vscode": AppDetails(
                    alias="vscode",
                    config_path=tmp_path / "vscode",
                    executable_path=Path("code")
                ),
                "cursor": AppDetails(
                    alias="cursor", 
                    config_path=tmp_path / "cursor",
                    executable_path=Path("cursor")
                )
            }
        )
        
        config_manager.load_config.return_value = mock_config
        return config_manager

    def test_edit_command_creation(self, mock_config_manager):
        """Test EditCommand can be created."""
        command = EditCommand(mock_config_manager)
        assert command.config_manager == mock_config_manager

    def test_validate_inputs_valid_base(self, mock_config_manager):
        """Test validate inputs for base layer."""
        command = EditCommand(mock_config_manager)
        # Should not raise
        command._validate_inputs("base", None, "settings")

    def test_validate_inputs_valid_app(self, mock_config_manager):
        """Test validate inputs for app layer."""
        command = EditCommand(mock_config_manager)
        # Should not raise
        command._validate_inputs("app", "vscode", "settings")

    def test_validate_inputs_invalid_layer_type(self, mock_config_manager):
        """Test validate inputs with invalid layer type."""
        command = EditCommand(mock_config_manager)
        with pytest.raises(VscSyncError, match="Invalid layer type 'invalid'"):
            command._validate_inputs("invalid", None, "settings")

    def test_validate_inputs_invalid_file_type(self, mock_config_manager):
        """Test validate inputs with invalid file type."""
        command = EditCommand(mock_config_manager)
        with pytest.raises(VscSyncError, match="Invalid file type 'invalid'"):
            command._validate_inputs("base", None, "invalid")

    def test_validate_inputs_missing_layer_name(self, mock_config_manager):
        """Test validate inputs with missing layer name for non-base."""
        command = EditCommand(mock_config_manager)
        with pytest.raises(VscSyncError, match="Layer name is required"):
            command._validate_inputs("app", None, "settings")

    def test_validate_inputs_unregistered_app(self, mock_config_manager):
        """Test validate inputs with unregistered app."""
        command = EditCommand(mock_config_manager)
        with pytest.raises(VscSyncError, match="App 'unregistered' is not registered"):
            command._validate_inputs("app", "unregistered", "settings")

    def test_construct_file_path_base(self, mock_config_manager, tmp_path):
        """Test construct file path for base layer."""
        command = EditCommand(mock_config_manager)
        path = command._construct_file_path("base", None, "settings")
        expected = tmp_path / "vscode-configs" / "base" / "settings.json"
        assert path == expected

    def test_construct_file_path_app(self, mock_config_manager, tmp_path):
        """Test construct file path for app layer."""
        command = EditCommand(mock_config_manager)
        path = command._construct_file_path("app", "vscode", "keybindings")
        expected = tmp_path / "vscode-configs" / "apps" / "vscode" / "keybindings.json"
        assert path == expected

    def test_construct_file_path_stack_snippets(self, mock_config_manager, tmp_path):
        """Test construct file path for stack snippets."""
        command = EditCommand(mock_config_manager)
        path = command._construct_file_path("stack", "python", "snippets")
        expected = tmp_path / "vscode-configs" / "stacks" / "python" / "snippets"
        assert path == expected

    def test_get_initial_content_settings(self, mock_config_manager):
        """Test get initial content for settings file."""
        command = EditCommand(mock_config_manager)
        content = command._get_initial_content("settings")
        assert content == "{\n}\n"

    def test_get_initial_content_extensions(self, mock_config_manager):
        """Test get initial content for extensions file."""
        command = EditCommand(mock_config_manager)
        content = command._get_initial_content("extensions")
        assert content == '{\n  "recommendations": [\n  ]\n}\n'

    def test_get_initial_content_keybindings(self, mock_config_manager):
        """Test get initial content for keybindings file."""
        command = EditCommand(mock_config_manager)
        content = command._get_initial_content("keybindings")
        assert content == "[\n]\n"

    @patch('src.vsc_sync.commands.edit_cmd.subprocess.run')
    def test_get_editor_finds_code(self, mock_run, mock_config_manager):
        """Test get editor finds code executable."""
        # Mock successful code --version call
        mock_run.return_value = Mock()
        
        command = EditCommand(mock_config_manager)
        editor = command._get_editor()
        
        assert editor == "code"
        mock_run.assert_called_once_with(
            ["code", "--version"],
            check=True,
            capture_output=True,
            text=True
        )

    @patch('src.vsc_sync.commands.edit_cmd.subprocess.run')
    @patch('src.vsc_sync.commands.edit_cmd.sys.platform', 'darwin')
    def test_get_editor_falls_back_to_open(self, mock_run, mock_config_manager):
        """Test get editor falls back to system default on macOS."""
        # Mock all editor checks failing
        mock_run.side_effect = FileNotFoundError()
        
        command = EditCommand(mock_config_manager)
        editor = command._get_editor()
        
        assert editor == "open"

    @patch('src.vsc_sync.commands.edit_cmd.subprocess.run')
    @patch('src.vsc_sync.commands.edit_cmd.Confirm.ask')
    def test_run_success_existing_file(self, mock_confirm, mock_run, mock_config_manager, tmp_path):
        """Test successful run with existing file."""
        # Setup
        config_path = tmp_path / "vscode-configs" / "base"
        config_path.mkdir(parents=True)
        settings_file = config_path / "settings.json"
        settings_file.write_text('{}')
        
        mock_run.return_value = Mock()  # Mock successful editor execution
        
        command = EditCommand(mock_config_manager)
        
        # Should not raise
        command.run("base", None, "settings")
        
        # Verify editor was called (once for --version check, once for opening file)
        assert mock_run.call_count == 2

    @patch('src.vsc_sync.commands.edit_cmd.subprocess.run')
    @patch('src.vsc_sync.commands.edit_cmd.Confirm.ask', return_value=True)
    def test_run_creates_new_file(self, mock_confirm, mock_run, mock_config_manager, tmp_path):
        """Test run creates new file when it doesn't exist."""
        mock_run.return_value = Mock()  # Mock successful editor execution
        
        command = EditCommand(mock_config_manager)
        command.run("base", None, "settings")
        
        # Verify file was created
        expected_file = tmp_path / "vscode-configs" / "base" / "settings.json"
        assert expected_file.exists()
        assert expected_file.read_text() == "{\n}\n"
        
        # Verify editor was called (once for --version check, once for opening file)
        assert mock_run.call_count == 2

    @patch('src.vsc_sync.commands.edit_cmd.subprocess.run')
    @patch('src.vsc_sync.commands.edit_cmd.Confirm.ask', return_value=False)
    def test_run_cancelled_by_user(self, mock_confirm, mock_run, mock_config_manager):
        """Test run cancelled when user declines file creation."""
        command = EditCommand(mock_config_manager)
        
        # Should not raise but should exit early
        command.run("base", None, "settings")
        
        # Editor should not be called
        mock_run.assert_not_called()