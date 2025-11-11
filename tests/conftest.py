"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_docs_dir(temp_dir):
    """Create sample documentation structure."""
    docs_dir = temp_dir / "docs"
    docs_dir.mkdir()

    # Create sample markdown files
    (docs_dir / "eloquent.md").write_text("""
# Eloquent ORM

## Defining Models

Create models using Artisan command.

## Retrieving Models

Retrieve all models from database.
""")

    (docs_dir / "migrations.md").write_text("""
# Database Migrations

## Creating Migrations

Use Artisan to create migrations.

## Running Migrations

Execute migrations with Artisan.
""")

    return docs_dir
