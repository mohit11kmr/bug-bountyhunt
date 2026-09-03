# Security Agent — Mozilla

HackerOne: https://hackerone.com/mozilla

## ⚠️ Program Rules (MANDATORY)

**Bounty Table:** Critical Sites: High $3,000–$6,000, Critical $6,000–$15,000. Core Sites: High $1,000–$3,000, Critical $3,000–$5,000. Critical vulns on out-of-scope assets: $500–$1,000. Domain takeovers on `*.mozilla.org`, `*.mozilla.com`, `*.mozilla.net`, `*.firefox.com`, `*.mozgcp.net`, `*.mozaws.net`: $100.

**Test Plan:**
- Test on staging/dev instances where specified (see per-target notes below), NOT production, to avoid disrupting users.
- Reflected XSS: affected URL + working payload. Stored XSS: step-by-step exploit process.
- Use `alert(document.domain)` in PoCs, never `alert(1)` or malicious payloads.
- No harmful/malicious payloads, especially for npm/pip package takeover reports.
- No automated/aggressive scanning of production services — use local/dev instances instead.

**Eligibility rules:**
- Bug must be original, unreported, and part of Mozilla's own code (third-party libs shipped in client code or third-party sites Mozilla uses also qualify).
- Do not access/modify/delete/store real user data — use your own test accounts.
- If you inadvertently touch user data, notify security@mozilla.org immediately and delete it.
- Firefox and Mozilla VPN *clients* are OUT of scope for this web bug bounty program — report via https://bugzilla.mozilla.org/form.client.bounty instead.
- Low/Medium severity reports are NOT bounty eligible (still may be fixed).
- No extortion/threats to withhold or publicly release issues.
- Follow HackerOne Code of Conduct + Mozilla Community Participation Guidelines.

**Response targets:** First response 5 business days, Triage 10 days, Bounty 30 days.

**Safe Harbor:** Gold Standard Safe Harbor policy is enabled.

Full policy (severity matrix, appeal process, disclosure policy): https://hackerone.com/mozilla

## ✅ IN Scope — Authorized targets (all 24 scopes eligible for submission)

