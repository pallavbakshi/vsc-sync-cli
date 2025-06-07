"""Tests for LayerConfigManager."""

import json
import pytest

from vsc_sync.core.config_manager import LayerConfigManager
from vsc_sync.exceptions import LayerNotFoundError


class TestLayerConfigManager:
    """Test class for LayerConfigManager functionality."""

    def test_init_with_valid_path(self, mock_vscode_configs_repo):
        """Test initialization with valid vscode-configs path."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        assert manager.vscode_configs_path == mock_vscode_configs_repo

    def test_init_with_invalid_path(self, temp_dir):
        """Test initialization with invalid vscode-configs path."""
        invalid_path = temp_dir / "nonexistent"
        with pytest.raises(LayerNotFoundError):
            LayerConfigManager(invalid_path)

    def test_get_layer_path_base(self, mock_vscode_configs_repo):
        """Test getting base layer path."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        path = manager.get_layer_path("base")
        assert path == mock_vscode_configs_repo / "base"

    def test_get_layer_path_app(self, mock_vscode_configs_repo):
        """Test getting app layer path."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        path = manager.get_layer_path("app", "vscode")
        assert path == mock_vscode_configs_repo / "apps" / "vscode"

    def test_get_layer_path_stack(self, mock_vscode_configs_repo):
        """Test getting stack layer path."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        path = manager.get_layer_path("stack", "python")
        assert path == mock_vscode_configs_repo / "stacks" / "python"

    def test_get_layer_path_invalid_type(self, mock_vscode_configs_repo):
        """Test getting layer path with invalid type."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        with pytest.raises(ValueError):
            manager.get_layer_path("invalid")

    def test_get_layer_path_missing_name(self, mock_vscode_configs_repo):
        """Test getting layer path without required name."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        with pytest.raises(ValueError):
            manager.get_layer_path("app")

    def test_layer_exists(self, mock_vscode_configs_repo):
        """Test layer existence checking."""
        manager = LayerConfigManager(mock_vscode_configs_repo)

        assert manager.layer_exists("base")
        assert manager.layer_exists("app", "vscode")
        assert manager.layer_exists("stack", "python")
        assert not manager.layer_exists("app", "nonexistent")
        assert not manager.layer_exists("invalid")

    def test_load_json_file_existing(self, mock_vscode_configs_repo):
        """Test loading existing JSON file."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        settings_file = mock_vscode_configs_repo / "base" / "settings.json"

        data = manager.load_json_file(settings_file)
        assert isinstance(data, dict)
        assert "editor.fontSize" in data

    def test_load_json_file_nonexistent(self, mock_vscode_configs_repo):
        """Test loading nonexistent JSON file."""
        manager = LayerConfigManager(mock_vscode_configs_repo)
        nonexistent_file = mock_vscode_configs_repo / "nonexistent.json"

        data = manager.load_json_file(nonexistent_file)
        assert data == {}

    def test_deep_merge_dicts(self, mock_vscode_configs_repo):
        """Test deep merging of dictionaries."""
        manager = LayerConfigManager(mock_vscode_configs_repo)

        base = {"editor": {"fontSize": 12, "tabSize": 2}, "terminal": {"fontSize": 10}}
        override = {
            "editor": {"fontSize": 14, "wordWrap": "on"},
            "workbench": {"colorTheme": "dark"},
        }

        result = manager.deep_merge_dicts(base, override)

        assert result["editor"]["fontSize"] == 14  # Overridden
        assert result["editor"]["tabSize"] == 2  # Preserved
        assert result["editor"]["wordWrap"] == "on"  # Added
        assert result["terminal"]["fontSize"] == 10  # Preserved
        assert result["workbench"]["colorTheme"] == "dark"  # Added

    def test_collect_extensions(self, mock_vscode_configs_repo):
        """Test collecting extensions from layers."""
        manager = LayerConfigManager(mock_vscode_configs_repo)

        # Create layer info objects
        from vsc_sync.models import LayerInfo

        layers = [
            LayerInfo(layer_type="base", path=mock_vscode_configs_repo / "base"),
            LayerInfo(
                layer_type="stack",
                layer_name="python",
                path=mock_vscode_configs_repo / "stacks" / "python",
            ),
        ]

        extensions = manager.collect_extensions(layers)

        # Should contain extensions from both layers, deduplicated
        assert "ms-python.python" in extensions
        assert "ms-python.pylint" in extensions
        assert len(extensions) == len(set(extensions))  # No duplicates

    def test_find_keybindings(self, mock_vscode_configs_repo):
        """Test finding keybindings from most specific layer."""
        manager = LayerConfigManager(mock_vscode_configs_repo)

        from vsc_sync.models import LayerInfo

        layers = [
            LayerInfo(layer_type="base", path=mock_vscode_configs_repo / "base"),
            LayerInfo(
                layer_type="app",
                layer_name="vscode",
                path=mock_vscode_configs_repo / "apps" / "vscode",
            ),
        ]

        keybindings_path = manager.find_keybindings(layers)

        # Should find keybindings.json from base layer (most specific available)
        assert (
            keybindings_path == mock_vscode_configs_repo / "base" / "keybindings.json"
        )

    # -------------------- Tasks.json Support --------------------

    def test_find_tasks_file_precedence(self, temp_dir):
        """Ensure tasks.json is selected from most specific layer."""
        # Build minimal repo structure with tasks in different layers
        repo = temp_dir / "repo"
        (repo / "base").mkdir(parents=True)
        (repo / "base" / "tasks.json").write_text("{}")

        app_layer = repo / "apps" / "cursor"
        app_layer.mkdir(parents=True)
        (app_layer / "tasks.json").write_text('{"label": "build"}')

        stack_layer = repo / "stacks" / "python"
        stack_layer.mkdir(parents=True)
        (stack_layer / "tasks.json").write_text('{"label": "lint"}')

        manager = LayerConfigManager(repo)

        from vsc_sync.models import LayerInfo

        layers = [
            LayerInfo(layer_type="base", path=repo / "base"),
            LayerInfo(layer_type="app", layer_name="cursor", path=app_layer),
            LayerInfo(layer_type="stack", layer_name="python", path=stack_layer),
        ]

        # stack should win
        tasks_path = manager.find_tasks_file(layers)
        assert tasks_path == stack_layer / "tasks.json"

    def test_merge_layers_tasks_source(self, temp_dir):
        """tasks_source should be populated in MergeResult."""
        repo = temp_dir / "repo"
        (repo / "base").mkdir(parents=True)
        (repo / "base" / "settings.json").write_text("{}")
        (repo / "base" / "tasks.json").write_text("{}")

        manager = LayerConfigManager(repo)
        result = manager.merge_layers(app_alias=None, stacks=None)
        assert result.tasks_source == repo / "base" / "tasks.json"

    def test_collect_snippets(self, mock_vscode_configs_repo):
        """Test collecting snippet directories."""
        manager = LayerConfigManager(mock_vscode_configs_repo)

        from vsc_sync.models import LayerInfo

        layers = [LayerInfo(layer_type="base", path=mock_vscode_configs_repo / "base")]

        snippets_paths = manager.collect_snippets(layers)

        assert len(snippets_paths) == 1
        assert snippets_paths[0] == mock_vscode_configs_repo / "base" / "snippets"

    def test_merge_layers_basic(self, mock_vscode_configs_repo):
        """Test basic layer merging."""
        manager = LayerConfigManager(mock_vscode_configs_repo)

        result = manager.merge_layers(app_alias="vscode", stacks=["python"])

        # Check merged settings
        assert "editor.fontSize" in result.merged_settings  # From base
        assert "workbench.colorTheme" in result.merged_settings  # From app
        assert "python.defaultInterpreterPath" in result.merged_settings  # From stack

        # Check extensions
        assert "ms-python.python" in result.extensions
        assert "ms-python.pylint" in result.extensions

        # Check layers applied
        assert len(result.layers_applied) == 3  # base + app + stack

        # Check keybindings
        assert result.keybindings_source is not None

    def test_merge_layers_missing_app(self, mock_vscode_configs_repo):
        """Test merging with nonexistent app layer."""
        manager = LayerConfigManager(mock_vscode_configs_repo)

        result = manager.merge_layers(app_alias="nonexistent", stacks=["python"])

        # Should still work with base and stack layers
        assert len(result.layers_applied) == 2  # base + stack only
        assert "editor.fontSize" in result.merged_settings
        assert "python.defaultInterpreterPath" in result.merged_settings
        assert "workbench.colorTheme" not in result.merged_settings  # App layer skipped
