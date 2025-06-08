"""Tests for the PRD-based keybindings sorting logic."""

import json
from pathlib import Path

from vsc_sync.commands.edit_cmd import EditCommand
from vsc_sync.config import ConfigManager
from vsc_sync.models import AppDetails, VscSyncConfig


def _setup_app(tmp_path):
    """Create a minimal config & managed app so that EditCommand can work."""

    cfg_path = tmp_path / "cfg.json"
    cm = ConfigManager(cfg_path)

    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    app_details = AppDetails(
        alias="vscode",
        config_path=tmp_path / "vscode_cfg",
        executable_path=Path("code"),
    )
    app_details.config_path.mkdir()

    cm.save_config(
        VscSyncConfig(vscode_configs_path=repo_path, managed_apps={"vscode": app_details})
    )

    return cm, app_details


def test_prd_sorting(tmp_path):
    """Verify that the new PRD ordering rules are applied correctly."""

    config_manager, app = _setup_app(tmp_path)

    kb_file = app.config_path / "keybindings.json"

    unsorted = [
        # Duplicate key, *with* when clause (specific) – should end up **after**
        # the variant without a when clause.
        {"key": "ctrl+c", "command": "copy.when", "when": "editorTextFocus && !multiCursor"},
        # No when clause – should be first within its key group.
        {"key": "ctrl+c", "command": "copy"},
        # Key starting with dash – will appear first overall because '-' sorts
        # before letters in ASCII.
        {"key": "-ctrl+x", "command": "cut"},
        # Completely different key.
        {"key": "a", "command": "noop"},
    ]

    kb_file.write_text(json.dumps(unsorted))

    cmd = EditCommand(config_manager)

    # Perform sorting in-place without interactive confirmation.
    cmd._sort_keybindings(kb_file, yes=True)

    sorted_data = json.loads(kb_file.read_text())

    # Expect 4 entries (duplicates are *not* removed).
    assert len(sorted_data) == 4

    # Overall order assertions -------------------------------------------------
    assert sorted_data[0]["key"].startswith("-")  # '-ctrl+x'
    assert sorted_data[1]["key"] == "a"

    # ctrl+c group – general (no when) comes before specific (with when)
    assert sorted_data[2]["key"] == "ctrl+c"
    assert "when" not in sorted_data[2]

    assert sorted_data[3]["key"] == "ctrl+c"
    assert sorted_data[3].get("when")  # has when clause
