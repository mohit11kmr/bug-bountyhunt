# PRD — BountyGrimoire
## Local-First AI Bug Bounty Hunting Workbench

**Document status:** Corrected baseline
**Version:** 1.0
**Date:** 2026-09-03
**Product:** BountyGrimoire
**Primary runtime:** Local operator machine
**Primary interface:** Claude Code / OpenCode + local web dashboard

---

## 1. Product Definition

### 1.1 What the product actually is today

BountyGrimoire is a **local-first, operator-controlled AI security research workbench** for authorized bug bounty and penetration-testing work.

The product combines:

- HackerOne program discovery and scope/policy loading.
- A blocking reconnaissance pass before vulnerability hunting.
- 17 specialized vulnerability hunters for normal hunts.
- 7 focused authenticated hunters for cross-account testing.
- A single validation pass that independently checks candidate findings.
- Program memory stored locally so confirmed patterns and false positives can inform later hunts.
- Session persistence and resume support.
- Local report generation for manual human submission.
- A localhost dashboard for program tracking, run control, findings status, progress, and model selection.
- A skill generator that can refine hunter skills from disclosed bounty reports and user-provided writeups.

### 1.2 What it is NOT today

The following are **not implemented in the current repository** and must not be described as current MVP functionality:

- Multi-tenant SaaS accounts.
- Email/password authentication.
- Team/RBAC support.
- Subscription billing or Stripe checkout.
- PostgreSQL/Supabase.
- Redis/queues as application infrastructure.
- Vercel/Railway deployment.
- A Next.js/React application.
- Scheduled cloud monitoring.
- Automated HackerOne report submission.
- PDF report export.
- Public external API.
- Enterprise SLA / hosted uptime guarantees.

These may be future product directions, but they are roadmap items rather than current implementation requirements.

---

## 2. Problem Statement

Manual bug bounty research is slow because the researcher repeatedly performs scope review, reconnaissance, endpoint discovery, vulnerability-specific testing, validation, note-taking, and report preparation.

BountyGrimoire is intended to reduce that repetitive work while keeping the researcher in control of authorization, scope, destructive actions, final validation, and report submission.

The product's core principle is:

> **Automate breadth, preserve human control over authorization and final disclosure.**

---

## 3. Goals

### 3.1 Primary goals

1. Start an authorized target hunt with a small number of operator actions.
2. Load the program's scope and policy before any target testing begins.
3. Perform recon first and use the resulting attack surface to focus specialized hunters.
4. Run independent vulnerability hunters in parallel where safe to do so.
5. Validate findings before presenting them as actionable results.
6. Persist useful findings, false positives, technologies, endpoints, and sessions locally.
7. Allow a researcher to inspect progress without reading raw CLI logs manually.
8. Produce a human-reviewable report artifact without automatically submitting it.

### 3.2 Secondary goals

- Allow the operator to select among supported CLI/model profiles.
- Resume unfinished or completed conversations when the underlying CLI session can be continued.
- Improve skills using fresh disclosed reports or private research notes.

---

## 4. Non-Goals

The following are explicitly out of scope for the current product baseline:

- Becoming a generic vulnerability scanner with a large signature/CVE database.
- Acting as a hosted security platform for arbitrary third-party customers.
- Automatically submitting HackerOne reports.
- Replacing human authorization decisions.
- Automatically bypassing anti-bot, WAF, or program-specific restrictions.
- Aggressive or unrestricted scanning.
- Managing payment, invoices, or customer subscriptions.

---

## 5. Users

### 5.1 Security researcher / bug bounty hunter

Needs to load a program, select an in-scope target, launch a hunt, monitor progress, inspect findings, continue a session, and generate a report.

### 5.2 Authorized penetration tester

Uses the same engine against explicitly authorized targets, with additional authenticated accounts when the engagement permits account creation and cross-account testing.

### 5.3 Skill maintainer / researcher

Uses `generate-skill.py` to improve individual hunter skills or all skills from public disclosures and private writeups.

---

## 6. Functional Requirements

### FR-01 — Program discovery

The system shall allow the operator to search HackerOne programs from the local dashboard when valid credentials are configured.

Search results should expose at minimum:

- Program name.
- Program handle.
- Submission state.
- Bounty availability indicator when returned by the source.

### FR-02 — Program loading

`/load-program-h1 <handle>` shall load program metadata, scope, policy/rules, and write the active program context to `CLAUDE.md`.

The active program context becomes the operational source of truth for subsequent hunts.

### FR-03 — Scope gate

`/hunt <target>` and `/hunt-auth <target>` shall check `CLAUDE.md` before testing.

A target that is not explicitly in scope must be refused.

Program-specific notes such as staging-only restrictions, required headers, proxies, or testing restrictions must be passed to the hunters.

### FR-04 — Recon-first orchestration

A normal hunt shall run one blocking recon pass before vulnerability hunters.

Recon output should cover, where applicable:

- technologies;
- endpoints and HTTP methods;
- parameters;
- forms;
- interesting paths;
- relevant memory hits.

### FR-05 — Specialized hunters

A standard hunt supports these 17 types:

