"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from vsc_sync.models import AppDetails, VscSyncConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_vscode_configs_repo(temp_dir):
    """Create a mock vscode-configs repository structure."""
    repo_path = temp_dir / "vscode-configs"

    # Create base layer
    base_dir = repo_path / "base"
    base_dir.mkdir(parents=True)

    (base_dir / "settings.json").write_text('{"editor.fontSize": 14}')
    (base_dir / "keybindings.json").write_text("[]")
    (base_dir / "extensions.json").write_text(
        '{"recommendations": ["ms-python.python"]}'
    )

    snippets_dir = base_dir / "snippets"
    snippets_dir.mkdir()
    (snippets_dir / "global.code-snippets").write_text("{}")

    # Create app layer
    app_dir = repo_path / "apps" / "vscode"
    app_dir.mkdir(parents=True)
    (app_dir / "settings.json").write_text(
        '{"workbench.colorTheme": "Dark+ (default dark)"}'
    )

    # Create stack layer
    stack_dir = repo_path / "stacks" / "python"
    stack_dir.mkdir(parents=True)
    (stack_dir / "settings.json").write_text(
        '{"python.defaultInterpreterPath": "/usr/bin/python3"}'
    )
    (stack_dir / "extensions.json").write_text(
        '{"recommendations": ["ms-python.pylint"]}'
    )

    return repo_path


@pytest.fixture
def mock_app_config_dir(temp_dir):
    """Create a mock VSCode app configuration directory."""
    config_dir = temp_dir / "vscode_config"
    config_dir.mkdir()

    (config_dir / "settings.json").write_text('{"editor.tabSize": 2}')
    (config_dir / "keybindings.json").write_text("[]")

    snippets_dir = config_dir / "snippets"
    snippets_dir.mkdir()

    return config_dir


@pytest.fixture
def sample_app_details(mock_app_config_dir):
    """Create sample AppDetails for testing."""
    return AppDetails(
        alias="test-vscode",
        config_path=mock_app_config_dir,
        executable_path=Path("/usr/bin/code"),
    )


@pytest.fixture
def sample_vsc_sync_config(mock_vscode_configs_repo, sample_app_details):
    """Create sample VscSyncConfig for testing."""
    return VscSyncConfig(
        vscode_configs_path=mock_vscode_configs_repo,
        managed_apps={"test-vscode": sample_app_details},
    )


@pytest.fixture
def mock_config_manager(temp_dir, sample_vsc_sync_config):
    """Create a mock ConfigManager with test configuration."""
    from vsc_sync.config import ConfigManager

    config_path = temp_dir / "config.json"
    manager = ConfigManager(config_path)
    manager._config = sample_vsc_sync_config

    return manager
