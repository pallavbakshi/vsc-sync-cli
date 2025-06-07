"""Application management for discovering and interacting with VSCode-like apps."""

import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ..exceptions import AppConfigPathError, ExtensionError
from ..models import AppDetails

logger = logging.getLogger(__name__)


class AppManager:
    """Manages VSCode-like applications and their configurations."""

    @staticmethod
    def get_extension_directory(app_alias: str) -> Path:
        """Get the extension directory for a specific app."""
        home = Path.home()
        extension_dirs = {
            "vscode": home / ".vscode" / "extensions",
            "vscodium": home / ".vscode-oss" / "extensions",
            "cursor": home / ".cursor" / "extensions",
            "windsurf": home / ".windsurf" / "extensions",
            "void": home / ".void" / "extensions",
            "pearai": home / ".pearai" / "extensions",
        }

        return extension_dirs.get(app_alias, home / f".{app_alias}" / "extensions")

    @staticmethod
    def get_default_app_paths() -> Dict[str, Dict[str, Path]]:
        """Get default configuration paths for common VSCode-like applications."""
        system = platform.system()
        home = Path.home()

        if system == "Darwin":  # macOS
            base_path = home / "Library" / "Application Support"
            return {
                "vscode": {
                    "config": base_path / "Code" / "User",
                    "executable": Path(
                        "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
                    ),
                },
                "vscodium": {
                    "config": base_path / "VSCodium" / "User",
                    "executable": Path(
                        "/Applications/VSCodium.app/Contents/Resources/app/bin/codium"
                    ),
                },
                "cursor": {
                    "config": base_path / "Cursor" / "User",
                    "executable": Path(
                        "/Applications/Cursor.app/Contents/Resources/app/bin/cursor"
                    ),
                },
                "windsurf": {
                    "config": base_path / "Windsurf" / "User",
                    "executable": Path(
                        "/Applications/Windsurf.app/Contents/Resources/app/bin/windsurf"
                    ),
                },
                "void": {
                    "config": base_path / "Void" / "User",
                    "executable": Path("/usr/local/bin/void"),
                },
                "pearai": {
                    "config": base_path / "PearAI" / "User",
                    "executable": Path(
                        "/Applications/PearAI.app/Contents/Resources/app/bin/pearai"
                    ),
                },
            }

        elif system == "Windows":
            app_data = home / "AppData" / "Roaming"
            return {
                "vscode": {
                    "config": app_data / "Code" / "User",
                    "executable": Path(
                        "C:/Program Files/Microsoft VS Code/bin/code.cmd"
                    ),
                },
                "vscodium": {
                    "config": app_data / "VSCodium" / "User",
                    "executable": Path("C:/Program Files/VSCodium/bin/codium.cmd"),
                },
                "cursor": {
                    "config": app_data / "Cursor" / "User",
                    "executable": Path("C:/Program Files/Cursor/cursor.exe"),
                },
            }

        else:  # Linux
            config_base = home / ".config"
            return {
                "vscode": {
                    "config": config_base / "Code" / "User",
                    "executable": Path("/usr/bin/code"),
                },
                "vscodium": {
                    "config": config_base / "VSCodium" / "User",
                    "executable": Path("/usr/bin/codium"),
                },
                "cursor": {
                    "config": config_base / "Cursor" / "User",
                    "executable": Path("/usr/bin/cursor"),
                },
            }

    @staticmethod
    def auto_discover_apps() -> Dict[str, AppDetails]:
        """Auto-discover installed VSCode-like applications."""
        discovered_apps = {}
        default_paths = AppManager.get_default_app_paths()

        for app_alias, paths in default_paths.items():
            config_path = paths["config"]
            executable_path = paths.get("executable")

            # Check if config directory exists (indicating the app is installed/used)
            if config_path.exists():
                # Verify executable exists if specified
                exec_path = None
                if executable_path and executable_path.exists():
                    exec_path = executable_path
                elif executable_path:
                    # Try to find executable in PATH
                    try:
                        result = subprocess.run(
                            (
                                ["which", app_alias]
                                if platform.system() != "Windows"
                                else ["where", app_alias]
                            ),
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            exec_path = Path(result.stdout.strip().split("\n")[0])
                    except Exception:
                        pass

                discovered_apps[app_alias] = AppDetails(
                    alias=app_alias, config_path=config_path, executable_path=exec_path
                )

                logger.debug(f"Discovered app '{app_alias}' at {config_path}")

        return discovered_apps

    @staticmethod
    def validate_app_config_path(config_path: Path) -> bool:
        """Validate that a path looks like a VSCode user configuration directory."""
        if not config_path.exists() or not config_path.is_dir():
            return False

        # Check for typical VSCode user directory structure
        expected_files = ["settings.json", "keybindings.json"]
        expected_dirs = ["snippets"]

        # At least one of these should exist in a used VSCode config directory
        for file_name in expected_files:
            if (config_path / file_name).exists():
                return True

        for dir_name in expected_dirs:
            if (config_path / dir_name).exists():
                return True

        # If none exist, it might be a fresh installation
        # Check if parent directory structure looks like VSCode
        parent_name = config_path.parent.name.lower()
        return any(
            app in parent_name
            for app in ["code", "cursor", "vscodium", "windsurf", "void", "pearai"]
        )

    @staticmethod
    def get_installed_extensions(app_details: AppDetails) -> List[str]:
        """Get list of installed extensions for an application."""
        if not app_details.executable_path:
            raise ExtensionError(
                f"No executable path configured for {app_details.alias}"
            )

        try:
            result = subprocess.run(
                [str(app_details.executable_path), "--list-extensions"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            extensions = [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            logger.debug(f"Found {len(extensions)} extensions for {app_details.alias}")
            return extensions

        except subprocess.TimeoutExpired:
            raise ExtensionError(
                f"Timeout while listing extensions for {app_details.alias}"
            )
        except subprocess.CalledProcessError as e:
            raise ExtensionError(
                f"Failed to list extensions for {app_details.alias}: {e}"
            )
        except Exception as e:
            raise ExtensionError(
                f"Unexpected error listing extensions for {app_details.alias}: {e}"
            )

    @staticmethod
    def install_extension(app_details: AppDetails, extension_id: str) -> bool:
        """Install an extension for an application."""
        if not app_details.executable_path:
            raise ExtensionError(
                f"No executable path configured for {app_details.alias}"
            )

        try:
            result = subprocess.run(
                [str(app_details.executable_path), "--install-extension", extension_id],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )

            logger.debug(f"Installed extension {extension_id} for {app_details.alias}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(
                f"Timeout while installing extension {extension_id} for {app_details.alias}"
            )
            return False
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to install extension {extension_id} for {app_details.alias}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error installing extension {extension_id} for {app_details.alias}: {e}"
            )
            return False

    @staticmethod
    def uninstall_extension(app_details: AppDetails, extension_id: str) -> bool:
        """Uninstall an extension for an application."""
        if not app_details.executable_path:
            raise ExtensionError(
                f"No executable path configured for {app_details.alias}"
            )

        try:
            result = subprocess.run(
                [
                    str(app_details.executable_path),
                    "--uninstall-extension",
                    extension_id,
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )

            logger.debug(
                f"Uninstalled extension {extension_id} for {app_details.alias}"
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error(
                f"Timeout while uninstalling extension {extension_id} for {app_details.alias}"
            )
            return False
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to uninstall extension {extension_id} for {app_details.alias}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error uninstalling extension {extension_id} for {app_details.alias}: {e}"
            )
            return False
