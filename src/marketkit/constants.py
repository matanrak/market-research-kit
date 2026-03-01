"""marketkit constants and enums."""

from __future__ import annotations

from enum import Enum

APP_NAME = "marketkit"
COMMAND_PREFIX = "mk"
RESEARCH_DIR_NAME = ".market-research"

# Agent configurations: where each AI coding agent expects slash commands.
AGENT_CONFIG: dict[str, dict[str, str]] = {
    "claude": {"name": "Claude Code", "folder": ".claude", "subdir": "commands"},
    "gemini": {"name": "Gemini CLI", "folder": ".gemini", "subdir": "commands"},
    "cursor": {"name": "Cursor", "folder": ".cursor", "subdir": "commands"},
    "copilot": {"name": "GitHub Copilot", "folder": ".github", "subdir": "agents"},
    "codex": {"name": "Codex CLI", "folder": ".codex", "subdir": "prompts"},
    "windsurf": {"name": "Windsurf", "folder": ".windsurf", "subdir": "workflows"},
    "opencode": {"name": "opencode", "folder": ".opencode", "subdir": "command"},
}

DEFAULT_AGENT = "claude"


class CommandTemplate(str, Enum):
    """Core slash command templates shipped with marketkit."""
    SPECIFY = "specify"
    PLAN = "plan"
    RESEARCH = "research"
    REPORT = "report"

    @property
    def filename(self) -> str:
        return f"{COMMAND_PREFIX}.{self.value}.md"

    @property
    def source(self) -> str:
        return f"{self.value}.md"
