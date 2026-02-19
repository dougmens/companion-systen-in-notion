# Notion Sync – LaunchAgent Execution Chain

Hardened `launchd → bash launcher → python` pipeline for Notion Sync dry-runs.

---

## A) Root Cause Summary

### Error symptoms

```
error: the following arguments are required: --registry
sh: --registry: command not found
```

### Why this happens

Both errors come from the same underlying mistake: **`--registry <path>` is not
a single argument – it is two separate tokens**, and they were either
concatenated into one string or newline-split by the shell.

| Pattern | What happens |
|---|---|
| `ProgramArguments` with one `<string>/path/script.sh --registry /path/to/reg.json</string>` | launchd passes the whole thing as `argv[0]`; bash tries to run `--registry` as a command → `sh: --registry: command not found` |
| `cmd="python3 $SCRIPT --registry $REG"` then `$cmd` (unquoted) | Shell word-splits on spaces → python sees `--registry` and `/path/to/reg.json` as two argv elements correctly only if there are no spaces, but fails silently if the path has spaces; eval makes it worse |
| `eval "$cmd"` | eval re-runs the string through the shell; if `$REG` contains spaces or special chars the shell re-tokenises incorrectly |
| Newline in variable | `ARGS=$'--registry\n/path'`; `"$ARGS"` passes one token with a literal newline; python's argparse sees `--registry\n/path` as one unrecognised flag |

### The fix

1. **Plist** – Every argument is its own `<string>` element in `ProgramArguments`.
2. **Launcher** – Arguments are stored in a bash array and forwarded via
   `exec "${cmd[@]}"`. No `eval`, no `$cmd`, no `sh -c`.
3. **Python** – `argparse` with `allow_abbrev=False` and `required=True` on
   `--registry`; crisp file-not-found message; `sys.argv` logged at startup.

---

## Repository layout

```
.
├── notion_sync_launchagent.sh        # bash launcher (called by launchd)
├── notion_dry_run.py                 # python entrypoint
├── config/
│   └── notion_sync_registry.json    # registry file (edit for real databases)
├── launchd/
│   └── com.user.notionsync.plist    # LaunchAgent plist (template)
├── logs/                            # created at runtime (gitignored)
└── tests/
    └── test_argv_passing.sh         # regression test (13 assertions)
```

---

## B) Installation

### 1. Set absolute paths in the plist

Edit `launchd/com.user.notionsync.plist` and replace every occurrence of
`/Users/yourname` with your real home directory:

```bash
REPO="$HOME/companion-systen-in-notion"
sed -i '' "s|/Users/yourname|$HOME|g" launchd/com.user.notionsync.plist
```

### 2. Create the log directory

```bash
mkdir -p ~/Library/Logs/NotionSync
```

### 3. Install the LaunchAgent

```bash
cp launchd/com.user.notionsync.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.notionsync.plist
```

### 4. Reload after any plist edit

```bash
launchctl bootout  gui/$(id -u) ~/Library/LaunchAgents/com.user.notionsync.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.notionsync.plist
```

---

## C) Manual 5-step Verification Checklist

Run these in order from the repo root.

### Step 1 – Syntax check

```bash
bash -n notion_sync_launchagent.sh && echo "OK: launcher syntax"
python3 -m py_compile notion_dry_run.py && echo "OK: python syntax"
plutil -lint launchd/com.user.notionsync.plist && echo "OK: plist valid"
```

Expected: all three print OK.

### Step 2 – CLI direct run (python)

```bash
python3 notion_dry_run.py --registry config/notion_sync_registry.json
```

Expected output includes:

```
[INFO] notion_dry_run: notion_dry_run.py starting. sys.argv = [..., '--registry', '...registry.json']
[INFO] notion_dry_run: Dry-run complete – no changes written.
```

### Step 3 – Launcher run with argv debug

```bash
DEBUG=1 bash notion_sync_launchagent.sh --registry config/notion_sync_registry.json
```

Expected stderr includes (from the launcher's debug block):

```
DEBUG notion_sync_launchagent.sh: exec tokens:
  argv[0]=python3
  argv[1]=/absolute/path/notion_dry_run.py
  argv[2]=--registry
  argv[3]=/absolute/path/config/notion_sync_registry.json
```

`argv[2]` must be exactly `--registry` and `argv[3]` must be exactly the path.
If they are merged into one token, the argument passing is still broken.

### Step 4 – launchctl start (one-shot)

```bash
launchctl start com.user.notionsync
sleep 2
tail -30 ~/Library/Logs/NotionSync/notion_sync.stdout.log
```

Expected log contains `sys.argv` line showing `--registry` as a separate token.

### Step 5 – Confirm error paths

```bash
# Missing --registry flag → exit 2
python3 notion_dry_run.py; echo "exit: $?"

# Wrong path → exit 2 with clear message
python3 notion_dry_run.py --registry /tmp/no_such_file.json; echo "exit: $?"
```

---

## D) Automated regression test

```bash
bash tests/test_argv_passing.sh
```

Runs 7 test groups (13 assertions) covering:
- Syntax checks
- Direct python invocation
- Launcher forwarding + DEBUG token dump
- Missing flag → non-zero exit
- Bad path → non-zero exit
- Path with spaces → survives intact

---

## Debug flag

| Method | Effect |
|---|---|
| `DEBUG=1 bash notion_sync_launchagent.sh …` | Prints exact `argv[n]` tokens before exec |
| `python3 notion_dry_run.py --debug …` | Sets log level to DEBUG |
| `DEBUG=1 python3 notion_dry_run.py …` | Same as `--debug` |
| Add `<key>DEBUG</key><string>1</string>` in plist `EnvironmentVariables` | Enables debug in launchd context |
