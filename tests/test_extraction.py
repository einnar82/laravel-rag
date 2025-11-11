"""Tests for document extraction module."""

import pytest
from pathlib import Path
from src.extraction.markdown_parser import MarkdownParser, DocSection


class TestMarkdownParser:
    """Test cases for MarkdownParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return MarkdownParser(version="12")

    @pytest.fixture
    def sample_markdown(self, tmp_path):
        """Create a sample markdown file."""
        content = """# Eloquent ORM

## Defining Models

To define a model, use the following:

```php
php artisan make:model Flight
```

## Retrieving Models

You can retrieve models using:

```php
$flights = Flight::all();
```
"""
        file_path = tmp_path / "eloquent.md"
        file_path.write_text(content)
        return file_path

    def test_parse_file(self, parser, sample_markdown):
        """Test parsing a markdown file."""
        sections = parser.parse_file(sample_markdown)

        assert len(sections) == 2
        assert sections[0].section == "Defining Models"
        assert sections[1].section == "Retrieving Models"
        assert sections[0].version == "12"
        assert "php artisan make:model" in sections[0].content

    def test_generate_anchor(self, parser):
        """Test anchor generation."""
        anchor = parser._generate_anchor("eloquent.md", "Defining Models")
        assert anchor == "eloquent.md#defining-models"

        anchor = parser._generate_anchor("test.md", "Complex: Title (with symbols)!")
        assert "#" in anchor
        assert "(" not in anchor
        assert ")" not in anchor

    def test_clean_content(self, parser):
        """Test content cleaning."""
        dirty_content = "Line 1\n\n\n\nLine 2  \nLine 3"
        clean = parser.clean_content(dirty_content)

        assert "\n\n\n" not in clean
        assert clean.startswith("Line 1")
