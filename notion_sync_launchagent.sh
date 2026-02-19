#!/usr/bin/env bash
# notion_sync_launchagent.sh
#
# LaunchAgent entry-point for Notion Sync.
# Called by launchd via ProgramArguments.  Forwards all arguments verbatim
# to notion_dry_run.py using a bash array so no word-splitting or eval ever
# touches the argument values.
#
# Usage (CLI):
#   ./notion_sync_launchagent.sh --registry config/notion_sync_registry.json
#
# Usage (launchd): configured via com.user.notionsync.plist
#
# Environment overrides:
#   REGISTRY_PATH  – fallback if --registry is not supplied on the CLI
#   DEBUG=1        – print resolved argv tokens before exec

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve the directory this script lives in (works even when called via a
# symlink, because launchd resolves the real path before exec).
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Locate python3.  Prefer the explicit path from the plist EnvironmentVariables
# (NOTION_PYTHON), then PATH.
# ---------------------------------------------------------------------------
PY="${NOTION_PYTHON:-python3}"

# ---------------------------------------------------------------------------
# Parse --registry from the arguments forwarded by launchd / the caller.
# We do NOT use eval or string-concatenation.  We walk $@ manually so that
# paths containing spaces survive intact.
# ---------------------------------------------------------------------------
REGISTRY_PATH="${REGISTRY_PATH:-}"   # env fallback (set in plist if desired)

args_remaining=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --registry)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --registry requires a path argument" >&2
                exit 2
            fi
            REGISTRY_PATH="$2"
            shift 2
            ;;
        --registry=*)
            REGISTRY_PATH="${1#--registry=}"
            shift
            ;;
        *)
            args_remaining+=("$1")
            shift
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Validate we actually have a registry path (from CLI or env).
# ---------------------------------------------------------------------------
if [[ -z "$REGISTRY_PATH" ]]; then
    echo "ERROR: --registry <path> is required (or set REGISTRY_PATH env var)" >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Build the command as an array – the only safe way to forward arguments.
# Each token is a separate array element; no globbing, no word-splitting.
# ---------------------------------------------------------------------------
cmd=(
    "$PY"
    "$SCRIPT_DIR/notion_dry_run.py"
    "--registry"
    "$REGISTRY_PATH"
)

# Forward any extra arguments that were not consumed above.
if [[ ${#args_remaining[@]} -gt 0 ]]; then
    cmd+=("${args_remaining[@]}")
fi

# ---------------------------------------------------------------------------
# Debug: print the exact tokens that will be exec'd.
# Gated behind DEBUG=1 so it is silent in normal launchd operation.
# ---------------------------------------------------------------------------
if [[ "${DEBUG:-0}" == "1" ]]; then
    echo "DEBUG notion_sync_launchagent.sh: exec tokens:" >&2
    for i in "${!cmd[@]}"; do
        printf '  argv[%d]=%q\n' "$i" "${cmd[$i]}" >&2
    done
fi

# ---------------------------------------------------------------------------
# Replace this shell process with python.  exec means no child-process
# overhead and signals propagate correctly to python.
# ---------------------------------------------------------------------------
exec "${cmd[@]}"
