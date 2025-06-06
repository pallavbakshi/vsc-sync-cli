"""File operations utilities for vsc-sync."""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ..exceptions import VscSyncError

logger = logging.getLogger(__name__)


class FileOperations:
    """Handles file and directory operations for vsc-sync."""

    @staticmethod
    def backup_directory(source_dir: Path, backup_suffix: Optional[str] = None) -> Path:
        """Create a backup of a directory."""
        if not source_dir.exists():
            raise VscSyncError(f"Source directory does not exist: {source_dir}")

        if backup_suffix is None:
            timestamp = int(time.time())
            backup_suffix = f"bak.{timestamp}"

        backup_path = source_dir.with_name(f"{source_dir.name}.{backup_suffix}")

        try:
            shutil.copytree(source_dir, backup_path, dirs_exist_ok=False)
            logger.info(f"Created backup: {source_dir} -> {backup_path}")
            return backup_path

        except Exception as e:
            raise VscSyncError(f"Failed to create backup of {source_dir}: {e}")

    @staticmethod
    def write_json_file(
        file_path: Path, data: Dict[str, Any], create_dirs: bool = True
    ) -> None:
        """Write data to a JSON file."""
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Wrote JSON file: {file_path}")

        except Exception as e:
            raise VscSyncError(f"Failed to write JSON file {file_path}: {e}")

    @staticmethod
    def read_json_file(file_path: Path) -> Dict[str, Any]:
        """Read data from a JSON file."""
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            logger.warning(f"Failed to read JSON file {file_path}: {e}")
            return {}

    @staticmethod
    def copy_file(source: Path, destination: Path, create_dirs: bool = True) -> None:
        """Copy a file from source to destination."""
        if not source.exists():
            raise VscSyncError(f"Source file does not exist: {source}")

        if create_dirs:
            destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(source, destination)
            logger.debug(f"Copied file: {source} -> {destination}")

        except Exception as e:
            raise VscSyncError(f"Failed to copy file {source} to {destination}: {e}")

    @staticmethod
    def copy_directory_contents(
        source_dir: Path, destination_dir: Path, overwrite_existing: bool = True
    ) -> None:
        """Copy contents of source directory to destination directory."""
        if not source_dir.exists():
            raise VscSyncError(f"Source directory does not exist: {source_dir}")

        destination_dir.mkdir(parents=True, exist_ok=True)

        try:
            for item in source_dir.iterdir():
                dest_item = destination_dir / item.name

                if item.is_file():
                    if dest_item.exists() and not overwrite_existing:
                        logger.warning(f"Skipping existing file: {dest_item}")
                        continue
                    shutil.copy2(item, dest_item)
                    logger.debug(f"Copied file: {item} -> {dest_item}")

                elif item.is_dir():
                    if dest_item.exists() and not overwrite_existing:
                        logger.warning(f"Skipping existing directory: {dest_item}")
                        continue
                    shutil.copytree(item, dest_item, dirs_exist_ok=overwrite_existing)
                    logger.debug(f"Copied directory: {item} -> {dest_item}")

        except Exception as e:
            raise VscSyncError(
                f"Failed to copy directory contents from {source_dir} to {destination_dir}: {e}"
            )

    @staticmethod
    def safe_remove_file(file_path: Path) -> bool:
        """Safely remove a file, returning True if successful."""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Removed file: {file_path}")
                return True
            return False

        except Exception as e:
            logger.warning(f"Failed to remove file {file_path}: {e}")
            return False

    @staticmethod
    def ensure_directory(dir_path: Path) -> None:
        """Ensure a directory exists, creating it if necessary."""
        try:
            dir_path.mkdir(parents=True, exist_ok=True)

        except Exception as e:
            raise VscSyncError(f"Failed to create directory {dir_path}: {e}")

    @staticmethod
    def is_file_different(file1: Path, file2: Path) -> bool:
        """Check if two files are different."""
        if not file1.exists() or not file2.exists():
            return True

        try:
            # Quick size check first
            if file1.stat().st_size != file2.stat().st_size:
                return True

            # Content comparison for small files (< 1MB)
            if file1.stat().st_size < 1024 * 1024:
                return file1.read_bytes() != file2.read_bytes()

            # For larger files, just assume different for safety
            return True

        except Exception:
            # If we can't compare, assume different
            return True
