# Bugzilla (bugzilla.mozilla.org) — VERIFIED Recon Handoff

> Prepared: 2026-09-02 | All facts below are LIVE-VERIFIED via curl against the
> target today. No assumptions. In-scope, bounty-eligible, max severity critical.

## Why this target
- 24-year-old interactive web app (Perl/Bugzilla) — largest interactive attack
  surface among Mozilla's 21 in-scope targets. Auth, search, REST API, attachments.
- Different surface class vs Taskcluster (GraphQL read-only API that netted 0).

## Stack (verified)
- nginx + Varnish/Fastly CDN, HSTS max-age=31536000 includeSubDomains
- x-xss-protection: 1; mode=block, x-frame-options: SAMEORIGIN, x-content-type-options: nosniff

## REST API structure (verified live)
- `GET /rest/bug/<id>` → JSON; bug 58525 = accessible public (returns SeaMonkey bug w/ assigned_to_detail)
- `GET /rest/bug/1` → {"error":true,"code":101,"message":"Bug 1 does not exist."} — bug 1 properly gated
- `GET /rest/bug/1/attachment` → same code 101 (bug hidden → attachments also gated)
- `GET /rest/bug?keywords=csectype-uaf&include_fields=id,summary,groups` → anonymous search WORKS; returns security-keyworded bug summaries (BY DESIGN, public)
- `GET /rest/component?product=Firefox` → requires component param
- `GET /rest/product?type=accessible` → returned 502 transient (retry needed)
- REST doc: bmo.readthedocs.io/en/latest/api (bmo forks: products, flags differ from vanilla Bugzilla)

## HTML CGI endpoints (verified live, all 200)
- /login, /buglist.cgi, /show_bug.cgi, /enter_bug.cgi, /robots.txt
- `show_bug.cgi?id=1` → HTTP 200 but title "Missing Bug ID" (generic template, NO real bug content leak — verified)

## Verified NON-findings (do NOT re-report)
- Bug 1 access: properly gated both REST + HTML → no IDOR leak
- Anonymous search of security bugs: by-design public, not a vuln
- No stack/version disclosure beyond nginx

## Attack-surface notes for hunters (what to test, UNVERIFIED = hypothesis only)
- `enter_bug.cgi` — bug creation: hidden-field injection, group/component permissions on report creation
- `buglist.cgi` — query param injection (ORDER BY / SQLi attempt in legacy CGI path), saved search feature
- `/rest/bug` POST — create/update via API: field manipulation, group mutation, attachment tampering
- `/rest/attachment/<id>` — cross-user attachment access (classic IDOR) — test with a REAL public attachment id, not bug 1
- `/rest/user` — user lookup/email enumeration
- `/rest/flag` — flag/request assignment authz
- Legacy session cookies /login — session fixation, cookie flags
- Time-based blind SQLi in `buglist.cgi` params (legacy Perl DBAL is older)
- XML/JSON content-type parsing quirks (Bugzilla XMLRPC legacy)

## Program rules recap (from /load-program-h1 mozilla) — VERIFY before reporting
- ❌ Blind SSRF (out of scope) | ❌ Info/source disclosure (open source) | ❌ DoS/rate-limit
- ✅ IDOR, SQLi, RCE, auth bypass, path traversal, secret leak, non-blind SSRF

## Rate limits (MANDATORY)
- Max 2 req/sec per endpoint, sleep 0.5 between same-host curls, STOP on 429/503.
- Real Firefox User-Agent required. Proxy via localhost:8088.
