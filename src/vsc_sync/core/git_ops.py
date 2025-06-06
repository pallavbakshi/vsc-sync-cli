"""Git operations utilities for vsc-sync."""

import logging
from pathlib import Path
from typing import Optional

try:
    import git

    HAS_GITPYTHON = True
except ImportError:
    HAS_GITPYTHON = False
    git = None

from ..exceptions import GitOperationError

logger = logging.getLogger(__name__)


class GitOperations:
    """Handles Git operations for vsc-sync."""

    @staticmethod
    def is_git_available() -> bool:
        """Check if Git and GitPython are available."""
        return HAS_GITPYTHON and git is not None

    @staticmethod
    def clone_repository(
        repo_url: str, destination: Path, branch: Optional[str] = None
    ) -> None:
        """Clone a Git repository to the specified destination."""
        if not GitOperations.is_git_available():
            raise GitOperationError(
                "Git support is not available. Please install GitPython: pip install gitpython"
            )

        try:
            if destination.exists():
                raise GitOperationError(
                    f"Destination directory already exists: {destination}"
                )

            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Cloning repository {repo_url} to {destination}")

            clone_kwargs = {}
            if branch:
                clone_kwargs["branch"] = branch

            repo = git.Repo.clone_from(repo_url, destination, **clone_kwargs)
            logger.info(f"Successfully cloned repository to {destination}")

        except git.GitCommandError as e:
            raise GitOperationError(f"Git command failed: {e}")
        except Exception as e:
            raise GitOperationError(f"Failed to clone repository: {e}")

    @staticmethod
    def is_git_repository(path: Path) -> bool:
        """Check if a directory is a Git repository."""
        if not GitOperations.is_git_available():
            return False

        try:
            git.Repo(path)
            return True
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False

    @staticmethod
    def pull_latest(repo_path: Path) -> None:
        """Pull latest changes from the remote repository."""
        if not GitOperations.is_git_available():
            raise GitOperationError("Git support is not available")

        try:
            repo = git.Repo(repo_path)

            if repo.is_dirty():
                logger.warning(f"Repository at {repo_path} has uncommitted changes")

            # Pull from origin
            origin = repo.remotes.origin
            origin.pull()
            logger.info(f"Pulled latest changes for repository at {repo_path}")

        except git.InvalidGitRepositoryError:
            raise GitOperationError(f"Not a valid Git repository: {repo_path}")
        except git.GitCommandError as e:
            raise GitOperationError(f"Git pull failed: {e}")
        except Exception as e:
            raise GitOperationError(f"Failed to pull repository: {e}")

    @staticmethod
    def get_current_branch(repo_path: Path) -> str:
        """Get the current branch name."""
        if not GitOperations.is_git_available():
            raise GitOperationError("Git support is not available")

        try:
            repo = git.Repo(repo_path)
            return repo.active_branch.name

        except git.InvalidGitRepositoryError:
            raise GitOperationError(f"Not a valid Git repository: {repo_path}")
        except Exception as e:
            raise GitOperationError(f"Failed to get current branch: {e}")

    @staticmethod
    def has_uncommitted_changes(repo_path: Path) -> bool:
        """Check if repository has uncommitted changes."""
        if not GitOperations.is_git_available():
            return False

        try:
            repo = git.Repo(repo_path)
            return repo.is_dirty() or len(repo.untracked_files) > 0

        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False
        except Exception:
            # If we can't determine, assume there are changes for safety
            return True

    @staticmethod
    def get_remote_url(repo_path: Path) -> Optional[str]:
        """Get the remote URL of the repository."""
        if not GitOperations.is_git_available():
            return None

        try:
            repo = git.Repo(repo_path)
            if repo.remotes:
                return repo.remotes.origin.url
            return None

        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return None
        except Exception:
            return None
