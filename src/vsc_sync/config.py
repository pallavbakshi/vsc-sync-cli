"""Configuration management for vsc-sync CLI."""

import json
import logging
from pathlib import Path
from typing import Optional

from .exceptions import ConfigError
from .models import VscSyncConfig
from .utils import get_vsc_sync_config_path

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages loading and saving of vsc-sync's own configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or get_vsc_sync_config_path()
        self._config: Optional[VscSyncConfig] = None

    def load_config(self) -> VscSyncConfig:
        """Load configuration from disk, creating default if not exists."""
        if not self.config_path.exists():
            logger.info("No configuration file found, creating default config")
            self._config = VscSyncConfig(
                vscode_configs_path=Path.home() / "vscode-configs", managed_apps={}
            )
            return self._config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            self._config = VscSyncConfig(**config_data)
            logger.debug(f"Loaded configuration from {self.config_path}")
            return self._config

        except Exception as e:
            raise ConfigError(
                f"Failed to load configuration from {self.config_path}: {e}"
            )

    def save_config(self, config: Optional[VscSyncConfig] = None) -> None:
        """Save configuration to disk."""
        config_to_save = config or self._config

        if config_to_save is None:
            raise ConfigError("No configuration to save")

        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Convert Pydantic model to dict for JSON serialization
            config_dict = config_to_save.model_dump(mode="json")

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved configuration to {self.config_path}")
            self._config = config_to_save

        except Exception as e:
            raise ConfigError(
                f"Failed to save configuration to {self.config_path}: {e}"
            )

    @property
    def config(self) -> VscSyncConfig:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def is_initialized(self) -> bool:
        """Check if vsc-sync has been initialized."""
        return self.config_path.exists() and bool(self.config.vscode_configs_path)
