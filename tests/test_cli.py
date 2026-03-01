import json
import os
from pathlib import Path
from typer.testing import CliRunner
from marketkit import app, CommandTemplate
from marketkit.constants import AGENT_CONFIG


runner = CliRunner()


def test_init_creates_research_dir():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert Path(".market-research").is_dir()
        assert Path(".market-research/config.toml").exists()
        assert Path(".market-research/plans").is_dir()
        assert Path(".market-research/templates").is_dir()


def test_init_copies_command_templates():
    """Default (claude) puts commands in .claude/commands/."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        commands_dir = Path(".claude/commands")
        assert commands_dir.is_dir()
        for cmd in CommandTemplate:
            assert (commands_dir / cmd.filename).exists(), f"Missing {cmd.filename}"


def test_init_ai_agents():
    """--ai flag installs commands to the correct agent directory."""
    for agent_key, agent in AGENT_CONFIG.items():
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["init", "--ai", agent_key])
            assert result.exit_code == 0, f"init --ai {agent_key} failed: {result.output}"
            commands_dir = Path(agent["folder"]) / agent["subdir"]
            assert commands_dir.is_dir(), f"Missing dir for {agent_key}: {commands_dir}"
            for cmd in CommandTemplate:
                assert (commands_dir / cmd.filename).exists(), f"Missing {cmd.filename} for {agent_key}"


def test_init_ai_unknown_agent():
    """--ai with an unknown agent name exits with error."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init", "--ai", "nonexistent"])
        assert result.exit_code == 1
        assert "Unknown agent" in result.output


def test_init_copies_document_templates():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert Path(".market-research/templates/brief-template.md").exists()
        assert Path(".market-research/templates/plan-template.md").exists()


def test_init_idempotent():
    """Running init twice should not overwrite config.toml."""
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        config = Path(".market-research/config.toml")
        config.write_text("[project]\nname = \"custom\"\n")
        runner.invoke(app, ["init"])
        assert 'name = "custom"' in config.read_text()


def test_status_no_project():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "No .market-research/" in result.output


def test_status_with_project():
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "brief" in result.output.lower() or "research" in result.output.lower()


def test_gather_no_project():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["gather"])
        assert result.exit_code != 0


def test_context_outputs_json():
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["context"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "PROJECT_ROOT" in data
        assert "RESEARCH_DIR" in data
        assert "BRIEF" in data
        assert "TEMPLATES_DIR" in data
        assert "AVAILABLE_DOCS" in data
        assert "PLANS" in data
        assert "PLAN_COUNT" in data
        assert isinstance(data["AVAILABLE_DOCS"], list)
        assert isinstance(data["PLANS"], list)
        assert data["PLAN_COUNT"] == 0


def test_context_no_project():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["context"])
        assert result.exit_code == 1


def test_new_plan_creates_directory():
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["new-plan", "test-slug"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "PLAN_DIR" in data
        assert "DATA_DIR" in data
        assert "PLAN_NAME" in data
        assert "test-slug" in data["PLAN_NAME"]
        assert Path(data["DATA_DIR"]).is_dir()


def _setup_scored_posts(base_dir):
    """Helper: create a plan with scored posts for gather tests."""
    plan_dir = base_dir / ".market-research" / "plans" / "test-plan" / "data"
    plan_dir.mkdir(parents=True)
    collection = {
        "angle": "test",
        "target_icp": "",
        "query": "q",
        "source": "x_api",
        "collected_at": "2026-03-01T00:00:00Z",
        "post_count": 4,
        "posts": [
            {"id": "1", "platform": "x", "author": "a", "text": "low", "url": "u", "timestamp": "t", "metrics": {}, "score": 1},
            {"id": "2", "platform": "x", "author": "b", "text": "high", "url": "u", "timestamp": "t", "metrics": {}, "score": 5},
            {"id": "3", "platform": "x", "author": "c", "text": "mid", "url": "u", "timestamp": "t", "metrics": {}, "score": 3},
            {"id": "4", "platform": "x", "author": "d", "text": "med", "url": "u", "timestamp": "t", "metrics": {}, "score": 2},
        ],
    }
    (plan_dir / "test.json").write_text(json.dumps(collection))


def test_gather_top_returns_n_highest():
    """--top N returns N posts sorted by score descending."""
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        _setup_scored_posts(Path("."))
        result = runner.invoke(app, ["gather", "--plan", "test-plan", "--top", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_posts"] == 4  # total available in dataset
        assert data["returned_posts"] == 2  # sliced count
        scores = [p["score"] for p in data["posts"]]
        assert scores == [5, 3]


def test_gather_sorted_by_score():
    """Without --top, all posts are returned sorted by score descending."""
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        _setup_scored_posts(Path("."))
        result = runner.invoke(app, ["gather", "--plan", "test-plan"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_posts"] == 4
        assert data["returned_posts"] == 4
        scores = [p["score"] for p in data["posts"]]
        assert scores == [5, 3, 2, 1]


def test_gather_top_backward_compat():
    """Posts without a score field default to 0."""
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        plan_dir = Path(".market-research/plans/old-plan/data")
        plan_dir.mkdir(parents=True)
        collection = {
            "angle": "test", "target_icp": "", "query": "q", "source": "x",
            "collected_at": "2026-03-01T00:00:00Z", "post_count": 2,
            "posts": [
                {"id": "1", "platform": "x", "author": "a", "text": "old", "url": "u", "timestamp": "t", "metrics": {}},
                {"id": "2", "platform": "x", "author": "b", "text": "old2", "url": "u", "timestamp": "t", "metrics": {}},
            ],
        }
        (plan_dir / "test.json").write_text(json.dumps(collection))
        result = runner.invoke(app, ["gather", "--plan", "old-plan", "--top", "1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_posts"] == 2  # total available
        assert data["returned_posts"] == 1  # sliced


def test_gather_top_zero_rejected():
    """--top 0 exits with error."""
    with runner.isolated_filesystem():
        runner.invoke(app, ["init"])
        _setup_scored_posts(Path("."))
        result = runner.invoke(app, ["gather", "--plan", "test-plan", "--top", "0"])
        assert result.exit_code == 1


def test_search_x_paid_api_missing_token():
    """Command exists and errors gracefully when no token is configured."""
    env = os.environ.copy()
    env.pop("X_BEARER_TOKEN", None)
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["search-x-paid-api", "test query", "--output", "out.json"],
            env=env,
        )
        assert result.exit_code == 1
        assert "X_BEARER_TOKEN" in (result.output + (result.stderr or ""))
