"""Tests for keybindings sorting feature."""

import json
from pathlib import Path

from vsc_sync.commands.edit_cmd import EditCommand
from vsc_sync.config import ConfigManager
from vsc_sync.models import AppDetails, VscSyncConfig


def create_config(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    config_manager = ConfigManager(cfg_path)

    # minimal config with dummy repo path
    repo = tmp_path / "repo"
    repo.mkdir()

    app_details = AppDetails(
        alias="vscode",
        config_path=tmp_path / "vscode_cfg",
        executable_path=Path("code"),
    )
    app_details.config_path.mkdir()

    config_manager.save_config(
        VscSyncConfig(vscode_configs_path=repo, managed_apps={"vscode": app_details})
    )
    return config_manager, app_details


def test_sort_keybindings(tmp_path):
    config_manager, app_details = create_config(tmp_path)

    file_path = app_details.config_path / "keybindings.json"

    # Craft unsorted array with duplicates
    data = [
        {"key": "ctrl+c", "command": "copy"},
        {"key": "-ctrl+x", "command": "cut"},
        {"key": "ctrl+c", "command": "otherCopy"},  # duplicate key, last wins
        {"key": "a", "command": "noop"},
    ]
    file_path.write_text(json.dumps(data))

    # Add comment line and trailing char to simulate VS Code file
    file_path.write_text(
        "// header comment\n" + file_path.read_text() + "%", encoding="utf-8"
    )

    cmd = EditCommand(config_manager)

    # Call private sorter with yes=True to skip prompt
    cmd._sort_keybindings(file_path, yes=True)

    sorted_data = json.loads(file_path.read_text())

    # Duplicate removed -> length 3
    assert len(sorted_data) == 3

    # First entry should start with '-' (dash-first rule)
    assert sorted_data[0]["key"].startswith("-")

    # Ensure duplicate removed kept last version (command otherCopy)
    for entry in sorted_data:
        if entry["key"] == "ctrl+c":
            assert entry["command"] == "otherCopy"
