"""General utility functions for vsc-sync."""

import logging
import platform
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def get_platform_config_dir() -> Path:
    """Get the platform-specific configuration directory."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        return Path.home() / "AppData" / "Roaming"
    else:  # Linux and others
        return Path.home() / ".config"


def get_vsc_sync_config_path() -> Path:
    """Get the path where vsc-sync stores its own configuration."""
    config_dir = get_platform_config_dir()

    if platform.system() == "Darwin":
        return config_dir / "vsc-sync" / "config.json"
    elif platform.system() == "Windows":
        return config_dir / "vsc-sync" / "config.json"
    else:
        return config_dir / "vsc-sync" / "config.json"


def resolve_path(path_str: str) -> Path:
    """Resolve a path string to an absolute Path object."""
    path = Path(path_str).expanduser().resolve()
    return path


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation."""
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"{message}{suffix}: ").strip().lower()

    if not response:
        return default

    return response in ("y", "yes", "true", "1")
