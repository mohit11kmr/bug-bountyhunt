#!/usr/bin/env python3
"""
BountyGrimoire — local status + control dashboard.

- Monitors: current program, every program/target scanned (memory/ + sessions/),
  findings, per-program AI spend, and a live progress readout while a scan runs.
- Operates: starting a scan launches `opencode run` / `claude -p` as a
  subprocess (via `script` for pty-like line buffering), piped straight to a
  log file this dashboard polls and streams into the program's own workspace
  card — no separate terminal window is opened.

Zero third-party dependencies — Python stdlib only. Binds to 127.0.0.1 ONLY:
this can trigger real scans and reads sensitive scan data, must never be
reachable from outside this machine.

Run:  python3 gui/server.py
Then open: http://127.0.0.1:8765
"""
import base64
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
GUI_DIR = Path(__file__).resolve().parent
RUNS_DIR = GUI_DIR / "runs"
RUNS_INDEX_PATH = RUNS_DIR / "_index.json"
WATCHLIST_PATH = GUI_DIR / "watchlist.json"
FINDINGS_STATUS_PATH = GUI_DIR / "findings_status.json"
REPORTS_DIR = ROOT / "reports"
HOST = "127.0.0.1"
PORT = 8765

FINDING_SUBMIT_STATUSES = {"not_reported", "drafted", "submitted"}
# The 17 hunter types — used to (a) recognize hunter-subagent tool calls in a
# live run's event stream for progress tracking, and (b) match a finding's
# `type` field against report filenames when auto-detecting drafted reports.
HUNTER_TYPES = ["idor", "ssrf", "sqli", "xss", "auth", "rce", "xxe", "ssti",
                "secrets", "otp", "pii", "bizlogic", "callback", "enumerable",
                "insecure", "referer", "checksum"]

ARG_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,255}$")
TYPES_RE = re.compile(r"^[a-z,]{1,200}$")
HANDLE_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
ACTIONS = {"load-program-h1", "hunt", "hunt-auth"}

# Matches this project's launcher scripts (start-bounty.sh / -gemini.sh / -bigpickle.sh) —
# same three ways of running BountyGrimoire, now selectable per-run from the GUI.
# claude-sonnet is the default: measured directly (see fixlog) — `claude -p
# --output-format stream-json` flushes output progressively (visible within
# ~3s, growing steadily), while `opencode run --format json` buffers
# internally and delivers everything in one lump near the end regardless of
# how it's piped. For a live "watch it work" feed, Claude streams; opencode
# batches — pick opencode only when the free tier matters more than that.
PROFILES = {
    "claude-sonnet": {"cli": "claude", "model": "sonnet",
                       "label": "Claude Code · Sonnet (live streaming)"},
    "opencode-bigpickle": {"cli": "opencode", "model": "opencode/big-pickle",
                            "label": "opencode · big-pickle (free, output arrives in batches)"},
    "opencode-gemini": {"cli": "opencode", "model": "google/gemini-3.6-flash",
                         "label": "opencode · Gemini (output arrives in batches)"},
}
DEFAULT_PROFILE = "claude-sonnet"

RUNS = {}  # run_id -> run dict (includes non-serializable _proc while live)
RUNS_LOCK = threading.Lock()
WATCHLIST_LOCK = threading.Lock()


# ── status data (read-only) ─────────────────────────────────────────────────

def _parse_scope_table(text):
    """Parse the '## ... IN Scope' markdown table CLAUDE.md is generated
    with: `| Target | Type | Notes |` rows until the next heading."""
    m = re.search(r"^##[^\n]*IN Scope[^\n]*\n(.*?)(?=\n##|\Z)", text, re.S | re.M)
    if not m:
        return []
    targets = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("Target", "") or set(cells[0]) <= {"-", ":"}:
            continue
        notes = cells[2] if len(cells) > 2 else ""
        targets.append({
            "target": cells[0], "type": cells[1] if len(cells) > 1 else "",
            "notes": notes[:200],
        })
    return targets


