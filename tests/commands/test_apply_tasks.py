"""Tests for tasks.json handling in ApplyCommand."""

from pathlib import Path

from vsc_sync.commands.apply_cmd import ApplyCommand
from vsc_sync.models import AppDetails, MergeResult, LayerInfo, VscSyncConfig
from vsc_sync.config import ConfigManager


def test_apply_tasks_file(temp_dir):
    """_apply_tasks should copy tasks.json into the app config directory."""
    # Setup mock app config dir
    app_config_dir = temp_dir / "user_config"
    app_config_dir.mkdir()

    app_details = AppDetails(
        alias="vscode",
        config_path=app_config_dir,
        executable_path=Path("/usr/bin/code"),
    )

    # Create tasks source file
    tasks_source = temp_dir / "tasks.json"
    tasks_source.write_text('{"label": "build"}')

    merge_result = MergeResult(
        merged_settings={},
        keybindings_source=None,
        extensions=[],
        snippets_paths=[],
        layers_applied=[LayerInfo(layer_type="base", path=temp_dir)],
        tasks_source=tasks_source,
    )

    # Minimal ConfigManager with dummy repo path
    repo_path = temp_dir / "repo"
    repo_path.mkdir()

    cfg_manager = ConfigManager(temp_dir / "config.json")
    cfg_manager.save_config(
        VscSyncConfig(vscode_configs_path=repo_path, managed_apps={})
    )

    cmd = ApplyCommand(cfg_manager)

    # Call the private method directly
    cmd._apply_tasks(app_details, tasks_source)

    assert (app_config_dir / "tasks.json").exists()
    assert (app_config_dir / "tasks.json").read_text() == tasks_source.read_text()