| Target | Type | Notes |
|---|---|---|
| vpn.mozilla.org | URL | Backend server behind Mozilla VPN |
| support.mozilla.org | URL | **Test on staging only: support.allizom.org**. Src: github.com/mozilla/kitsune |
| www.mozilla.org | URL | Bedrock. **Test on staging: www.allizom.org**. Src: github.com/mozilla/bedrock |
| crash-reports.allizom.org | URL | Firefox crash report endpoint (staging). Src: github.com/mozilla-services/socorro |
| relay.firefox.com | URL | **Test on staging: relay.allizom.org**. Set header `X-HackerOne-Research`. Focus on APIs: mozilla.github.io/fx-private-relay/api_docs.html |
| crash-stats.allizom.org | URL | Crash report analytics (staging). Src: github.com/mozilla-services/socorro |
| aus5.mozilla.org | URL | Backend update system. No disruptive testing/scanning on production. Src: github.com/mozilla-releng/balrog |
| developer.mozilla.org | URL | MDN. **Intrusive/content-changing tests on staging: developer.allizom.org**. Src: github.com/mdn/mdn |
| monitor.mozilla.org | URL | Mozilla Monitor. Src: github.com/mozilla/blurts-server |
| bugzilla.mozilla.org | URL | No automated scanners; don't create/modify bugs. **Test on bugzilla-dev.allizom.org**. Src: github.com/mozilla-bteam/bmo |
| lando.services.mozilla.com | URL | + api.lando.services.mozilla.com, lando.moz.tools. **Test on dev/staging: ui.dev.lando.nonprod.cloudops.mozgcp.net, ui.stage.lando.nonprod.cloudops.mozgcp.net, api.dev.lando.nonprod.cloudops.mozgcp.net, api.stage.lando.nonprod.cloudops.mozgcp.net** |
| firefox-ci-tc.services.mozilla.com | URL | TaskCluster CI/CD. Src: github.com/taskcluster/taskcluster |
| Mozilla Ad Routing Service (MARS) | OTHER | ads.mozilla.org, ads-img.mozilla.org, contile.services.mozilla.com, spocs.getpocket.com, spocs.getpocket.dev, spocs.mozilla.net, spocs.allizom.net. **Test on staging: ads.allizom.org**. Src: github.com/mozilla-services/mars |
| Firefox Homepage Newtab | OTHER | client-api.getpocket.com, admin-api.getpocket.com, curation-admin-tools.readitlater.com. Don't add/modify prod data — use local instance. Src: github.com/Pocket/content-monorepo |
| accounts.firefox.com | URL | Mozilla Accounts. + api.accounts.firefox.com, oauth.accounts.firefox.com, profile.accounts.firefox.com, verifier.accounts.firefox.com, graphql.accounts.firefox.com, subscriptions.firefox.com. Src: github.com/mozilla/fxa |
| addons.allizom.org | URL | Firefox Addons **staging only, no production testing**. + services.addons.allizom.org, versioncheck-bg.addons.allizom.org, versioncheck.addons.allizom.org. Src: github.com/mozilla/addons-server |
| www.firefox.com | URL | Springfield marketing site (not the Firefox client). **Test on staging: www.springfield.moz.works**. Src: github.com/mozmeao/springfield |
| sync.services.mozilla.com | URL | Firefox Sync. + *.sync.services.mozilla.com, token.services.mozilla.com. Src: github.com/mozilla-services/syncstorage-rs, tokenlib |
| Product Delivery | OTHER | archive.mozilla.org, download.mozilla.org, download-installer.cdn.mozilla.net, treeherder.mozilla.org. **No automated scans**. Content intentionally public. Src: github.com/mozilla/treeherder |
| hg.mozilla.org | URL | Mercurial source hosting. Website vulns = Core Site; source-code vulns = Critical Site. Src: github.com/mozilla/version-control-tools |
| pontoon.allizom.org | URL | Localization service, **staging only, no production testing**. Src: github.com/mozilla/pontoon |
| phabricator.allizom.org | URL | **Test only on dev (phabricator-dev.allizom.org) or staging (phabricator.allizom.org)**. Src: github.com/mozilla-conduit/phabricator |
| merino.services.mozilla.com | URL | Firefox Suggest. **Test on staging: merino.services.allizom.org**. Src: github.com/mozilla-services/merino-py |
| firefox.settings.services.mozilla.com | URL | Remote Settings. + firefox-settings-attachments.cdn.mozilla.net. **Test on staging: firefox.settings.services.allizom.org/v1/** |

## 💰 Bounty eligible targets

All 24 targets above are bounty eligible (max severity: critical for every one).

## ❌ OUT of Scope — NEVER test these

- No out-of-scope structured scopes returned by the API for this program (all listed assets are in scope).
- Firefox and Mozilla VPN **client software** — out of scope for this web program; report separately at https://bugzilla.mozilla.org/form.client.bounty
- Production instances where a staging/dev instance is explicitly designated above — test staging/dev only for those targets.
- HackerOne's standard [Core Ineligible Findings](https://docs.hackerone.com/en/articles/8494488-core-ineligible-findings) and Mozilla's custom scope exclusions listed at https://hackerone.com/mozilla?type=team#scope_exclusions (not machine-readable via this API call — check the policy page directly before testing edge cases).

## Proxy

All curl requests MUST use: `-x http://localhost:8088 --proxy-insecure`

## Workflow

1. Always verify the target is IN scope before any request.
2. NEVER test OUT of scope targets — especially production instances flagged above as "staging only".
3. Prioritize bounty-eligible targets first (all 24 targets qualify — pick based on max_severity/impact).
4. Use curl with proxy AND user-agent for ALL requests.
5. Use available skills to analyze findings.

## ⛔ Submission Safety (MANDATORY)
NEVER call any HackerOne MCP tool that creates, modifies, or submits a report
(e.g. `submit_report`, `create_report_intent`, `submit_report_intent`,
`update_report_intent`, or any `mcp__hackerone__*`/`hackerone-mcp` write action) —
even if such a tool is available in this session's toolset. `/report` only writes
a local Markdown file under `reports/`. The human reviews it and submits manually
through the HackerOne web UI. This applies to every agent and subagent in this project.