def read_current_program():
    claude_md = ROOT / "CLAUDE.md"
    if not claude_md.exists():
        return None
    text = claude_md.read_text(errors="replace")
    name_match = re.search(r"^#\s*Security Agent\s*—\s*(.+)$", text, re.M)
    handle_match = re.search(r"HackerOne:\s*https://hackerone\.com/(\S+)", text)
    return {
        "name": name_match.group(1).strip() if name_match else None,
        "handle": handle_match.group(1).strip() if handle_match else None,
        "scope": _parse_scope_table(text),
    }


def _load_json(path):
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception:
        return None


# ── HackerOne program search ────────────────────────────────────────────────

def _h1_credentials():
    """Read H1 API credentials from .env. Accepts both naming conventions
    seen across this project (H1_USER/H1_TOKEN) and the hackerone-mcp's own
    (H1_USERNAME/H1_API_TOKEN), since they've historically diverged here."""
    env_path = ROOT / ".env"
    creds = {}
    if env_path.exists():
        for line in env_path.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                creds[k.strip()] = v.strip()
    user = creds.get("H1_USER") or creds.get("H1_USERNAME")
    token = creds.get("H1_TOKEN") or creds.get("H1_API_TOKEN")
    return user, token


def search_h1_programs(query, limit=25, high_probability_only=True):
    """Search public HackerOne programs by name/handle substring.
    Requires H1 credentials in .env — HackerOne's list-programs endpoint
    rejects unauthenticated requests even for public programs.

    high_probability_only filters to programs that actually pay bounties AND
    are currently accepting submissions — the two facts the list endpoint
    exposes that matter most for "is this worth my time". It's a floor, not
    a ranking: HackerOne's public API doesn't expose payout history/averages,
    so this can't rank by expected payout, only exclude the programs that
    structurally can't pay (no bounty program) or won't accept a report right
    now (paused submissions)."""
    user, token = _h1_credentials()
    if not user or not token:
        return None, ("Set H1_USER (or H1_USERNAME) and H1_TOKEN (or H1_API_TOKEN) "
                       "in .env to search HackerOne programs.")

    auth = base64.b64encode(f"{user}:{token}".encode()).decode()
    results = []
    seen_ids = set()
    page = 1
    query_lower = query.lower().strip()

    while len(results) < limit and page <= 20:
        req = urllib.request.Request(
            f"https://api.hackerone.com/v1/hackers/programs?page[size]=100&page[number]={page}",
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json",
                     "User-Agent": "BountyGrimoire/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return None, f"HackerOne API error: {e.code} {e.reason}"
        except Exception as e:
            return None, f"Could not reach HackerOne API: {e}"

        items = data.get("data") or []
        if not items:
            break
        for item in items:
            attrs = item.get("attributes", {})
            handle = attrs.get("handle", "")
            name = attrs.get("name", "")
            if item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])

            matches_query = not query_lower or query_lower in handle.lower() or query_lower in name.lower()
            if not matches_query:
                continue
            if high_probability_only and not (
                attrs.get("offers_bounties") and attrs.get("submission_state") == "open"
            ):
                continue

            results.append({
                "handle": handle,
                "name": name,
                "offers_bounties": attrs.get("offers_bounties"),
                "state": attrs.get("state"),
                "submission_state": attrs.get("submission_state"),
            })
            if len(results) >= limit:
                break
        if not data.get("links", {}).get("next"):
            break
        page += 1

    return results, None


# ── watchlist (operate) ─────────────────────────────────────────────────────

def _read_watchlist():
    if not WATCHLIST_PATH.exists():
        return []
    data = _load_json(WATCHLIST_PATH)
    return data if isinstance(data, list) else []


def _write_watchlist(items):
    WATCHLIST_PATH.write_text(json.dumps(items, indent=2))


def add_to_watchlist(handle, name):
    """Add a handle to the workspace if not already there. Idempotent —
    returns the existing entry instead of erroring if it's already tracked,
    since 'Start' re-adds on every click."""
    if not HANDLE_RE.match(handle or ""):
        return None, "Invalid handle."
    with WATCHLIST_LOCK:
        items = _read_watchlist()
        existing = next((i for i in items if i["handle"] == handle), None)
        if existing:
            return existing, None
        entry = {"handle": handle, "name": name or handle, "added_at": _now_iso()}
        items.append(entry)
        _write_watchlist(items)
    return entry, None


