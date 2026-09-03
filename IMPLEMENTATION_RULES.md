# BountyGrimoire — IMPLEMENTATION_RULES.md

## 1. Purpose
This file is the implementation guardrail for the BountyGrimoire repository.

The current product is a local-first bug bounty research/workbench. The current code is the source of truth for existing behavior; the corrected PRD, TDD, and UI/UX specification define intended behavior.

Do not turn the project into a different product or silently convert it into a hosted SaaS.

## 2. Source-of-Truth Hierarchy
When sources conflict, use this order:
1. Explicit user instruction for the current task.
2. Existing working code and observed runtime behavior.
3. `PRD_CORRECTED.md`.
4. `TDD_CORRECTED.md`.
5. `UI_UX_CORRECTED.md`.
6. Older documentation that conflicts with the above.

When intentionally changing behavior, update the relevant docs and tests in the same change.

## 3. Preserve Existing Product
Do not delete, disable, rename, or replace working capabilities merely for simplification.

Preserve the existing CLI, GUI/dashboard, sessions, scope handling, storage artifacts, scripts, configuration conventions, orchestration, and report workflows unless the corrected docs explicitly require a behavior change.

Do not perform a full rewrite in another framework.

Do not introduce Next.js, React-only SPA architecture, PostgreSQL/Supabase, Stripe, Redis/BullMQ, Firebase, or hosted deployment infrastructure unless a future phase explicitly calls for it.

## 4. Current Product Boundary
Current target: a local-first bug bounty research/workbench.

It should remain primarily local, CLI-compatible, GUI-accessible through the existing local server, transparent about artifacts, and safe-by-default for authorized testing.

Future hosted SaaS architecture must remain a separate roadmap/architecture decision.

## 5. Security and Authorization
Only operate on targets the researcher is authorized to test.

Every run must have an explicit, human-readable target/scope definition.

Do not add features intended to bypass authorization, access controls, rate limits, authentication, or security controls.

Do not claim hard network-level enforcement when only instructions/policy exist. Clearly distinguish policy, application validation, and hard enforcement.

Never hard-code or expose API keys, tokens, passwords, cookies, credentials, or session secrets.

## 6. Finding Integrity
A model/agent suggestion is not automatically a vulnerability.

Keep clear states such as discovered/suspected/validated/rejected where supported.

A finding must retain relevant target, evidence, run/session context, and status. Never silently upgrade a suspected finding to validated.

## 7. Evidence Contract
Evidence should be reproducible, attributable to a run, sanitized when necessary, free of unnecessary secrets, deterministic, and linked to the originating action/target.

When changing evidence schemas, update all producers and consumers together.

Use one canonical representation for sessions, runs, findings, validated findings, tested URLs, and reports. If compatibility is needed, isolate it in a boundary adapter.

## 8. Session Schema
Before changing session persistence, inspect every reader and writer, report generation, GUI loading, and existing artifacts.

Do not assume older markdown documentation is more authoritative than the runtime code.

If multiple formats exist, select a canonical internal representation, add narrow compatibility handling if needed, and test it.

## 9. CLI + GUI Alignment
CLI and GUI are two interfaces over shared core behavior.

Do not duplicate domain/business logic.

Prefer shared functions, schemas, validation, normalization, and state handling.

When adding functionality, identify the shared core operation first, then expose it to CLI/GUI as appropriate.

## 10. API/Route Rules
Every GUI API endpoint needs a defined request/response shape, explicit invalid-input handling, sensible HTTP status codes, and safe error responses.

Do not expose secrets or unnecessary local filesystem details.

Do not create semantically duplicate endpoints.

## 11. UI/UX Rules
The UI must reflect real system state.

Never show validated/complete/ready unless the backend state proves it.

Never use fake metrics, fake findings, fake progress, or fake completion.

Important states include empty, ready, running, completed, failed, no findings, findings available, partial/incomplete, and invalid input.

The main researcher workflow should support target/program selection, scope inspection, run start, live state, findings review, evidence inspection, report/export, and previous session/run access.

## 12. Testing Rules
For every non-trivial change:
- run syntax/compile checks for changed Python files
- add targeted unit tests for changed logic
- add API tests for changed routes
- add schema/serialization tests for changed persistence
- run UI smoke tests for changed critical workflows where practical

Never claim tests passed unless actually run.

If a required dependency, DB, browser, network, or provider is unavailable, state that limitation.

## 13. Failure-Path Testing
Test relevant failure paths: invalid target/scope, missing session, malformed JSON, missing artifacts, process failure, timeout, duplicate run, partial results, no findings, rejected finding, interrupted run.

## 14. Documentation Rules
Update the smallest canonical document when behavior changes:
- product -> PRD
- architecture/API/schema -> TDD
- interaction/design -> UI/UX
- developer guardrails -> this file

Do not maintain conflicting duplicate specifications.

## 15. Change Discipline
For each phase:
1. inspect current code
2. state current behavior
3. identify exact gap
4. implement the smallest coherent change
5. add/update tests
6. run verification
7. update documentation
8. report changed files, tests, limitations, and a suggested commit message

Do not mix unrelated cleanup into feature work.

## 16. Git Discipline
Inspect git status before changes.

Do not force-reset, delete user work, rewrite history, or overwrite unrelated changes.

Never claim a commit/push occurred unless actually performed.

## 17. Dependency Discipline
Do not add dependencies without checking whether an existing dependency already provides the capability. Document why a new dependency is necessary.

Avoid broad upgrades during feature work.

## 18. No Fake Completion
Files being created, code looking plausible, or type checks passing do not equal feature completion.

Completion requires behavior-level verification appropriate to the change.

## 19. Definition of Done
A phase is complete only when:
- implementation matches corrected docs
- existing functionality is preserved
- changed behavior has tests/verification
- changed APIs/schemas are consistent
- UI accurately reflects backend state
- security assumptions are documented accurately
- docs are updated
- verification results are honestly reported

## 20. Hosted SaaS Boundary
Do not implement hosted SaaS infrastructure during local-first phases.

A future hosted phase must separately define tenancy, auth, database, job queue, secrets, network isolation, billing, observability, deployment, and migration architecture.

## 21. Default Behavior
When uncertain: inspect before changing, preserve before replacing, verify before claiming, document before assuming, and choose the smallest safe implementation.
