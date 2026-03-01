"""JSON file writer/reader for collected posts.

Each research worker writes one JSON file per angle/query.
The gather_posts() function merges and deduplicates across files.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .collectors.base import Post


def write_collection(
    path: Path,
    posts: list[Post],
    *,
    angle: str,
    source: str,
    query: str = "",
    target_icp: str = "",
) -> None:
    """Write a collection of posts to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "angle": angle,
        "target_icp": target_icp,
        "query": query,
        "source": source,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "post_count": len(posts),
        "posts": [p.to_dict() for p in posts],
    }

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def read_collection(path: Path) -> dict | None:
    """Read a collection JSON file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    return json.loads(path.read_text())


def gather_posts(raw_dir: Path) -> dict:
    """Merge all JSON files in a directory, deduplicate by post ID.

    Returns a dict with merged posts, collection metadata, and stats.
    """
    seen_ids: set[str] = set()
    all_posts: list[dict] = []
    collections: list[dict] = []

    for json_file in sorted(raw_dir.glob("*.json")):
        data = read_collection(json_file)
        if data is None:
            continue

        collections.append({
            "file": json_file.name,
            "angle": data.get("angle", ""),
            "target_icp": data.get("target_icp", ""),
            "query": data.get("query", ""),
            "post_count": data.get("post_count", 0),
        })

        for post in data.get("posts", []):
            # Normalize score: agents may write total_score instead of score
            if "total_score" in post and "score" not in post:
                post["score"] = post["total_score"]

            # Deduplicate by id, falling back to url for agent-written posts
            pid = post.get("id") or post.get("url") or ""
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_posts.append(post)
            elif not pid:
                # No id or url — include anyway, can't dedup
                all_posts.append(post)

    return {
        "total_posts": len(all_posts),
        "collections": collections,
        "posts": all_posts,
    }
