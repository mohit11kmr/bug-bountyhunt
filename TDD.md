# TDD: AI Security Scanner SaaS

**Product Name:** SecScan AI
**Version:** 2.0 — rewritten to match the actual scanning engine (BountyGrimoire)
**Date:** September 3, 2026
**Author:** Mohit Kumar
**Status:** Draft

> **Note on this revision:** v1.0 of this TDD specified a generic SaaS stack
> (Next.js + Supabase + Stripe + Nuclei + OpenAI, deployed on Vercel/Railway)
> that didn't exist anywhere in this codebase. The scanning engine SecScan AI
> is meant to productize is **BountyGrimoire**, a working local tool already
> in this repo (`gui/server.py`, `gui/index.html`, `.claude/skills/`,
> `.opencode/`). This revision replaces the invented stack with that real
> one. PRD.md's business content (personas, pricing, GTM, success metrics)
> is unchanged — only the technical design below is new.

---

## 1. Technical Overview

### 1.1 What Actually Exists Today

BountyGrimoire, as it stands in this repo, is a **local, single-user CLI +
GUI tool** — not a hosted multi-tenant SaaS. Before proposing SaaS
infrastructure on top of it, this section describes what's real:

- **Scan engine**: 17 specialized vulnerability-hunting "skills"
  (`.claude/skills/find-*/`, mirrored as opencode subagents in
  `.opencode/agents/`) covering IDOR, SSRF, SQLi, XSS, Auth, RCE, XXE, SSTI,
  Secrets, OTP, PII, BizLogic, Callback, Enumerable, Insecure, Referer,
  Checksum. These run as Claude Code / opencode subagents, not a
  traditional scanner binary — there's no Nuclei/HTTPX/Subfinder dependency
  anywhere in this codebase.
- **Orchestration**: `.claude/commands/hunt.md` (and its `hunt-auth`
  variant) launches all 17 in parallel via the Task/subagent tool, then a
  single validator subagent cross-checks findings against program scope
  before anything is reported.
- **Program intake**: `.claude/commands/load-program-h1.md` pulls a
  HackerOne program's real scope/policy via the HackerOne API/MCP and
  writes it into `CLAUDE.md`, which every hunt/report command reads as its
  source of truth for scope, proxy settings, and program rules.
- **Local dashboard**: `gui/server.py` (Python stdlib `http.server`, zero
  third-party dependencies) + `gui/index.html` (plain HTML/CSS/JS, no
  framework) — binds to `127.0.0.1` only. It can search HackerOne for
  bounty-paying open programs, track them in a workspace, start a scan
  (embedded live output per program card, not a separate window), pause
  and resume a run via the underlying CLI's own session-continuation
  (`opencode run --session` / `claude --resume`), and track findings,
  in-scope targets, and AI token/cost spend.
- **Report generation**: `.claude/commands/report.md` writes a local
  Markdown file under `reports/`. There is no PDF export and no automated
  submission — every report is reviewed and submitted by the human via the
  HackerOne web UI. This is enforced, not just documented: HackerOne's
  mutating MCP tools (`submit_report`, `create_report_intent`, etc.) are
  explicitly denied in `.claude/settings.json`, and every hunting command
  carries the same instruction. See §5.3.

None of this needs a database server, a hosted frontend, or a payment
processor to work — it already runs entirely on the operator's own machine.

