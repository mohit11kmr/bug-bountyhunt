# Mozilla — Taskcluster (firefox-ci-tc) BountyGrimoire Recon Handoff

> Prepared: 2026-09-02 | Authorized in-scope target verified via HackerOne API
> Target: https://firefox-ci-tc.services.mozilla.com/ (bounty=TRUE, max_severity=critical)

## Why this target
- $12k unauthenticated RCE was disclosed here on 2026-08-05 (report 3782701):
  "Unauthenticated RCE in Taskcluster web-server via GraphQL filter argument (sift $where)"
  → Taskcluster's **GraphQL layer is the known high-value attack surface**.
- 51 GraphQL query fields enumerated (full introspection enabled below).

## Verified facts (already collected, do NOT redo)
- Stack: Fastly CDN, nginx/openresty, Varnish (x-cache MISS/MISS), HSTS on.
- GraphQL endpoint: `POST /graphql` — full introspection ENABLED.
- Anonymous session confirmed: `{isLoggedIn}` → `false`.
- Anonymous `currentScopes` (what anonymous is authorized for):
  assume:anonymous, auth:current-scopes, auth:expand-scopes,
  auth:get-client:*, auth:get-role:*, auth:list-roles,
  github:get-badge:*, github:get-repository:*, github:latest-status:*,
  github:list-builds, hooks:get:*, hooks:list-hooks:*, hooks:list-last-fires:*,
  hooks:status:*, index:find-task:*, index:list-namespaces:*, index:list-tasks:*,
  purge-cache:all-p... (truncated — pull full via `{currentScopes}`)

## KEY FINDING 1 — Role namespace fully enumerable anonymously
`query { listRoleIds { edges { node { roleId } } } }`
Returns entire Taskcluster role directory, including:
- `github-team:MozillaSecurity/tc-admin`  ← admin team role name exposed
- `workerType: gecko-t/win11-64-24h2-alpha`
- `hook-id:git-push/mozilla/{firefox-dev, enterprise-firefox-try}/*`
- `hook-id:hg-push/{autoland, mozilla-central, comm-central, birch, cedar, ash, comm-*}/*`

`auth:list-roles` + `auth:get-role:*` are BOTH anonymously granted → test whether
anonymous can read an arbitrary role's `expandedScopes` (access-control / config leak).

## KEY FINDING 2 — GraphQL query fields (51) mapped
Query fields (all with args): root, artifact(runId), latestArtifact, getCredentials,
isLoggedIn, cachePurges, clients(clientOptions/searchTerm), client(clientId),
githubRepository(owner,repo), renderTaskclusterYml(payload), hookGroups/hooks/hook/hookStatus/
hookLastFires, taskNamespace, namespaces, listDenylistAddresses(searchTerm), provisioner(s),
roles(searchTerm), listRoleIds(searchTerm), role(roleId), currentScopes, expandScopes(scopes),
secrets(searchTerm), secret(name), status(taskId), task(taskId), dependentTasks,
dependents(taskId), indexedTask(indexPath), tasks(taskIds), taskGroup, taskActions,
listPendingTasks(listClaimedTasks), WorkerManager*(workerPoolId...), workerType,
pendingTasks, workerTypes, worker, workers.

Interesting for HIGH-bug classes:
- `getCredentials()` — credential object (subfield selection required) — authz test
- `secret(name)` — secrets object — SSRF/config-leak test (do NOT dump real secrets)
- `expandScopes(scopes)` — scope expansion — SSRF/authz test
- `task(taskId)` / `tasks(taskIds)` — IDOR potential (task artifacts)
- `client(clientId)` — IDOR (Client type: clientId, expires, lastDateUsed,
  lastRotated, scopes, expandedScopes, disabled, deleteOnExpiration)
- `role(roleId)` — IDOR (Role type: roleId, scopes, expandedScopes, created,
  lastModified, description)

## Example valid GraphQL queries (works, tested)
- `query { role(roleId: "anonymous") { roleId expandedScopes } }`
- `query { listRoleIds { edges { node { roleId } } } }`
- Introspect type: `query { __type(name:"Role") { fields { name } } }`

## Predatory attack-surface notes (BountyGrimoire hunters should focus)
1. **Access-control / IDOR**: anonymous `auth:get-client:*` + `auth:get-role:*` →
   test `role(roleId:...)` and `client(clientId:...)` for arbitrary object read.
   Read-only disclosure of scopes/tokens — likely Medium/High if sensitive.
2. **SSRF**: `renderTaskclusterYml(payload)` / `expandScopes` / hook fetch paths —
   test whether a malicious payload can trigger server-side fetch. (Blind SSRF is
   OUT of scope per program policy; only demonstrable/non-blind counts.)
3. **Secrets leak**: `secret(name)` — verify authorization enforcement. DO NOT
   exfiltrate real secrets; just prove unauthorized read to demonstrate impact.
4. **IDOR artifacts**: `artifact(taskId,runId)` / `task(taskId)` — test cross-tenant
   access to other pipelines' artifacts (worker secrets often stored as artifacts).

## Program exclusion rules (VERIFY before reporting)
- ❌ Blind SSRF — OUT of scope
- ❌ Information disclosure / source disclosure (open source) — OUT
- ❌ Stored XSS/HTML injection requiring admin/privileged access — OUT
- ❌ DoS / rate-limit issues — OUT
- ❌ Firefox/VPN client bugs — go to bugzilla form, not here
- ✅ IDOR, SQLi, RCE, non-blind SSRF, auth bypass, path traversal, secret leak, etc.

## Tooling / rate limits (MANDATORY)
- Max 2 req/sec per endpoint, `sleep 0.5` between same-host curls,
  stop on 429/503. User-Agent must be a real Firefox UA.
- Use proxy if configured; all curl per /hunt rules.

## Next step for hunter
Start with the access-control test (Finding 1): can anonymous read an arbitrary
role/client expandedScopes? That's the cleanest HIGH candidate. Then artifact IDOR.