def remove_from_watchlist(handle):
    with WATCHLIST_LOCK:
        items = _read_watchlist()
        new_items = [i for i in items if i["handle"] != handle]
        if len(new_items) == len(items):
            return False, "Not on the watchlist."
        _write_watchlist(new_items)
    return True, None


def _empty_program(slug):
    return {
        "slug": slug, "last_updated": None, "confirmed_patterns": 0,
        "false_positives": 0, "discovered_endpoints": 0, "sessions": [],
    }


def read_memory():
    programs = {}
    memory_dir = ROOT / "memory"
    if not memory_dir.exists():
        return programs
    for f in memory_dir.glob("*.json"):
        data = _load_json(f)
        if data is None:
            continue
        slug = data.get("program") or f.stem
        programs[slug] = {
            "slug": slug,
            "last_updated": data.get("last_updated"),
            "confirmed_patterns": len(data.get("confirmed_patterns") or []),
            "false_positives": len(data.get("false_positives") or []),
            "discovered_endpoints": len(data.get("discovered_endpoints") or []),
            "sessions": [],
        }
    return programs


def read_sessions(programs):
    """Read /hunt-produced hunt sessions only.

    `sessions/` also holds a second, unrelated file shape written by the
    manual /session-save|-load|-list command trio ({name, saved_at, scope,
    tested_urls, findings, notes} — no `validated_findings`/`hunters_launched`
    key). Only `hunt-*.json` files carry the schema this reader expects;
    skipping anything else avoids injecting a phantom, null-target session
    card into a program's history if a manual audit-session save exists
    alongside real hunt output.
    """
    sessions_dir = ROOT / "sessions"
    if not sessions_dir.exists():
        return
    for f in sorted(sessions_dir.glob("hunt-*.json")):
        data = _load_json(f)
        if data is None:
            continue
        slug = data.get("program") or "unknown"
        if slug not in programs:
            programs[slug] = _empty_program(slug)

        findings = data.get("validated_findings") or []
        by_severity = {}
        for finding in findings:
            sev = finding.get("estimated_severity", "Unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        programs[slug]["sessions"].append({
            "file": f.name,
            "target": data.get("target"),
            "date": data.get("date"),
            "hunters_launched": data.get("hunters_launched"),
            "endpoints_discovered": data.get("endpoints_discovered"),
            "summary": data.get("summary"),
            "findings_count": len(findings),
            "findings_by_severity": by_severity,
            "findings": findings,  # full records — collect_findings() flattens these
            "discarded_count": len(data.get("discarded") or []),
            "bounty_eligible": data.get("bounty_eligible"),
            "suggested_action": data.get("suggested_action"),
        })


# ── findings tracking ────────────────────────────────────────────────────────

def _read_findings_status():
    data = _load_json(FINDINGS_STATUS_PATH)
    return data if isinstance(data, dict) else {}


def _write_findings_status(data):
    FINDINGS_STATUS_PATH.write_text(json.dumps(data, indent=2))


def _reports_index():
    """Lowercased text of every report filename, for a loose drafted-report
    match against a finding's vuln type + target — best-effort, not exact."""
    if not REPORTS_DIR.exists():
        return []
    return [f.name.lower() for f in REPORTS_DIR.glob("*.md")]


def _guess_drafted(finding_type, target, report_names):
    vuln = (finding_type or "").split("/")[0].lower()
    target_frag = (target or "").split(".")[0].lower()
    for name in report_names:
        if vuln and vuln in name and target_frag and target_frag in name:
            return True
    return False


def collect_findings(programs):
    """Flatten every session's findings, across every tracked program, into
    one list — each with a stable id and a locally-tracked report status
    ('not_reported' by default, 'drafted' auto-detected from reports/,
    'submitted' only ever set manually by the user)."""
    status_map = _read_findings_status()
    report_names = _reports_index()
    findings = []
    for slug, p in programs.items():
        for s in p.get("sessions", []):
            for f in s.get("findings", []):
                uid = f"{s['file']}:{f.get('finding_id')}"
                manual_status = status_map.get(uid, {}).get("status")
                status = manual_status or (
                    "drafted" if _guess_drafted(f.get("type"), s.get("target"), report_names)
                    else "not_reported"
                )
                findings.append({
                    "uid": uid, "program": slug, "target": s.get("target"),
                    "date": s.get("date"), "type": f.get("type"),
                    "severity": f.get("estimated_severity"),
                    "endpoint": f.get("endpoint"), "description": f.get("description"),
                    "confidence": f.get("confidence"), "qualifying": f.get("qualifying"),
                    "status": status,
                    "notes": status_map.get(uid, {}).get("notes", ""),
                })
    return findings


