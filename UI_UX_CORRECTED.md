# UI/UX Specification — BountyGrimoire Dashboard
## Corrected, Implementation-Aligned Design

**Version:** 1.0  
**Date:** 2026-09-03  
**Current UI technology:** plain HTML/CSS/JavaScript in `gui/index.html`  
**Current API:** `gui/server.py` on `127.0.0.1:8765`

---

## 1. UX Objective

The dashboard should answer five questions immediately:

1. **Which program am I working on?**
2. **Which targets are in scope?**
3. **What hunt is running right now?**
4. **What findings have been validated, and what is their report status?**
5. **What should I do next?**

The interface must behave like a **security operations workbench**, not a generic SaaS analytics dashboard.

---

## 2. Current UI Reality

The supplied implementation already contains:

- a header with BountyGrimoire branding;
- current-program badge;
- total token/cost badge;
- model profile selector;
- HackerOne program search;
- tracked program cards;
- scope checklist for the active program;
- recent session history;
- run controls;
- embedded run feed;
- stop/resume controls;
- findings table;
- report-status selector;
- five-second dashboard refresh;
- two-second active-run polling.

The corrected UX should **preserve these capabilities** while improving hierarchy, safety cues, discoverability, and workflow continuity.

---

## 3. Information Architecture

The screen should be organized into four layers.

```text
┌──────────────────────────────────────────────────────────────┐
│ GLOBAL HEADER                                                 │
│ BountyGrimoire | Active Program | Spend | Safety status      │
├──────────────────────────────────────────────────────────────┤
│ 1. PROGRAM WORKSPACE                                         │
│ Search/Add Program                                           │
│ Tracked Programs                                             │
├──────────────────────────────────────────────────────────────┤
│ 2. ACTIVE HUNT                                                │
│ Target → Mode → Model → Start/Stop/Resume                    │
│ Scope → Progress → Live events                               │
├──────────────────────────────────────────────────────────────┤
│ 3. FINDINGS                                                   │
│ Filters → Severity → Type → Report Status → Endpoint         │
├──────────────────────────────────────────────────────────────┤
│ 4. SESSION HISTORY / MEMORY                                  │
│ Previous runs, endpoints, patterns, false positives           │
└──────────────────────────────────────────────────────────────┘
```

The current implementation is card/table based; this layout is a hierarchy specification, not a requirement to introduce a framework.

---

## 4. Global Header

### Required content

**Left**

- BountyGrimoire logo/name.
- Small product descriptor: `Authorized Security Research Workbench`.

**Center/right**

- `Active: <program>` badge.
- `AI spend: <tokens> · $<cost>` badge.
- Safety indicator: `Local only`.

### Safety rule

The safety indicator must never imply network isolation beyond what actually exists.

Use:

> `Local only · 127.0.0.1`

Avoid:

> `Fully secure` / `Sandboxed` / `Protected`

unless the implementation truly guarantees those claims.

---

## 5. Program Search and Tracking

### Search panel

The search panel is a **discovery task**, not the primary dashboard task, so it should remain compact until used.

Recommended hierarchy:

```text
Find a HackerOne program
[ company / handle / keyword                 ] [Search]

Search results
─────────────────────────────────────────────
Program Name     handle · bounty state   [Track]
```

### Tracked-program card

Each card should present:

**Header**

- Program name.
- HackerOne handle.
- state pill: Not started / Processing / Complete.

**Key metrics**

- confirmed patterns;
- known false positives;
- discovered endpoints;
- hunt sessions;
- AI spend.

**Recent activity**

- latest session date;
- latest target;
- finding count;
- next suggested action.

**Action row**

- Load program.
- Start hunt.
- Start authenticated hunt where applicable.

Avoid forcing the user to scan a large table before finding the action button.

---

## 6. Active Program / Scope View

The active program is a safety-critical context and needs stronger visual treatment than ordinary metadata.

### Scope block

Show:

```text
IN-SCOPE TARGETS
12 / 24 tested

✓ support.allizom.org       staging only
✓ www.allizom.org           staging only
○ example.mozilla.org       not tested
...
```

Each target must support a notes tooltip/detail view.

### Safety messaging

Place a small persistent statement near the scope block:

> `Testing is restricted to the loaded program policy. Verify staging/production notes before starting a hunt.`

Do not hide critical scope restrictions in a tooltip only.

---

## 7. Hunt Composer

The hunt control should be one compact, explicit sequence:

