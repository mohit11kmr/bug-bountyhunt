# BountyGrimoire — Claude Master Implementation Prompt

You are the senior engineer responsible for implementing this repository.

Before changing code, read:
1. `CLAUDE.md`
2. `IMPLEMENTATION_RULES.md`
3. `PRD_CORRECTED.md`
4. `TDD_CORRECTED.md`
5. `UI_UX_CORRECTED.md`
6. `README.md`

The repository itself is part of the specification.

## OBJECTIVE
Bring the existing BountyGrimoire codebase into alignment with the corrected PRD, TDD, and UI/UX specification while preserving useful existing functionality.

This is a local-first bug bounty research/workbench.

Do NOT silently convert it into a hosted SaaS.
Do NOT replace the current architecture merely because another stack appears cleaner.
Do NOT delete working functionality unless explicitly required.

## PHASE 0 — RECONNAISSANCE
Inspect the complete relevant repository before editing.

Inspect:
- docs listed above
- GUI
- local server/API
- CLI/entrypoints
- session/storage
- scope/configuration
- findings/evidence
- reporting/export
- scripts
- dependencies
- tests
- git status

Determine:
A. what is actually implemented
B. what PRD requires
C. what TDD requires
D. what UI/UX requires
E. exact mismatches
F. code that must be preserved
G. risky areas

Do not start a rewrite.

## PHASE 1 — CANONICAL CONTRACT
Identify canonical structures for:
- session
- run
- finding
- validated finding
- tested URL
- report
- scope

Inspect every reader and writer before modifying persistence.

If multiple formats exist:
1. choose a canonical internal representation
2. add a narrow normalization/compatibility layer if needed
3. update consumers
4. add tests
5. document it

## PHASE 2 — CORE CORRECTNESS
Implement the required core/backend changes from `TDD_CORRECTED.md`.

Preserve CLI behavior unless explicitly changed.

Ensure:
- explicit scope
- truthful run lifecycle
- reliable finding states
- attributable evidence
- deterministic failure handling
- predictable API behavior
- no secret leakage

Add targeted tests for every changed subsystem.

## PHASE 3 — CLI + GUI ALIGNMENT
Keep domain logic shared.

Verify that CLI and GUI agree on:
- run lifecycle
- session persistence
- findings
- validation/rejection
- tested URLs
- report generation
- errors

Implement missing GUI functionality from the UI/UX spec without duplicating core logic.

## PHASE 4 — UI/UX
Align the current UI with `UI_UX_CORRECTED.md`.

Prioritize:
- target/program selection
- scope visibility
- run configuration/start
- running state/live feed
- findings list/detail
- evidence
- validation/rejection status
- report/export
- previous sessions/runs
- loading/error/empty/success states

Never show fake data or status.

A security research tool must make clear what was tested, where, what evidence exists, whether a finding is validated, and what the next action is.

## PHASE 5 — TEST + HARDEN
Add automated tests for critical behavior.

Prioritize:
Core:
- scope validation
- session normalization
- finding normalization
- evidence handling
- report generation
- run state transitions

API:
- valid input
- invalid input
- missing session/artifact
- running/completed/failed states

CLI:
- expected invocation
- invalid input
- failure handling

UI:
- open dashboard
- configure target
- start run
- observe state
- inspect findings/evidence
- export report
- inspect previous session

Test failure paths too.

Never claim a test passed unless you executed it.

## PHASE 6 — DOC CONSISTENCY
Update stale docs so README, PRD, TDD, UI/UX, schemas, APIs, and startup instructions match reality.

Keep future hosted SaaS clearly separated from current local-first architecture.

## SECURITY
Only support authorized security research.

Do not implement credential theft, unauthorized access, access-control bypass, rate-limit evasion, or security-control bypass.

Do not hard-code secrets or expose them in logs, UI, reports, or commits.

## STRICT CHANGE RULES
Do NOT:
- rewrite the entire repo
- replace frameworks without explicit requirement
- introduce PostgreSQL/Supabase/Stripe/Redis/Firebase/hosted infrastructure into local-first phases
- delete user work
- force-reset git
- fabricate tests/results/screenshots
- claim controls exist when they do not

DO:
- inspect first
- preserve working behavior
- make small coherent changes
- test
- verify
- document
- report limitations honestly

## REQUIRED PHASE CYCLE
For every phase:
1. Inspect
2. Gap analysis
3. Implement
4. Test
5. Verify
6. Review for regressions
7. Document
8. Report

At the end of every phase report:
- files changed
- behavior changed
- tests run
- verification result
- known limitations
- remaining work
- suggested commit message

## FINAL RELEASE GATE
Before declaring complete, verify:
- PRD requirements map to implementation
- TDD matches actual code
- UI/UX matches actual UI
- schema/API mismatches are resolved
- CLI works
- GUI works
- run lifecycle is truthful
- findings are not falsely validated
- evidence is attributable
- scope is explicit
- secrets are protected
- error states work
- critical tests exist and run
- README instructions work
- no unnecessary SaaS infrastructure was introduced

Final report sections:
### IMPLEMENTED
### VERIFIED
### NOT VERIFIED
### KNOWN LIMITATIONS
### NEXT RECOMMENDED PHASE

Do not call the project production-ready unless evidence supports that claim.