def set_finding_status(uid, status=None, notes=None):
    if status is not None and status not in FINDING_SUBMIT_STATUSES:
        return None, f"Invalid status. Use one of: {', '.join(sorted(FINDING_SUBMIT_STATUSES))}"
    with WATCHLIST_LOCK:  # reuse the same lock — both are small local JSON files
        data = _read_findings_status()
        entry = data.get(uid, {})
        if status is not None:
            entry["status"] = status
        if notes is not None:
            entry["notes"] = notes
        data[uid] = entry
        _write_findings_status(data)
    return entry, None


def _derive_status(handle, has_data):
    """not_started / processing / complete.
    - processing: a run for this handle is currently live
    - complete: the most recent run for this handle finished (done/error/stopped
      all count — the action ran to completion, whatever it turned up), OR we
      have memory/session data for it from before this GUI tracked runs
    - not_started: none of the above"""
    last = _last_run_for_handle(handle)
    if last and last["status"] == "running":
        return "processing"
    if last is not None or has_data:
        return "complete"
    return "not_started"


def build_status():
    programs = read_memory()
    read_sessions(programs)
    for p in programs.values():
        p["sessions"].sort(key=lambda s: s.get("date") or "", reverse=True)

    all_findings = collect_findings(programs)  # before stripping full findings below

    watchlist = _read_watchlist()
    for entry in watchlist:
        handle = entry["handle"]
        has_data = handle in programs
        if not has_data:
            programs[handle] = _empty_program(handle)
        programs[handle]["display_name"] = entry["name"]
        programs[handle]["tracked"] = True
        programs[handle]["status"] = _derive_status(handle, has_data)
        programs[handle]["spend"] = program_spend(handle)

    current_program = read_current_program()
    if current_program and current_program.get("handle") in programs:
        hunted_targets = {
            s.get("target", "").lower() for p in programs.values() for s in p.get("sessions", [])
        }
        for t in current_program["scope"]:
            t["hunted"] = t["target"].lower() in hunted_targets

    for p in programs.values():
        for s in p.get("sessions", []):
            s.pop("findings", None)  # full records already folded into all_findings

    return {
        "current_program": current_program,
        "programs": sorted(programs.values(), key=lambda p: p["slug"]),
        "watchlist": watchlist,
        "findings": all_findings,
        "total_spend": total_spend(),
    }


# ── run management (operate) ────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _last_run_for_handle(handle):
    """Most recent run (any status) whose arg matches this handle."""
    with RUNS_LOCK:
        candidates = []
        for r in RUNS.values():
            _refresh(r)
            if (r.get("arg") or "").lower() == (handle or "").lower():
                candidates.append(_public_run(r))
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["started_at"])


def _all_runs_for_handle(handle):
    with RUNS_LOCK:
        return [_public_run(r) for r in RUNS.values()
                if (r.get("arg") or "").lower() == (handle or "").lower()]


def program_spend(handle):
    """Cumulative tokens/cost spent on this handle across every run the GUI
    has ever tracked (the on-disk run index isn't pruned, so this survives
    server restarts) — a rough per-program AI-spend ledger."""
    total_tokens = 0
    total_cost = 0.0
    run_count = 0
    for r in _all_runs_for_handle(handle):
        usage = r.get("usage") or {}
        total_tokens += usage.get("total_tokens") or 0
        total_cost += usage.get("cost") or 0
        run_count += 1
    return {"total_tokens": total_tokens, "total_cost": round(total_cost, 4), "run_count": run_count}


def total_spend():
    total_tokens = 0
    total_cost = 0.0
    with RUNS_LOCK:
        runs = [_public_run(r) for r in RUNS.values()]
    for r in runs:
        usage = r.get("usage") or {}
        total_tokens += usage.get("total_tokens") or 0
        total_cost += usage.get("cost") or 0
    return {"total_tokens": total_tokens, "total_cost": round(total_cost, 4), "run_count": len(runs)}


