# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer",
#     "click>=8.1",
#     "rich",
#     "httpx",
#     "truststore>=0.10.4",
#     "platformdirs",
#     "readchar",
# ]
# ///
"""marketkit — structured market research for AI coding agents."""

from .cli import app
from .constants import APP_NAME, COMMAND_PREFIX, RESEARCH_DIR_NAME, CommandTemplate


def main():
    app()


if __name__ == "__main__":
    main()
