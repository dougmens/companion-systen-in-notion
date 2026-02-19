#!/usr/bin/env bash
# tests/test_argv_passing.sh
#
# Regression test for the launchd → launcher → python argument-passing chain.
# Tests that --registry is always received by python as a distinct argv token,
# never concatenated, never shell-split, never interpreted as a command.
#
# Run with:
#   bash tests/test_argv_passing.sh
#
# Returns:
#   0 – all tests passed
#   1 – one or more tests failed

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHER="$REPO_ROOT/notion_sync_launchagent.sh"
PYTHON_SCRIPT="$REPO_ROOT/notion_dry_run.py"
REGISTRY="$REPO_ROOT/config/notion_sync_registry.json"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass() { echo "  PASS: $1"; (( PASS++ )) || true; }
fail() { echo "  FAIL: $1"; (( FAIL++ )) || true; }

assert_contains() {
    local label="$1" pattern="$2" output="$3"
    # Use grep -F -- to prevent patterns starting with '-' being parsed as flags.
    if echo "$output" | grep -qF -- "$pattern"; then
        pass "$label"
    else
        fail "$label – expected to find: $pattern"
        echo "    output was:"
        echo "$output" | sed 's/^/      /'
    fi
}

assert_exit_zero() {
    local label="$1" code="$2"
    if [[ "$code" -eq 0 ]]; then
        pass "$label (exit 0)"
    else
        fail "$label (exit $code, expected 0)"
    fi
}

assert_exit_nonzero() {
    local label="$1" code="$2"
    if [[ "$code" -ne 0 ]]; then
        pass "$label (exit $code ≠ 0)"
    else
        fail "$label (exit 0, expected non-zero)"
    fi
}

# ---------------------------------------------------------------------------
echo "=== Test 1: bash -n syntax check (launcher) ==="
bash -n "$LAUNCHER" && pass "bash -n launcher" || fail "bash -n launcher"

# ---------------------------------------------------------------------------
echo "=== Test 2: python3 -m py_compile (entrypoint) ==="
python3 -m py_compile "$PYTHON_SCRIPT" && pass "py_compile notion_dry_run.py" || fail "py_compile notion_dry_run.py"

# ---------------------------------------------------------------------------
echo "=== Test 3: Python receives --registry as distinct argv token ==="
# We call python directly to validate argparse accepts the argument.
out=$(python3 "$PYTHON_SCRIPT" --registry "$REGISTRY" 2>&1)
ec=$?
assert_exit_zero "direct python --registry invocation" "$ec"
assert_contains "sys.argv logged" "--registry" "$out"
assert_contains "registry path logged" "$REGISTRY" "$out"

# ---------------------------------------------------------------------------
echo "=== Test 4: Launcher forwards --registry correctly ==="
out=$(DEBUG=1 bash "$LAUNCHER" --registry "$REGISTRY" 2>&1)
ec=$?
assert_exit_zero "launcher --registry forwarding" "$ec"
# DEBUG=1 makes the launcher print: argv[2]=--registry  argv[3]=<path>
assert_contains "argv[2] is --registry flag" "argv[2]=--registry" "$out"
assert_contains "argv[3] is registry path"   "$REGISTRY"           "$out"
assert_contains "python received --registry" "--registry"           "$out"

# ---------------------------------------------------------------------------
echo "=== Test 5: Missing --registry causes non-zero exit ==="
set +e
python3 "$PYTHON_SCRIPT" 2>/dev/null
ec=$?
set -e
assert_exit_nonzero "missing --registry → non-zero exit" "$ec"

# ---------------------------------------------------------------------------
echo "=== Test 6: Missing registry FILE causes non-zero exit ==="
set +e
python3 "$PYTHON_SCRIPT" --registry /tmp/does_not_exist_9f3c2a.json 2>/dev/null
ec=$?
set -e
assert_exit_nonzero "bad registry path → non-zero exit" "$ec"

# ---------------------------------------------------------------------------
echo "=== Test 7: Path with spaces survives arg forwarding ==="
SPACE_DIR="$(mktemp -d "/tmp/notion test XXXXXX")"
SPACE_REG="$SPACE_DIR/registry with spaces.json"
cp "$REGISTRY" "$SPACE_REG"
out=$(DEBUG=1 bash "$LAUNCHER" --registry "$SPACE_REG" 2>&1)
ec=$?
# Cleanup immediately.
rm -rf "$SPACE_DIR"
assert_exit_zero "path-with-spaces invocation" "$ec"
assert_contains "space path in argv log" "notion test" "$out"

# ---------------------------------------------------------------------------
echo ""
echo "Results: $PASS passed, $FAIL failed"
if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
