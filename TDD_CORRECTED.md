# TDD — BountyGrimoire
## Implementation Design for the Current Local-First System

**Version:** 1.0  
**Date:** 2026-09-03  
**Source of truth:** repository contents + runtime-generated file contracts  

---

## 1. Architecture Summary

BountyGrimoire is currently a **local process orchestration application**, not a hosted web service.

```text
┌──────────────────────────────────────────────────────────────┐
│                    Operator Machine                         │
│                                                              │
│  Claude Code / OpenCode                                      │
│          │                                                   │
│          ├── .claude/commands/                              │
│          ├── .claude/skills/                                 │
│          ├── .opencode/commands/                             │
│          └── .opencode/agents/                               │
│                  │                                           │
│                  ▼                                           │
│          scan / recon / hunters / validator                  │
│                  │                                           │
│                  ├── memory/*.json                           │
│                  ├── sessions/*.json                         │
│                  └── reports/*.md                            │
│                                                              │
│  Local Dashboard                                             │
│  gui/index.html  ◀──HTTP──▶  gui/server.py                  │
│                                │                             │
│                                ├── program search             │
│                                ├── run lifecycle              │
│                                ├── watchlist                 │
│                                ├── findings status            │
│                                └── run event parsing           │
└──────────────────────────────────────────────────────────────┘
                 │
                 ├──────── read-only HackerOne program data
                 ├──────── LLM/CLI provider selected by run
                 └──────── target traffic for explicitly authorized scopes
```

### Architectural principle

The dashboard does **not** implement the vulnerability engine itself. It starts and observes the CLI-driven hunting workflow.

---

## 2. Source Tree and Responsibilities

```text
.
├── .claude/
│   ├── commands/              # Claude command workflows
│   ├── skills/find-*/         # 17 vulnerability skills
│   └── settings.json          # Claude permission allow/deny policy
├── .opencode/
│   ├── commands/              # OpenCode command workflows
│   └── agents/                # OpenCode equivalents of hunter skills
├── gui/
│   ├── index.html             # dashboard UI, CSS and browser-side JS
│   ├── server.py              # local HTTP + run/process orchestration
│   ├── watchlist.json         # runtime watchlist
│   ├── findings_status.json   # runtime report-status map
│   └── runs/                  # runtime run index + NDJSON logs
├── memory/                    # per-program durable knowledge
├── sessions/                  # persisted hunt results
├── reports/                   # runtime report drafts
├── accounts/                  # runtime authenticated-account data
├── CLAUDE.md                  # active program policy/scope
├── generate-skill.py          # skill generation/refinement
├── install.sh                 # local environment bootstrap
└── start-bounty*.sh           # CLI launchers
```

`reports/`, `accounts/`, and `gui/runs/` are runtime artifacts and may not exist in a clean source archive.

---

## 3. Runtime Components

### 3.1 Dashboard server

`gui/server.py` uses Python standard-library HTTP primitives:

- `ThreadingHTTPServer`
- `BaseHTTPRequestHandler`
- JSON files for persistence
- `subprocess.Popen` for CLI orchestration
- `urllib.request` for HackerOne API access
- `threading.Lock` for local file/state coordination

The server listens on:

```text
127.0.0.1:8765
```

### 3.2 Dashboard client

`gui/index.html` is a single-page plain HTML/CSS/JavaScript application.

There is no React, Next.js, Vite, Tailwind build, or npm runtime dependency for the dashboard itself.

### 3.3 Scanner control plane

The dashboard starts one of these configured profiles:

| Profile ID | CLI | Model | UX implication |
|---|---|---|---|
| `claude-sonnet` | `claude` | `sonnet` | Progressive/live stream expected |
| `opencode-bigpickle` | `opencode` | `opencode/big-pickle` | Output may arrive in batches |
| `opencode-gemini` | `opencode` | `google/gemini-3.6-flash` | Output may arrive in batches |

The selected profile is metadata for the run and is surfaced in the dashboard.

---

## 4. Exact Dashboard API Contract

### GET endpoints

| Endpoint | Purpose | Source |
|---|---|---|
| `/` | Serve dashboard | `gui/index.html` |
| `/index.html` | Same as `/` | `gui/index.html` |
| `/api/status` | Current program, programs, findings, total spend | server state/files |
| `/api/profiles` | Available CLI/model profiles | `PROFILES` constant |
| `/api/runs` | Run list | in-memory + persisted run index |
| `/api/search?q=<q>` | HackerOne program search | HackerOne API |
| `/api/runs/<id>` | Run detail, parsed events, usage, progress | run log |

