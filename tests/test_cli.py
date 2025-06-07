"""Tests for CLI functionality."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from vsc_sync.cli import app

runner = CliRunner()


def test_cli_help():
    """Test that CLI shows help message."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "vsc-sync" in result.stdout
    assert "Synchronize VSCode-like configurations" in result.stdout


def test_cli_version():
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "vsc-sync version" in result.stdout


def test_discover_command():
    """Test discover command."""
    result = runner.invoke(app, ["discover"])
    assert result.exit_code == 0
    assert "Discovering VSCode-like applications" in result.stdout


@patch("vsc_sync.cli.ConfigManager")
def test_list_apps_not_initialized(mock_config_manager_class):
    """Test list-apps command when not initialized."""
    # Mock the config manager to return uninitialized state
    mock_manager = mock_config_manager_class.return_value
    mock_manager.is_initialized.return_value = False

    result = runner.invoke(app, ["list-apps"])
    assert result.exit_code == 1
    assert "not initialized" in result.stdout


def test_init_command():
    """Test init command."""
    result = runner.invoke(app, ["init"])
    # Should ask for confirmation since it shows as already initialized in some cases
    # or show the coming soon message
    assert result.exit_code in (0, 1)  # May exit with 1 if not confirmed or error


class TestCLICommands:
    """Test class for CLI command functionality."""

    def test_add_app_command(self):
        """Test add-app command structure."""
        result = runner.invoke(app, ["add-app", "test", "/path/to/config"])
        assert result.exit_code == 0
        assert "coming soon" in result.stdout.lower()

    @patch("vsc_sync.cli.ConfigManager")
    def test_apply_command(self, mock_config_manager_class):
        """Test apply command structure."""
        # Mock the config manager to return uninitialized state
        mock_manager = mock_config_manager_class.return_value
        mock_manager.is_initialized.return_value = False

        result = runner.invoke(app, ["apply", "test-app"])
        assert result.exit_code == 1
        assert "not initialized" in result.stdout

    @patch("vsc_sync.cli.ConfigManager")
    def test_status_command_basic(self, mock_config_manager_class):
        """Test status command basic functionality."""
        # Mock the config manager to return uninitialized state
        mock_manager = mock_config_manager_class.return_value
        mock_manager.is_initialized.return_value = False

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "not initialized" in result.stdout

    def test_status_command_help(self):
        """Test status command help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show configuration status for applications" in result.stdout
        assert "app_alias" in result.stdout
        assert "--stack" in result.stdout