def _pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _refresh(run):
    """Update a run's status. Normal case: poll our own subprocess handle.
    After a server restart we don't have that handle any more (Popen objects
    aren't persisted) — fall back to a raw PID liveness check for runs
    reattached from the on-disk index."""
    if run["status"] != "running":
        return run

    proc = run.get("_proc")
    if proc is not None:
        rc = proc.poll()
        if rc is None:
            return run
        run["status"] = "done" if rc == 0 else "error"
        run["returncode"] = rc
        lf = run.pop("_log_file", None)
        if lf:
            try:
                lf.close()
            except Exception:
                pass
    elif not _pid_alive(run.get("pid")):
        # Reattached from a previous server instance and the process is gone —
        # we can't recover its real exit code, but it did finish.
        run["status"] = "done"
        run["returncode"] = None
    else:
        return run  # still alive, nothing to update

    run["finished_at"] = run.get("finished_at") or _now_iso()
    if not run.get("usage"):
        try:
            _, _, usage = _parse_log(Path(run["log_path"]), run.get("cli", "opencode"))
            run["usage"] = usage
        except Exception:
            pass
    _save_runs_index()
    return run


def _public_run(run):
    return {k: v for k, v in run.items() if not k.startswith("_")}


def _save_runs_index():
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        data = [_public_run(r) for r in RUNS.values()]
        RUNS_INDEX_PATH.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def load_runs_index():
    """Reattach runs from a previous server process (index survives restarts;
    live Popen handles obviously don't). Called once at startup."""
    data = _load_json(RUNS_INDEX_PATH)
    if not isinstance(data, list):
        return
    for r in data:
        if r.get("status") == "running" and not _pid_alive(r.get("pid")):
            r["status"] = "done"
            r["returncode"] = None
            r["finished_at"] = r.get("finished_at") or _now_iso()
        RUNS[r["id"]] = r


def _parse_opencode_line(obj, events, text_parts):
    """opencode run --format json event shape: {type, part: {...}}."""
    t = obj.get("type")
    part = obj.get("part") or {}
    usage = None
    if t == "text":
        txt = part.get("text", "")
        events.append({"type": "text", "text": txt})
        text_parts.append(txt)
    elif t == "tool_use":
        state = part.get("state") or {}
        events.append({
            "type": "tool", "tool": part.get("tool"),
            "status": state.get("status"), "title": state.get("title"),
        })
    elif t == "step_finish":
        tokens = part.get("tokens") or {}
        usage = {"total_tokens": tokens.get("total"), "cost": part.get("cost")}
    # step_start and anything else: skip, too noisy for the feed
    return usage


def _parse_claude_line(obj, events, text_parts):
    """claude -p --output-format stream-json event shape: Anthropic Messages
    API-style {type: assistant/user/result, message: {content: [...]}}."""
    t = obj.get("type")
    usage = None
    if t == "assistant":
        for block in (obj.get("message") or {}).get("content") or []:
            bt = block.get("type")
            if bt == "text":
                txt = block.get("text", "")
                events.append({"type": "text", "text": txt})
                text_parts.append(txt)
            elif bt == "tool_use":
                events.append({
                    "type": "tool", "tool": block.get("name"),
                    "status": "running", "title": json.dumps(block.get("input"))[:200],
                })
    elif t == "user":
        for block in (obj.get("message") or {}).get("content") or []:
            if block.get("type") == "tool_result":
                events.append({"type": "tool", "tool": None, "status": "completed", "title": None})
    elif t == "result":
        usage = {"total_tokens": (obj.get("usage") or {}).get("output_tokens"),
                  "cost": obj.get("total_cost_usd")}
    return usage


def _parse_log(log_path, cli, limit=300):
    """Turn a run's NDJSON event log into a compact event feed. `cli` selects
    which streaming schema to interpret it as (opencode vs. Claude Code)."""
    events = []
    text_parts = []
    usage = None
    if not log_path.exists():
        return events, "", usage
    line_parser = _parse_claude_line if cli == "claude" else _parse_opencode_line
    lines = log_path.read_text(errors="replace").splitlines()
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            events.append({"type": "raw", "text": line[:500]})
            continue
        u = line_parser(obj, events, text_parts)
        if u is not None:
            usage = u
    return events[-limit:], "\n".join(text_parts), usage