### 1.2 System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                    OPERATOR'S OWN MACHINE (localhost only)             │
│                                                                          │
│  ┌────────────────────────────┐      ┌────────────────────────────┐   │
│  │   gui/index.html            │◀────▶│   gui/server.py              │   │
│  │   (plain HTML/CSS/JS,       │ HTTP │   (Python stdlib             │   │
│  │   no build step, no         │ 127. │   http.server, no deps)      │   │
│  │   framework)                │ 0.0.1│                              │   │
│  └────────────────────────────┘ :8765 └──────────────┬───────────────┘   │
│                                                        │                  │
│                             spawns (subprocess.Popen)  │                  │
│                                                        ▼                  │
│                          ┌──────────────────────────────────────────┐   │
│                          │  opencode run / claude -p                 │   │
│                          │  (--format json / --output-format         │   │
│                          │   stream-json — NDJSON piped to a          │   │
│                          │   per-run log file gui/runs/<id>.ndjson)  │   │
│                          └────────────────┬─────────────────────────┘   │
│                                           │ reads commands from           │
│                                           ▼                               │
│         .claude/commands/*.md  ◀── mirrored ──▶  .opencode/commands/*.md │
│         .claude/skills/find-*/ ◀── mirrored ──▶  .opencode/agents/*.md   │
│         (17 hunter skills, /hunt, /hunt-auth, /load-program-h1,          │
│          /report, /session-*, /setup-account, /update-skills)            │
│                                           │                               │
│                                           ▼                               │
│              Local file storage (see §2) — memory/, sessions/,           │
│              reports/, gui/watchlist.json, gui/findings_status.json,     │
│              gui/runs/_index.json, CLAUDE.md                             │
└───────────────────────────────────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
        ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
        │     HackerOne        │ │  Claude API /         │ │  Target's own       │
        │  (program search,    │ │  Google Gemini /      │ │  in-scope           │
        │  scope, policy —     │ │  opencode's free       │ │  infrastructure     │
        │  read-only MCP       │ │  tier — whichever       │ │  (curl/recon        │
        │  tools + REST API)   │ │  model profile is        │ │  traffic during     │
        │                       │ │  selected per run)      │ │  a hunt)            │
        └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

There is no Vercel, no Supabase, no Stripe, no Railway, and no Redis in
the current system — every one of those was part of the invented v1.0
stack and has been removed from this design. If/when this becomes a
hosted multi-tenant product, §11 (Roadmap) covers what would actually need
to be added, and why that's a separate, later phase rather than a
rewrite-from-scratch of what's already working.

### 1.3 Technology Stack (as implemented)

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Dashboard backend** | Python 3 stdlib (`http.server`) | `gui/server.py` — zero third-party dependencies, deliberately |
| **Dashboard frontend** | Plain HTML/CSS/JS | `gui/index.html` — no React/Next.js/build step |
| **Scan orchestration** | Claude Code CLI, opencode CLI | Selectable per run (`PROFILES` in `gui/server.py`): Claude Sonnet (streams live), opencode `big-pickle` (free, batches output), opencode + Gemini |
| **Vulnerability logic** | 17 markdown "skill" files | `.claude/skills/find-*/SKILL.md`, generated/refined from real disclosed HackerOne reports via `generate-skill.py` |
| **Program data source** | HackerOne API + `hackerone-mcp` | Read-only program search/scope/policy lookups; write/submit tools explicitly blocked (§5.3) |
| **Data persistence** | Local JSON files | No database server — see §2 |
| **Process transparency** | `script` (util-linux) | Wraps the CLI subprocess so output is line-buffered instead of block-buffered, and so the exact same output stream can be tailed for both the live UI feed and post-hoc parsing |
| **Auth** | None | Single local user, dashboard bound to `127.0.0.1` only |
| **Billing** | None (not yet built) | See §11 for what a real billing layer would need |

### 1.4 Implementation Structure (SecScan AI SaaS)

When this becomes a hosted multi-tenant product (§11.3), the implementation
follows a **backend/frontend separation** — the scanning engine (BountyGrimoire)
lives in `backend/scanner/`, while the SaaS infrastructure wraps it:

```
SecScanAI/
├── backend/                        # API + Scanner Engine
│   ├── api/                        # REST/GraphQL endpoints
│   │   ├── auth/                   # Login, signup, OAuth (Supabase Auth)
│   │   ├── billing/                # Stripe webhooks, subscriptions
│   │   ├── scans/                  # Start/stop/resume scans
│   │   └── reports/                # Generate/download reports
│   │
│   ├── scanner/                    # BountyGrimoire engine (copied from this repo)
│   │   ├── skills/                 # 17 hunters (.claude/skills/find-*/)
│   │   │   ├── find-idor/
│   │   │   ├── find-xss/
│   │   │   ├── find-sqli/
│   │   │   └── ... (17 total)
│   │   ├── agents/                 # opencode agents (.opencode/agents/)
│   │   ├── orchestration/          # hunt.md, hunt-auth.md logic
│   │   └── generator/              # generate-skill.py
│   │
│   ├── db/                         # Database schema + migrations
│   │   ├── schema.prisma           # PostgreSQL via Prisma
│   │   └── migrations/
│   │
│   ├── config/                     # Environment, secrets, Docker
│   │   ├── .env.example
│   │   └── docker-compose.yml
│   │
│   └── tests/                      # Backend tests (pytest/jest)
│
├── frontend/                       # Dashboard UI
│   ├── src/
│   │   ├── app/                    # Next.js App Router
│   │   ├── components/             # UI components (shadcn/ui)
│   │   ├── lib/                    # API client, utils
│   │   └── styles/                 # CSS/Tailwind
│   ├── public/                     # Static assets
│   └── package.json
│
├── docs/                           # Documentation
│   ├── PRD.md                      # Business requirements
│   ├── TDD.md                      # This file
│   └── api/                        # API documentation
│
├── scripts/                        # Deployment, CI/CD
│   ├── deploy.sh
│   └── setup.sh
│
└── README.md
```

**Why this structure:**

| Separation | Benefit |
|------------|---------|
| `backend/scanner/` isolated | Scanning engine (BountyGrimoire) can be updated independently |
| `backend/api/` separate | Auth/billing logic doesn't couple with scanner internals |
| `frontend/` standalone | UI can be developed/deployed independently |
| `docs/` centralized | PRD/TDD stay with the implementation |

**Data flow:**

```
User → Frontend (Next.js dashboard)
         ↓
       Backend API (auth verification, billing check)
         ↓
       Scanner Engine (17 hunters in parallel)
         ↓
       Results → Database (PostgreSQL)
         ↓
       Frontend (reports, findings, dashboard)