```text
TARGET
[ https://target.example.com                         ]

MODE
[ Standard Hunt ▼ ]   [ Authenticated Hunt ]

MODEL
[ Claude Code · Sonnet ▼ ]

SCOPE
✓ program loaded   ✓ target in scope

[ Start Hunt ]
```

### Standard hunt

Show:

- target;
- optional `--types` equivalent as an advanced control;
- model profile.

### Authenticated hunt

Show an extra safety gate:

```text
AUTHENTICATED MODE
Attacker + Victim test sessions required.
Only use when the program permits this workflow.

[ ] I verified account creation/use is permitted.
```

The UI should not pretend to create accounts itself because the current dashboard does not provide that functionality.

---

## 8. Run State UX

Run state is the most important dynamic state in the application.

### State labels

Use exactly:

- `Queued`
- `Running`
- `Done`
- `Stopped`
- `Error`
- `Resumed`

### Progress presentation

Show three separate indicators:

```text
RECON              ✓ complete
HUNTERS            13 / 17 launched · estimated
VALIDATION         pending
OVERALL            Running
```

Never present inferred hunter progress as exact.

The word **Estimated** should remain visible next to inferred progress.

### Live event feed

The feed should prioritize:

1. security-relevant milestones;
2. recon findings;
3. hunter dispatch;
4. validation outcomes;
5. errors/warnings.

Routine tool noise should be visually de-emphasized.

---

## 9. Run Controls

### While running

Primary control:

- `Stop Hunt`

Secondary:

- `View Full Run`

### After completion

Primary:

- `Review Findings`

Secondary:

- `Resume`
- `Generate Report`

The current implementation can resume a run. The UI must make clear that resume starts a continuation run rather than rewinding the original run.

---

## 10. Findings Workspace

Findings should become the main focus after a hunt completes.

### Table columns

Current minimum:

| Program | Target | Severity | Type | Endpoint | Report Status |
|---|---|---|---|---|---|

Recommended additions:

| Confidence | Validation | Last Updated |
|---|---|---|

### Filters

Add lightweight controls above the table:

```text
Severity [All ▼]  Type [All ▼]  Status [All ▼]  Program [All ▼]
[ Search endpoint / keyword ]
```

### Severity display

Severity must not rely on color alone.

Use:

- text label;
- optional icon;
- consistent severity token.

Example:

`HIGH  ●`

rather than a color-only dot.

### Finding row interaction

Clicking a finding should expose a detail drawer/modal containing:

- title;
- endpoint;
- description;
- evidence;
- reproduction command;
- confidence;
- qualifying state;
- report status;
- notes;
- report action.

The current server already exposes enough finding data to support the first version of such a detail view, though the current HTML does not yet implement it.

---

## 11. Report Status UX

Use three statuses:

```text
NOT REPORTED
DRAFTED
SUBMITTED
```

Important semantics:

- `Drafted` means a local report artifact was detected/associated.
- `Submitted` is a manual bookkeeping state.
- The UI must never imply that BountyGrimoire submitted a HackerOne report automatically.

Recommended status helper text:

> `Submission is always completed manually in HackerOne.`

---

## 12. Session History

Every tracked program should expose recent sessions in a compact history table:

| Date | Target | Hunters | Findings | Action |
|---|---|---:|---:|---|
| 2026-09-03 | target.example | 17/17 | 2 | Review |

Clicking `Review` should reuse the same findings/run-detail pattern instead of sending the operator to raw JSON.

---

## 13. Memory UX

Memory is useful but can become confusing with findings if mixed into the same table.

Provide a collapsed “Program Intelligence” section with:

```text
Confirmed patterns     18
Known false positives  27
Discovered endpoints   132
Last memory update     2026-09-03
```

Add a short disclaimer:

> `Memory is historical guidance. Current findings still require fresh reproduction.`

---

## 14. Error UX

Errors should be actionable.

### Bad

> `Request failed.`

### Better

> `HackerOne search failed. Check H1_USER/H1_TOKEN in .env, then retry.`

### Run errors

Show:

- run ID;
- profile;
- target;
- exit state;
- short error explanation;
- `View raw run` action.

Never expose secrets in error messages.

---

## 15. Empty States

### No program

```text
No program loaded.
Search for your HackerOne program, then load it before starting a hunt.
[ Find Program ]
```

### No runs

```text
No hunts yet.
Load an in-scope program and start your first authorized hunt.
```

### No findings

```text
No validated findings yet.
A completed hunt with zero findings is a valid result.
```

Do not use celebratory language for “zero findings”; the outcome is neutral.

