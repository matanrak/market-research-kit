import json
from pathlib import Path
from marketkit.writer import write_collection, read_collection, gather_posts
from marketkit.collectors.base import Post


def test_write_collection_creates_file(tmp_path):
    path = tmp_path / "raw" / "pain-devops.json"
    posts = [
        Post(id="1", platform="x", author="jane", text="hello",
             url="https://x.com/jane/status/1", timestamp="2026-03-01T10:00:00Z",
             metrics={"likes": 10}),
        Post(id="2", platform="x", author="bob", text="world",
             url="https://x.com/bob/status/2", timestamp="2026-03-01T11:00:00Z",
             metrics={"likes": 5}),
    ]
    write_collection(
        path=path,
        posts=posts,
        angle="pain-devops",
        target_icp="DevOps Engineer",
        query="claude code SSH slow -is:retweet",
        source="x_api",
    )
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["angle"] == "pain-devops"
    assert data["target_icp"] == "DevOps Engineer"
    assert data["query"] == "claude code SSH slow -is:retweet"
    assert data["source"] == "x_api"
    assert "collected_at" in data
    assert len(data["posts"]) == 2
    assert data["posts"][0]["id"] == "1"
    assert data["posts"][1]["author"] == "bob"
    # raw field should not be in output
    assert "raw" not in data["posts"][0]


def test_write_collection_special_chars(tmp_path):
    """Posts with quotes, backslashes, unicode roundtrip through JSON."""
    path = tmp_path / "special.json"
    post = Post(
        id="99", platform="x", author="test",
        text='triple \'\'\' and "doubles" and back\\slash and \U0001f389',
        url="https://x.com/test/status/99",
        timestamp="2026-03-01T00:00:00Z",
        metrics={"likes": 1},
    )
    write_collection(path, [post], angle="test", target_icp="", query="test", source="x_api")
    data = json.loads(path.read_text())
    assert data["posts"][0]["text"] == post.text


def test_read_collection(tmp_path):
    path = tmp_path / "test.json"
    posts = [
        Post(id="1", platform="x", author="jane", text="hello",
             url="https://x.com/jane/status/1", timestamp="2026-03-01T10:00:00Z",
             metrics={"likes": 10}),
    ]
    write_collection(path, posts, angle="test", target_icp="Tester", query="q", source="x_api")
    data = read_collection(path)
    assert data["angle"] == "test"
    assert len(data["posts"]) == 1
    assert data["posts"][0]["id"] == "1"


def test_read_collection_missing_file():
    data = read_collection(Path("/nonexistent/posts.json"))
    assert data is None


def test_gather_posts_deduplicates(tmp_path):
    """gather_posts merges multiple files and deduplicates by post ID."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    post_a = Post(id="1", platform="x", author="jane", text="hello",
                  url="https://x.com/jane/status/1", timestamp="2026-03-01T10:00:00Z",
                  metrics={"likes": 10})
    post_b = Post(id="2", platform="x", author="bob", text="world",
                  url="https://x.com/bob/status/2", timestamp="2026-03-01T11:00:00Z",
                  metrics={"likes": 5})
    post_dup = Post(id="1", platform="x", author="jane", text="hello",
                    url="https://x.com/jane/status/1", timestamp="2026-03-01T10:00:00Z",
                    metrics={"likes": 10})

    write_collection(raw_dir / "angle1.json", [post_a, post_b],
                     angle="a1", target_icp="ICP1", query="q1", source="x_api")
    write_collection(raw_dir / "angle2.json", [post_dup],
                     angle="a2", target_icp="ICP2", query="q2", source="x_api")

    result = gather_posts(raw_dir)
    assert len(result["posts"]) == 2  # deduped by ID
    assert len(result["collections"]) == 2
    assert result["total_posts"] == 2


def test_gather_posts_empty_dir(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    result = gather_posts(raw_dir)
    assert result["posts"] == []
    assert result["total_posts"] == 0


def test_score_preserved_through_write_read(tmp_path):
    """Score survives write_collection -> read_collection cycle."""
    path = tmp_path / "scored.json"
    posts = [
        Post(id="1", platform="x", author="jane", text="hello",
             url="https://x.com/jane/status/1", timestamp="2026-03-01T10:00:00Z",
             metrics={"likes": 50}, score=4),
        Post(id="2", platform="x", author="bob", text="world",
             url="https://x.com/bob/status/2", timestamp="2026-03-01T11:00:00Z",
             metrics={"likes": 3}, score=1),
    ]
    write_collection(path, posts, angle="test", target_icp="", query="q", source="x_api")
    data = read_collection(path)
    assert data["posts"][0]["score"] == 4
    assert data["posts"][1]["score"] == 1