`idor`, `ssrf`, `sqli`, `xss`, `auth`, `rce`, `xxe`, `ssti`, `secrets`, `otp`, `pii`, `bizlogic`, `callback`, `enumerable`, `insecure`, `referer`, `checksum`.

`--types` shall restrict a hunt to the requested supported hunter types.

### FR-06 — Authenticated hunting

`/hunt-auth <target>` shall support an authenticated workflow with two test identities when the target's program policy allows it.

The current focused authenticated set is:

- IDOR;
- Auth/authorization;
- authenticated XSS;
- business logic;
- PII exposure;
- secrets exposure;
- authenticated enumeration.

### FR-07 — Safety and rate control

Hunters shall follow the active program policy and current command-level rate controls, including the project's maximum request rate guidance and mandatory stop behavior on 429/503 responses.

No hunter or validator may call HackerOne submission/write tools.

### FR-08 — Validation

Candidate findings shall pass through a validation stage before being treated as confirmed/likely results.

Validation shall check at minimum:

- target scope;
- qualifying/non-qualifying status;
- reproducibility;
- technical evidence;
- business impact;
- severity estimate.

### FR-09 — Program memory

The system shall maintain local per-program memory for useful knowledge such as:

- confirmed patterns;
- false positives;
- discovered endpoints;
- technology stack notes;
- reusable hunt information.

Memory must not be treated as proof of a current vulnerability; current reproduction remains required.

### FR-10 — Sessions

Hunt artifacts shall be stored under `sessions/` using a consistent machine-readable schema.

A session shall preserve enough state to understand:

- program;
- target;
- date/time;
- hunters launched;
- endpoints discovered when available;
- validated findings;
- discarded findings;
- notes / suggested next action.

### FR-11 — Resume

The dashboard shall expose resume for runs where the underlying CLI session can be continued.

Resume must create a new run record linked to the previous run/session rather than silently overwriting the original run.

### FR-12 — Local dashboard

The dashboard shall provide:

- active program state;
- tracked programs;
- program statistics;
- model profile selector;
- start controls;
- live/near-live run feed;
- run status and progress estimate;
- findings table;
- finding report status;
- total local AI usage/cost summary.

### FR-13 — Report generation

`/report` shall generate a local Markdown report containing the verified finding details, reproduction, evidence, impact, severity/CVSS recommendation, and remediation.

Submission remains a manual human action.

### FR-14 — Skill generation

`generate-skill.py` shall support:

- individual skill generation;
- all skills;
- public HackerOne disclosed-report input;
- optional private writeup folders/files;
- Anthropic;
- OpenAI;
- OpenAI-compatible providers.

Generated OpenCode agents must remain synchronized with the Claude skill source according to the project's defined mirroring rules.

---

## 7. Product Workflow

### 7.1 Standard workflow

```text
Start local launcher
   ↓
Load HackerOne program
   ↓
Program policy + scope written to CLAUDE.md
   ↓
Choose in-scope target
   ↓
Recon-first
   ↓
17 hunters in parallel (or selected --types)
   ↓
Collect candidate findings
   ↓
Single validation pass
   ↓
Save session + update memory
   ↓
Review findings in dashboard / CLI
   ↓
Generate local report
   ↓
Human reviews and submits manually
```

### 7.2 Authenticated workflow

```text
Load program
   ↓
Verify account creation/use is allowed
   ↓
Create or load attacker + victim test identities
   ↓
Verify both sessions
   ↓
Authenticated recon
   ↓
7 focused authenticated hunters
   ↓
Validation
   ↓
Session + memory
   ↓
Human review / report
```

---

## 8. Dashboard Requirements

### 8.1 Program workspace

The dashboard should make the currently loaded program visually obvious and show tracked programs separately.

Each program card should expose:

- name/handle;
- status;
- confirmed patterns;
- false positives;
- discovered endpoints;
- number of sessions;
- local AI spend;
- recent sessions;
- relevant run controls.

### 8.2 Run controls

Run controls shall support:

- `load-program-h1`;
- `hunt`;
- `hunt-auth`;
- target input where needed;
- model profile selection;
- stop;
- resume;
- view live run details.

### 8.3 Findings workspace

The findings table shall show at minimum:

- program;
- target;
- severity;
- type;
- endpoint;
- report status.

Report status currently supports:

- Not reported;
- Drafted;
- Submitted.

“Submitted” is a local bookkeeping state only; it does not mean the application submitted anything automatically.

---

## 9. Safety Requirements

### SR-01
The product is for authorized testing only.

### SR-02
Program policy and scope must be read before target testing.

### SR-03
Human review remains mandatory before disclosure/submission.

### SR-04
HackerOne write/submission tools must remain blocked.

### SR-05
The local dashboard shall bind to `127.0.0.1` unless a future security redesign explicitly introduces authenticated remote access.

### SR-06
Sensitive credentials must not be exposed through logs, reports, UI events, or generated artifacts unnecessarily.

### SR-07
The `--dangerous` execution mode must remain clearly identified as unrestricted and should be used only in an appropriately isolated environment.

---

## 10. Current Data Model

The current implementation is file-backed.

