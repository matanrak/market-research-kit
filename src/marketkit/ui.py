"""marketkit UI components: console, progress tracking, banner, interactive selectors."""

from __future__ import annotations

import readchar
import typer
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from typer.core import TyperGroup

from .constants import APP_NAME

console = Console()


# --- StepTracker (simplified from spec-kit's StepTracker) ---

class StepTracker:
    """Live progress tree for CLI commands. Renders as a Rich Tree."""

    def __init__(self, title: str):
        self.title = title
        self.steps: list[dict] = []
        self._refresh_cb = None

    def add(self, key: str, label: str):
        if not any(s["key"] == key for s in self.steps):
            self.steps.append({"key": key, "label": label, "status": "pending", "detail": ""})
            self._maybe_refresh()

    def start(self, key: str, detail: str = ""):
        self._update(key, "running", detail)

    def complete(self, key: str, detail: str = ""):
        self._update(key, "done", detail)

    def error(self, key: str, detail: str = ""):
        self._update(key, "error", detail)

    def skip(self, key: str, detail: str = ""):
        self._update(key, "skipped", detail)

    def _update(self, key: str, status: str, detail: str):
        for step in self.steps:
            if step["key"] == key:
                step["status"] = status
                step["detail"] = detail
                break
        self._maybe_refresh()

    def _maybe_refresh(self):
        if self._refresh_cb:
            try:
                self._refresh_cb()
            except Exception:
                pass

    def attach_refresh(self, cb):
        self._refresh_cb = cb

    def render(self) -> Tree:
        tree = Tree(f"[cyan]{self.title}[/cyan]", guide_style="grey50")
        status_icons = {
            "done": "[green]\u25cf[/green]",
            "pending": "[bright_black]\u25cb[/bright_black]",
            "running": "[cyan]\u25cb[/cyan]",
            "error": "[red]\u25cf[/red]",
            "skipped": "[yellow]\u25cb[/yellow]",
        }
        for step in self.steps:
            icon = status_icons.get(step["status"], "\u25cb")
            detail = f" [bright_black]({step['detail']})[/bright_black]" if step["detail"] else ""
            if step["status"] == "pending":
                tree.add(f"{icon} [bright_black]{step['label']}{detail}[/bright_black]")
            else:
                tree.add(f"{icon} {step['label']}{detail}")
        return tree


# --- Interactive selector (spec-kit pattern: readchar + Rich Live) ---

def get_key() -> str:
    """Get a single keypress in a cross-platform way using readchar."""
    key = readchar.readkey()

    if key == readchar.key.UP or key == readchar.key.CTRL_P:
        return "up"
    if key == readchar.key.DOWN or key == readchar.key.CTRL_N:
        return "down"
    if key == readchar.key.ENTER:
        return "enter"
    if key == readchar.key.ESC:
        return "escape"
    if key == readchar.key.CTRL_C:
        raise KeyboardInterrupt
    return key


def select_with_arrows(
    options: dict[str, str],
    prompt_text: str = "Select an option",
    default_key: str | None = None,
) -> str:
    """Interactive arrow-key selection with Rich Live display.

    Args:
        options: Dict of {key: description} to display.
        prompt_text: Text shown above the options.
        default_key: Option key to start highlighted.

    Returns:
        The selected option key.
    """
    option_keys = list(options.keys())
    if default_key and default_key in option_keys:
        selected_index = option_keys.index(default_key)
    else:
        selected_index = 0

    selected_key = None

    def create_selection_panel():
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="left", width=3)
        table.add_column(style="white", justify="left")

        for i, key in enumerate(option_keys):
            if i == selected_index:
                table.add_row("\u25b6", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")
            else:
                table.add_row(" ", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")

        table.add_row("", "")
        table.add_row("", "[dim]Use \u2191/\u2193 to navigate, Enter to select, Esc to cancel[/dim]")

        return Panel(
            table,
            title=f"[bold]{prompt_text}[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )

    console.print()

    def run_selection_loop():
        nonlocal selected_key, selected_index
        with Live(create_selection_panel(), console=console, transient=True, auto_refresh=False) as live:
            while True:
                try:
                    key = get_key()
                    if key == "up":
                        selected_index = (selected_index - 1) % len(option_keys)
                    elif key == "down":
                        selected_index = (selected_index + 1) % len(option_keys)
                    elif key == "enter":
                        selected_key = option_keys[selected_index]
                        break
                    elif key == "escape":
                        console.print("\n[yellow]Selection cancelled[/yellow]")
                        raise typer.Exit(1)

                    live.update(create_selection_panel(), refresh=True)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Selection cancelled[/yellow]")
                    raise typer.Exit(1)

    run_selection_loop()

    if selected_key is None:
        console.print("\n[red]Selection failed.[/red]")
        raise typer.Exit(1)

    return selected_key


# --- Banner (spec-kit pattern: custom TyperGroup) ---

class BannerGroup(TyperGroup):
    def format_help(self, ctx, formatter):
        show_banner()
        super().format_help(ctx, formatter)


BANNER = r"""
  _ __ ___   __ _ _ __| | _____| |_| | _(_) |_
 | '_ ` _ \ / _` | '__| |/ / _ \ __| |/ / | __|
 | | | | | | (_| | |  |   <  __/ |_|   <| | |_
 |_| |_| |_|\__,_|_|  |_|\_\___|\__|_|\_\_|\__|
"""
TAGLINE = "Structured Market Research for AI Coding Agents"


def show_banner():
    banner_lines = BANNER.strip().split("\n")
    colors = ["bright_blue", "blue", "cyan", "bright_cyan", "white", "bright_white"]

    styled_banner = Text()
    for i, line in enumerate(banner_lines):
        color = colors[i % len(colors)]
        styled_banner.append(line + "\n", style=color)

    console.print(Align.center(styled_banner))
    console.print(Align.center(Text(TAGLINE, style="italic bright_yellow")))
    console.print()
