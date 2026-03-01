"""Shared test fixtures for marketkit."""

import pytest
from marketkit.collectors.base import Post


@pytest.fixture
def make_post():
    """Factory fixture for creating Post objects."""
    def _make(
        id="1",
        author="jane",
        text="Hello world",
        platform="x",
        **kwargs,
    ):
        defaults = dict(
            id=id,
            platform=platform,
            author=author,
            text=text,
            url=f"https://x.com/{author}/status/{id}",
            timestamp="2026-03-01T10:00:00Z",
            metrics={"likes": 10},
        )
        defaults.update(kwargs)
        return Post(**defaults)
    return _make


@pytest.fixture
def tmp_research_dir(tmp_path):
    """Create a minimal .market-research/ directory structure."""
    research = tmp_path / ".market-research"
    research.mkdir()
    (research / "plans").mkdir()
    (research / "config.toml").write_text("[project]\nname = \"test\"\n")
    return research
