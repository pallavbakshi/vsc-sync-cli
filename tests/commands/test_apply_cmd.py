"""Tests for the apply command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from vsc_sync.commands.apply_cmd import ApplyCommand
from vsc_sync.config import ConfigManager
from vsc_sync.exceptions import AppConfigPathError, VscSyncError
from vsc_sync.models import AppDetails, VscSyncConfig, MergeResult


class TestApplyCommand:
    """Test class for ApplyCommand functionality."""

    def test_apply_command_creation(self, temp_dir, mock_vscode_configs_repo):
        """Test creating an ApplyCommand instance."""
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

        apply_cmd = ApplyCommand(config_manager)
        assert apply_cmd.config_manager == config_manager

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

        apply_cmd = ApplyCommand(config_manager)
        result = apply_cmd._validate_app("test-vscode")

        assert result == app_details

    def test_validate_app_not_registered(self, temp_dir, mock_vscode_configs_repo):
        """Test validating an unregistered app."""
        config_manager = ConfigManager(temp_dir / "config.json")

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo, managed_apps={}
        )
        config_manager.save_config(config)

        apply_cmd = ApplyCommand(config_manager)

        with pytest.raises(VscSyncError, match="App 'nonexistent' is not registered"):
            apply_cmd._validate_app("nonexistent")

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

        apply_cmd = ApplyCommand(config_manager)

        with pytest.raises(
            AppConfigPathError, match="App config directory does not exist"
        ):
            apply_cmd._validate_app("test-vscode")

    def test_create_backup(self, temp_dir, mock_vscode_configs_repo):
        """Test creating a backup."""
        config_manager = ConfigManager(temp_dir / "config.json")

        # Create app config directory with some content
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

        apply_cmd = ApplyCommand(config_manager)

        backup_path = apply_cmd._create_backup(app_details, "test-backup")

        assert backup_path.exists()
        assert backup_path.name == "vscode_config.test-backup"
        assert (backup_path / "settings.json").exists()

    def test_apply_settings(self, temp_dir, mock_vscode_configs_repo):
        """Test applying settings.json."""
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

        apply_cmd = ApplyCommand(config_manager)

        test_settings = {"editor.fontSize": 16, "workbench.colorTheme": "dark"}
        apply_cmd._apply_settings(app_details, test_settings)

        settings_file = app_config_dir / "settings.json"
        assert settings_file.exists()

    def test_apply_tasks_respect_flag(self, temp_dir):
        """_apply_configurations should skip tasks when tasks_enabled is False."""
        from vsc_sync.commands.apply_cmd import ApplyCommand

        # Setup app details and config manager stub
        app_config_dir = temp_dir / "user_config"
        app_config_dir.mkdir()

        app_details = AppDetails(
            alias="vscode",
            config_path=app_config_dir,
            executable_path=Path("/usr/bin/code"),
        )

        # Create a tasks source file
        tasks_src = temp_dir / "tasks.json"
        tasks_src.write_text("{}")

        merge_result = MergeResult(
            merged_settings={},
            keybindings_source=None,
            extensions=[],
            snippets_paths=[],
            layers_applied=[],
            tasks_source=tasks_src,
        )

        repo = temp_dir / "repo"
        repo.mkdir()
        config_manager = ConfigManager(temp_dir / "cfg.json")
        config_manager.save_config(
            VscSyncConfig(vscode_configs_path=repo, managed_apps={})
        )

        cmd = ApplyCommand(config_manager)

        # Apply with tasks disabled
        cmd._apply_configurations(
            app_details,
            merge_result,
            prune_extensions=False,
            clean_extensions=False,
            tasks_enabled=False,
            include_settings=False,
            include_keybindings=False,
            include_extensions=False,
            include_snippets=False,
        )

        # tasks.json should not be copied
        assert not (app_config_dir / "tasks.json").exists()

    def test_apply_keybindings(self, temp_dir, mock_vscode_configs_repo):
        """Test applying keybindings.json."""
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

        apply_cmd = ApplyCommand(config_manager)

        # Use the keybindings from the mock repo
        keybindings_source = mock_vscode_configs_repo / "base" / "keybindings.json"
        apply_cmd._apply_keybindings(app_details, keybindings_source)

        keybindings_file = app_config_dir / "keybindings.json"
        assert keybindings_file.exists()
        assert keybindings_file.read_text() == keybindings_source.read_text()

    def test_apply_snippets(self, temp_dir, mock_vscode_configs_repo):
        """Test applying snippets."""
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

        apply_cmd = ApplyCommand(config_manager)

        snippets_paths = [mock_vscode_configs_repo / "base" / "snippets"]
        apply_cmd._apply_snippets(app_details, snippets_paths)

        app_snippets_dir = app_config_dir / "snippets"
        assert app_snippets_dir.exists()
        assert (app_snippets_dir / "global.code-snippets").exists()

    @patch("vsc_sync.commands.apply_cmd.AppManager.get_installed_extensions")
    @patch("vsc_sync.commands.apply_cmd.AppManager.install_extension")
    def test_apply_extensions_install(
        self, mock_install, mock_get_installed, temp_dir, mock_vscode_configs_repo
    ):
        """Test applying extensions with installations."""
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

        # Mock currently installed extensions
        mock_get_installed.return_value = ["existing.extension"]
        mock_install.return_value = True

        apply_cmd = ApplyCommand(config_manager)

        target_extensions = ["existing.extension", "new.extension"]
        apply_cmd._apply_extensions(
            app_details, target_extensions, prune_extensions=False
        )

        # Should install the new extension
        mock_install.assert_called_once_with(app_details, "new.extension")

    @patch("vsc_sync.commands.apply_cmd.AppManager.get_installed_extensions")
    @patch("vsc_sync.commands.apply_cmd.AppManager.uninstall_extension")
    def test_apply_extensions_prune(
        self, mock_uninstall, mock_get_installed, temp_dir, mock_vscode_configs_repo
    ):
        """Test applying extensions with pruning."""
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

        # Mock currently installed extensions
        mock_get_installed.return_value = ["wanted.extension", "unwanted.extension"]
        mock_uninstall.return_value = True

        apply_cmd = ApplyCommand(config_manager)

        target_extensions = ["wanted.extension"]
        apply_cmd._apply_extensions(
            app_details, target_extensions, prune_extensions=True
        )

        # Should uninstall the unwanted extension
        mock_uninstall.assert_called_once_with(app_details, "unwanted.extension")

    def test_show_setting_changes(self, temp_dir, mock_vscode_configs_repo):
        """Test showing setting changes."""
        config_manager = ConfigManager(temp_dir / "config.json")

        config = VscSyncConfig(
            vscode_configs_path=mock_vscode_configs_repo, managed_apps={}
        )
        config_manager.save_config(config)

        apply_cmd = ApplyCommand(config_manager)

        current = {
            "editor": {"fontSize": 12, "tabSize": 2},
            "terminal": {"fontSize": 10},
            "oldSetting": "value",
        }

        new = {
            "editor": {"fontSize": 14, "wordWrap": "on", "tabSize": 2},
            "terminal": {"fontSize": 10},
            "newSetting": "value",
        }

        # This should not raise an exception
        apply_cmd._show_setting_changes(current, new)

    @patch("vsc_sync.commands.apply_cmd.Confirm.ask")
    def test_confirm_apply_yes(self, mock_confirm, temp_dir, mock_vscode_configs_repo):
        """Test confirming apply with yes."""
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

        apply_cmd = ApplyCommand(config_manager)

        from vsc_sync.models import MergeResult

        merge_result = MergeResult(
            merged_settings={"test": True}, extensions=["test.extension"]
        )

        mock_confirm.return_value = True

        result = apply_cmd._confirm_apply(
            app_details,
            merge_result,
            include_settings=True,
            include_keybindings=True,
            include_extensions=True,
            include_snippets=True,
        )
        assert result is True

    @patch("vsc_sync.commands.apply_cmd.Confirm.ask")
    def test_confirm_apply_no(self, mock_confirm, temp_dir, mock_vscode_configs_repo):
        """Test confirming apply with no."""
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

        apply_cmd = ApplyCommand(config_manager)

        from vsc_sync.models import MergeResult

        merge_result = MergeResult()

        mock_confirm.return_value = False

        result = apply_cmd._confirm_apply(
            app_details,
            merge_result,
            include_settings=False,
            include_keybindings=False,
            include_extensions=False,
            include_snippets=False,
        )
        assert result is False

    @patch("vsc_sync.commands.apply_cmd.Confirm.ask")
    def test_run_dry_run(self, mock_confirm, temp_dir, mock_vscode_configs_repo):
        """Test running apply command with dry run."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        (app_config_dir / "settings.json").write_text('{"existing": true}')

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

        apply_cmd = ApplyCommand(config_manager)

        # Should not raise exception and should not modify files
        apply_cmd.run(app_alias="test-vscode", dry_run=True)

        # Original settings should be unchanged
        settings_content = (app_config_dir / "settings.json").read_text()
        assert json.loads(settings_content) == {"existing": True}

    @patch("vsc_sync.commands.apply_cmd.Confirm.ask")
    def test_run_force_apply(self, mock_confirm, temp_dir, mock_vscode_configs_repo):
        """Test running apply command with force flag."""
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

        apply_cmd = ApplyCommand(config_manager)

        # Should not prompt for confirmation with force=True
        apply_cmd.run(app_alias="test-vscode", force=True)

        # Should not have called confirm
        mock_confirm.assert_not_called()

        # Should have applied settings
        settings_file = app_config_dir / "settings.json"
        assert settings_file.exists()

    def test_run_with_backup(self, temp_dir, mock_vscode_configs_repo):
        """Test running apply command with backup."""
        config_manager = ConfigManager(temp_dir / "config.json")

        app_config_dir = temp_dir / "vscode_config"
        app_config_dir.mkdir()
        (app_config_dir / "settings.json").write_text('{"original": true}')

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

        apply_cmd = ApplyCommand(config_manager)

        apply_cmd.run(
            app_alias="test-vscode", backup=True, backup_suffix="test", force=True
        )

        # Should have created backup
        backup_dir = temp_dir / "vscode_config.test"
        assert backup_dir.exists()
        assert (backup_dir / "settings.json").exists()

        # Original settings should exist in backup
        backup_settings = json.loads((backup_dir / "settings.json").read_text())
        assert backup_settings == {"original": True}
