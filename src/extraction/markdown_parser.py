"""Parse Markdown files and extract sections based on H2 headings."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.config import settings
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

    # Files to exclude from indexing (navigation/meta files)
    EXCLUDED_FILES = {
        'documentation.md',  # Table of contents / navigation index
        'readme.md',         # Repository readme
        'license.md',        # MIT license text (not documentation)
    }

    def __init__(
        self,
        version: str,
        chunk_strategy: Optional[str] = None,
        max_chunk_size: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        preserve_code_blocks: Optional[bool] = None,
    ):
        """Initialize the parser.

        Args:
            version: Laravel version being parsed
            chunk_strategy: Chunking strategy ('anchor' or 'adaptive')
            max_chunk_size: Maximum characters per chunk
            min_chunk_size: Minimum characters per chunk
            chunk_overlap: Overlap between chunks
            preserve_code_blocks: Try to keep code blocks intact
        """
        self.version = version
        self.chunk_strategy = chunk_strategy or settings.chunk_strategy
        self.max_chunk_size = max_chunk_size or settings.max_chunk_size
        self.min_chunk_size = min_chunk_size or settings.min_chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.preserve_code_blocks = preserve_code_blocks if preserve_code_blocks is not None else settings.preserve_code_blocks

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

            # Apply chunking strategy
            if self.chunk_strategy == "adaptive":
                # Split large sections into smaller chunks if needed
                section_chunks = self._adaptive_chunk(section_content, section_title)

                for chunk_idx, chunk_content in enumerate(section_chunks):
                    section = DocSection(
                        version=self.version,
                        file=file_name,
                        section=f"{section_title} (Part {chunk_idx + 1}/{len(section_chunks)})" if len(section_chunks) > 1 else section_title,
                        content=chunk_content,
                        heading_path=heading_path,
                        anchor=f"{anchor}_part{chunk_idx}" if len(section_chunks) > 1 else anchor,
                        chunk_index=len(sections),
                        h1_title=h1_title,
                    )
                    sections.append(section)
            else:
                # Original anchor-based chunking (no splitting)
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

        logger.debug(f"Extracted {len(sections)} sections from {file_name} (strategy: {self.chunk_strategy})")
        return sections

    def parse_directory(self, docs_dir: Path) -> list[DocSection]:
        """Parse all Markdown files in a directory.

        Args:
            docs_dir: Directory containing Markdown files

        Returns:
            List of all DocSection objects from all files
        """
        all_sections = []
        all_markdown_files = sorted(docs_dir.glob("*.md"))

        # Filter out excluded files
        markdown_files = [
            f for f in all_markdown_files
            if f.name.lower() not in self.EXCLUDED_FILES
        ]

        excluded_count = len(all_markdown_files) - len(markdown_files)
        if excluded_count > 0:
            excluded_names = [f.name for f in all_markdown_files if f.name.lower() in self.EXCLUDED_FILES]
            logger.debug(f"Excluding {excluded_count} non-documentation files: {', '.join(excluded_names)}")

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

    def _adaptive_chunk(self, content: str, section_title: str) -> List[str]:
        """Split content into smaller chunks if it exceeds max_chunk_size.

        Uses smart splitting that:
        - Tries to preserve code blocks intact
        - Splits at paragraph boundaries
        - Maintains overlap for context
        - Respects min/max chunk size limits

        Args:
            content: Section content to potentially split
            section_title: Section title (for logging)

        Returns:
            List of chunk strings (may be single item if no split needed)
        """
        content_length = len(content)

        # If content is within limits, return as-is
        if content_length <= self.max_chunk_size:
            return [content]

        logger.debug(f"Splitting large section '{section_title}' ({content_length} chars) into smaller chunks")

        chunks = []
        current_pos = 0

        while current_pos < content_length:
            # Calculate chunk end position
            chunk_end = min(current_pos + self.max_chunk_size, content_length)

            # Extract tentative chunk
            chunk = content[current_pos:chunk_end]

            # If not at the end, try to find a good breaking point
            if chunk_end < content_length:
                chunk = self._find_break_point(chunk, content, current_pos)

            # Add chunk if it meets minimum size or it's the last chunk
            if len(chunk) >= self.min_chunk_size or chunk_end >= content_length:
                chunks.append(chunk.strip())

                # Move position forward, accounting for overlap
                current_pos += len(chunk) - self.chunk_overlap
            else:
                # Chunk too small, include more content
                current_pos = chunk_end

        logger.debug(f"Split into {len(chunks)} chunks")
        return chunks if chunks else [content]

    def _find_break_point(self, chunk: str, full_content: str, start_pos: int) -> str:
        """Find a good breaking point for a chunk.

        Priority:
        1. End of code block (if preserve_code_blocks is True)
        2. Double newline (paragraph boundary)
        3. Single newline
        4. Space
        5. Hard cut at max_chunk_size

        Args:
            chunk: Current chunk being processed
            full_content: Full content being chunked
            start_pos: Starting position in full content

        Returns:
            Adjusted chunk with good break point
        """
        # If preserving code blocks, check if we're inside one
        if self.preserve_code_blocks:
            # Count code block markers before this chunk
            preceding_content = full_content[:start_pos + len(chunk)]
            code_block_starts = len(re.findall(r'```', preceding_content[:start_pos]))
            code_block_markers_in_chunk = len(re.findall(r'```', chunk))

            # If odd number of markers before chunk, we started inside a code block
            in_code_block = (code_block_starts % 2) == 1

            if in_code_block:
                # Try to find the end of the code block
                end_marker_match = re.search(r'```', chunk)
                if end_marker_match:
                    # Include up to and including the closing marker
                    return chunk[:end_marker_match.end()]

        # Try to break at paragraph boundary (double newline)
        para_break = chunk.rfind('\n\n')
        if para_break > len(chunk) * 0.6:  # Only if it's in the latter 40%
            return chunk[:para_break + 2]

        # Try to break at single newline
        newline_break = chunk.rfind('\n')
        if newline_break > len(chunk) * 0.7:  # Only if it's in the latter 30%
            return chunk[:newline_break + 1]

        # Try to break at space
        space_break = chunk.rfind(' ')
        if space_break > len(chunk) * 0.8:  # Only if it's in the latter 20%
            return chunk[:space_break + 1]

        # Hard cut (no good break point found)
        return chunk

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
