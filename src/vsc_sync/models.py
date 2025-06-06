"""Pydantic models for vsc-sync configuration and data structures."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AppDetails(BaseModel):
    """Details about a registered VSCode-like application."""

    alias: str = Field(..., description="Unique alias for the application")
    config_path: Path = Field(
        ..., description="Path to the app's user configuration directory"
    )
    executable_path: Optional[Path] = Field(
        None, description="Path to the app's executable"
    )


class VscSyncConfig(BaseModel):
    """Configuration for the vsc-sync CLI tool itself."""

    vscode_configs_path: Path = Field(
        ..., description="Path to the vscode-configs repository"
    )
    managed_apps: Dict[str, AppDetails] = Field(
        default_factory=dict, description="Dictionary of managed applications by alias"
    )
    default_editor: Optional[str] = Field(
        None, description="Default editor command for 'edit' command"
    )


class ExtensionsConfig(BaseModel):
    """Structure of extensions.json files."""

    recommendations: List[str] = Field(
        default_factory=list, description="List of recommended extension IDs"
    )


class SettingsConfig(BaseModel):
    """Structure for settings.json files - flexible to allow any VSCode settings."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional fields not defined in the model

    settings: Dict[str, Any] = Field(
        default_factory=dict, description="VSCode settings as key-value pairs"
    )


class LayerInfo(BaseModel):
    """Information about a configuration layer."""

    layer_type: str = Field(
        ..., description="Type of layer: base, app, stack, or project"
    )
    layer_name: Optional[str] = Field(
        None, description="Name of the layer (for app/stack/project types)"
    )
    path: Path = Field(..., description="Path to the layer directory")


class MergeResult(BaseModel):
    """Result of merging configuration layers."""

    merged_settings: Dict[str, Any] = Field(default_factory=dict)
    keybindings_source: Optional[Path] = Field(None)
    extensions: List[str] = Field(default_factory=list)
    snippets_paths: List[Path] = Field(default_factory=list)
    layers_applied: List[LayerInfo] = Field(default_factory=list)