| Artifact | Purpose |
|---|---|
| `CLAUDE.md` | Active program scope/policy/context |
| `memory/<program>.json` | Persistent program intelligence |
| `sessions/*.json` | Hunt results / session history |
| `gui/watchlist.json` | Dashboard tracked programs |
| `gui/findings_status.json` | Local finding/report status |
| `gui/runs/_index.json` | Persistent run index |
| `gui/runs/<id>.ndjson` | Raw run event log |
| `reports/*.md` | Human-reviewed report drafts |
| `accounts/<target>.json` | Authenticated test-account/session state when used |

The last three directories may be created at runtime and are not necessarily present in a clean checkout.

---

## 11. Performance Requirements

These are **local-tool targets**, not hosted SaaS SLAs:

- Dashboard should remain responsive while a CLI run is active.
- Run progress should update without requiring the operator to inspect the terminal.
- Live Claude output should be visible progressively where supported by the selected CLI.
- Buffered OpenCode profiles may update in batches; the UI should disclose this instead of pretending progress is exact.
- Old run logs must eventually receive a retention/cleanup policy before the tool is used for large numbers of hunts.

No claim is made in this baseline for 1,000+ concurrent users or 100+ concurrent cloud scans.

---

## 12. Reliability Requirements

The product should gracefully handle:

- CLI not installed;
- CLI exits with error;
- invalid JSON event lines;
- interrupted runs;
- dashboard restart while a run is in progress;
- missing optional runtime directories;
- invalid API input;
- missing HackerOne credentials;
- HackerOne API errors/rate limiting;
- unavailable scan targets.

Run state written to disk must never be silently destroyed by a UI refresh.

---

## 13. Known Gaps / Required Hardening

1. There is no automated test suite in the current repository.
2. Scope enforcement is primarily command/agent policy enforcement, not a kernel/network-level egress policy.
3. The local dashboard has no user authentication; its localhost-only binding is a security boundary.
4. The run API can trigger scans for processes on the same machine; remote exposure must not be enabled without authentication and authorization.
5. `session-save.md` and the dashboard's `read_sessions()` expect different session field shapes; these schemas must be unified.
6. Report draft detection from filenames is heuristic and should not be treated as authoritative linkage.
7. `hunter_progress()` is explicitly best-effort and should be validated against real `/hunt` event logs.
8. Credentials used for authenticated research require stricter secret-handling and cleanup rules than the current documentation alone provides.
9. There is no formal retention/rotation policy for run logs, session data, or generated reports.
10. There is no CI pipeline or load test suite for the current tool.

---

## 14. Acceptance Criteria for the Current Baseline

A release is acceptable when all of the following are true:

- `python3 -m py_compile gui/server.py generate-skill.py` passes.
- Local dashboard starts successfully on `127.0.0.1:8765`.
- `/api/status`, `/api/profiles`, `/api/runs`, `/api/search`, run control endpoints, watchlist endpoints, and finding-status endpoints respond correctly for valid/invalid inputs.
- `/load-program-h1` produces a coherent `CLAUDE.md` scope/policy context.
- `/hunt` enforces scope before target testing.
- Recon executes before hunter fan-out.
- Validation occurs before a finding becomes a confirmed/likely result.
- Hunt sessions are written in the same schema consumed by the dashboard.
- Report generation never performs HackerOne submission.
- Claude and OpenCode skill definitions remain synchronized where required.
- The dashboard clearly distinguishes estimated progress from confirmed state.

---

## 15. Future Roadmap — Hosted SaaS, Separately Phased

Only after the local-first product is stable should the project consider a hosted product.

### Phase H1 — Application boundary

- Define a versioned service/API boundary around the scanner engine.
- Add authenticated user accounts.
- Introduce tenant isolation.
- Replace local JSON persistence with a transactional database.

### Phase H2 — Hosted execution

- Isolate each scan in a sandbox/worker environment.
- Add durable job queueing.
- Add outbound egress controls.
- Add centralized logs and audit trails.

### Phase H3 — Billing and collaboration

- Subscription/billing provider.
- Workspace/team roles.
- Usage metering.
- Report sharing and integrations.

### Phase H4 — Hosted security product

- Scheduled monitoring.
- Public API.
- Compliance/reporting packages.
- Enterprise controls and SLA.

The hosted architecture must be treated as a new security boundary, not as a simple deployment of `gui/server.py` to the public internet.

---

## 16. Product Language Rules

Use these terms consistently:

- **BountyGrimoire** — current product/repository.
- **hunt** — one targeted security-testing workflow.
- **recon** — blocking attack-surface discovery step.
- **hunter** — specialized vulnerability-testing agent/skill.
- **validator** — independent finding verification pass.
- **program context** — scope/policy information loaded into `CLAUDE.md`.
- **session** — persisted hunt result/context.
- **memory** — durable per-program research knowledge.
- **report draft** — local Markdown artifact for human review.

Do not call current functionality “multi-tenant”, “hosted SaaS”, “continuous cloud monitoring”, or “automated submission”.

---

## 17. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-03 | Rebased PRD on actual repository behavior; separated current product from future SaaS roadmap; added explicit gaps and acceptance criteria. |