### POST endpoints

| Endpoint | Purpose |
|---|---|
| `/api/run` | Start `load-program-h1`, `hunt`, or `hunt-auth` |
| `/api/runs/<id>/stop` | Stop active run |
| `/api/runs/<id>/resume` | Start a continuation run |
| `/api/start-project` | Add program to watchlist + start `load-program-h1` |
| `/api/watchlist` | Track a program without starting a run |
| `/api/watchlist/<handle>/remove` | Remove tracked program |
| `/api/findings/<uid>` | Set local finding status/notes |

There are no dashboard routes for arbitrary file upload, account management, billing, or HackerOne submission.

---

## 5. Run Lifecycle

```text
created
  │
  ▼
running
  │\
  │ ├── stop ───────► stopped
  │ ├── rc=0 ───────► done
  │ └── rc!=0 ──────► error
  │
  └── server restart
          │
          └── PID liveness re-check
```

### Run identity

Each run receives a unique ID and stores metadata including command/profile/target and the path to its event log.

### Persistence

`gui/runs/_index.json` is written so completed runs survive dashboard restarts.

For a run still executing when the dashboard restarts, only the PID and persisted metadata are available; the exact exit code cannot always be recovered.

This is why the UI must describe reconstructed state as such rather than presenting it as perfect process telemetry.

---

## 6. CLI Event Parsing

The server supports two event schemas.

### OpenCode

`_parse_opencode_line()` recognizes:

- `text` → visible feed text;
- `tool_use` → tool event;
- `step_finish` → usage/cost information.

### Claude Code

`_parse_claude_line()` recognizes:

- `assistant` text/tool-use blocks;
- `user` tool-result blocks;
- `result` usage/cost.

The server stores/serves a normalized lightweight feed so the browser does not need to understand provider-specific event schemas.

---

## 7. Hunter Progress Model

`hunter_progress()` is intentionally **estimated**.

It infers hunter dispatch/completion from tool events containing:

- tool name `task`;
- “hunter” in title;
- one of the known hunter type names.

Therefore:

```text
Displayed progress ≠ authoritative orchestration state
```

The API must expose the `estimated=true` marker and the UI should display an “estimated” label.

A required future test must feed real `/hunt` event logs from both supported CLIs into the parser and verify that the 17-hunter count is correct.

---

## 8. Persistence Contracts

### 8.1 Active program

`CLAUDE.md` is the current operational context.

The server extracts:

- program name;
- HackerOne handle;
- in-scope targets;
- scope notes.

### 8.2 Program memory

`memory/<program>.json` is read as a JSON document. The dashboard currently derives counts from:

- `confirmed_patterns`;
- `false_positives`;
- `discovered_endpoints`.

### 8.3 Session data

The dashboard currently consumes a schema containing fields such as:

```json
{
  "target": "...",
  "program": "...",
  "date": "...",
  "hunters_launched": 17,
  "endpoints_discovered": 13,
  "summary": "...",
  "validated_findings": [],
  "discarded": [],
  "bounty_eligible": "...",
  "suggested_action": "..."
}
```

### 8.4 Finding IDs

Dashboard finding identity is currently derived as:

```text
<session filename>:<finding_id>
```

This is adequate for local bookkeeping but is not a globally portable identifier.

### 8.5 Two session file shapes in one directory — RESOLVED

`sessions/` holds two unrelated features, not one inconsistent schema:

1. **Hunt sessions** — written by `.claude/commands/hunt.md` Step 10 as
   `hunt-<target>-<date>.json`, using `target`/`date`/`hunters_launched`/
   `endpoints_discovered`/`summary`/`validated_findings[]`/`discarded[]`/
   `bounty_eligible`/`suggested_action`. This is the schema `gui/server.py`'s
   `read_sessions()` consumes, and matches the real hunt output on disk.
2. **Manual audit sessions** — a separate, dashboard-independent checkpoint
   feature via `.claude/commands/session-save.md`/`session-load.md`/
   `session-list.md`, using `name`/`saved_at`/`scope`/`tested_urls[]`/
   `findings[]`/`notes`, written to `sessions/<name>.json`.

