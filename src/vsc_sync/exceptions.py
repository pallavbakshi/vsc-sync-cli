"""Custom exceptions for vsc-sync."""


class VscSyncError(Exception):
    """Base exception for all vsc-sync errors."""


class ConfigError(VscSyncError):
    """Raised when there's an issue with configuration."""


class LayerNotFoundError(VscSyncError):
    """Raised when a specified layer doesn't exist."""


class AppConfigPathError(VscSyncError):
    """Raised when there's an issue with an app's configuration path."""


class MergeConflictError(VscSyncError):
    """Raised when there's a conflict during configuration merging."""


class GitOperationError(VscSyncError):
    """Raised when a Git operation fails."""


class ExtensionError(VscSyncError):
    """Raised when there's an issue with extension management."""
