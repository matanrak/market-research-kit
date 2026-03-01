"""marketkit CLI commands: app, callback, init, status, gather."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.align import Align
from rich.live import Live
from rich.panel import Panel

from .constants import APP_NAME, COMMAND_PREFIX, RESEARCH_DIR_NAME, CommandTemplate, AGENT_CONFIG, DEFAULT_AGENT
from .ui import console, StepTracker, BannerGroup, show_banner
from .config import _find_package_dir, _install_command_template, _find_project_root


# --- CLI App ---

app = typer.Typer(
    name=APP_NAME,
    help="Structured market research for AI coding agents.",
    add_completion=False,
    invoke_without_command=True,
    cls=BannerGroup,
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Show help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        # BannerGroup.format_help handles banner + help output
        console.print(ctx.get_help())
        console.print()


@app.command()
def init(
    ai: str = typer.Option(DEFAULT_AGENT, "--ai", help=f"AI agent to use: {', '.join(AGENT_CONFIG)}"),
    force: bool = typer.Option(False, "--force", help=f"Re-copy templates even if {RESEARCH_DIR_NAME}/ exists"),
    debug: bool = typer.Option(False, "--debug", help="Show verbose output"),
):
    """Initialize a market research directory and copy templates."""
    if ai not in AGENT_CONFIG:
        console.print(f"[red]Error:[/red] Unknown agent '{ai}'")
        console.print(f"[yellow]Available agents:[/yellow] {', '.join(AGENT_CONFIG)}")
        raise typer.Exit(1)

    agent = AGENT_CONFIG[ai]

    tracker = StepTracker(f"{APP_NAME} init")
    tracker.add("dirs", "Create directory structure")
    tracker.add("config", "Write config.toml")
    tracker.add("templates", "Copy document templates")
    tracker.add("commands", f"Install commands → {agent['folder']}/{agent['subdir']}/")

    with Live(tracker.render(), console=console, refresh_per_second=8, transient=True) as live:
        tracker.attach_refresh(lambda: live.update(tracker.render()))

        research_dir = Path(RESEARCH_DIR_NAME)

        # Create directories
        tracker.start("dirs")
        research_dir.mkdir(exist_ok=True)
        (research_dir / "plans").mkdir(exist_ok=True)
        (research_dir / "templates").mkdir(exist_ok=True)
        tracker.complete("dirs")

        # Create config.toml (preserve existing)
        tracker.start("config")
        config_path = research_dir / "config.toml"
        if not config_path.exists():
            config_path.write_text(
                '# marketkit project configuration\n\n'
                '[project]\nname = ""\n\n'
                '[collector]\ndefault = "x_api"\n\n'
                '[x_api]\n'
                '# Token is read from X_BEARER_TOKEN env var or platformdirs config\n'
                '# cost_per_tweet = 0.005\n'
            )
            tracker.complete("config", "created")
        else:
            tracker.skip("config", "already exists")

        # Copy document templates
        tracker.start("templates")
        try:
            templates_src = _find_package_dir("templates")
            copied = 0
            for template in templates_src.glob("*-template.md"):
                shutil.copy2(template, research_dir / "templates" / template.name)
                copied += 1
            tracker.complete("templates", f"{copied} templates")
        except FileNotFoundError:
            tracker.error("templates", "source not found")

        # Copy command templates to agent-specific directory
        tracker.start("commands")
        try:
            commands_src = _find_package_dir("templates/commands")
            commands_dest = Path(agent["folder"]) / agent["subdir"]
            commands_dest.mkdir(parents=True, exist_ok=True)
            copied = 0
            for cmd in CommandTemplate:
                src = commands_src / cmd.source
                if src.exists():
                    _install_command_template(src, commands_dest / cmd.filename)
                    copied += 1
            tracker.complete("commands", f"{copied} commands → {agent['name']}")
        except FileNotFoundError:
            tracker.error("commands", "source not found")

    # Print final tracker state (non-transient, spec-kit pattern)
    console.print(tracker.render())
    console.print()
    console.print(f"[green]{APP_NAME} initialized for {agent['name']}.[/green] Commands available:")
    descriptions = {
        CommandTemplate.SPECIFY: "Define research brief (ICPs, hypothesis)",
        CommandTemplate.PLAN: "Generate research query plan",
        CommandTemplate.RESEARCH: "Execute plan with parallel agents",
        CommandTemplate.REPORT: "Synthesize findings",
    }
    for cmd in CommandTemplate:
        console.print(f"  /{cmd.filename[:-3]:<16s}\u2014 {descriptions[cmd]}")


@app.command()
def status():
    """Show current research project status."""
    research_dir = Path(RESEARCH_DIR_NAME)
    if not research_dir.is_dir():
        console.print(Panel(
            f"No {RESEARCH_DIR_NAME}/ directory found. Run [cyan]{APP_NAME} init[/cyan] first.",
            title="Error",
            border_style="red",
        ))
        raise typer.Exit(1)

    brief = research_dir / "brief.md"
    plans_dir = research_dir / "plans"

    plan_dirs = sorted(d for d in plans_dir.iterdir() if d.is_dir()) if plans_dir.is_dir() else []

    console.print("[bold]marketkit research project[/bold]")
    console.print(f"  Brief:    {'[green]exists[/green]' if brief.exists() else '[dim]not created[/dim]'}")
    console.print(f"  Plans:    {len(plan_dirs)}")
    for p in plan_dirs:
        has_plan = (p / "plan.md").exists()
        has_data = (p / "data").is_dir() and any((p / "data").iterdir())
        has_report = (p / "report.md").exists()
        if has_report:
            state = "[green]report[/green]"
        elif has_data:
            state = "[cyan]data[/cyan]"
        elif has_plan:
            state = "[yellow]plan[/yellow]"
        else:
            state = "[dim]empty[/dim]"
        console.print(f"    {p.name}  {state}")


@app.command()
def gather(
    plan: Optional[str] = typer.Option(None, help="Specific plan name (e.g., 20260301-1430-ai-travel)"),
    top: Optional[int] = typer.Option(None, help="Return only the top N highest-scoring posts"),
):
    """Merge and deduplicate all collected posts. Outputs JSON to stdout."""
    from .writer import gather_posts

    research_dir = Path(RESEARCH_DIR_NAME)
    if not research_dir.is_dir():
        console.print(Panel(
            f"No {RESEARCH_DIR_NAME}/ directory found. Run [cyan]{APP_NAME} init[/cyan] first.",
            title="Error",
            border_style="red",
        ))
        raise typer.Exit(1)

    plans_dir = research_dir / "plans"

    if plan:
        data_dirs = [plans_dir / plan / "data"]
        if not data_dirs[0].is_dir():
            console.print(Panel(f"Plan [bold]{plan}[/bold] not found.", title="Error", border_style="red"))
            raise typer.Exit(1)
    else:
        data_dirs = sorted(plans_dir.glob("*/data"))

    if not data_dirs:
        console.print(Panel("No plans found.", title="Error", border_style="red"))
        raise typer.Exit(1)

    seen_ids: set[str] = set()
    all_posts: list[dict] = []
    all_collections: list[dict] = []

    for data_dir in data_dirs:
        result = gather_posts(data_dir)
        all_collections.extend(result["collections"])
        for post in result["posts"]:
            pid = post.get("id") or post.get("url") or ""
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_posts.append(post)
            elif not pid:
                all_posts.append(post)

    # Sort by score descending, slice to top N if requested
    all_posts.sort(key=lambda p: p.get("score", 0), reverse=True)
    total_available = len(all_posts)
    if top is not None:
        if top < 1:
            console.print(Panel("--top must be >= 1.", title="Error", border_style="red"))
            raise typer.Exit(1)
        all_posts = all_posts[:top]

    output = {
        "total_posts": total_available,
        "returned_posts": len(all_posts),
        "collections": all_collections,
        "posts": all_posts,
    }

    # Output to stdout for piping (use print, not console.print, to avoid markup)
    print(json.dumps(output, indent=2, ensure_ascii=False))


@app.command()
def context():
    """Output project context as JSON for agent consumption."""
    root = _find_project_root()
    if root is None:
        sys.stderr.write(f"Error: No {RESEARCH_DIR_NAME}/ directory found in any parent directory.\n")
        raise typer.Exit(1)

    research_dir = root / RESEARCH_DIR_NAME

    # AVAILABLE_DOCS: check for key documents
    available_docs: list[str] = []
    for doc_name in ("brief.md",):
        if (research_dir / doc_name).exists():
            available_docs.append(doc_name)

    # PLANS: scan plans/ directory
    plans: list[dict] = []
    plans_dir = research_dir / "plans"
    if plans_dir.is_dir():
        for plan_dir in sorted(plans_dir.iterdir()):
            if plan_dir.is_dir():
                data_dir = plan_dir / "data"
                data_files = len(list(data_dir.glob("*"))) if data_dir.is_dir() else 0
                plans.append({
                    "name": plan_dir.name,
                    "has_plan": (plan_dir / "plan.md").exists(),
                    "has_report": (plan_dir / "report.md").exists(),
                    "data_files": data_files,
                })

    output = {
        "PROJECT_ROOT": str(root),
        "RESEARCH_DIR": str(research_dir),
        "BRIEF": str(research_dir / "brief.md"),
        "TEMPLATES_DIR": str(research_dir / "templates"),
        "AVAILABLE_DOCS": available_docs,
        "PLANS": plans,
        "PLAN_COUNT": len(plans),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


@app.command("search-x-paid-api")
def search_x_paid_api(
    query: str = typer.Argument(..., help="Search query for X/Twitter API"),
    output: Path = typer.Option(..., help="Output JSON file path"),
    angle: str = typer.Option("", help="Research angle name"),
    icp: str = typer.Option("", help="Target ICP"),
    max_results: int = typer.Option(100, help="Max results per page (10-100)"),
    pages: int = typer.Option(1, help="Number of pages to fetch"),
):
    """Search X/Twitter via paid API v2. Requires X_BEARER_TOKEN."""
    from .collectors.x_api import XApiCollector
    from .writer import write_collection

    try:
        collector = XApiCollector()
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        raise typer.Exit(1)

    try:
        posts = collector.search(query, max_results=max_results, pages=pages)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        raise typer.Exit(1)

    output_path = output.resolve()
    write_collection(output_path, posts, angle=angle, target_icp=icp, query=query, source="twitter-api")

    print(json.dumps({"posts_collected": len(posts), "output": str(output_path)}))


@app.command("new-plan")
def new_plan(
    slug: str = typer.Argument(help="Short descriptive slug for the plan (e.g., 'ai-travel')"),
):
    """Create a new research plan directory. Outputs JSON to stdout."""
    from datetime import datetime

    root = _find_project_root()
    if root is None:
        sys.stderr.write(f"Error: No {RESEARCH_DIR_NAME}/ directory found in any parent directory.\n")
        raise typer.Exit(1)

    research_dir = root / RESEARCH_DIR_NAME
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    plan_name = f"{timestamp}-{slug}"

    plan_dir = research_dir / "plans" / plan_name
    data_dir = plan_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "PLAN_DIR": str(plan_dir),
        "DATA_DIR": str(data_dir),
        "PLAN": str(plan_dir / "plan.md"),
        "REPORT": str(plan_dir / "report.md"),
        "PLAN_NAME": plan_name,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