```

**How this relates to current BountyGrimoire:**

| Current (BountyGrimoire/) | Future (SecScanAI/) |
|---------------------------|---------------------|
| `gui/server.py` (Python stdlib) | `backend/api/` (Node.js/Python) |
| `gui/index.html` (plain HTML) | `frontend/` (Next.js) |
| `.claude/skills/find-*/` | `backend/scanner/skills/` (copied) |
| `.opencode/agents/` | `backend/scanner/agents/` (copied) |
| Local JSON files | PostgreSQL database |
| No auth (127.0.0.1 only) | Supabase Auth (per-user) |
| No billing | Stripe (subscriptions) |

---

## 2. Data Storage Design

There is no PostgreSQL/Supabase instance. State lives in plain JSON/Markdown
files under the project directory, each owned by a specific part of the
system. This is intentional for a local single-user tool — it's what makes
`gui/server.py` a zero-dependency script instead of something that needs a
provisioned database before it can run at all.

### 2.1 Storage Map

```
BountyGrimoire/
├── CLAUDE.md                      # Current program's scope/policy/proxy — the
│                                   #   single source of truth every hunt/report
│                                   #   command reads before touching a target
├── memory/
│   └── <program-slug>.json        # Long-lived, cross-session knowledge per
│                                   #   program: confirmed_patterns, false_positives,
│                                   #   discovered_endpoints, technology_stack
├── sessions/
│   └── hunt-<target>-<date>.json  # One file per completed /hunt run: target,
│                                   #   hunters_launched, validated_findings[]
│                                   #   (full records: type, severity, endpoint,
│                                   #   description, confidence), discarded[],
│                                   #   bounty_eligible, suggested_action
├── reports/
│   └── report-<vuln>-<target>-<date>.md   # Human-reviewed, human-submitted
├── gui/
│   ├── watchlist.json             # Programs tracked in the dashboard's
│                                   #   Workspace: [{handle, name, added_at}]
│   ├── findings_status.json       # Per-finding report status the operator
│                                   #   sets manually: {"<session_file>:<finding_id>":
│                                   #   {status: not_reported|drafted|submitted, notes}}
│   └── runs/
│       ├── _index.json            # Every run ever started, across restarts:
│                                   #   id, cli, action, arg, profile, pid,
│                                   #   started_at/finished_at, status, usage
│                                   #   (tokens/cost) — the AI-spend ledger (§10)
│                                   #   is just a sum over this file
│       └── <run-id>.ndjson        # Raw NDJSON event stream for one run —
│                                   #   opencode's `--format json` or Claude's
│                                   #   `--output-format stream-json` shape
```

### 2.2 Why files instead of a database

- **No provisioning step.** `python3 gui/server.py` works on a fresh clone
  with nothing else running. A Supabase/Postgres dependency would mean the
  README's "3 commands to get started" claim (§7.1 of PRD) is false for
  anyone who hasn't also set up a database.
- **Single user, low write volume.** One operator, a handful of concurrent
  runs at most (the dashboard already enforces one active run at a time —
  `_launch()` in `gui/server.py`), findings numbering in the dozens per
  program, not millions of rows. A DB's concurrency guarantees aren't
  buying anything here.
- **Durability already covered.** `gui/runs/_index.json` is rewritten on
  every state transition (`_save_runs_index()`), so a run's status/spend
  survives a dashboard restart — verified directly: started a run, killed
  the server mid-scan, restarted it, and the run correctly reattached by
  PID and later resolved via the log file, with token/cost totals intact
  across the restart.
- **Git-ignored appropriately.** `.gitignore` already excludes
  `gui/runs/`, `gui/watchlist.json`, `gui/findings_status.json`,
  `memory/`, `sessions/`, `reports/`, and `CLAUDE.md` — this data is
  operator-specific and often covers an active, undisclosed engagement; it
  should never end up in version control regardless of storage format.

### 2.3 If this becomes multi-tenant (see §11)

The file-per-program-per-run model maps fairly directly onto tables if a
hosted, multi-user version is ever built: `programs` (≈ merged
`memory/<slug>.json` + `watchlist.json` entries, scoped by `user_id`),
`runs` (≈ `gui/runs/_index.json` rows, scoped by `user_id`), `findings`
(≈ flattened `sessions/*.json` records + `findings_status.json`). That
migration is a §11 roadmap item, not something to design speculatively now
— the current schema-in-JSON already reflects the real shape of the data,
which is the useful part to carry forward.

---

## 3. API Design

`gui/server.py` exposes a small REST-ish API over its own stdlib
`http.server`. No auth layer — every route trusts the local caller because
the socket is bound to `127.0.0.1` only.

### 3.1 Status & Discovery

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Current program (parsed from `CLAUDE.md`, including its in-scope target checklist with hunted/not-hunted flags), every tracked program with its stats/spend, flattened findings across all programs, total AI spend |
| GET | `/api/profiles` | Available model profiles (Claude Sonnet, opencode big-pickle, opencode+Gemini) and the default |
| GET | `/api/search?q=<text>` | Searches real HackerOne programs via the authenticated API, filtered to `offers_bounties=true AND submission_state=open` (a floor, not a payout ranking — see the docstring on `search_h1_programs()`) |

### 3.2 Workspace

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/watchlist` | Add a program to the workspace without starting anything (idempotent) |
| POST | `/api/watchlist/<handle>/remove` | Untrack a program (its past session/memory data isn't deleted, only stops being surfaced as "tracked") |

### 3.3 Runs (operate)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/run` | Start `/load-program-h1`, `/hunt`, or `/hunt-auth` with a chosen model profile. Rejected with a clear error if a run is already active — one at a time, by design |
| GET | `/api/runs` | List every run this dashboard has ever tracked (newest first), including ones reattached after a restart |
| GET | `/api/runs/<id>` | Full detail for one run: live-parsed event feed, token/cost usage, and a best-effort "N/17 hunters launched, M completed" estimate for hunt/hunt-auth runs (explicitly marked `estimated: true` — see the caveat in `hunter_progress()`) |
| POST | `/api/runs/<id>/stop` | Terminates the run's subprocess |
| POST | `/api/runs/<id>/resume` | Extracts the CLI's own session ID from the run's log and starts a *new* run continuing that session (`opencode run --session <id>` / `claude --resume <id>`) — this is genuine conversation continuation, not a restart from scratch; verified by resuming a finished run and watching it correctly say "let me check where we left off" |

### 3.4 Findings

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/findings/<uid>` | Set a finding's manual report status (`not_reported` / `drafted` / `submitted`) and notes. `drafted` is also auto-detected by matching a finding's vuln type + target against filenames in `reports/`; `submitted` is always set by the human, since there's no automated submission to detect it from |

### 3.5 What's deliberately not here

There's no `/api/scans` REST resource with a `results JSONB` blob the way
v1.0 of this doc specified — a "scan" in this system isn't a single
opaque unit of work, it's a `/hunt` **run** (tracked under §3.3) whose
output lands in a `sessions/*.json` file (§2.1) that `/api/status` already
surfaces per-program. Modeling it as a generic `scans` CRUD resource would
be designing for a hypothetical multi-tenant version before the
single-user version's real shape has settled.

---

## 4. Frontend Structure

### 4.1 Why no component framework

`gui/index.html` is one file: inline `<style>`, a handful of top-level
`<div>` sections, and one `<script>` block using `fetch`/template strings
directly against the DOM. No React, no build step, no `npm install` before
the dashboard runs. For a single-page local tool polled every few seconds,
a component framework's main benefits (routing, complex state
management across many views) don't apply — there's one view.

### 4.2 Page Sections (as built)

```
gui/index.html
├── header                          # current program badge, total AI-spend badge
├── model-profile selector          # applies to the next run started from any card
├── "Find new bounty projects"      # search box -> real HackerOne results,
│                                   #   "+ Add" only tracks, never starts a run
├── Findings panel                  # flattened across all tracked programs,
│                                   #   per-row report-status <select>
└── Workspace                       # one .program-card per tracked program:
    ├── stats row                   #   confirmed patterns, false positives,
    │                                #   discovered endpoints, sessions, spend
    ├── sessions table               #   past /hunt runs for this program
    ├── in-scope target checklist    #   only for the currently-loaded program
    │                                #   (CLAUDE.md only holds one program's
    │                                #   scope at a time) — ✓/○ hunted flag
    ├── embedded run feed            #   ONLY while/after a run exists for this
    │   (run-embed)                  #   card — live text/tool-call events,
    │                                #   estimated hunter-progress bar, Pause/
    │                                #   Resume — rendered inside the card
    │                                #   itself, not a separate panel or a
    │                                #   real OS terminal window
    └── start row                    #   action select (load program / hunt /
                                      #   hunt-auth) + target (a <select> of
                                      #   real scope targets when this is the
                                      #   current program, else free text) +
                                      #   Start button
```

The embedded-feed-per-card layout (rather than a top-level "current run"
panel, and rather than opening a real terminal emulator window) was a
deliberate revision after two things were tried and rejected: a separate
top-level run panel didn't make clear *which* company's work was showing,
and spawning an actual OS terminal window (`xfce4-terminal -x script ...`)
worked but opened somewhere disconnected from the workspace card it
belonged to. Embedding the feed inside the specific program's own card
satisfies both "see the real work happening" and "it's clearly this
company's scan," without a second surface to look at.

### 4.3 Live feed mechanics

`gui/server.py` parses two different NDJSON event shapes depending on
which CLI produced them (`_parse_opencode_line` / `_parse_claude_line`),
normalizing both into `{type: "text"|"tool", ...}` events the frontend
renders identically. Measured directly (see §9.3): Claude's
`--output-format stream-json` flushes progressively — visible within ~3
seconds and growing steadily — while opencode's `--format json` batches
internally and the log stays at 0 bytes until the run is nearly done,
regardless of how it's piped (tried block streams, `script`-allocated
ptys — the batching is inside opencode's own output handling, not fixable
from the piping side). This is *why* Claude Sonnet is the dashboard's
default model profile, not an arbitrary choice.

---

## 5. Security Architecture

### 5.1 Threat Model

This is a single-operator local tool that (a) holds no third-party user
data, (b) can execute arbitrary shell commands via the underlying CLI's
Bash tool, and (c) can send real network traffic at whatever target is
in scope. The security design follows from that: the main risks are
**accidental scope violations** and **accidental submission of a
finding**, not multi-tenant data isolation (there's only one tenant).

### 5.2 Local-Only Network Exposure

`gui/server.py` binds `ThreadingHTTPServer` to `127.0.0.1` explicitly
(`HOST = "127.0.0.1"`) — verified with `ss -tlnp`, which shows the listener
bound to `127.0.0.1:8765` only, not `0.0.0.0`. The dashboard can trigger
real scans and reads findings that may be covered by an active,
undisclosed bug bounty engagement; it must never be reachable from another
machine.

### 5.3 Submission Safety (enforced, not just documented)

Every hunting command carries an explicit instruction never to call a
HackerOne MCP tool that creates, modifies, or submits a report
(`submit_report`, `create_report_intent`, `submit_report_intent`,
`update_report_intent`, or any other mutating `mcp__hackerone__*` /
`hackerone-mcp` action) — see the "⛔ Submission Safety" block baked into
`CLAUDE.md`, `.claude/commands/load-program-h1.md` (so every future-loaded
program's `CLAUDE.md` carries it automatically), `report.md`, `hunt.md`,
and `hunt-auth.md`.

That's a prompt-level instruction, which is why it's backed by a second,
independent layer: `.claude/settings.json`'s `permissions.deny` list
blocks those specific tool names outright for Claude Code sessions.
Verified directly in-session — adding the deny entries immediately revoked
access to those tools mid-conversation. Read-only HackerOne tools
(`get_program`, `get_program_scope`, `list_programs`, `search_hacktivity`,
etc.) stay allowed; they're useful for research and can't submit anything.
This second layer currently only covers Claude Code — opencode's
equivalent permission-deny syntax hasn't been verified, so for opencode
runs the prompt-level instruction is the only guard. That gap is called
out explicitly here rather than papered over.

### 5.4 Scope Enforcement

`CLAUDE.md` (regenerated per-program by `/load-program-h1` from the real
HackerOne API response) is the only source of truth for what's in scope,
what proxy/user-agent to use, and program-specific rules (e.g. "staging
only, never production" per-target notes). Every hunting command's first
instruction is to verify the target is in scope before any request — this
is a prompt-level control, same caveat as §5.3: it depends on the model
following the instruction, there's no separate technical enforcement
layer stopping an out-of-scope `curl` call today. A future hardening step
(§11) would be a request-level allowlist proxy rather than relying on the
agent to self-check.

### 5.5 Credentials

`.env` holds `H1_USER`/`H1_TOKEN` (or `H1_USERNAME`/`H1_API_TOKEN` — both
naming conventions are accepted defensively, since they've historically
diverged across this project and the `hackerone-mcp` server's own expected
names) and is git-ignored along with `.env.bak` and any `*.env.bak`
variant. `gui/server.py` reads `.env` directly off disk for the HackerOne
search feature — it never accepts credentials over HTTP, and the dashboard
itself has no login, so there's no session/token to leak.

### 5.6 Input Validation on the Dashboard's Own API

Handle/target/action/profile inputs to `/api/run`, `/api/watchlist`, etc.
are validated against fixed allowlists and regexes (`ARG_RE`, `HANDLE_RE`,
`TYPES_RE`, `ACTIONS`, `PROFILES`) before being placed into a
`subprocess.Popen` argv list (never a shell string) — verified directly:
posting a target containing `; rm -rf /` is rejected by `ARG_RE` before
it ever reaches a shell.

---

## 6. Running It (there is no "deployment")

### 6.1 It runs on the operator's own machine

```bash
python3 gui/server.py
# -> http://127.0.0.1:8765
```

No Vercel project, no Railway service, no CI/CD pipeline — this is a
script the operator runs when they want the dashboard, same as any of the
project's other launcher scripts (`start-bounty.sh`, `start-bounty-gemini.sh`,
`start-bounty-bigpickle.sh`), which pick which CLI/model to run the
underlying hunt commands with directly, outside the dashboard.

### 6.2 Requirements

| Requirement | Why |
|-------------|-----|
| Python 3 | Runs `gui/server.py` — stdlib only, no `pip install` needed for the dashboard itself |
| `opencode` and/or `claude` CLI on `PATH` | Whichever model profiles are selected must have their CLI installed; `install.sh` now checks for at least one rather than hard-requiring `claude` |
| `script` (util-linux) | Optional but recommended — gives line-buffered output instead of the block-buffered default; the dashboard degrades gracefully (a few seconds of extra lag) if it's missing |
| `H1_USER`/`H1_TOKEN` in `.env` | Only needed for the dashboard's program search — HackerOne's list-programs endpoint rejects unauthenticated requests even for public programs (verified: a plain unauthenticated request returns 401) |

### 6.3 If this becomes hosted (see §11)

Running this for a single operator on their own machine and running it as
a multi-tenant hosted service are different problems — the latter needs
per-user credential storage, a request queue instead of "one run at a
time," and a real auth layer, none of which this section pretends to
solve. §11 scopes that as a distinct, later phase.

---

## 7. Testing Strategy

### 7.1 What's actually been verified

There's no automated test suite in this repo yet (no `vitest`/`pytest`
config) — verification so far has been direct, manual, and adversarial
rather than a written test file, and is worth recording precisely because
it's what's actually been checked rather than what's planned:

| What | How verified |
|------|---------------|
| Search filters correctly | Real HackerOne API calls for "shopify", "gitlab" — confirmed `offers_bounties`/`submission_state` filtering against live data |
| Run start/stop/resume | Started real `/load-program-h1` runs via both `opencode` and `claude` profiles, captured live event streams, paused mid-run, resumed and confirmed genuine session continuation (the resumed agent referenced prior context unprompted) |
| Status survives a restart | Started a run, killed and restarted `gui/server.py` mid-run, confirmed the run correctly reattached via PID and later resolved via log content; repeated across a full server restart *after* completion and confirmed `status: complete` and token/cost totals persisted |
| Input validation | Posted a target string containing shell metacharacters (`; rm -rf /`) to `/api/run`, confirmed `400` rejection before it reached a subprocess |
| MCP submission block works | Added the deny entries to `.claude/settings.json`, confirmed (via the tool list available mid-session) that the blocked tool names became immediately unavailable |
| Rendering, not just the API | Used Playwright (`playwright-cli`) to load the actual page, confirmed the Findings table, scope checklist, spend badge, and embedded per-card live feed all render with real data — not inferred from `curl` output alone |
| Streaming latency, Claude vs opencode | Timed byte-arrival at the log file for identical prompts under both CLIs — opencode: 0 bytes for the full run then one lump; Claude: progressive growth from ~3s in |

### 7.2 What a real test suite would cover (not yet built)

- `_parse_opencode_line` / `_parse_claude_line` against fixture NDJSON —
  regression protection for when either CLI's event schema changes
- `_derive_status` / `_last_run_for_handle` state-machine transitions
  (not_started → processing → complete) under concurrent/racing `_refresh`
  calls
- `search_h1_programs` pagination and the `high_probability_only` filter
  against a mocked HackerOne API response
- `hunter_progress()`'s heuristic against a **real** `/hunt` run's log —
  called out explicitly as unverified in the code's own docstring, since
  every test run so far has deliberately used the safe, read-only
  `/load-program-h1` action rather than triggering real scan traffic just
  to inspect event shapes

---

## 8. Monitoring & Observability

No Sentry, no PostHog, no hosted logging — there's no fleet of users to
aggregate telemetry across, and adding a third-party telemetry SDK to a
tool that handles undisclosed bug bounty scope would itself be a
questionable idea before there's a real product decision to have one.

| What | Where it actually lives today |
|------|-------------------------------|
| Run history | `gui/runs/_index.json` — every run this dashboard has started, forever (not currently pruned) |
| Raw event logs | `gui/runs/<id>.ndjson` — one file per run, also not currently pruned |
| Errors | Printed to whatever terminal `python3 gui/server.py` was started from; no structured error tracking |
| AI spend | Derived live from `gui/runs/_index.json`'s `usage` fields — see §10 |

If `gui/runs/` growing unbounded becomes a real problem, a retention/prune
step is a small, concrete addition — not built yet because it hasn't
actually been a problem across the runs generated so far.

### 8.1 Alerting Thresholds

None of the below are wired to a real alert channel today (there's no
Sentry/PagerDuty, as above) — this is the threshold *table*, useful now
for the operator to eyeball manually and directly reusable once real
alerting is worth building (§11.3):

| Signal | Threshold | Why this number |
|--------|-----------|-------------------|
| A run stuck in `running` with no new NDJSON line | >5 minutes | Both CLIs (§4.3) produce *something* well within 5 minutes even in opencode's worst-case batching (~30s observed, §4.3) — past 5 minutes with zero output suggests a hung process, not just slow output |
| `gui/runs/` directory size | >500MB | Arbitrary but concrete — at that point the "not currently pruned" note in §8 above stops being theoretical and the retention step should actually get built |
| A single program's AI spend (`program_spend()`, §10) | >$10 with zero confirmed findings | Directly the "tokens spent for zero payout" scenario §10.1's `pontoon.allizom.org` example already illustrates — worth a manual review prompt, not necessarily stopping anything automatically |
| HackerOne API errors from `/api/search` | >3 consecutive failures | Distinguishes a transient blip from a real outage or a revoked/expired token (§5.5) worth investigating |
| Repeated out-of-scope-target near-misses (§19.1's runbook triggered) | >1 in a session | Even one is notable; more than one in the same session suggests the scope-check instruction (§5.4) isn't being followed reliably, not just an isolated slip |

These are calibrated against what's actually been observed in this
session's testing (§7.1), not industry-standard SaaS thresholds copied in
— e.g. "5 minutes of silence" is specifically informed by the measured
opencode-vs-Claude buffering behavior in §4.3/§9.2, not a generic default.

---

## 9. Performance Notes

### 9.1 What matters for a local single-page dashboard

Page-load/bundle-size optimization (code splitting, image optimization,
CDN caching) doesn't apply — there's no build, no bundle, and exactly one
operator loading the page from `localhost`. The performance question that
actually matters here is **feed latency**, covered next.

### 9.2 The real bottleneck: subprocess output buffering

Confirmed directly (§7.1, §4.3): the dominant latency isn't network or
rendering, it's how promptly the underlying CLI flushes its own stdout.
`script`-wrapping (`gui/server.py`'s `_launch()`) helps opencode's
buffering somewhat by giving the child a pty, but doesn't fully solve it —
opencode still delivers most output in one late burst regardless. Claude
Code's `stream-json` output doesn't have this problem. This is a CLI
behavior difference to design around (default to Claude for the live-feed
experience), not something more piping cleverness fixes.

### 9.3 Resource ceiling

This runs on the operator's own machine, which may not be generously
resourced — verified on the actual development machine: 4 CPU cores,
frequently under 2GB free RAM. `_launch()`'s one-run-at-a-time lock exists
partly for this reason: 17 hunter subagents already run in parallel
*within* a single `/hunt` invocation, and stacking multiple full hunts
concurrently on a resource-constrained machine risks exactly the kind of
instability that's already been observed unrelated to this tool on the
same machine. A resource-aware scheduler (checking free RAM before
starting a queued run) is a real, not-yet-built improvement — see §11.

---

## 10. Cost Analysis (AI spend, not cloud infra)

There's no Vercel/Supabase/Stripe/Railway bill for this tool as it exists
today — it runs locally with no hosting cost. The cost that's real and
worth tracking is **AI token spend**, which the dashboard already surfaces
per-program and in total (`program_spend()` / `total_spend()` in
`gui/server.py`, summed from every run's captured `usage.total_tokens` /
`usage.cost`).

### 10.1 What's actually been measured

| Run | Profile | Tokens | Cost |
|-----|---------|--------|------|
| `/load-program-h1 mozilla` (opencode, big-pickle) | free tier | 46,295 | $0.00 |
| `/load-program-h1 mozilla` (Claude Sonnet) | paid | 3,531 | $0.1477 |
| Full 17-hunter `/hunt` on `pontoon.allizom.org` (prior session, from `sessions/`) | — | not tracked (predates the dashboard) | — |

The Mozilla `pontoon.allizom.org` hunt session on record (`sessions/hunt-
pontoon.allizom.org-2026-09-03.json`) is a useful real-world data point for
§10.2's ROI question even without a token count attached to it: a full
17-hunter pass produced zero bounty-eligible findings (several genuine
Medium-severity issues, but Mozilla only pays High/Critical) — a concrete
example of a scan that cost real tokens/time for zero payout, which is
exactly the kind of outcome a cost/ROI view (§11) would surface instead of
hiding.

### 10.2 Why "cost per SaaS user" (v1.0's framing) doesn't apply yet

v1.0 of this document modeled infrastructure cost per hosted user (Vercel/
Supabase/OpenAI scaling with signups). That's a real question for a future
hosted version (§11), but it's premature while there's no hosting layer —
the actual, present cost driver is AI tokens per *scan*, which scales with
how many programs/targets the operator runs, not with a user count that
doesn't exist yet.

---

## 11. Roadmap

### 11.1 Already built (this repo, verified working)

- [x] 17-skill AI scanning engine (Claude Code / opencode subagents)
- [x] HackerOne program search, scope loading, findings tracking
- [x] Local dashboard: workspace, embedded live feed, pause/resume via
      real session continuation, model selection (Claude / opencode /
      Gemini), per-program + total AI spend tracking, in-scope target
      checklist
- [x] Submission-safety guard (prompt-level + Claude Code permission-deny)
- [x] Local Markdown report generation (manual submission only)

### 11.2 Near-term hardening (small, concrete, not yet built)

- [ ] `hunter_progress()` heuristic verified against a real `/hunt` run's
      log (currently only tested against safe `/load-program-h1` runs)
- [ ] opencode-side technical enforcement for the submission-safety guard
      (currently Claude Code-only at the permission layer)
- [ ] Resource-aware run scheduling (check free RAM before starting a
      queued run, rather than a flat one-at-a-time lock)
- [ ] `gui/runs/` retention/pruning if the unbounded log growth becomes a
      real problem
- [ ] Automated tests for the parsing/state-machine logic named in §7.2

### 11.3 If/when this becomes a hosted, multi-tenant SaaS

This is the point at which most of v1.0's original stack becomes relevant
again — but as additions on top of a working single-user engine, not a
replacement for it:

- [ ] Per-user credential storage (today: one `.env` on one machine)
- [ ] A real database once there's more than one tenant's worth of
      programs/runs/findings to isolate (§2.3 sketches the migration path)
- [ ] Auth (today: none, trusted by `127.0.0.1` binding)
- [ ] Billing (today: none — this tool has no monetization layer at all)
- [ ] A request queue instead of "one run at a time" per machine
- [ ] Hosted frontend + worker infrastructure

---

## 12. CI/CD Pipeline Design

**Currently: none.** No `.github/workflows/`, no automated test run on
push, no automated deploy — confirmed by checking the repo, there's no CI
config anywhere. This is consistent with §7.1: there's no test suite for a
pipeline to run yet, and nothing to "deploy" for a script the operator runs
directly on their own machine (§6).

### 12.1 What a pipeline would need, once §7.2's test suite exists
- **On every PR**: run the (not-yet-built) `pytest`/`vitest`-equivalent
  suite for `gui/server.py`'s parsing/state-machine logic (§7.2), lint
  (`ruff` or similar for the Python, since there's no JS build step to
  lint beyond basic syntax checking of `gui/index.html`'s inline script)
- **On merge to main**: for the *local tool* as it exists today, nothing
  needs to auto-deploy — a GitHub Action re-running the test suite on
  `main` and failing loudly is sufficient
- **Once hosted (§11.3)**: merge to `main` auto-deploys to staging (§13);
  promotion to production is a manual, deliberate step (not full
  continuous deployment) until there's enough monitoring (§8) and enough
  users that an untested production regression would be caught by
  automated smoke tests rather than by a customer report

### 12.2 Why this wasn't built yet
Building CI for a test suite that doesn't exist, targeting a deployment
target that doesn't exist, would be pure scaffolding — §7.2 (tests) is the
actual prerequisite here, not CI tooling itself.

---

## 13. Environment Strategy (Staging / Production)

**Two different things are easy to conflate under "staging" here — worth
separating explicitly:**

### 13.1 Staging for *scan targets* — already exists, unrelated to deployment
Many HackerOne programs' scope explicitly designates a staging subdomain
as the only place testing is allowed (e.g. Mozilla's `CLAUDE.md`, loaded
live by `/load-program-h1`, marks several targets "staging only, never
production" — `support.allizom.org`, `pontoon.allizom.org`, etc.). Hunter
skills already respect this via the per-target notes in `CLAUDE.md` (§5.4
Scope Enforcement). This is a program-scope concept, not an app-deployment
concept — flagging it so the term "staging" in this section isn't confused
with it.

### 13.2 Staging/production for the app itself — not applicable yet
There is exactly one environment today: the operator's own machine,
running `python3 gui/server.py` directly against real data. There's no
"staging deploy" because there's no deploy at all (§6, §12).

### 13.3 Once hosted (§11.3)
- **Dev**: local machine, same as today, unchanged
- **Staging**: mirrors production infra, uses Stripe *test mode*, a
  separate database instance/project from production, seeded with fake
  programs/findings rather than real (potentially still-undisclosed)
  bounty data — production data must never be copied into staging given
  the confidentiality concerns already covered in §2.2/§5.1
- **Production**: real data, real billing, gated behind whatever manual
  promotion step §12.1 describes

---

## 14. Database Migration Strategy

### 14.1 Today: JSON files, no formal migrations, but not unversioned chaos either
There's no schema-migration tool because there's no database (§2) — but
the JSON "schemas" in §2.1 already change shape as features get added
(e.g. `gui/runs/_index.json` gained a `usage` field when spend-tracking
was added; `findings_status.json` didn't exist until report-status
tracking was built). This has been handled defensively rather than
formally: `_load_json()` returns `None` on any parse failure instead of
crashing, and readers use `.get(key, default)` rather than assuming a key
exists — old files from before a field existed don't break new code, they
just read as `None`/absent for that field. That's adequate at the current
scale (one operator, files they can inspect by hand) and not something
worth over-engineering with a formal versioning scheme before there's a
second consumer of these files.

### 14.2 Once a real database exists (§2.3, §11.3)
- Standard additive-migration discipline: add new nullable columns first,
  backfill in a background step, only drop old columns in a *later*
  release once nothing reads them — never a single migration that both
  adds and removes in a way that breaks a mid-deploy request
- Migration tooling: whatever the eventual DB choice's native tooling is
  (Supabase's CLI + a query builder's migration generator, if that's the
  eventual choice — not committing to a specific one here since §11.3
  hasn't chosen the DB yet, only sketched the shape of the data in §2.3)
- Every migration reversible, or explicitly documented as a one-way door
  (e.g. a destructive column drop) with a required backup taken first —
  ties into §18 (Disaster Recovery)

---

## 15. API Versioning Strategy

### 15.1 Today: unversioned, and that's fine
`gui/server.py`'s routes (§3) have no version prefix — `/api/status`, not
`/api/v1/status`. This is fine *because* the server and its only client
(`gui/index.html`) are always the same version, served from the same
process, on the same machine — there's no scenario where an old client
talks to a new server or vice versa, which is the entire problem API
versioning exists to solve.

### 15.2 Once there's an external API (PRD.md §3.2.2 — public API access, Phase 2)
That's the point versioning becomes necessary — an external integration
built against today's route shape would break silently on any breaking
change otherwise. At that point: URL-prefixed versioning (`/api/v1/...`),
a documented deprecation window before removing an old version (minimum
90 days, communicated via the changelog/status page), and additive-only
changes preferred within a version (new optional fields fine, removing or
renaming a field is a `v2` change).

---

## 16. Rate Limiting

### 16.1 The dashboard's own API: deliberately none
`/api/*` on `gui/server.py` has no rate limiter. This isn't an oversight —
the real protection is §5.2's `127.0.0.1`-only binding: there is exactly
one trusted local caller, and a rate limiter would be defending against a
threat model (many untrusted callers) that doesn't exist here. Adding one
now would be solving a problem the system doesn't have.

### 16.2 Where rate limiting actually matters today: outbound scan traffic
This is the real rate-limiting concern for this tool, and it's already
built — `.claude/commands/hunt.md`'s "Rate limiting rules (MANDATORY)"
section, followed by every hunter skill: max 2 requests/second per
endpoint, `--limit-rate 100k` on curl, `sleep 0.5` between calls to the
same host, stop immediately on a `429`/`503`. This protects the *target*
from being hammered, and protects the operator from getting IP-banned or
violating a program's testing-rate rules — a more relevant concern for a
security-scanning tool than inbound API rate limiting.

### 16.3 Once hosted with external users (§11.3)
Standard per-user/per-IP rate limiting on the hosted API becomes necessary
once callers aren't a single trusted operator — a Redis-backed limiter
(the old v1.0 doc's Upstash Redis idea) is a reasonable choice at that
point, just premature today.

---

## 17. Caching Strategy

### 17.1 Today: no caching needed
Every dashboard read is a local file read (`gui/watchlist.json`, session
files, etc.) — microseconds, not worth caching. HackerOne search results
(`/api/search`) aren't cached either: each search is a live API call,
which is fine for one operator making occasional searches, and gives
always-fresh `submission_state`/`offers_bounties` data (§3.1) rather than
risking stale results.

### 17.2 Once search volume grows (many concurrent operators, §11.3)
A shared, short-TTL (e.g. hourly) cache of HackerOne's program list would
cut redundant API calls significantly if many hosted users are searching
overlapping program sets — not built because it isn't needed at current
(single-operator) scale.

---

## 18. Disaster Recovery Plan

### 18.1 A real, currently-unaddressed gap
`.gitignore` correctly excludes `memory/`, `sessions/`, `reports/`,
`gui/watchlist.json`, `gui/findings_status.json`, and `CLAUDE.md` from
version control (§2.2) — this data is operator-specific and often covers
an active, undisclosed bug bounty engagement, so it must never end up in a
shared git history. **The consequence, not previously written down
anywhere: none of it is backed up either.** If the operator's disk fails,
every hunt session, confirmed finding, tracked-program list, and report-
status record is gone with no recovery path. This is worth stating plainly
rather than leaving implicit.

### 18.2 Recommended mitigation (not yet built into the tool itself)
This is currently the operator's own responsibility, not something
`gui/server.py` automates:
- A periodic encrypted local backup (e.g. an encrypted archive of
  `memory/`, `sessions/`, `reports/`, `gui/*.json` to external storage)
- Or, if the operator accepts the confidentiality tradeoff for their own
  threat model, a *private* (never public) git repo for just these paths
  — deliberately not the default, since it would be easy for someone to
  copy this pattern without registering that it inverts the
  `.gitignore` protection §2.2 relies on

### 18.3 Once a real database exists (§11.3)
Standard DB-provider backup/point-in-time-recovery — whatever the eventual
hosting choice's native offering is, tested by an actual restore drill
before it's trusted, not just assumed to work because it's configured.

---

## 19. Incident Response Plan

Scoped to the incidents that are actually possible with *this* tool today
— not a generic hosted-SaaS incident-response template, since most of
that template's scenarios (production outage, DB failover) don't apply
yet (§6, §18).

### 19.1 Runbook: accidental out-of-scope target contact
1. Stop the run immediately (`/api/runs/<id>/stop`, §3.3)
2. Check `CLAUDE.md`'s scope tables against what was actually contacted
3. If genuinely out of scope: do not retain any response data captured
   from that request; most programs' policy (their `CLAUDE.md`-loaded
   rules, §5.4) covers accidental-scope-touch disclosure — follow it
4. Document what happened and why the scope check (§5.4) didn't catch it
   in advance — this is exactly the kind of gap a request-level allowlist
   proxy (§5.4's noted future hardening) would close

### 19.2 Runbook: submission-safety guard bypassed
This would be serious — a finding submitted to HackerOne without human
review, despite §5.3's guards. 
1. Immediately check HackerOne's report history for the program in
   question for anything unexpected
2. If something was submitted: contact the program directly to explain
   and request withdrawal/correction if the report was premature or
   incorrect
3. Revoke and rotate the `H1_TOKEN` (§5.5) as a precaution regardless of
   root cause
4. Root-cause it against §5.3's two guard layers — did the prompt-level
   instruction get ignored, or did the permission-deny layer fail? — and
   close the specific gap (this is exactly the class of bug §5.3 already
   flags as open for opencode, which lacks the permission-deny layer)

### 19.3 Runbook: dashboard exposed beyond localhost
(e.g. `HOST` accidentally changed from `127.0.0.1` to `0.0.0.0`, or run
behind a reverse proxy without realizing it removes the localhost
guarantee)
1. Stop `gui/server.py` immediately
2. Treat as a credential-exposure event — `.env`'s `H1_USER`/`H1_TOKEN`
   (§5.5) could have been reachable via `/api/search`'s use of them, and
   any findings data (§2.1) could have been read by anyone who found the
   open port
3. Rotate `H1_TOKEN`
4. Review access logs if any exist (none currently — §8 — which is itself
   a reason to keep this scenario's blast radius small by never exposing
   the port in the first place, §5.2)

### 19.4 Once hosted (§11.3)
Standard Sev1–4 severity classification, an on-call rotation, a public
status page, and a postmortem template — none of which make sense to
build for a tool one person runs on their own machine.

---

## 20. Load Testing Plan

### 20.1 Not applicable to the current tool, and that's fine to say plainly
One operator, one browser tab, one run at a time by explicit design
(`_launch()`'s single-run lock, §3.3, §9.3) — "does it handle 1,000
concurrent users" is not a meaningful question for what exists today, and
running a load test against it would produce a number describing nothing
real.

### 20.2 Before claiming PRD.md §5.3's scalability targets (once hosted)
PRD.md's Non-Functional Requirements claim 1,000+ concurrent users and
100+ concurrent scans — those numbers currently have zero load-testing
evidence behind them, same caveat as §15 (Unit Economics) in PRD.md: a
target, not a measurement. Before that section is used to represent
anything to a customer or investor, it needs:
- A load-testing tool (k6 or similar) run against the eventual hosted API
- Specific attention to the concurrency model change: today's "one run at
  a time" is a *global* lock; hosted, it needs to become "one run at a
  time *per operator*, many operators concurrently" — that's a different
  system, not just the same lock at higher volume, and deserves its own
  design pass rather than assuming it falls out of removing the lock

---

## 21. Additional Reliability & DX Enhancements (Nice to Have)

Lower priority than §§12–20 — mostly relevant only once hosted (§11.3),
listed here for completeness rather than because any is planned near-term.

| Item | Why it'd help | Applies today? |
|------|----------------|------------------|
| Feature flags | Gradual rollout of risky changes once there are users to protect from a bad release | No — one operator, changes are just tested manually before use |
| Structured logging | Machine-parseable logs for debugging at scale | Partial — `gui/server.py`'s prints (§8) are plain text; fine for one operator reading their own terminal, not fine for aggregating across many hosted instances |
| Audit trail | Compliance requirement once handling other people's data (PRD.md §10.2 GDPR) | No — single operator, their own data, no third party to audit access on behalf of |
| SDK / client library | Developer experience once the public API (§15.2) exists | No — no public API yet |
| Webhook delivery guarantees (retries, signing) | Reliability once PRD.md §3.2.2's webhook integration ships | No — no webhooks exist yet |
| Circuit breaker pattern | Fault tolerance against a flaky upstream (AI provider, HackerOne API) | Partial case exists already — `search_h1_programs()` catches and surfaces HackerOne API errors cleanly rather than crashing, but there's no automatic backoff/circuit-open behavior on repeated failures |
| Auto-scaling config | Handling traffic spikes | No — nothing to scale, it's a script on one machine |
| Load balancing strategy | High availability across multiple instances | No — one instance, one machine, by design |

---

## 22. Appendix

### 22.1 Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Sep 3, 2026 | Initial draft — generic SaaS stack (Next.js/Supabase/Stripe/Nuclei/OpenAI) not grounded in this codebase |
| 2.0 | Sep 3, 2026 | Rewritten to describe the actual scanning engine (BountyGrimoire) already implemented in this repo. PRD.md's business content unchanged. |
| 2.1 | Sep 3, 2026 | Added §§12–21: CI/CD, environment strategy, DB migration strategy, API versioning, rate limiting, caching, disaster recovery, incident response, load testing, and a nice-to-have reliability/DX list — closing the gaps a completeness review flagged. Each new section states current reality first, future/hosted plan second, same as the rest of this document. |

---

*Document generated for SecScan AI — technical design section, now grounded in the BountyGrimoire codebase this product actually builds on.*