def _build_command(cli, model, run_id, message, resume_session_id=None):
    if cli == "opencode":
        bin_path = shutil.which("opencode")
        if not bin_path:
            return None, "'opencode' not found in PATH on the server process."
        cmd = [bin_path, "run", "--format", "json", "--dir", str(ROOT),
               "--title", f"gui-{run_id}", "--model", model]
        if resume_session_id:
            cmd += ["--session", resume_session_id]
        cmd.append(message)
        return cmd, None
    if cli == "claude":
        bin_path = shutil.which("claude")
        if not bin_path:
            return None, "'claude' not found in PATH on the server process."
        cmd = [bin_path, "-p", "--output-format", "stream-json", "--verbose",
               "--permission-mode", "bypassPermissions", "--model", model]
        if resume_session_id:
            cmd += ["--resume", resume_session_id]
        cmd.append(message)
        return cmd, None
    return None, f"Unknown CLI: {cli}"


def _extract_session_id(log_path, cli):
    """Pull the session id opencode/claude assigned, from whatever's been
    logged so far — needed to resume a paused run later."""
    if not log_path.exists():
        return None
    for line in log_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if cli == "claude":
            sid = obj.get("session_id")
        else:
            sid = obj.get("sessionID") or (obj.get("part") or {}).get("sessionID")
        if sid:
            return sid
    return None


def _launch(cli, model, message, meta, resume_session_id=None):
    """Spawn the subprocess under `script` (so it's genuinely line-buffered
    instead of block-buffering into the log with a multi-second lag — the
    live feed is embedded per-program in the workspace, not a separate OS
    window, so this doesn't need a real terminal emulator, just pty-like
    buffering behavior). `meta` carries the run's logical identity
    (action/arg/types/profile/etc)."""
    with RUNS_LOCK:
        for r in RUNS.values():
            _refresh(r)
        if any(r["status"] == "running" for r in RUNS.values()):
            return None, "A scan is already running — stop it or wait before starting another."

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"
    log_path = RUNS_DIR / f"{run_id}.ndjson"

    cmd, err = _build_command(cli, model, run_id, message, resume_session_id=resume_session_id)
    if err:
        return None, err

    script_bin = shutil.which("script")
    if script_bin:
        # -qfec: quiet, flush immediately, exec (no extra shell), the command string
        argv = [script_bin, "-qfec", shlex.join(cmd), "/dev/null"]
    else:
        argv = cmd  # still works, just block-buffered (a few seconds of lag)

    log_file = open(log_path, "wb")
    try:
        proc = subprocess.Popen(argv, stdout=log_file, stderr=subprocess.STDOUT, cwd=str(ROOT))
    except Exception as e:
        log_file.close()
        return None, f"Failed to start: {e}"

    run = {
        "id": run_id, "cli": cli, "message": message, "pid": proc.pid,
        "started_at": _now_iso(), "finished_at": None, "status": "running",
        "returncode": None, "log_path": str(log_path),
        "_proc": proc, "_log_file": log_file,
        **meta,
    }
    with RUNS_LOCK:
        RUNS[run_id] = run
    _save_runs_index()
    return run_id, None


def start_run(action, arg, types, profile=DEFAULT_PROFILE):
    if action not in ACTIONS:
        return None, f"Unknown action: {action}"
    if not ARG_RE.match(arg or ""):
        return None, "Invalid target/handle — only letters, numbers, dots, dashes, colons, slashes allowed."
    if types and not TYPES_RE.match(types):
        return None, "Invalid --types value."
    if profile not in PROFILES:
        return None, f"Unknown model profile: {profile}"

    cli = PROFILES[profile]["cli"]
    model = PROFILES[profile]["model"]
    message = f"/{action} {arg}"
    if types and action != "load-program-h1":
        message += f" --types {types}"

    meta = {"action": action, "arg": arg, "types": types or None, "profile": profile}
    return _launch(cli, model, message, meta)


