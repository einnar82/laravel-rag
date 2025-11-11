"""Parse Markdown files and extract sections based on H2 headings."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils.logger import app_logger as logger


@dataclass
class DocSection:
    """Represents a documentation section with metadata."""

    version: str
    file: str
    section: str
    content: str
    heading_path: str
    anchor: str
    chunk_index: int
    h1_title: Optional[str] = None


class MarkdownParser:
    """Parse Laravel documentation Markdown files."""

    # Regex patterns for different heading levels
    H1_PATTERN = re.compile(r"^# (.+)$", re.MULTILINE)
    H2_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)
    H3_PATTERN = re.compile(r"^### (.+)$", re.MULTILINE)
    H4_PATTERN = re.compile(r"^#### (.+)$", re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")

    # Priority order for heading levels to use for chunking
    HEADING_PRIORITY = ['H2', 'H3', 'H4']

    def __init__(self, version: str):
        """Initialize the parser.

        Args:
            version: Laravel version being parsed
        """
        self.version = version

    def parse_file(self, file_path: Path) -> list[DocSection]:
        """Parse a Markdown file and extract sections by H2 headings.

        Args:
            file_path: Path to the Markdown file

        Returns:
            List of DocSection objects
        """
        content = file_path.read_text(encoding="utf-8")
        file_name = file_path.name

        logger.debug(f"Parsing {file_name}...")

        # Extract H1 title (main page title)
        h1_match = self.H1_PATTERN.search(content)
        h1_title = h1_match.group(1).strip() if h1_match else None

        # Try to find headings in priority order: H2 > H3 > H4
        heading_matches = None
        heading_level = None

        for level in self.HEADING_PRIORITY:
            if level == 'H2':
                matches = list(self.H2_PATTERN.finditer(content))
            elif level == 'H3':
                matches = list(self.H3_PATTERN.finditer(content))
            elif level == 'H4':
                matches = list(self.H4_PATTERN.finditer(content))

            if matches:
                heading_matches = matches
                heading_level = level
                logger.debug(f"Using {level} headings for chunking {file_name}")
                break

        if not heading_matches:
            # No suitable headings found, treat entire file as single section
            logger.info(f"No H2/H3/H4 headings found in {file_name}, using entire file as single section")
            return [
                DocSection(
                    version=self.version,
                    file=file_name,
                    section=h1_title or file_name.replace('.md', '').title(),
                    content=content,
                    heading_path=h1_title or file_name,
                    anchor=f"{file_name}",
                    chunk_index=0,
                    h1_title=h1_title,
                )
            ]

        sections = []
        for idx, match in enumerate(heading_matches):
            section_title = match.group(1).strip()
            start_pos = match.start()

            # End position is start of next heading or end of file
            end_pos = heading_matches[idx + 1].start() if idx + 1 < len(heading_matches) else len(content)

            # Extract section content
            section_content = content[start_pos:end_pos].strip()

            # Generate anchor (GitHub-style)
            anchor = self._generate_anchor(file_name, section_title)

            # Create heading path
            heading_path = f"{h1_title} > {section_title}" if h1_title else section_title

            # Create section object
            section = DocSection(
                version=self.version,
                file=file_name,
                section=section_title,
                content=section_content,
                heading_path=heading_path,
                anchor=anchor,
                chunk_index=idx,
                h1_title=h1_title,
            )

            sections.append(section)

        logger.debug(f"Extracted {len(sections)} sections from {file_name}")
        return sections

    def parse_directory(self, docs_dir: Path) -> list[DocSection]:
        """Parse all Markdown files in a directory.

        Args:
            docs_dir: Directory containing Markdown files

        Returns:
            List of all DocSection objects from all files
        """
        all_sections = []
        markdown_files = sorted(docs_dir.glob("*.md"))

        logger.info(f"Parsing {len(markdown_files)} Markdown files...")

        for file_path in markdown_files:
            try:
                sections = self.parse_file(file_path)
                all_sections.extend(sections)
            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}")
                continue

        logger.info(f"Total sections extracted: {len(all_sections)}")
        return all_sections

    @staticmethod
    def _generate_anchor(file_name: str, heading: str) -> str:
        """Generate GitHub-style anchor link.

        Args:
            file_name: Name of the Markdown file
            heading: Heading text

        Returns:
            Anchor string (e.g., "eloquent.md#defining-models")
        """
        # Convert heading to lowercase and replace spaces with hyphens
        anchor_id = heading.lower()
        anchor_id = re.sub(r"[^\w\s-]", "", anchor_id)  # Remove special chars
        anchor_id = re.sub(r"[-\s]+", "-", anchor_id)  # Replace spaces/hyphens
        anchor_id = anchor_id.strip("-")  # Remove leading/trailing hyphens

        return f"{file_name}#{anchor_id}"

    @staticmethod
    def clean_content(content: str) -> str:
        """Clean and normalize content for better embedding.

        Args:
            content: Raw content

        Returns:
            Cleaned content
        """
        # Remove excessive whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r" {2,}", " ", content)

        return content.strip()
