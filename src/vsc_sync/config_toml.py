"""TOML-based system configuration management."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .exceptions import VscSyncError
from .models import TomlConfig

logger = logging.getLogger(__name__)


class TomlConfigManager:
    """Manages loading and parsing of the system-wide TOML configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the TOML config manager.
        
        Args:
            config_path: Path to the TOML config file. If None, uses default location.
        """
        if config_path is None:
            config_path = self.get_default_config_path()
        
        self.config_path = Path(config_path)
        self._config: Optional[TomlConfig] = None

    @staticmethod
    def get_default_config_path() -> Path:
        """Get the default path for the TOML configuration file."""
        return Path.home() / ".config" / "vsc-sync" / "config.toml"

    def ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def config_exists(self) -> bool:
        """Check if the TOML configuration file exists."""
        return self.config_path.exists()

    def load_config(self) -> TomlConfig:
        """Load the TOML configuration file.
        
        Returns:
            TomlConfig: The loaded configuration, or default config if file doesn't exist.
        """
        if self._config is not None:
            return self._config

        if not self.config_exists():
            logger.debug(f"TOML config file not found at {self.config_path}, using defaults")
            self._config = TomlConfig()
            return self._config

        try:
            with open(self.config_path, "rb") as f:
                toml_data = tomllib.load(f)
            
            # Convert the TOML data to our model
            self._config = TomlConfig(**toml_data)
            logger.debug(f"Loaded TOML config from {self.config_path}")
            return self._config

        except Exception as e:
            raise VscSyncError(f"Failed to load TOML config from {self.config_path}: {e}") from e

    def save_config(self, config: TomlConfig) -> None:
        """Save the TOML configuration to file.
        
        Args:
            config: The configuration to save.
        """
        self.ensure_config_dir()
        
        try:
            # Convert Pydantic model to dict for TOML serialization
            config_dict = self._model_to_toml_dict(config)
            toml_content = self._dict_to_toml_string(config_dict)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(toml_content)
            
            self._config = config
            logger.info(f"Saved TOML config to {self.config_path}")

        except Exception as e:
            raise VscSyncError(f"Failed to save TOML config to {self.config_path}: {e}") from e

    def create_example_config(self) -> TomlConfig:
        """Create an example configuration with common settings.
        
        Returns:
            TomlConfig: Example configuration with sample data.
        """
        from .models import DefaultConfig, LayerAlias
        
        # Create example layer aliases
        layer_aliases = {
            "base": LayerAlias(
                name="base",
                path=Path("~/vscode-configs/base"),
                description="Base configuration layer"
            ),
            "python": LayerAlias(
                name="python",
                path=Path("~/vscode-configs/stacks/python"),
                description="Python development settings"
            ),
            "web": LayerAlias(
                name="web",
                path=Path("~/vscode-configs/stacks/web"),
                description="Web development settings"
            ),
            "personal": LayerAlias(
                name="personal",
                path=Path("~/my-configs/personal-settings.json"),
                description="Personal preference overrides"
            )
        }
        
        # Create example layer presets
        layer_presets = {
            "python-dev": ["base", "python", "personal"],
            "web-dev": ["base", "web", "personal"],
            "minimal": ["base"]
        }
        
        # Create defaults with common settings
        defaults = DefaultConfig(
            components=["settings", "keybindings", "extensions"],
            backup=True,
            extension_mode="add"
        )
        
        # Create editor-specific settings
        editor_settings = {
            "vscode": {
                "auto_backup": True,
                "extension_timeout": 10
            },
            "cursor": {
                "auto_backup": False,
                "extension_timeout": 15
            }
        }
        
        return TomlConfig(
            defaults=defaults,
            vscode_configs_path=Path("~/vscode-configs"),  # Default path
            layer_aliases=layer_aliases,
            layer_presets=layer_presets,
            editor_settings=editor_settings
        )

    def _model_to_toml_dict(self, config: TomlConfig) -> Dict[str, Any]:
        """Convert Pydantic model to a dict suitable for TOML serialization."""
        data = config.model_dump()
        
        # Convert Path objects to strings
        def convert_paths(obj):
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            elif isinstance(obj, Path):
                return str(obj)
            else:
                return obj
        
        return convert_paths(data)

    def _dict_to_toml_string(self, data: Dict[str, Any]) -> str:
        """Convert a dictionary to a TOML string.
        
        Note: This is a simple implementation. For production use,
        consider using a proper TOML serialization library like tomli-w.
        """
        lines = []
        
        def write_section(section_data: Dict[str, Any], section_path: str = ""):
            """Write a section of the TOML file."""
            simple_items = {}
            complex_items = {}
            
            # Separate simple and complex items
            for key, value in section_data.items():
                if isinstance(value, dict):
                    complex_items[key] = value
                else:
                    simple_items[key] = value
            
            # Write simple items first
            for key, value in simple_items.items():
                if isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                elif isinstance(value, bool):
                    lines.append(f'{key} = {str(value).lower()}')
                elif isinstance(value, list):
                    if all(isinstance(item, str) for item in value):
                        items_str = ", ".join(f'"{item}"' for item in value)
                        lines.append(f'{key} = [{items_str}]')
                    else:
                        lines.append(f'{key} = {value}')
                else:
                    lines.append(f'{key} = {value}')
            
            # Write complex items as subsections
            for key, value in complex_items.items():
                if section_path:
                    subsection_path = f"{section_path}.{key}"
                else:
                    subsection_path = key
                
                lines.append(f'\n[{subsection_path}]')
                write_section(value, subsection_path)
        
        # Write general settings first
        general_settings = {}
        if "vscode_configs_path" in data and data["vscode_configs_path"]:
            general_settings["vscode_configs_path"] = data["vscode_configs_path"]
        
        if general_settings:
            lines.append("# Path to vscode-configs repository for intelligent layer resolution")
            for key, value in general_settings.items():
                if isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                else:
                    lines.append(f'{key} = {value}')
            lines.append('')
        
        # Write defaults section
        if "defaults" in data:
            lines.append('[defaults]')
            write_section(data["defaults"])
            lines.append('')
        
        # Write layer_aliases section
        if "layer_aliases" in data and data["layer_aliases"]:
            for alias_name, alias_data in data["layer_aliases"].items():
                lines.append(f'[layer_aliases.{alias_name}]')
                write_section(alias_data)
                lines.append('')
        
        # Write layer_presets section
        if "layer_presets" in data and data["layer_presets"]:
            lines.append('[layer_presets]')
            for preset_name, preset_layers in data["layer_presets"].items():
                layers_str = ", ".join(f'"{layer}"' for layer in preset_layers)
                lines.append(f'{preset_name} = [{layers_str}]')
            lines.append('')
        
        # Write editor_settings section
        if "editor_settings" in data and data["editor_settings"]:
            for editor_name, editor_data in data["editor_settings"].items():
                lines.append(f'[editor_settings.{editor_name}]')
                write_section(editor_data)
                lines.append('')
        
        return '\n'.join(lines)

    def resolve_layer_alias(self, alias_name: str) -> Optional[Path]:
        """Resolve a layer alias to its path.
        
        Args:
            alias_name: Name of the layer alias to resolve.
            
        Returns:
            Path to the layer, or None if alias not found.
        """
        config = self.load_config()
        
        if alias_name in config.layer_aliases:
            alias = config.layer_aliases[alias_name]
            return Path(alias.path).expanduser()
        
        return None

    def resolve_layer_preset(self, preset_name: str) -> Optional[List[Path]]:
        """Resolve a layer preset to a list of paths.
        
        Args:
            preset_name: Name of the layer preset to resolve.
            
        Returns:
            List of paths for the preset, or None if preset not found.
        """
        config = self.load_config()
        
        if preset_name not in config.layer_presets:
            return None
        
        preset_aliases = config.layer_presets[preset_name]
        resolved_paths = []
        
        for layer_spec in preset_aliases:
            # Use full resolution for preset items (intelligent + alias + literal)
            path = self.resolve_layer_spec(layer_spec)
            if path is None:
                logger.warning(f"Layer spec '{layer_spec}' in preset '{preset_name}' could not be resolved")
                continue
            resolved_paths.append(path)
        
        return resolved_paths if resolved_paths else None

    def find_layer_by_name(self, layer_name: str) -> Optional[Path]:
        """Find a layer by name in the vscode-configs directory structure.
        
        Searches in the following order:
        1. Direct match in base/ directory (base)
        2. Match in apps/ directory (vscode, cursor, etc.)
        3. Match in stacks/ directory (python, javascript, etc.)
        4. Match in projects/ directory (react-app, etc.)
        
        Args:
            layer_name: Name of the layer to find (e.g., "base", "vscode", "python")
            
        Returns:
            Path to the layer directory, or None if not found.
        """
        config = self.load_config()
        
        if not config.vscode_configs_path:
            logger.debug("No vscode_configs_path set in TOML config, skipping intelligent resolution")
            return None
        
        vscode_configs_dir = Path(config.vscode_configs_path).expanduser()
        
        if not vscode_configs_dir.exists():
            logger.warning(f"vscode_configs_path does not exist: {vscode_configs_dir}")
            return None
        
        # Search order: base, apps, stacks, projects
        search_paths = [
            vscode_configs_dir / layer_name,  # Direct match (for "base")
            vscode_configs_dir / "apps" / layer_name,
            vscode_configs_dir / "stacks" / layer_name,
            vscode_configs_dir / "projects" / layer_name,
        ]
        
        for search_path in search_paths:
            if search_path.exists() and search_path.is_dir():
                logger.debug(f"Found layer '{layer_name}' at {search_path}")
                return search_path
        
        logger.debug(f"Layer '{layer_name}' not found in vscode-configs directory structure")
        return None

    def resolve_layer_spec(self, layer_spec: str) -> Optional[Path]:
        """Resolve a layer specification using multiple fallback strategies.
        
        Resolution order:
        1. Try as layer name in vscode-configs directory (base, vscode, python, etc.)
        2. Try as layer alias from config.toml
        3. Try as literal path
        
        Args:
            layer_spec: Layer specification (name, alias, or path)
            
        Returns:
            Resolved path, or None if resolution failed.
        """
        # Strategy 1: Try intelligent name resolution
        resolved_path = self.find_layer_by_name(layer_spec)
        if resolved_path is not None:
            return resolved_path
        
        # Strategy 2: Try alias resolution
        resolved_path = self.resolve_layer_alias(layer_spec)
        if resolved_path is not None:
            return resolved_path
        
        # Strategy 3: Try as literal path
        literal_path = Path(layer_spec).expanduser()
        if literal_path.exists():
            return literal_path
        
        logger.warning(f"Could not resolve layer specification: {layer_spec}")
        return None