def resume_run(run_id):
    with RUNS_LOCK:
        old = RUNS.get(run_id)
        if not old:
            return None, "Run not found."
        _refresh(old)
        if old["status"] == "running":
            return None, "That run is still active — nothing to resume."
        old_public = _public_run(old)

    session_id = _extract_session_id(Path(old_public["log_path"]), old_public["cli"])
    if not session_id:
        return None, "No session found for this run yet — it produced no output to resume from."

    profile = old_public.get("profile", DEFAULT_PROFILE)
    if profile not in PROFILES:
        return None, f"Unknown model profile: {profile}"
    cli = PROFILES[profile]["cli"]
    model = PROFILES[profile]["model"]

    meta = {
        "action": old_public.get("action"), "arg": old_public.get("arg"),
        "types": old_public.get("types"), "profile": profile,
        "resumed_from": run_id,
    }
    return _launch(cli, model, "continue where you left off", meta, resume_session_id=session_id)


def start_project(handle, name, profile=DEFAULT_PROFILE):
    """'Start' button: add to the workspace (idempotent) and immediately
    kick off /load-program-h1 for it so scope/rules get loaded."""
    entry, err = add_to_watchlist(handle, name)
    if err:
        return None, err
    run_id, err = start_run("load-program-h1", handle, "", profile=profile)
    if err:
        return None, err
    return run_id, None


def stop_run(run_id):
    with RUNS_LOCK:
        run = RUNS.get(run_id)
        if not run:
            return False, "Run not found."
        _refresh(run)
        if run["status"] != "running":
            return False, "Run is not active."
        proc = run.get("_proc")
        try:
            proc.terminate()
        except Exception as e:
            return False, f"Failed to stop: {e}"
        run["status"] = "stopped"
        run["finished_at"] = _now_iso()
        lf = run.pop("_log_file", None)
        if lf:
            try:
                lf.close()
            except Exception:
                pass
        try:
            _, _, usage = _parse_log(Path(run["log_path"]), run.get("cli", "opencode"))
            run["usage"] = usage
        except Exception:
            pass
    _save_runs_index()
    return True, None


def list_runs():
    with RUNS_LOCK:
        for r in RUNS.values():
            _refresh(r)
        items = sorted(RUNS.values(), key=lambda r: r["started_at"], reverse=True)
        return [_public_run(r) for r in items]


def hunter_progress(events, action):
    """Best-effort 'N/M hunters launched, K completed', inferred from tool_use
    events that look like hunter-subagent dispatches (tool name 'task', or a
    title mentioning one of the 17 hunter types / the word 'hunter').

    NOTE: unverified against a live /hunt run — every run used to build and
    test this GUI was /load-program-h1 (deliberately, since that's a safe
    read-only HackerOne API call; an actual /hunt sends real traffic at a
    real target's scope, which isn't something to trigger just to inspect
    event shapes). /load-program-h1 never spawns subagents, so the exact
    tool name/shape opencode or Claude use to dispatch the 17 hunters was
    never observed. Treat this as a rough indicator, not ground truth, until
    it's been checked against a real /hunt run's log."""
    if action not in ("hunt", "hunt-auth"):
        return None
    max_hunters = 17 if action == "hunt" else 7
    seen = {}
    rank = {"completed": 2, "error": 2, "running": 1, "pending": 1}
    for e in events:
        if e.get("type") != "tool":
            continue
        tool = (e.get("tool") or "").lower()
        title = (e.get("title") or "")
        matched_type = next((t for t in HUNTER_TYPES if t in title.lower()), None)
        if not (tool == "task" or "hunter" in title.lower() or matched_type):
            continue
        key = matched_type or title[:40] or tool
        status = e.get("status") or "running"
        if key not in seen or rank.get(status, 1) >= rank.get(seen[key], 0):
            seen[key] = status
    completed = sum(1 for s in seen.values() if s in ("completed", "error"))
    return {"launched": len(seen), "completed": completed, "max": max_hunters, "estimated": True}


def get_run_detail(run_id):
    with RUNS_LOCK:
        run = RUNS.get(run_id)
        if not run:
            return None
        _refresh(run)
        public = _public_run(run)
    # hunt/hunt-auth fan out to many subagents each making many tool calls —
    # use a larger window so early hunter-dispatch events aren't truncated
    # out of the (best-effort) progress count.
    limit = 1000 if public.get("action") in ("hunt", "hunt-auth") else 300
    events, text, usage = _parse_log(Path(public["log_path"]), public.get("cli", "opencode"), limit=limit)
    public["events"] = events[-300:]  # keep the feed itself light
    public["text_output"] = text
    public["usage"] = usage
    public["hunter_progress"] = hunter_progress(events, public.get("action"))
    return public


