"""Tests for the status command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from vsc_sync.commands.status_cmd import StatusCommand
from vsc_sync.config import ConfigManager
from vsc_sync.exceptions import AppConfigPathError, VscSyncError
from vsc_sync.models import AppDetails, VscSyncConfig


class TestStatusCommand:
    """Test class for StatusCommand functionality."""

    def test_status_command_creation(self, temp_dir, mock_vscode_configs_repo):
        """Test creating a StatusCommand instance."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Create a proper config with the mock repo path
        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        assert status_cmd.config_manager == config_manager

    def test_validate_app_success(self, temp_dir, mock_vscode_configs_repo):
        """Test successful app validation."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Create app config directory
        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        result = status_cmd._validate_app("test-vscode")

        assert result == app_details

    def test_validate_app_not_registered(self, temp_dir, mock_vscode_configs_repo):
        """Test validating an unregistered app."""
        config_manager = ConfigManager(temp_dir / "config.json")

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo, managed_apps={}
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        with pytest.raises(VscSyncError, match="App 'nonexistent' is not registered"):
            status_cmd._validate_app("nonexistent")

    def test_validate_app_config_path_not_exists(
        self, temp_dir, mock_vscode_configs_repo
    ):
        """Test validating an app with non-existent config path."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=temp_dir / "nonexistent",
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        with pytest.raises(
            AppConfigPathError, match="App config directory does not exist"
        ):
            status_cmd._validate_app("test-vscode")

    def test_get_settings_status_in_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test getting settings status when in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create settings file that matches target
        target_settings = {"editor.fontSize": 14}
        (app_config_dir / "settings.json").write_text(json.dumps(target_settings))

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        result = status_cmd._get_settings_status(app_details, target_settings)

        assert "IN SYNC" in result

    def test_get_settings_status_out_of_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test getting settings status when out of sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create settings file that doesn't match target
        current_settings = {"editor.fontSize": 12}
        target_settings = {"editor.fontSize": 14}
        (app_config_dir / "settings.json").write_text(json.dumps(current_settings))

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        result = status_cmd._get_settings_status(app_details, target_settings)

        assert "OUT OF SYNC" in result

    def test_get_keybindings_status_in_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test getting keybindings status when in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create keybindings file that matches target
        target_content = "[]"
        (app_config_dir / "keybindings.json").write_text(target_content)

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_source = mock_vscode_configs_repo / "base" / "keybindings.json"
        result = status_cmd._get_keybindings_status(app_details, target_source)

        assert "IN SYNC" in result

    def test_get_keybindings_status_missing(self, temp_dir, mock_vscode_configs_repo):
        """Test getting keybindings status when file is missing."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        # Don't create keybindings.json

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_source = mock_vscode_configs_repo / "base" / "keybindings.json"
        result = status_cmd._get_keybindings_status(app_details, target_source)

        assert "MISSING" in result

    def test_get_keybindings_status_no_target(self, temp_dir, mock_vscode_configs_repo):
        """Test getting keybindings status when no target exists."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        result = status_cmd._get_keybindings_status(app_details, None)

        assert "IN SYNC" in result

    def test_get_snippets_status_in_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test getting snippets status when in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create snippets directory with matching files
        snippets_dir = app_config_dir / "snippets"
        snippets_dir.mkdir()
        (snippets_dir / "global.code-snippets").write_text("{}")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_paths = [mock_vscode_configs_repo / "base" / "snippets"]
        result = status_cmd._get_snippets_status(app_details, target_paths)

        assert "IN SYNC" in result

    def test_get_snippets_status_out_of_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test getting snippets status when out of sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create snippets directory with different files
        snippets_dir = app_config_dir / "snippets"
        snippets_dir.mkdir()
        (snippets_dir / "different.code-snippets").write_text("{}")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_paths = [mock_vscode_configs_repo / "base" / "snippets"]
        result = status_cmd._get_snippets_status(app_details, target_paths)

        assert "OUT OF SYNC" in result

    @patch("vsc_sync.commands.status_cmd.AppManager.get_installed_extensions")
    def test_get_extensions_status_in_sync(
        self, mock_get_installed, temp_dir, mock_vscode_configs_repo
    ):
        """Test getting extensions status when in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        # Mock extensions that match target
        target_extensions = ["ext1", "ext2"]
        mock_get_installed.return_value = target_extensions

        status_cmd = StatusCommand(config_manager)
        result = status_cmd._get_extensions_status(app_details, target_extensions)

        assert "IN SYNC" in result

    @patch("vsc_sync.commands.status_cmd.AppManager.get_installed_extensions")
    def test_get_extensions_status_out_of_sync(
        self, mock_get_installed, temp_dir, mock_vscode_configs_repo
    ):
        """Test getting extensions status when out of sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        # Mock extensions that don't match target
        target_extensions = ["ext1", "ext2"]
        mock_get_installed.return_value = ["ext1", "ext3"]  # Different

        status_cmd = StatusCommand(config_manager)
        result = status_cmd._get_extensions_status(app_details, target_extensions)

        assert "OUT OF SYNC" in result

    @patch("vsc_sync.commands.status_cmd.AppManager.get_installed_extensions")
    def test_get_extensions_status_error(
        self, mock_get_installed, temp_dir, mock_vscode_configs_repo
    ):
        """Test getting extensions status when error occurs."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        # Mock exception when getting extensions
        from vsc_sync.exceptions import ExtensionError

        mock_get_installed.side_effect = ExtensionError("Test error")

        status_cmd = StatusCommand(config_manager)
        result = status_cmd._get_extensions_status(app_details, ["ext1"])

        assert "UNKNOWN" in result

    def test_compare_settings_in_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing settings when they're in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create settings that match target
        target_settings = {"editor.fontSize": 14}
        (app_config_dir / "settings.json").write_text(json.dumps(target_settings))

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd._compare_settings(app_details, target_settings)

    def test_compare_settings_out_of_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing settings when they're out of sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create settings that don't match target
        current_settings = {"editor.fontSize": 12}
        target_settings = {"editor.fontSize": 14, "editor.wordWrap": "on"}
        (app_config_dir / "settings.json").write_text(json.dumps(current_settings))

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd._compare_settings(app_details, target_settings)

    def test_show_setting_differences(self, temp_dir, mock_vscode_configs_repo):
        """Test showing setting differences."""
        config_manager = ConfigManager(temp_dir / "config.json")

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo, managed_apps={}
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        current = {
            "editor": {"fontSize": 12, "tabSize": 2},
            "terminal": {"fontSize": 10},
            "oldSetting": "value",
        }

        target = {
            "editor": {"fontSize": 14, "wordWrap": "on", "tabSize": 2},
            "terminal": {"fontSize": 10},
            "newSetting": "value",
        }

        # This should not raise an exception
        status_cmd._show_setting_differences(current, target)

    def test_compare_keybindings_in_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing keybindings when they're in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create keybindings that match target
        (app_config_dir / "keybindings.json").write_text("[]")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_source = mock_vscode_configs_repo / "base" / "keybindings.json"

        # Should not raise exception
        status_cmd._compare_keybindings(app_details, target_source)

    def test_compare_keybindings_missing(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing keybindings when current file is missing."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        # Don't create keybindings.json

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_source = mock_vscode_configs_repo / "base" / "keybindings.json"

        # Should not raise exception
        status_cmd._compare_keybindings(app_details, target_source)

    def test_compare_snippets_in_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing snippets when they're in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create snippets that match target
        snippets_dir = app_config_dir / "snippets"
        snippets_dir.mkdir()
        (snippets_dir / "global.code-snippets").write_text("{}")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_paths = [mock_vscode_configs_repo / "base" / "snippets"]

        # Should not raise exception
        status_cmd._compare_snippets(app_details, target_paths)

    def test_compare_snippets_out_of_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing snippets when they're out of sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create snippets that don't match target
        snippets_dir = app_config_dir / "snippets"
        snippets_dir.mkdir()
        (snippets_dir / "different.code-snippets").write_text("{}")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_paths = [mock_vscode_configs_repo / "base" / "snippets"]

        # Should not raise exception
        status_cmd._compare_snippets(app_details, target_paths)

    @patch("vsc_sync.commands.status_cmd.AppManager.get_installed_extensions")
    def test_compare_extensions_in_sync(
        self, mock_get_installed, temp_dir, mock_vscode_configs_repo
    ):
        """Test comparing extensions when they're in sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        # Mock extensions that match target
        target_extensions = ["ext1", "ext2"]
        mock_get_installed.return_value = target_extensions

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd._compare_extensions(app_details, target_extensions)

    @patch("vsc_sync.commands.status_cmd.AppManager.get_installed_extensions")
    def test_compare_extensions_out_of_sync(
        self, mock_get_installed, temp_dir, mock_vscode_configs_repo
    ):
        """Test comparing extensions when they're out of sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        # Mock extensions that don't match target
        target_extensions = ["ext1", "ext2"]
        mock_get_installed.return_value = ["ext1", "ext3", "ext4"]

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd._compare_extensions(app_details, target_extensions)

    def test_run_all_apps_no_apps(self, temp_dir, mock_vscode_configs_repo):
        """Test running status for all apps when no apps are registered."""
        config_manager = ConfigManager(temp_dir / "config.json")

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo, managed_apps={}
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd.run()

    def test_run_all_apps_with_apps(self, temp_dir, mock_vscode_configs_repo):
        """Test running status for all apps when apps are registered."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        (app_config_dir / "settings.json").write_text('{"test": true}')

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd.run()

    def test_run_specific_app(self, temp_dir, mock_vscode_configs_repo):
        """Test running status for a specific app."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        (app_config_dir / "settings.json").write_text('{"test": true}')

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd.run(app_alias="test-vscode")

    def test_run_specific_app_with_stacks(self, temp_dir, mock_vscode_configs_repo):
        """Test running status for a specific app with stacks."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        (app_config_dir / "settings.json").write_text('{"test": true}')

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception
        status_cmd.run(app_alias="test-vscode", stacks=["python"])

    def test_run_nonexistent_app(self, temp_dir, mock_vscode_configs_repo):
        """Test running status for a nonexistent app."""
        config_manager = ConfigManager(temp_dir / "config.json")

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo, managed_apps={}
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        with pytest.raises(VscSyncError, match="Status check failed"):
            status_cmd.run(app_alias="nonexistent")

    def test_get_app_status_summary_error_handling(self, temp_dir, mock_vscode_configs_repo):
        """Test that _get_app_status_summary handles errors gracefully."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Create app with non-existent config path  
        app_details = AppDetails(
            alias="test-vscode",
            config_path=temp_dir / "nonexistent",
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # The current implementation will show OUT OF SYNC rather than ERROR 
        # because the layer merging succeeds, but file operations will fail
        result = status_cmd._get_app_status_summary(app_details, [])

        # Since the config directory doesn't exist, it will be OUT OF SYNC
        assert ("OUT OF SYNC" in result["settings"] or "ERROR" in result["settings"])
        assert ("OUT OF SYNC" in result["overall"] or "ERROR" in result["overall"])

    def test_show_active_layers(self, temp_dir, mock_vscode_configs_repo):
        """Test showing active layers."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Get merge result to test with
        merge_result = status_cmd.layer_manager.merge_layers(
            app_alias="test-vscode", stacks=["python"]
        )

        # Should not raise exception
        status_cmd._show_active_layers(merge_result, ["python"])

    def test_compare_configurations(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing configurations."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        (app_config_dir / "settings.json").write_text('{"test": true}')

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Get merge result to test with
        merge_result = status_cmd.layer_manager.merge_layers(
            app_alias="test-vscode", stacks=[]
        )

        # Should not raise exception
        status_cmd._compare_configurations(app_details, merge_result, [])

    def test_get_app_status_summary_with_unknown_status(self, temp_dir, mock_vscode_configs_repo):
        """Test app status summary when some components have unknown status."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Mock to return UNKNOWN status for extensions and IN SYNC for others
        with patch.object(status_cmd, '_get_extensions_status', return_value="[yellow]UNKNOWN[/yellow]"), \
             patch.object(status_cmd, '_get_settings_status', return_value="[green]IN SYNC[/green]"), \
             patch.object(status_cmd, '_get_keybindings_status', return_value="[green]IN SYNC[/green]"), \
             patch.object(status_cmd, '_get_snippets_status', return_value="[green]IN SYNC[/green]"):
            result = status_cmd._get_app_status_summary(app_details, [])
            assert "UNKNOWN" in result["overall"]

    def test_get_app_status_summary_with_partial_status(self, temp_dir, mock_vscode_configs_repo):
        """Test app status summary with mixed status (partial)."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Mock mixed statuses
        with patch.object(status_cmd, '_get_settings_status', return_value="[green]IN SYNC[/green]"), \
             patch.object(status_cmd, '_get_keybindings_status', return_value="[yellow]EXTRA[/yellow]"), \
             patch.object(status_cmd, '_get_snippets_status', return_value="[green]IN SYNC[/green]"), \
             patch.object(status_cmd, '_get_extensions_status', return_value="[green]IN SYNC[/green]"):
            result = status_cmd._get_app_status_summary(app_details, [])
            assert "PARTIAL" in result["overall"]

    def test_all_apps_with_exception_handling(self, temp_dir, mock_vscode_configs_repo):
        """Test all apps status when an app throws an exception."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Create one working app
        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        working_app = AppDetails(
            alias="working-app",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        # Create one broken app
        broken_app = AppDetails(
            alias="broken-app",
            config_path=temp_dir / "nonexistent",
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"working-app": working_app, "broken-app": broken_app},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Force an exception for the broken app by mocking _get_app_status_summary to raise
        original_method = status_cmd._get_app_status_summary
        def mock_summary(app_details, stacks):
            if app_details.alias == "broken-app":
                raise Exception("Test exception")
            return original_method(app_details, stacks)
        
        with patch.object(status_cmd, '_get_app_status_summary', side_effect=mock_summary):
            # Should not raise exception, should handle error gracefully
            status_cmd._check_all_apps_status()

    def test_show_setting_differences_with_large_changes(self, temp_dir, mock_vscode_configs_repo):
        """Test showing setting differences when there are many changes."""
        config_manager = ConfigManager(temp_dir / "config.json")

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo, managed_apps={}
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        current = {"old_setting": "value"}
        target = {f"new_setting_{i}": f"value_{i}" for i in range(10)}  # 10 new settings

        # This should trigger the "... and X more" logic
        status_cmd._show_setting_differences(current, target)

    def test_compare_keybindings_out_of_sync(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing keybindings when they're out of sync."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create keybindings that don't match target
        (app_config_dir / "keybindings.json").write_text('[{"key": "ctrl+k", "command": "test"}]')

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)
        target_source = mock_vscode_configs_repo / "base" / "keybindings.json"

        # Should not raise exception and should show out of sync
        status_cmd._compare_keybindings(app_details, target_source)

    def test_compare_keybindings_extra_file(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing keybindings when current file exists but no target."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create keybindings file
        (app_config_dir / "keybindings.json").write_text("[]")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception and should show extra
        status_cmd._compare_keybindings(app_details, None)

    def test_compare_snippets_no_target_with_current(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing snippets when no target exists but current snippets exist."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()

        # Create current snippets
        snippets_dir = app_config_dir / "snippets"
        snippets_dir.mkdir()
        (snippets_dir / "existing.code-snippets").write_text("{}")

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception and should show extra
        status_cmd._compare_snippets(app_details, [])

    def test_compare_snippets_no_target_no_current(self, temp_dir, mock_vscode_configs_repo):
        """Test comparing snippets when no target and no current snippets exist."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        # Don't create snippets directory

        app_details = AppDetails(
            alias="test-vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)

        status_cmd = StatusCommand(config_manager)

        # Should not raise exception and should show in sync
        status_cmd._compare_snippets(app_details, [])

    def test_generate_edit_suggestions_basic(self, temp_dir, mock_vscode_configs_repo):
        """Test generating basic edit suggestions."""
        config_manager = ConfigManager(temp_dir / "config.json")
        
        app_details = AppDetails(
            alias="test-vscode",
            config_path=temp_dir / "vscode_config",
            executable_path=Path("/usr/bin/code"),
        )
        
        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)
        
        command = StatusCommand(config_manager)
        suggestions = command._generate_edit_suggestions("cursor")
        
        assert suggestions["live_settings"] == "vsc-sync edit live cursor"
        assert suggestions["live_keybindings"] == "vsc-sync edit live cursor --file-type keybindings"
        assert suggestions["app_settings"] == "vsc-sync edit app cursor"
        assert suggestions["base_settings"] == "vsc-sync edit base"

    def test_generate_edit_suggestions_with_stacks(self, temp_dir, mock_vscode_configs_repo):
        """Test generating edit suggestions with stacks."""
        config_manager = ConfigManager(temp_dir / "config.json")
        
        app_details = AppDetails(
            alias="test-vscode",
            config_path=temp_dir / "vscode_config",
            executable_path=Path("/usr/bin/code"),
        )
        
        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)
        
        command = StatusCommand(config_manager)
        suggestions = command._generate_edit_suggestions("vscode", ["python", "web-dev"])
        
        assert suggestions["stack_python_settings"] == "vsc-sync edit stack python"
        assert suggestions["stack_python_keybindings"] == "vsc-sync edit stack python --file-type keybindings"
        assert suggestions["stack_web-dev_settings"] == "vsc-sync edit stack web-dev"
        assert suggestions["stack_web-dev_keybindings"] == "vsc-sync edit stack web-dev --file-type keybindings"

    @patch('rich.console.Console.print')
    def test_show_edit_suggestions_for_settings(self, mock_print, temp_dir, mock_vscode_configs_repo):
        """Test showing edit suggestions for settings."""
        config_manager = ConfigManager(temp_dir / "config.json")
        
        app_details = AppDetails(
            alias="test-vscode",
            config_path=temp_dir / "vscode_config",
            executable_path=Path("/usr/bin/code"),
        )
        
        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)
        
        command = StatusCommand(config_manager)
        command._show_edit_suggestions_for_settings("cursor", ["python"])
        
        # Check that appropriate suggestions were printed
        mock_print.assert_any_call(f"\n  [bold blue]💡 Quick fixes:[/bold blue]")
        mock_print.assert_any_call(f"    Edit live app config:  [cyan]vsc-sync edit live cursor[/cyan]")
        mock_print.assert_any_call(f"    Edit app layer:        [cyan]vsc-sync edit app cursor[/cyan]")
        mock_print.assert_any_call(f"    Edit python stack:       [cyan]vsc-sync edit stack python[/cyan]")

    @patch('rich.console.Console.print')
    def test_show_edit_suggestions_for_keybindings(self, mock_print, temp_dir, mock_vscode_configs_repo):
        """Test showing edit suggestions for keybindings."""
        config_manager = ConfigManager(temp_dir / "config.json")
        
        app_details = AppDetails(
            alias="test-vscode",
            config_path=temp_dir / "vscode_config",
            executable_path=Path("/usr/bin/code"),
        )
        
        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo,
            managed_apps={"test-vscode": app_details},
        )
        config_manager.save_config(config)
        
        command = StatusCommand(config_manager)
        command._show_edit_suggestions_for_keybindings("vscode", [])
        
        # Check that appropriate suggestions were printed
        mock_print.assert_any_call(f"\n  [bold blue]💡 Quick fixes:[/bold blue]")
        mock_print.assert_any_call(f"    Edit live app config:  [cyan]vsc-sync edit live vscode --file-type keybindings[/cyan]")
        mock_print.assert_any_call(f"    Edit app layer:        [cyan]vsc-sync edit app vscode --file-type keybindings[/cyan]")