Both are legitimate and both are preserved as-is — no schema merge. The
actual bug was that `read_sessions()` globbed *every* `sessions/*.json` file
indiscriminately, so a manual audit-session save would be misread as a hunt
session (producing a phantom, null-target/zero-finding card in the
dashboard). Fixed by scoping the glob to `hunt-*.json` only
(`gui/server.py:read_sessions()`), verified against a synthetic manual-session
file alongside the two real hunt-session files on disk.

If a stronger machine-checkable discriminator is wanted later, add a `kind`
field (`"hunt"` / `"audit"`) to both writers instead of relying on the
filename convention — not required for correctness today.

---

## 9. Scope and Safety Architecture

### 9.1 Current control layers

1. **Program context** in `CLAUDE.md`.
2. **Command instructions** requiring scope verification.
3. **Hunter instructions** carrying qualifying/non-qualifying rules and rate controls.
4. **Claude permission deny rules** for dangerous destructive actions and HackerOne report write operations.
5. **Local-only binding** of the dashboard server.
6. **Manual human submission** requirement.

### 9.2 Important limitation

This is not a hard network enforcement layer.

If an execution context bypasses the command instructions or runs arbitrary shell commands, the application does not currently implement a dedicated egress firewall that guarantees only in-scope hosts can receive traffic.

A future hosted design must add process/container/network isolation rather than relying only on prompts.

### 9.3 HackerOne submission safety

The project explicitly denies HackerOne write/submission tools in `.claude/settings.json` and the command documents.

The report flow ends at a local Markdown artifact.

---

## 10. Authenticated Testing Data

`setup-account.md` describes a two-account attacker/victim flow and stores credentials, IDs, tokens, and cookie-file locations.

Because these are secrets, the implementation must treat `accounts/` and referenced cookie files as sensitive runtime artifacts.

Required hardening:

- Add a `.gitignore` rule covering `accounts/`.
- Never render passwords/tokens into dashboard output.
- Prefer OS secret storage for long-lived secrets.
- Delete temporary cookies when a session is complete unless retention is explicitly required.
- Add redaction before logging command output containing auth material.

---

## 11. Security of the Dashboard API

### Current state

The server is local-only and unauthenticated.

This is acceptable only while all access is restricted to the trusted local operator environment.

### Required invariants

- Keep `HOST = 127.0.0.1`.
- Validate action/argument/profile inputs server-side.
- Do not interpolate run arguments into a shell command string.
- Keep process execution in an argument-list form (`Popen([...])`).
- Avoid exposing raw credentials in `/api/status` or `/api/runs/<id>`.

### Before any remote exposure

The system would require, at minimum:

- authentication;
- authorization;
- CSRF protection where browser cookies are used;
- request rate limiting;
- audit logging;
- tenant isolation;
- network egress control;
- secret isolation;
- secure session handling.

---

## 12. Installation / Launch Architecture

`install.sh` currently:

1. checks Node, Python, curl, and git;
2. checks for Claude Code and/or OpenCode;
3. creates `.venv`;
4. installs `anthropic`, `openai`, and `datasets`;
5. creates basic runtime directories;
6. optionally runs skill generation when credentials are present.

Launchers then execute either Claude Code or OpenCode from the project directory.

### Documentation correction

The product does not require Node for the dashboard runtime itself. The installer checks Node because the supported CLI tooling may rely on it.

The README should therefore distinguish:

- **dashboard runtime dependency:** Python 3;
- **LLM/CLI runtime dependency:** Claude Code and/or OpenCode;
- **skill-generator Python packages:** optional for skill generation.

---

## 13. Testing Strategy

### 13.1 Current verified baseline

Static verification performed for the supplied source archive:

- `python3 -m py_compile gui/server.py generate-skill.py` passes.
- Claude/OpenCode command and skill files are present.
- The OpenCode equivalents add expected OpenCode-specific frontmatter such as `mode: subagent`.

A first slice of automated tests now exists at `tests/test_server.py`
(stdlib `unittest`, zero new dependency — run via
`python3 -m unittest discover -s tests -v`): scope-table parsing, `_load_json`
failure handling, watchlist add/remove/idempotency, and the hunt-session vs.
manual-audit-session discrimination fix from §8.5. All file-touching tests
redirect `WATCHLIST_PATH`/`ROOT` to a temp directory so runs never mutate
real workspace data. 14/14 passing as of 2026-09-04. This is a starting
slice, not full coverage — the remaining items below are still open.