# ── HTTP layer ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep terminal quiet

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve_file(GUI_DIR / "index.html", "text/html")
        elif path == "/api/status":
            self._serve_json(build_status())
        elif path == "/api/profiles":
            self._serve_json({"profiles": [
                {"id": k, "label": v["label"]} for k, v in PROFILES.items()
            ], "default": DEFAULT_PROFILE})
        elif path == "/api/runs":
            self._serve_json({"runs": list_runs()})
        elif path == "/api/search":
            query = urlparse(self.path).query
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            from urllib.parse import unquote_plus
            q = unquote_plus(params.get("q", ""))
            results, err = search_h1_programs(q)
            if err:
                self._serve_json({"error": err}, status=400)
            else:
                self._serve_json({"results": results})
        elif path.startswith("/api/runs/"):
            run_id = path[len("/api/runs/"):]
            detail = get_run_detail(run_id)
            if detail is None:
                self.send_error(404, "Run not found")
            else:
                self._serve_json(detail)
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except Exception:
            self._serve_json({"error": "invalid JSON body"}, status=400)
            return

        if path == "/api/run":
            run_id, err = start_run(
                (body.get("action") or "").strip(),
                (body.get("arg") or "").strip(),
                (body.get("types") or "").strip(),
                profile=(body.get("profile") or DEFAULT_PROFILE).strip(),
            )
            if err:
                self._serve_json({"error": err}, status=400)
            else:
                self._serve_json({"run_id": run_id}, status=202)
        elif path.startswith("/api/runs/") and path.endswith("/stop"):
            run_id = path[len("/api/runs/"):-len("/stop")]
            ok, note = stop_run(run_id)
            if ok:
                self._serve_json({"stopped": True, "note": note})
            else:
                self._serve_json({"error": note}, status=400)
        elif path.startswith("/api/runs/") and path.endswith("/resume"):
            run_id = path[len("/api/runs/"):-len("/resume")]
            new_run_id, err = resume_run(run_id)
            if err:
                self._serve_json({"error": err}, status=400)
            else:
                self._serve_json({"run_id": new_run_id}, status=202)
        elif path == "/api/start-project":
            run_id, err = start_project(
                (body.get("handle") or "").strip(),
                (body.get("name") or "").strip(),
                profile=(body.get("profile") or DEFAULT_PROFILE).strip(),
            )
            if err:
                self._serve_json({"error": err}, status=400)
            else:
                self._serve_json({"run_id": run_id}, status=202)
        elif path == "/api/watchlist":
            # Track-only, no run — for a program already loaded outside the GUI
            # (e.g. via CLI before this dashboard existed).
            entry, err = add_to_watchlist(
                (body.get("handle") or "").strip(),
                (body.get("name") or "").strip(),
            )
            if err:
                self._serve_json({"error": err}, status=400)
            else:
                self._serve_json(entry, status=201)
        elif path.startswith("/api/watchlist/") and path.endswith("/remove"):
            handle = path[len("/api/watchlist/"):-len("/remove")]
            ok, err = remove_from_watchlist(handle)
            if ok:
                self._serve_json({"removed": True})
            else:
                self._serve_json({"error": err}, status=400)
        elif path.startswith("/api/findings/"):
            from urllib.parse import unquote
            uid = unquote(path[len("/api/findings/"):])
            entry, err = set_finding_status(uid, status=body.get("status"), notes=body.get("notes"))
            if err:
                self._serve_json({"error": err}, status=400)
            else:
                self._serve_json(entry)
        else:
            self.send_error(404, "Not found")

    def _serve_file(self, filepath, content_type):
        try:
            body = filepath.read_bytes()
        except FileNotFoundError:
            self.send_error(404, "Not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    load_runs_index()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[BountyGrimoire GUI] http://{HOST}:{PORT}  (localhost only — Ctrl+C to stop)")
    print("[BountyGrimoire GUI] scans started from here run via: opencode run --format json")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BountyGrimoire GUI] stopped")


if __name__ == "__main__":
    main()
