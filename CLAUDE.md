# CLAUDE.md — marketkit

Structured market research toolkit for AI coding agents.

## Project Structure

```
pyproject.toml          # Package config (marketkit-cli)
src/marketkit/          # Source code
tests/                  # Test suite
docs/plans/             # Planning documents
```

## Development

```bash
uv venv && uv pip install -e ".[test]"
uv run python -m pytest -v
```

## Command Template Rules

These rules are constitutional — every `/mk.*` command template must follow them.

### Gate Checks with Actionable Errors

Every command validates prerequisites before doing anything. If something's missing, it names the exact command to run to fix it. No silent degradation. Example: "No brief found. Run `/mk.specify` first."

### Make Informed Guesses

Agents should be opinionated, not indecisive. Max 3 `[NEEDS CLARIFICATION]` markers. Default to industry-standard assumptions for things like retention, performance targets, error handling. Only ask when the choice significantly impacts scope.

## Research Before Implementation

Before writing any implementation code, research the library/service/API first. Even for commonly used tools.

**The rule:** If you're about to write code that calls an external library or service, and you haven't read its current docs in this session, stop and research first.
