"""Fetch Laravel documentation from GitHub repository."""

import subprocess
from pathlib import Path
from typing import Optional

from src.config import settings
from src.utils.logger import app_logger as logger


class DocsFetcher:
    """Fetch and manage Laravel documentation from Git repository."""

    def __init__(
        self,
        repo_url: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        version: Optional[str] = None,
    ):
        """Initialize the documentation fetcher.

        Args:
            repo_url: Git repository URL for Laravel docs
            cache_dir: Directory to cache documentation
            version: Laravel version to fetch
        """
        self.repo_url = repo_url or settings.laravel_docs_repo
        self.cache_dir = cache_dir or settings.docs_cache_dir
        self.version = version or settings.laravel_version
        self.branch_name = f"{self.version}.x"
        self.version_dir = self.cache_dir / f"v{self.version}"

    def fetch_docs(self, force: bool = False) -> Path:
        """Fetch Laravel documentation for the specified version.

        Args:
            force: Force re-fetch even if docs exist

        Returns:
            Path to the fetched documentation directory

        Raises:
            RuntimeError: If Git operations fail
        """
        logger.info(f"Fetching Laravel v{self.version} documentation...")

        # Check if already exists
        if self.version_dir.exists() and not force:
            logger.info(f"Documentation already exists at {self.version_dir}")
            return self.version_dir

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Remove existing if force fetch
        if force and self.version_dir.exists():
            logger.warning(f"Removing existing documentation at {self.version_dir}")
            subprocess.run(["rm", "-rf", str(self.version_dir)], check=True)

        try:
            # Clone repository with specific branch
            logger.info(f"Cloning {self.repo_url} (branch: {self.branch_name})...")
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    self.branch_name,
                    "--single-branch",
                    self.repo_url,
                    str(self.version_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info(f"Successfully fetched documentation to {self.version_dir}")
            return self.version_dir

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to fetch documentation: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_markdown_files(self) -> list[Path]:
        """Get all Markdown files from the documentation directory.

        Returns:
            List of paths to Markdown files

        Raises:
            FileNotFoundError: If documentation directory doesn't exist
        """
        if not self.version_dir.exists():
            raise FileNotFoundError(
                f"Documentation not found at {self.version_dir}. Run fetch_docs() first."
            )

        markdown_files = list(self.version_dir.glob("*.md"))
        logger.info(f"Found {len(markdown_files)} Markdown files")

        return sorted(markdown_files)

    def get_file_content(self, file_path: Path) -> str:
        """Read content from a Markdown file.

        Args:
            file_path: Path to the Markdown file

        Returns:
            File content as string
        """
        return file_path.read_text(encoding="utf-8")
