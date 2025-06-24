"""Core configuration management for merging and processing vscode-configs layers."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..exceptions import LayerNotFoundError, VscSyncError
from ..models import ExtensionsConfig, LayerInfo, MergeResult

logger = logging.getLogger(__name__)


class LayerConfigManager:
    """Manages loading, merging, and processing of vscode-configs layers."""

    def __init__(self, vscode_configs_path: Path):
        self.vscode_configs_path = Path(vscode_configs_path)
        if not self.vscode_configs_path.exists():
            raise LayerNotFoundError(
                f"vscode-configs directory not found: {vscode_configs_path}",
            )

    def get_layer_path(self, layer_type: str, layer_name: Optional[str] = None) -> Path:
        """Get the path to a specific layer directory."""
        if layer_type == "base":
            return self.vscode_configs_path / "base"
        if layer_type in ("app", "stack", "project"):
            if not layer_name:
                raise ValueError(
                    f"layer_name is required for layer_type '{layer_type}'",
                )
            return self.vscode_configs_path / f"{layer_type}s" / layer_name
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
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load JSON file {file_path}: {e}")
            return {}

    def deep_merge_dicts(
        self, base: Dict[str, Any], override: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deep-merge two dictionaries while preserving VSCode "last key wins" ordering.

        * Keys from *base* are copied first.
        * For each key in *override*:
            – If both values are dictionaries we recurse.
            – Otherwise the *override* value should win.

        To mimic VSCode's behaviour (where the *last* occurrence of a setting
        in the same file wins) we re-insert overridden keys at the end of the
        resulting OrderedDict.  Regular ``dict`` preserves insertion order in
        Python ≥ 3.7, so a pop / re-assign dance is enough.
        """

        # We rely on insertion-order preservation, guaranteed since CPython 3.7.
        result: Dict[str, Any] = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Deep merge nested dictionaries first
                merged_nested = self.deep_merge_dicts(result[key], value)
                # Re-insert to move the key to the end (higher precedence)
                result.pop(key)
                result[key] = merged_nested
            else:
                # Remove any existing key so that the new value ends up last
                if key in result:
                    result.pop(key)
                result[key] = value

        return result

    def collect_extensions(self, layers: List[LayerInfo]) -> List[str]:
        """Collect and deduplicate extensions from multiple layers."""
        extensions = []

        for layer in layers:
            # Handle custom file layers
            if layer.layer_type == "custom_file" and layer.original_file_path:
                if layer.original_file_path.name == "extensions.json":
                    extensions_file = layer.original_file_path
                else:
                    continue  # Skip if not an extensions file
            else:
                # Handle directory layers
                extensions_file = layer.path / "extensions.json"

            if extensions_file.exists():
                try:
                    extensions_data = self.load_json_file(extensions_file)
                    config = ExtensionsConfig(**extensions_data)
                    extensions.extend(config.recommendations)
                except Exception as e:
                    logger.warning(
                        f"Failed to load extensions from {extensions_file}: {e}",
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
            # Handle custom file layers
            if layer.layer_type == "custom_file" and layer.original_file_path:
                if layer.original_file_path.name == "keybindings.json":
                    return layer.original_file_path
            else:
                # Handle directory layers
                keybindings_file = layer.path / "keybindings.json"
                if keybindings_file.exists():
                    return keybindings_file

        return None

    def merge_keybindings(self, layers: List[LayerInfo]) -> List[Dict]:
        """Merge keybindings from all layers, base first, then more specific layers."""
        merged_keybindings = []

        # Process layers in order (base first, then more specific)
        for layer in layers:
            # Handle custom file layers
            if layer.layer_type == "custom_file" and layer.original_file_path:
                if layer.original_file_path.name == "keybindings.json":
                    keybindings_file = layer.original_file_path
                else:
                    continue  # Skip if not a keybindings file
            else:
                # Handle directory layers
                keybindings_file = layer.path / "keybindings.json"

            if keybindings_file.exists():
                try:
                    layer_keybindings = self.load_json_file(keybindings_file)
                    if isinstance(layer_keybindings, list):
                        merged_keybindings.extend(layer_keybindings)
                        logger.debug(f"Added {len(layer_keybindings)} keybindings from {layer.layer_type}/{layer.layer_name or 'base'}")
                except Exception as e:
                    logger.warning(f"Failed to load keybindings from {keybindings_file}: {e}")

        return merged_keybindings

    def find_tasks_file(self, layers: List[LayerInfo]) -> Optional[Path]:
        """Find tasks.json from the most specific layer that has it."""
        # Check layers in reverse precedence (most specific first)
        for layer in reversed(layers):
            # Handle custom file layers
            if layer.layer_type == "custom_file" and layer.original_file_path:
                if layer.original_file_path.name == "tasks.json":
                    return layer.original_file_path
            else:
                # Handle directory layers
                tasks_file = layer.path / "tasks.json"
                if tasks_file.exists():
                    return tasks_file

        return None

    def collect_snippets(self, layers: List[LayerInfo]) -> List[Path]:
        """Collect snippet directories/files from all layers."""
        snippets_paths = []

        for layer in layers:
            # Handle custom file layers (snippets are typically directories, but could be files)
            if layer.layer_type == "custom_file" and layer.original_file_path:
                # Skip individual snippet files for now, as snippets are typically directories
                continue
            # Handle directory layers
            snippets_dir = layer.path / "snippets"
            if snippets_dir.exists():
                snippets_paths.append(snippets_dir)

        return snippets_paths

    def merge_layers(
        self, app_alias: Optional[str] = None, stacks: Optional[List[str]] = None,
    ) -> MergeResult:
        """Merge configuration layers in order of precedence."""
        layers = []
        stacks = stacks or []

        # Build list of layers in order of precedence (base -> app -> stacks)
        base_layer = LayerInfo(
            layer_type="base", layer_name=None, path=self.get_layer_path("base"),
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
        keybindings_source = self.find_keybindings(layers)  # Keep for backward compatibility
        merged_keybindings = self.merge_keybindings(layers)  # New merged approach
        snippets_paths = self.collect_snippets(layers)
        tasks_source = self.find_tasks_file(layers)

        return MergeResult(
            merged_settings=merged_settings,
            keybindings_source=keybindings_source,
            merged_keybindings=merged_keybindings,
            tasks_source=tasks_source,
            extensions=extensions,
            snippets_paths=snippets_paths,
            layers_applied=layers,
        )

    def merge_custom_layers(self, custom_layers: List[Tuple[int, Path]]) -> MergeResult:
        """Merge configuration from custom layer paths."""
        if not custom_layers:
            raise VscSyncError("No custom layers provided")

        # Sort by layer index to ensure proper precedence
        custom_layers.sort(key=lambda x: x[0])

        layers = []
        for layer_index, layer_path in custom_layers:
            # Validate and process the layer path
            processed_layer = self._process_custom_layer_path(layer_path, layer_index)
            layers.append(processed_layer)

        # Merge settings.json from all layers
        merged_settings = {}
        for layer in layers:
            settings_data = self._extract_settings_from_layer(layer)
            if settings_data:
                merged_settings = self.deep_merge_dicts(merged_settings, settings_data)

        # Collect other components
        extensions = self.collect_extensions(layers)
        keybindings_source = self.find_keybindings(layers)  # Keep for backward compatibility
        merged_keybindings = self.merge_keybindings(layers)  # New merged approach
        snippets_paths = self.collect_snippets(layers)
        tasks_source = self.find_tasks_file(layers)

        return MergeResult(
            merged_settings=merged_settings,
            keybindings_source=keybindings_source,
            merged_keybindings=merged_keybindings,
            tasks_source=tasks_source,
            extensions=extensions,
            snippets_paths=snippets_paths,
            layers_applied=layers,
        )

    def _process_custom_layer_path(self, layer_path: Path, layer_index: int) -> LayerInfo:
        """Process a custom layer path (file or directory) into a LayerInfo object."""
        if not layer_path.exists():
            raise VscSyncError(f"Custom layer path does not exist: {layer_path}")

        if layer_path.is_file():
            # If it's a file, create a virtual layer that references the specific file
            return LayerInfo(
                layer_type="custom_file",
                layer_name=f"layer{layer_index}",
                path=layer_path.parent,  # Use parent dir for compatibility
                original_file_path=layer_path,  # Store the actual file path
            )
        if layer_path.is_dir():
            # If it's a directory, use it directly
            return LayerInfo(
                layer_type="custom_dir",
                layer_name=f"layer{layer_index}",
                path=layer_path,
            )
        raise VscSyncError(f"Invalid layer path (not a file or directory): {layer_path}")

    def _extract_settings_from_layer(self, layer: LayerInfo) -> Dict[str, Any]:
        """Extract settings from a custom layer, handling both file and directory layers."""
        if layer.layer_type == "custom_file" and layer.original_file_path:
            # For file layers, check if the file is settings.json
            if layer.original_file_path.name == "settings.json":
                return self.load_json_file(layer.original_file_path)
            return {}
        # For directory layers, look for settings.json in the directory
        settings_file = layer.path / "settings.json"
        return self.load_json_file(settings_file)
