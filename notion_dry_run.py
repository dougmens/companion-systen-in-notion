#!/usr/bin/env python3
"""
notion_dry_run.py – Notion Sync dry-run entrypoint.

Invoked by notion_sync_launchagent.sh (which is triggered by launchd).
Performs a read-only sync preview against the Notion registry.

Exit codes:
  0  – success
  1  – runtime / Notion API error
  2  – bad arguments / missing registry file
"""

import argparse
import json
import logging
import os
import sys


# ---------------------------------------------------------------------------
# Logging setup – goes to stdout so launchd can capture it via
# StandardOutPath.  Format includes the process name so log files are
# unambiguous when multiple agents write to the same directory.
# ---------------------------------------------------------------------------
def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


log = logging.getLogger("notion_dry_run")


# ---------------------------------------------------------------------------
# Argument parsing – strict, no abbreviations, no surprises.
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notion_dry_run.py",
        description="Dry-run Notion sync – reads registry, previews changes, writes nothing.",
        allow_abbrev=False,  # prevents --reg matching --registry
    )
    parser.add_argument(
        "--registry",
        required=True,
        metavar="PATH",
        help="Path to the JSON registry file (required).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.environ.get("DEBUG", "0") == "1",
        help="Enable debug logging (also activated by DEBUG=1 env var).",
    )
    return parser


# ---------------------------------------------------------------------------
# Registry loading with clear error messages.
# ---------------------------------------------------------------------------
def _load_registry(path: str) -> dict:
    if not os.path.exists(path):
        log.error(
            "Registry file not found: %s\n"
            "  Hint: check --registry path or REGISTRY_PATH env var in the plist.",
            path,
        )
        sys.exit(2)

    if not os.path.isfile(path):
        log.error("Registry path exists but is not a file: %s", path)
        sys.exit(2)

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        log.error("Registry file is not valid JSON: %s\n  Detail: %s", path, exc)
        sys.exit(2)

    return data


# ---------------------------------------------------------------------------
# Main logic.
# ---------------------------------------------------------------------------
def main() -> None:
    parser = _build_parser()

    # Capture argparse errors and exit with code 2 (not the default 1).
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse already printed the error; preserve its exit code.
        sys.exit(exc.code)

    _configure_logging(args.debug)

    # ------------------------------------------------------------------
    # Early argv dump – confirms the shell forwarded arguments correctly.
    # Visible at INFO level so it always appears in launchd logs.
    # ------------------------------------------------------------------
    log.info("notion_dry_run.py starting. sys.argv = %r", sys.argv)
    log.info("Resolved --registry = %r", args.registry)

    registry = _load_registry(args.registry)
    log.info(
        "Registry loaded: version=%s, databases=%d",
        registry.get("version", "unknown"),
        len(registry.get("databases", [])),
    )

    # ------------------------------------------------------------------
    # Dry-run body – placeholder for real Notion API calls.
    # Replace this section with actual sync logic; do NOT touch the
    # argument-handling or logging above.
    # ------------------------------------------------------------------
    log.info("Dry-run complete – no changes written.")


if __name__ == "__main__":
    main()
