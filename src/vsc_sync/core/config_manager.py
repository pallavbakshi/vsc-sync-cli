"""Core configuration management for merging and processing vscode-configs layers."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..exceptions import LayerNotFoundError
from ..models import ExtensionsConfig, LayerInfo, MergeResult

logger = logging.getLogger(__name__)


class LayerConfigManager:
    """Manages loading, merging, and processing of vscode-configs layers."""

    def __init__(self, vscode_configs_path: Path):
        self.vscode_configs_path = Path(vscode_configs_path)
        if not self.vscode_configs_path.exists():
            raise LayerNotFoundError(
                f"vscode-configs directory not found: {vscode_configs_path}"
            )

    def get_layer_path(self, layer_type: str, layer_name: Optional[str] = None) -> Path:
        """Get the path to a specific layer directory."""
        if layer_type == "base":
            return self.vscode_configs_path / "base"
        elif layer_type in ("app", "stack", "project"):
            if not layer_name:
                raise ValueError(
                    f"layer_name is required for layer_type '{layer_type}'"
                )
            return self.vscode_configs_path / f"{layer_type}s" / layer_name
        else:
            raise ValueError(f"Unknown layer_type: {layer_type}")

    def layer_exists(self, layer_type: str, layer_name: Optional[str] = None) -> bool:
        """Check if a layer exists."""
        try:
            layer_path = self.get_layer_path(layer_type, layer_name)
            return layer_path.exists() and layer_path.is_dir()
        except ValueError:
            return False

    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a JSON file, returning empty dict if file doesn't exist."""
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load JSON file {file_path}: {e}")
            return {}

    def deep_merge_dicts(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self.deep_merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def collect_extensions(self, layers: List[LayerInfo]) -> List[str]:
        """Collect and deduplicate extensions from multiple layers."""
        extensions = []

        for layer in layers:
            extensions_file = layer.path / "extensions.json"
            if extensions_file.exists():
                try:
                    extensions_data = self.load_json_file(extensions_file)
                    config = ExtensionsConfig(**extensions_data)
                    extensions.extend(config.recommendations)
                except Exception as e:
                    logger.warning(
                        f"Failed to load extensions from {extensions_file}: {e}"
                    )

        # Return deduplicated list while preserving order
        seen = set()
        result = []
        for ext in extensions:
            if ext not in seen:
                seen.add(ext)
                result.append(ext)

        return result

    def find_keybindings(self, layers: List[LayerInfo]) -> Optional[Path]:
        """Find keybindings.json from the most specific layer that has it."""
        # Reverse to check most specific layers first
        for layer in reversed(layers):
            keybindings_file = layer.path / "keybindings.json"
            if keybindings_file.exists():
                return keybindings_file

        return None

    def collect_snippets(self, layers: List[LayerInfo]) -> List[Path]:
        """Collect snippet directories/files from all layers."""
        snippets_paths = []

        for layer in layers:
            snippets_dir = layer.path / "snippets"
            if snippets_dir.exists():
                snippets_paths.append(snippets_dir)

        return snippets_paths

    def merge_layers(
        self, app_alias: Optional[str] = None, stacks: Optional[List[str]] = None
    ) -> MergeResult:
        """Merge configuration layers in order of precedence."""
        layers = []
        stacks = stacks or []

        # Build list of layers in order of precedence (base -> app -> stacks)
        base_layer = LayerInfo(
            layer_type="base", layer_name=None, path=self.get_layer_path("base")
        )
        layers.append(base_layer)

        # Add app layer if specified
        if app_alias:
            if self.layer_exists("app", app_alias):
                app_layer = LayerInfo(
                    layer_type="app",
                    layer_name=app_alias,
                    path=self.get_layer_path("app", app_alias),
                )
                layers.append(app_layer)
            else:
                logger.warning(f"App layer '{app_alias}' not found, skipping")

        # Add stack layers
        for stack in stacks:
            if self.layer_exists("stack", stack):
                stack_layer = LayerInfo(
                    layer_type="stack",
                    layer_name=stack,
                    path=self.get_layer_path("stack", stack),
                )
                layers.append(stack_layer)
            else:
                logger.warning(f"Stack layer '{stack}' not found, skipping")

        # Merge settings.json from all layers
        merged_settings = {}
        for layer in layers:
            settings_file = layer.path / "settings.json"
            if settings_file.exists():
                layer_settings = self.load_json_file(settings_file)
                merged_settings = self.deep_merge_dicts(merged_settings, layer_settings)

        # Collect other components
        extensions = self.collect_extensions(layers)
        keybindings_source = self.find_keybindings(layers)
        snippets_paths = self.collect_snippets(layers)

        return MergeResult(
            merged_settings=merged_settings,
            keybindings_source=keybindings_source,
            extensions=extensions,
            snippets_paths=snippets_paths,
            layers_applied=layers,
        )