### 13.2 Required automated tests

Remaining coverage to add beyond the `tests/test_server.py` starting slice above.

#### Server unit tests

- JSON loading failures.
- Scope-table parsing.
- watchlist add/remove/idempotency.
- run state transitions.
- run persistence/reload.
- input validation.
- finding status transitions.
- cost aggregation.
- report filename matching.

#### API integration tests

- every GET endpoint;
- every POST endpoint;
- malformed JSON;
- invalid action/profile;
- nonexistent run;
- invalid finding status;
- missing runtime directories.

#### Event parser tests

Use fixture logs for Claude and OpenCode.

Verify:

- text extraction;
- tool events;
- result/usage parsing;
- malformed lines are skipped safely;
- hunter progress estimation.

#### Workflow contract tests

- load-program → CLAUDE.md;
- hunt command output → session schema;
- session schema → dashboard rendering;
- report output → report-status detection;
- skill source → OpenCode mirror.

#### Safety tests

- out-of-scope target rejected;
- banned HackerOne write actions are not invoked;
- dangerous filesystem commands remain blocked by the configured policy layer;
- secrets do not appear in dashboard JSON.

---

## 14. Operational Limits

The current system is optimized for one trusted operator on one machine.

Potential ceilings include:

- CPU/RAM contention from parallel hunters;
- large event logs;
- indefinite run-index growth;
- large memory files;
- target-side rate limits;
- LLM context/token costs;
- CLI-specific output buffering.

A local retention policy should be introduced before the volume of runs becomes material.

---

## 15. Disaster Recovery

The current tool has no centralized backup system.

Minimum local recovery recommendation:

- keep the repository under version control;
- back up `memory/`, `sessions/`, and manually retained `reports/` separately;
- exclude secrets/cookies from general repository backups unless encrypted;
- preserve `CLAUDE.md` for the active program context only when it contains no secret material.

The run log directory should be considered disposable telemetry, not the sole source of validated findings.

---

## 16. Future Hosted Architecture — Separate Design

Do not implement this by simply exposing port `8765` to the internet.

A future hosted system should use:

```text
Browser
  ↓
Authenticated Web App
  ↓
Versioned API
  ↓
Tenant + Authorization Layer
  ↓
Durable Job Queue
  ↓
Isolated Scan Worker / Sandbox
  ↓
Controlled Network Egress
  ↓
Target

Worker results
  ↓
Durable Database / Object Storage
  ↓
Report + Findings API
  ↓
Browser
```

Possible technology choices can be made later. The current repository does not justify a claim that PostgreSQL, Supabase, Stripe, Redis, Next.js, Vercel, or Railway already form part of the implemented system.

---

## 17. Technical Debt Backlog — Ordered

### P0

1. ~~Unify session schemas.~~ **Done** — see §8.5; `read_sessions()` now scopes to `hunt-*.json` so the separate manual audit-session feature can't pollute hunt history.
2. Add automated tests for `gui/server.py` and event parsers. **Started** — `tests/test_server.py` covers scope parsing, `_load_json`, watchlist, and session discrimination (§13.1); event-parser, run-lifecycle, and API-integration coverage still open.
3. Add secret exclusion/redaction for `accounts/`, cookies, and logs.
4. Add explicit `schema_version` to persisted JSON artifacts.
5. Test real `/hunt` progress parsing for both CLI providers.

### P1

6. Add run-log retention/cleanup.
7. Add stronger run-to-program attribution than “current CLAUDE.md program”.
8. Improve finding/report identity mapping beyond filename heuristics.
9. Add structured error logging with secret redaction.
10. Add CLI/version compatibility checks at startup.

### P2

11. Add reproducible fixtures for program loading.
12. Add a local export/import bundle for sessions and memory.
13. Add an explicit “safe mode” UI that hides unrestricted execution paths unless enabled.

---

## 18. Release Gate

Do not describe a release as production-ready until:

- automated tests exist and pass;
- session schemas are unified;
- credentials are protected;
- dashboard API behavior is covered by tests;
- run-state recovery is documented and tested;
- real `/hunt` event parsing has been verified;
- scope and submission safety controls are regression-tested.

---

## 19. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-03 | Rewritten against actual source tree, APIs, persistence formats, CLI orchestration, and safety model; removed fictional hosted-stack claims from the current implementation. |
