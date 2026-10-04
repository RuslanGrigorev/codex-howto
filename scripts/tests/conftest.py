"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\n\nThis is a test.")

    chapter_dir = tmp_path / "01-start"
    chapter_dir.mkdir()
    (chapter_dir / "overview.md").write_text("# Chapter Overview\n\nOverview content.")

    return tmp_path
