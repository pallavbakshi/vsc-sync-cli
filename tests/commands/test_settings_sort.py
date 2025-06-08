"""Tests for settings.json sorting feature."""

import json
import collections
from pathlib import Path

from vsc_sync.commands.edit_cmd import EditCommand
from vsc_sync.config import ConfigManager
from vsc_sync.models import AppDetails, VscSyncConfig


def _prepare(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cm = ConfigManager(cfg_path)

    repo = tmp_path / "repo"
    repo.mkdir()

    app_details = AppDetails(
        alias="vscode",
        config_path=tmp_path / "vscode_cfg",
        executable_path=Path("code"),
    )
    app_details.config_path.mkdir()

    cm.save_config(
        VscSyncConfig(vscode_configs_path=repo, managed_apps={"vscode": app_details})
    )

    return cm, app_details


def test_settings_sort_and_dedup(tmp_path):
    cm, app = _prepare(tmp_path)

    file_path = app.config_path / "settings.json"

    # Unsorted, with duplicates and comments
    content = (
        "// header comment\n"  # line comment
        "{\n"
        "  \"z.last\": 1,\n"
        "  /* block comment */\n"
        "  \"a.first\": false,\n"
        "  \"a.first\": true,  // duplicate, should win\n"
        "  \"m.middle\": 42\n"
        "}\n"
    )

    file_path.write_text(content)

    cmd = EditCommand(cm)

    cmd._sort_settings(file_path, yes=True)

    # Reload text and parse preserving order via OrderedDict
    ordered = json.loads(
        file_path.read_text(), object_pairs_hook=collections.OrderedDict
    )

    keys = list(ordered.keys())

    # Alphabetical order expected
    assert keys == sorted(keys)

    # Duplicate removed – key 'a.first' occurs only once and value is 'true'
    assert keys.count("a.first") == 1
    assert ordered["a.first"] is True