---

## 16. Visual Design System

The current UI uses a dark, terminal-inspired aesthetic. Keep that identity, but increase hierarchy and readability.

### Design principles

- Dark, high-contrast workspace.
- One primary accent for actions.
- Severity uses semantic color tokens plus text.
- Cards for entities; tables for comparisons.
- Monospace only for commands, endpoints, IDs, and raw evidence.
- Normal sans-serif for explanatory text.
- Avoid excessive glows, gradients, and decorative effects.
- Preserve fast scanning at 100% browser zoom.

### Suggested type hierarchy

```text
Page title      24–28 px
Section title   16–18 px
Card title      15–17 px
Body            13–14 px
Metadata        11–12 px
Code/evidence   12–13 px monospace
```

### Spacing

Use a compact 4/8-based spacing rhythm:

- 4 px — inline gaps;
- 8 px — control padding;
- 12 px — card internals;
- 16 px — section spacing;
- 24 px — major section separation.

---

## 17. Accessibility

Required:

- visible keyboard focus;
- buttons must have text labels, not icons alone;
- severity cannot be color-only;
- scope warnings must be readable without hover;
- status changes must be announced where practical;
- tables need semantic headers;
- form errors must be connected to their controls;
- text contrast must remain readable in the dark theme.

---

## 18. Responsive Behavior

The current dashboard is desktop-first because security research workflows involve commands, endpoints, and long event feeds.

### Desktop ≥ 1200 px

Two-column or multi-card workspace is acceptable.

### Tablet 768–1199 px

Collapse cards to one primary column with findings table horizontally scrollable.

### Mobile < 768 px

Do not attempt to reproduce the entire desktop dashboard.

Prioritize:

- active program;
- running hunt status;
- critical findings;
- stop/resume;
- scope warnings.

Secondary metrics can move behind collapsible sections.

---

## 19. UI Components to Implement Without Changing the Stack

The current plain HTML/JS architecture can support the following components without adopting React:

```text
Header
ProgramSearch
ProgramCard
ScopeChecklist
HuntComposer
RunStateCard
LiveEventFeed
HunterProgress
FindingsTable
FindingDetailDrawer
SessionHistory
MemorySummary
ErrorBanner
ConfirmDialog
```

Recommended implementation approach:

- keep one `render*()` function per component;
- centralize escaping in the existing `esc()` helper;
- centralize fetch/error handling;
- avoid inline styles for repeated patterns;
- move recurring constants into a small JS config block;
- preserve server-rendered JSON API contract.

---

## 20. Critical UX Fixes vs Current Implementation

### P0 — do first

1. Make the active program and scope state more prominent.
2. Add an explicit safe/authorized testing banner.
3. Label inferred hunter progress as `estimated` in a visually obvious way.
4. Add a finding-detail view instead of forcing users to inspect only the table row.
5. Add a clear `Review Findings → Generate Report` progression.
6. Make authenticated mode visually distinct and guarded.

### P1

7. Add filters to the findings table.
8. Add session detail/review actions.
9. Improve program-card action hierarchy.
10. Add persistent run error summaries.
11. Show clearer model/profile semantics and buffering expectations.

### P2

12. Add program intelligence/memory panel.
13. Add import/export of local session bundles.
14. Add configurable retention/cleanup controls.

---

## 21. What NOT to Build in This UI Revision

Do not add visual shells for functionality that does not exist in the current backend, such as:

- billing/subscriptions;
- team members/RBAC;
- cloud job queues;
- cloud deployment settings;
- hosted uptime/SLA dashboards;
- Stripe checkout;
- Supabase account pages;
- automatic HackerOne submission controls;
- fake “continuous monitoring” widgets.

A professional UI is better when every visible control corresponds to a real backend capability.

---

## 22. UI Acceptance Criteria

A UI revision is complete when:

- the active program is identifiable within 2 seconds;
- scope and scope notes are visible before hunt execution;
- the target, mode, and selected model are explicit before starting;
- running/complete/error states are unambiguous;
- estimated progress is labeled as estimated;
- a user can reach a validated finding from the dashboard without reading raw JSON;
- report status meaning is clear;
- the UI never implies automatic HackerOne submission;
- keyboard focus and text labels work in the dark theme;
- the interface remains usable while a run is active and the browser is polling every few seconds.

---

## 23. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-03 | Created an implementation-aligned UI/UX specification for the actual localhost dashboard; removed fictional SaaS screens and defined the missing finding/session/review workflow. |
