# PRD: AI Security Scanner SaaS

**Product Name:** SecScan AI
**Version:** 1.2 — see note below
**Date:** September 3, 2026
**Author:** Mohit Kumar
**Status:** Draft

> **Note (v1.2):** v1.1 fixed two internal-consistency bugs (§9 vs §1.5's
> targets; §6.3's competitor-savings math) and added a bridging note tying
> the scanning engine to BountyGrimoire (see [TDD.md](./TDD.md)). This
> revision fills in the gaps a completeness review flagged: legal/compliance,
> SLA, onboarding, support, MVP scope boundary, market validation, unit
> economics, a real feature-comparison table, a feedback mechanism, a
> rollback plan, and a Phase 2+ nice-to-have list (§§10–18). None of this
> changes the product vision from v1.0/1.1 — it fills in what was missing
> around it, and is honest about what's a plan vs. what's actually been done
> (mostly: none of §§10–18 has been executed yet, this is all still Draft).

---

## 1. Executive Summary

### 1.1 Product Overview
SecScan AI is an automated security scanning platform that uses AI to identify vulnerabilities in websites and APIs. It provides continuous monitoring, detailed reports, and actionable recommendations — making enterprise-grade security accessible to small businesses and developers at an affordable price. Under the hood, the scanning is done by BountyGrimoire's AI agents (Claude Code / opencode), not a traditional signature-based scanner — see TDD.md §1.

### 1.2 Problem Statement
- **68%** of small businesses lack dedicated security teams
- **Manual penetration testing** costs $5,000-$50,000 per engagement
- **Existing tools** are either too complex (Nuclei, Burp Suite) or too expensive (Enterprise scanners)
- **Small businesses** need affordable, automated security monitoring

### 1.3 Solution
A SaaS platform that:
- Automates security scanning with AI-powered analysis
- Generates human-readable reports (no security expertise required)
- Provides continuous monitoring (not one-time scans)
- Costs 90% less than manual penetration testing

### 1.4 Target Market
| Segment | Size | Pain Point |
|---------|------|------------|
| Small businesses (1-50 employees) | 33M+ in US | No security team, can't afford consultants |
| Freelance developers | 2M+ in US | Need to secure client websites |
| SaaS startups | 500K+ globally | Compliance requirements, limited budget |
| E-commerce stores | 2M+ in US | PCI compliance, customer data protection |

### 1.5 Success Metrics

| Metric | Target (6 months) | Target (12 months) |
|--------|-------------------|-------------------|
| Registered users | 1,000 | 5,000 |
| Paying customers | 100 | 500 |
| Monthly Recurring Revenue | $5,000 | $25,000 |
| Customer Acquisition Cost | <$50 | <$30 |
| Churn rate | <8% | <5% |
| Net Promoter Score | >40 | >50 |

### 1.6 Technical Implementation

For the detailed technical architecture, see **TDD.md §1** (what exists
today) and **TDD.md §1.4** (the hosted-SaaS folder structure this would
grow into, *once* §11.3's hosted phase is actually built — not yet).
Keeping the same "today vs. future" split TDD.md uses throughout, rather
than restating §1.4's future plan as flat present-tense fact:

**Today (this repo, verified working):**
- **Scanning engine**: BountyGrimoire's 17 AI-powered vulnerability hunters (`.claude/skills/find-*/`), orchestrated via Claude Code / opencode — TDD.md §1.1
- **Dashboard**: `gui/server.py` (Python stdlib) + `gui/index.html` (plain HTML/CSS/JS), no framework, `127.0.0.1`-only — TDD.md §1.3, §4
- **Storage**: local JSON files, no database — TDD.md §2
- **Auth / Billing**: none — single local operator, no monetization layer yet — TDD.md §1.3, §11.2

**Future, once this becomes a hosted product (TDD.md §1.4, §11.3 — not built):**
- **Architecture**: backend/frontend separation (`backend/api/` + `backend/scanner/` | `frontend/`)
- **Backend**: Auth (Supabase, planned), Billing (Stripe, planned), Scanner (BountyGrimoire, copied in), Database (PostgreSQL, planned)
- **Frontend**: Next.js dashboard (planned — replaces today's plain HTML/JS)
- **Deployment**: Docker containers, CI/CD pipeline (planned — TDD.md §12, §13)

---

## 2. User Personas

### 2.1 Primary: Small Business Owner
**Name:** Priya, 35, E-commerce Store Owner
- **Goal:** Protect customer data, avoid data breaches
- **Frustration:** Can't afford $10K+ for security audit
- **Behavior:** Checks dashboard weekly, acts on critical alerts
- **Willingness to pay:** $49-$99/month

### 2.2 Secondary: Freelance Developer
**Name:** Rahul, 28, Full-Stack Developer
- **Goal:** Deliver secure websites to clients
- **Frustration:** Manual security testing takes too long
- **Behavior:** Runs scans before project delivery
- **Willingness to pay:** $29-$49/month

### 2.3 Tertiary: Startup CTO
**Name:** Sarah, 32, CTO at Series A Startup
- **Goal:** Maintain compliance, protect user data
- **Frustration:** Engineering time too valuable for manual security
- **Behavior:** Runs weekly scans, monitors dashboard daily
- **Willingness to pay:** $99-$299/month

---

## 3. Feature Requirements

### 3.0 MVP Scope Boundary

The P0/P1 tags in §3.1 imply a boundary but never state it explicitly — this
is that explicit line. Anything not listed as **In MVP** below is out,
regardless of what a table elsewhere marks P1, until Phase 2:

**In MVP (must work before first paying customer):**
- Email/password auth (US-001, US-003) — Google OAuth (US-002) is *not* MVP, it's the first Phase 2 addition
- Quick Scan + Full Scan (not API Scan — API-specific testing is Phase 2)
- Executive Summary + Detailed Findings + Remediation Steps + Risk Scoring (not PDF Export — HTML/in-app report is enough for MVP)
- Scan History + Real-time Status + Vulnerability Summary (not Alert Notifications — no email/SMS infra needed for MVP)
- Subscription Management (Stripe checkout) + Usage Tracking
- Free + Starter + Pro tiers only — Enterprise tier (custom integrations, dedicated support) is sold manually, not self-serve, until there's a real Enterprise customer asking for it

**Explicitly not MVP** (all of §3.2 and §3.3): team management, integrations (Slack/GitHub/webhooks), custom scan rules, authenticated/internal-network scanning, compliance reports, threat intelligence. These are listed for direction, not commitment.

**Why this boundary matters:** every P1 item deferred out of MVP removes a
dependency (SMS provider, PDF renderer, OAuth app registration) that would
otherwise block launch for a feature that isn't load-bearing for the core
"scan → report → act" loop.

### 3.1 Core Features (MVP - Phase 1)

#### 3.1.1 Automated Security Scanning
| Feature | Priority | Description |
|---------|----------|-------------|
| **Quick Scan** | P0 | Basic vulnerability scan (5-10 minutes) |
| **Full Scan** | P0 | Comprehensive scan with subdomains (15-30 minutes) |
| **API Scan** | P1 | API-specific vulnerability testing |
| **Scheduled Scans** | P1 | Daily/weekly/monthly automated scans |

**Scan Capabilities** — one BountyGrimoire hunter skill per row (`.claude/skills/find-*/`; see TDD.md §1.1):
- SQL Injection (`find-sqli`)
- Cross-Site Scripting — reflected, stored, DOM (`find-xss`)
- IDOR / broken object-level auth (`find-idor`)
- SSRF (`find-ssrf`)
- Auth/session bypass, MFA bypass (`find-auth`, `find-otp`)
- RCE, command/template injection (`find-rce`, `find-ssti`)
- XXE (`find-xxe`)
- Exposed secrets/credentials, sensitive files (`find-secrets`)
- PII exposure (`find-pii`)
- Business-logic flaws — price manipulation, race conditions (`find-bizlogic`)
- Open redirect / callback hijacking (`find-callback`)
- ID/user enumeration (`find-enumerable`)
- Misconfigurations — CORS, exposed admin panels (`find-insecure`)
- Referer-header data leakage (`find-referer`)
- Checksum/signature bypass (`find-checksum`)

*Not currently covered by a BountyGrimoire skill (would need new work, not just wiring): SSL/TLS certificate/cipher auditing, outdated-software/CVE version fingerprinting. Both are good candidates for an 18th/19th skill rather than a separate scanner dependency.*

#### 3.1.2 AI-Powered Reports
| Feature | Priority | Description |
|---------|----------|-------------|
| **Executive Summary** | P0 | High-level overview for non-technical users |
| **Detailed Findings** | P0 | Technical details for developers |
| **Remediation Steps** | P0 | Step-by-step fix instructions |
| **Risk Scoring** | P0 | CVSS-based severity ratings |
| **PDF Export** | P1 | Downloadable reports |

#### 3.1.3 User Dashboard
| Feature | Priority | Description |
|---------|----------|-------------|
| **Scan History** | P0 | List of all past scans |
| **Real-time Status** | P0 | Live scan progress |
| **Vulnerability Summary** | P0 | Charts and metrics |
| **Alert Notifications** | P1 | Email/SMS for critical findings |

#### 3.1.4 Authentication & Billing
| Feature | Priority | Description |
|---------|----------|-------------|
| **Email/Password Auth** | P0 | Basic authentication |
| **Google OAuth** | P1 | Social login |
| **Subscription Management** | P0 | Stripe integration |
| **Usage Tracking** | P0 | Scan limits per plan |

### 3.2 Enhanced Features (Phase 2)

#### 3.2.1 Team Management
- Multi-user accounts
- Role-based access control (Admin, Viewer, Scanner)
- Audit logs

#### 3.2.2 Integrations
- Slack notifications
- GitHub integration (scan repos)
- Webhook support
- API access for custom integrations

#### 3.2.3 Advanced Scanning
- Custom scan rules
- Whitelisting/blacklisting paths
- Authenticated scanning (login required)
- Internal network scanning

### 3.3 Premium Features (Phase 3)

#### 3.3.1 Compliance Reports
- PCI DSS compliance check
- GDPR data exposure scan
- HIPAA security assessment
- SOC 2 preparation

#### 3.3.2 Threat Intelligence
- Dark web monitoring
- Brand monitoring
- Credential leak detection

---

## 4. User Stories

### 4.1 Epic: User Registration & Authentication

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-001 | As a user, I want to sign up with email/password | - Email verification required<br>- Password min 8 chars<br>- Duplicate email rejection |
| US-002 | As a user, I want to sign in with Google | - One-click OAuth flow<br>- Account linking if email exists |
| US-003 | As a user, I want to reset my password | - Email with reset link<br>- Link expires in 24 hours<br>- Password update confirmation |

### 4.2 Epic: Subscription & Billing

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-004 | As a user, I want to view pricing plans | - Clear plan comparison<br>- Feature list per plan<br>- Price display |
| US-005 | As a user, I want to subscribe to a plan | - Stripe checkout integration<br>- Plan selection<br>- Payment confirmation |
| US-006 | As a user, I want to manage my subscription | - Upgrade/downgrade<br>- Cancel subscription<br>- View billing history |
| US-007 | As a user, I want to see my scan usage | - Current usage vs limit<br>- Reset date<br>- Overage warnings |

### 4.3 Epic: Security Scanning

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-008 | As a user, I want to start a quick scan | - URL input validation<br>- Scan initiation<br>- Progress indicator |
| US-009 | As a user, I want to run a full scan | - Subdomain enumeration<br>- Comprehensive testing<br>- Estimated time display |
| US-010 | As a user, I want to schedule recurring scans | - Frequency selection (daily/weekly/monthly)<br>- Email notifications<br>- Auto-execution |
| US-011 | As a user, I want to see scan progress | - Real-time updates<br>- Current phase display<br>- Time remaining estimate |

### 4.4 Epic: Reports & Analytics

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-012 | As a user, I want to view scan results | - Vulnerability list<br>- Severity indicators<br>- Affected URLs |
| US-013 | As a user, I want an executive summary | - Risk score<br>- Top findings<br>- Recommendations |
| US-014 | As a user, I want detailed technical reports | - CVE references<br>- Proof of concept<br>- Fix instructions |
| US-015 | As a user, I want to export reports as PDF | - Professional formatting<br>- Company branding option<br>- Download link |

---

## 5. Non-Functional Requirements

### 5.1 Performance
| Metric | Requirement |
|--------|-------------|
| Page load time | <2 seconds |
| API response time | <500ms (p95) |
| Scan initiation | <5 seconds |
| Report generation | <30 seconds |
| Uptime | 99.9% |

### 5.2 Security
| Requirement | Implementation |
|-------------|---------------|
| Data encryption | AES-256 at rest, TLS 1.3 in transit |
| Authentication | JWT with secure cookie storage |
| API security | Rate limiting, input validation |
| Vulnerability scanning | OWASP Top 10 compliance |
| Data retention | 90 days for scan results |

### 5.3 Scalability
| Metric | Target |
|--------|--------|
| Concurrent users | 1,000+ |
| Concurrent scans | 100+ |
| Database size | 100GB+ |
| Monthly scans | 50,000+ |

### 5.4 Compliance
- GDPR compliant (data processing, right to deletion)
- SOC 2 Type II (planned for Phase 2)
- PCI DSS (planned for Phase 3)

*Expanded into a full legal/compliance plan — see §10.*

---

## 6. Pricing Strategy

### 6.1 Pricing Tiers

| Plan | Price | Scans/Month | Features |
|------|-------|-------------|----------|
| **Free** | $0 | 3 | Basic scan, 7-day retention |
| **Starter** | $29/month | 10 | Full scan, 30-day retention, PDF export |
| **Pro** | $79/month | 50 | All features, API access, scheduled scans |
| **Enterprise** | $199/month | Unlimited | Custom integrations, SLA, dedicated support |

### 6.2 Pricing Justification
- **Free tier:** User acquisition, lead generation
- **Starter:** Small businesses, freelancers
- **Pro:** Growing startups, agencies
- **Enterprise:** Larger companies, compliance needs

### 6.3 Competitive Analysis — Price

*Comparisons below use our Pro plan ($79/month) — our flagship tier and the one modeled in the revenue projections (see TDD §10.2).*

| Competitor | Price | Our Advantage |
|------------|-------|---------------|
| Nessus Professional | $3,490/year (~$291/month) | ~73% cheaper (Pro); up to 90% cheaper (Starter, $29/month) |
| Qualys | $500+/month | ~84% cheaper (Pro) |
| Burp Suite Pro | $449/year | No automation, manual |
| PentestPilot | $99/month | More features, better UX |

### 6.4 Competitive Analysis — Features

Price alone doesn't say *why* someone switches. This is the honest version,
including where competitors currently beat us:

| Capability | SecScan AI (MVP) | Nessus | Qualys | Burp Suite Pro | PentestPilot |
|---|---|---|---|---|---|
| AI-written, plain-language reports | ✅ | ❌ | ❌ | ❌ | Partial |
| No-install, browser-only workflow | ✅ | ❌ (desktop/appliance) | ✅ | ❌ (desktop app) | ✅ |
| Continuous/scheduled scanning | Phase 1 (P1) | ✅ | ✅ | ❌ (manual) | ✅ |
| Authenticated/internal-network scanning | ❌ (Phase 2) | ✅ | ✅ | ✅ | Partial |
| Compliance reports (PCI/GDPR/HIPAA) | ❌ (Phase 3) | ✅ (mature) | ✅ (mature) | ❌ | Partial |
| CVE/version-fingerprint database | ❌ (see §3.1 gap note) | ✅ (extensive) | ✅ (extensive) | Partial | Partial |
| Team management / RBAC | ❌ (Phase 2) | ✅ | ✅ | ✅ | ✅ |
| Price transparency (self-serve checkout) | ✅ | ❌ (sales call) | ❌ (sales call) | ✅ | ✅ |

**Honest read:** we win on AI-report readability, self-serve pricing, and
zero-install UX. We lose on depth (no CVE database, no authenticated/internal
scanning, no compliance reports) until Phase 2/3 ship. The pitch for MVP is
explicitly "good enough coverage at 10x lower cost and effort," not
"replaces Nessus/Qualys feature-for-feature" — overselling that in
marketing would set up exactly the churn §8's risk table already flags.

---

## 7. Go-to-Market Strategy

### 7.1 Launch Plan

| Phase | Duration | Activities |
|-------|----------|------------|
| **Pre-launch** | 2 weeks | Landing page, email list, social media |
| **Beta** | 4 weeks | Invite-only beta, feedback collection |
| **Launch** | 1 week | ProductHunt, Hacker News, Reddit |
| **Growth** | Ongoing | Content marketing, SEO, partnerships |

### 7.2 Marketing Channels

| Channel | Strategy | Budget |
|---------|----------|--------|
| ProductHunt | Launch day push | $0 |
| Reddit | r/bugbounty, r/SaaS, r/webdev | $0 |
| Twitter/X | Build in public | $0 |
| SEO | Blog content, tutorials | $200/month |
| Paid Ads | Google, LinkedIn | $500/month |
| Partnerships | Hosting companies, agencies | Revenue share |

### 7.3 Sales Funnel

```
Visitor → Sign Up (Free) → First Scan → Upgrade to Paid → Retention
   ↓           ↓              ↓              ↓              ↓
  100%        10%            5%             2%            80%
```

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Low initial adoption | High | High | Free tier, content marketing |
| High competition | Medium | Medium | Focus on UX, AI reports |
| Technical complexity | Medium | High | Build on BountyGrimoire's already-working 17-skill engine (TDD.md §1.1) rather than a new scanner from scratch; the two real gaps it doesn't cover yet (SSL/TLS auditing, CVE/version fingerprinting — §3.1) are scoped as new skills, not a new subsystem |
| Security breach | Low | Critical | Regular audits, bug bounty |
| Cost overruns | Medium | Medium | Free tiers, conservative spending |

*What to actually do if one of these materializes is now written down — see §17 (Rollback & Contingency Plan) instead of leaving it as an abstract "mitigation" column.*

---

## 9. Success Criteria

*Aligned with the §1.5 Success Metrics table — these were previously inconsistent (this section showed 4-5x higher targets than §1.5 for the same time horizons); numbers below now match §1.5 exactly at the 6- and 12-month marks, with a Month 1 launch milestone interpolated from the 6-month target.*

### 9.1 Launch Success (Month 1)
- [ ] 100+ registered users
- [ ] 15+ paying customers
- [ ] $500+ MRR
- [ ] <8% churn rate
- [ ] 4.0+ star rating

### 9.2 Growth Success (Month 6)
- [ ] 1,000+ registered users
- [ ] 100+ paying customers
- [ ] $5,000+ MRR
- [ ] <8% churn rate
- [ ] 2+ enterprise customers

### 9.3 Scale Success (Month 12)
- [ ] 5,000+ registered users
- [ ] 500+ paying customers
- [ ] $25,000+ MRR
- [ ] <5% churn rate
- [ ] 10+ enterprise customers
- [ ] Series A ready

---

## 10. Legal & Compliance

**Status: not drafted. This is the single largest blocker to actually
launching** — none of §§10.1–10.3 below is real legal text, and nothing
here should be treated as legal advice. A licensed attorney needs to review
all of it before signup is public.

### 10.1 Required Documents Before Launch

| Document | Why it's non-negotiable |
|----------|--------------------------|
| **Terms of Service** | Must include an explicit **authorization clause**: the user attests they own the target or have documented permission to scan it. Without this, SecScan AI facilitating a scan of an unauthorized third-party target creates real legal exposure (unauthorized-access laws like the US CFAA apply to the *target being scanned*, not just to who clicks "start") |
| **Privacy Policy** | What's collected (email, target URLs, scan results, IP address), retention (90 days per §5.2), which sub-processors see it (AI provider, payment processor, hosting — see TDD.md §11.3 for what those will actually be once built) |
| **Acceptable Use Policy** | No scanning targets without authorization; no using findings for extortion; account suspension terms |
| **DPA (Data Processing Agreement)** template | Needed for any EU customer subject to GDPR before they'll sign up as a business customer |

### 10.2 GDPR Specifics
- **Right to access / right to deletion**: user can request their account + all scan data be deleted; needs an actual deletion path (not just marking a row inactive) once a real database exists (TDD.md §2.3)
- **Data residency**: EU customers may require EU-hosted data — a real constraint on hosting choice once TDD.md §11.3 (hosted infra) is built, not something to bolt on after
- **Breach notification**: 72-hour notification requirement to affected users if scan data or credentials are exposed — ties directly into the Incident Response section of TDD.md (§19 there)

### 10.3 Compliance Roadmap (unchanged from §5.4, referenced here for completeness)
- GDPR compliant at launch (data processing, right to deletion) — **required**, not optional, given §10.2
- SOC 2 Type II — Phase 2, needed before larger customers (Sarah-persona, §2.3) will sign
- PCI DSS — Phase 3; note we likely never *directly* handle card data if payments route through Stripe Checkout, which narrows PCI scope significantly — confirm this with counsel rather than assuming it

---

## 11. Service Level Agreement (SLA)

| Tier | Uptime commitment | Support response time | Compensation if breached |
|------|--------------------|------------------------|---------------------------|
| Free | Best-effort, no SLA | No SLA | None |
| Starter | Best-effort, no SLA | 48 business hours (email) | None |
| Pro | 99.5% monthly | 24 business hours (email) | 10% monthly credit per 0.5% below target |
| Enterprise | 99.9% monthly | 4 hours (email + phone), 24/7 for Critical/Sev-1 | 25% monthly credit per 0.1% below target, capped at 100% |

- **Uptime definition**: dashboard + scan-initiation API reachable; a scan
  taking longer than its estimated window doesn't itself count as downtime
  unless the scan-start API is unreachable.
- **Exclusions**: scheduled maintenance (announced 48h ahead), and outages
  caused by a third-party dependency (AI provider, hosting) outside our
  control, are excluded from the uptime calculation but should still be
  status-paged (see TDD.md §19 Incident Response).
- SLA credits apply to future invoices only, no cash refunds — standard
  SaaS practice, keeps this from becoming a support-ticket revenue drain.

---

## 12. Onboarding Flow

Maps directly onto the sales funnel already in §7.3 (Visitor → Sign Up →
First Scan → Upgrade → Retention) — this is what happens at each step:

1. **Sign up** (US-001/US-002) → immediate email verification link.
2. **Welcome screen** (first login only): one sentence on what SecScan AI
   does, one clear CTA — "Scan your first site" — no multi-step product
   tour that delays getting to value.
3. **First scan prompt**: URL input pre-focused, Quick Scan pre-selected
   (not Full Scan — faster time-to-first-result matters more for a brand
   new user than comprehensiveness).
4. **Scan-in-progress**: real-time status (US-011) with a plain-language
   description of what's happening ("checking for exposed files...",
   "testing for injection points...") rather than a bare progress bar —
   this is the moment a non-technical persona (Priya, §2.1) decides
   whether the tool feels trustworthy.
5. **First results**: Executive Summary shown first, not the raw
   vulnerability list — leads with "here's your risk level," not a wall of
   findings that overwhelms a non-security-expert user.
6. **Upgrade prompt**: shown only after the value is demonstrated (post-first-scan), not before — pricing page visible from Free tier's scan-limit banner (§3.1.4 Usage Tracking), never a hard paywall blocking the first scan itself.
7. **Empty states matter**: before the first scan, Scan History (§3.1.3) shows a single "Run your first scan" CTA, not a blank table — a blank data table reads as broken, not as "you haven't done anything yet."

**Gap this closes**: US-008 through US-011 already specify the scanning
mechanics, but nothing previously described the *sequence* a brand-new
user moves through, which is what actually determines the 10%→5% dropoff
in §7.3's funnel.

---

## 13. Customer Support Plan

| Tier | Channels | Response time (ties to §11 SLA) | Notes |
|------|----------|-----------------------------------|-------|
| Free | Knowledge base + community forum only | N/A | No direct support — keeps support cost near-zero on a $0 tier |
| Starter | Email | 48 business hours | |
| Pro | Email + in-app chat | 24 business hours | |
| Enterprise | Email + chat + phone, 24/7 for Sev-1 | 4 hours | Dedicated point of contact |

**Knowledge base — minimum viable topic list at launch:**
- "How do I know if I'm authorized to scan a target?" (ties directly to §10.1's ToS clause — this will be the single most common pre-scan question)
- Reading your first report (executive summary vs. detailed findings)
- Understanding severity ratings (CVSS primer, plain language)
- Fixing the top 5 most common findings (one short guide each: exposed `.env`, missing security headers, outdated TLS, reflected XSS, open S3-style bucket)
- Billing: upgrade/downgrade/cancel

**Escalation path**: in-app chat (Pro+) → email queue if unresolved in one
exchange → engineering on-call only for confirmed product bugs (not "the
scan says my site has a vuln and I disagree" — that's a knowledge-base/
false-positive-report flow, not an incident).

**False-positive reporting**: needs its own lightweight path (a button on
each finding: "Report as false positive") — for an AI-generated report,
this is both a support-load reducer and a data source for improving the
underlying skills (BountyGrimoire's `/update-skills` mechanism, TDD.md
§1.1, already exists for exactly this kind of feedback loop on the
scanning side).

---

## 14. Market Validation Evidence

**Status: none gathered yet.** This is worth stating plainly rather than
implying validation that doesn't exist — §1.2's "68% of small businesses
lack a security team" and the market-size figures in §1.4 are industry
statistics, not evidence that *this specific product* solves the problem
in a way people will pay for. §8's Risk Assessment already flags "Low
initial adoption: High probability" — that risk exists precisely because
this section is empty today.

### 14.1 Validation Plan (before spending the §7.2 marketing budget)

1. **10–20 structured interviews** with people matching the three personas
   (§2) — not asking "would you use this" (people say yes to be nice), but
   "walk me through the last time you worried about your site's security"
   and "what did you actually do about it."
2. **Landing page + waitlist**, pre-launch (§7.1) — real signal is
   waitlist→beta conversion rate, not raw signup count.
3. **20–50 person beta cohort** (§7.1's Beta phase) actually using the
   product on real targets before public launch — track whether they run
   a *second* scan unprompted (the strongest available signal of real
   value, stronger than a survey response).
4. **Gate on results, not on the calendar**: don't move from Beta to public
   Launch (§7.1) on the 4-week timer alone if the beta cohort isn't
   showing repeat usage — extend Beta rather than launching into paid
   marketing spend against unvalidated demand.

### 14.2 Kill/pivot signal
If the beta cohort's repeat-scan rate is under 20% after the 4-week Beta
phase, that's a product-market-fit problem paid marketing spend won't fix
— see §17 (Rollback & Contingency Plan) for what happens next.

---

## 15. Unit Economics

Building on the CAC targets already in §1.5 (<$50 at 6mo, <$30 at 12mo),
using the Pro plan ($79/month, §6.1) as the reference price point:

| Metric | Formula | Value (at 12-month CAC target) |
|--------|---------|----------------------------------|
| ARPU (Pro) | plan price | $79/month |
| Target churn (12mo) | from §1.5 | <5%/month |
| Implied avg. customer lifetime | 1 / churn rate | ~20 months (at 5% churn) |
| Customer Lifetime Value (CLV) | ARPU × lifetime | ~$1,580 (revenue, not profit — no cost deduction yet) |
| CAC (target) | from §1.5 | <$30 |
| **LTV:CAC ratio** | CLV / CAC | **~53:1** |
| Payback period | CAC / ARPU | **<1 month** |

**This ratio is almost certainly too good to be real** — a healthy SaaS
LTV:CAC target is commonly cited around 3:1; 53:1 signals the CAC target
in §1.5 is aspirational, not measured (consistent with §14's "no market
validation yet"). Once real acquisition spend and actual churn data exist
post-launch (§9.1), recompute this with the **real** CAC, and expect it to
land far closer to industry-typical ratios. Treat the 53:1 figure as "this
is the upside case if the CAC target holds," not a number to put in front
of an investor as-is (§8's "Cost overruns" risk becomes far more likely if
real CAC is even 3-4x the target — still profitable, but a very different
story than 53:1).

**What's still missing to make this rigorous**: gross margin per customer
(AI token cost per scan × scans/month, from TDD.md §10, isn't yet
subtracted from ARPU here), and a blended CAC/CLV across all four pricing
tiers rather than Pro-only (§6.3's revenue projection has the same
Pro-only-modeling gap, noted there).

---

## 16. Feedback Collection Mechanism

- **Post-scan micro-survey**: single thumbs-up/down on "was this report
  useful?" attached to every completed scan — lowest-friction signal,
  answers the question §14's beta cohort tracking asks at scale.
- **NPS survey**: triggered after a user's 3rd completed scan (not on
  signup — too early to have an opinion) — feeds the §1.5 NPS target
  directly.
- **False-positive reporting**: per-finding "Report as false positive"
  button (§13) — direct product-quality signal, not just satisfaction.
- **Public roadmap / feature-request board**: low-cost (a tool like Canny
  or a pinned GitHub Discussions board), lets Pro/Enterprise users
  (§2.3's Sarah persona especially) see their request isn't ignored —
  cheap retention lever.
- **Beta cohort structured interviews** (§14.1) continue post-launch on a
  reduced cadence — quarterly check-ins with the largest Enterprise
  accounts specifically, since losing one Enterprise customer is a bigger
  MRR hit than losing several Starter ones.
- **Where it goes**: monthly product review against §1.5's success
  metrics — feedback that doesn't get reviewed on a cadence doesn't
  actually change anything, it just accumulates.

---

## 17. Rollback & Contingency Plan

What actually happens when one of §8's risks materializes — written down
in advance so it's a decision made calmly now, not improvised under
pressure later:

| Trigger | Response |
|---------|----------|
| Month-1 targets (§9.1) missed by >50% | Pause paid ad spend (§7.2) immediately; run the §14.1 interview process on actual signups (not the pre-launch persona guesses) to find out why, before spending more on acquisition that isn't converting |
| Beta cohort repeat-scan rate <20% (§14.2) | Do not proceed to public Launch (§7.1) on schedule — treat as a product problem, not a marketing problem; extend Beta |
| Real CAC exceeds §1.5's target by >3x | Pause paid channels (Google/LinkedIn ads, §7.2), shift budget entirely to the $0 organic channels (ProductHunt, Reddit, Twitter) until unit economics (§15) are re-validated |
| Security incident / data breach | Follow TDD.md §19 Incident Response Plan; GDPR 72-hour notification (§10.2) is a hard legal deadline, not a best-effort target |
| 6-month targets (§1.5) missed by >70% with no clear fix identified | Full product-market-fit review before continuing further spend — this is the "stop and rethink," not "try harder," threshold |
| A competitor (§6.4) ships a feature that closes our AI-report/UX advantage | Re-run §6.4's feature comparison; if our differentiation has genuinely eroded, the conversation is about product direction, not just messaging |

**What this section is not**: a guarantee any of these triggers will be
hit. It's the plan for *if* they are, decided while calm rather than after
the fact — the absence of this section was itself listed as a gap because
"we'll figure it out if it happens" is not a plan.

---

## 18. Phase 2+ Enhancements (Nice to Have)

Lower priority than anything in §3 (which already has its own Phase 2/3
breakdown) — these are cross-cutting product/marketing ideas that don't
fit neatly into a single feature epic. None of these block MVP (§3.0).

| Item | Benefit |
|------|---------|
| A/B testing on pricing page | Optimize the §6.1 tier presentation/pricing itself using real conversion data instead of guessing |
| Referral program | Organic growth lever cheaper than the §7.2 paid channels |
| Multi-language support | Opens the "SaaS startups 500K+ globally" segment (§1.4) beyond English-speaking markets |
| Mobile responsiveness | A meaningful share of the §7.3 funnel's early visitors will land on mobile even if scanning itself is a desktop workflow |
| Accessibility (WCAG 2.1 AA) | Both a compliance consideration (relevant to the Enterprise persona's own procurement checklists, §2.3) and simply wider addressable audience |
| Public API documentation | Needed once §3.2.2's API access ships — developer adoption doesn't happen without docs, this isn't optional once the feature exists |
| Content marketing calendar | Operationalizes the "Content marketing, SEO" line already in §7.1's Growth phase — currently just a phase name, not a plan |
| Social media strategy | Same gap as above for the Twitter/X "build in public" channel in §7.2 — a channel name isn't a strategy |

---

## 19. Appendix

### 19.1 Glossary
- **CVSS:** Common Vulnerability Scoring System
- **OWASP:** Open Web Application Security Project
- **CVE:** Common Vulnerabilities and Exposures
- **MRR:** Monthly Recurring Revenue
- **NPS:** Net Promoter Score
- **CAC:** Customer Acquisition Cost
- **CLV / LTV:** Customer Lifetime Value
- **DPA:** Data Processing Agreement (GDPR)
- **SLA:** Service Level Agreement

### 19.2 References
- OWASP Top 10 2021
- NIST Cybersecurity Framework
- CVSS v3.1 Specification
- SaaS Pricing Best Practices

### 19.3 Change Log
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Sep 3, 2026 | Initial draft |
| 1.1 | Sep 3, 2026 | Fixed §9/§1.5 target mismatch, fixed §6.3 competitor-savings math, added TDD.md bridging note |
| 1.2 | Sep 3, 2026 | Added §§10–18: Legal & Compliance, SLA, Onboarding Flow, Customer Support Plan, Market Validation, Unit Economics, Feature Comparison (§6.4), Feedback Collection, Rollback Plan, Phase 2+ nice-to-haves |
| 1.3 | Sep 3, 2026 | Fixed §8's Nuclei/PRD-TDD inconsistency — §8 previously listed "Nuclei" as our own mitigation for technical complexity, contradicting TDD.md §1.1's explicit "no Nuclei dependency" statement. Verified TDD §1.1's "17 skills" list is accurate (a review claiming it undercounts to 15 was a miscount — re-verified against the actual filesystem, 17 skills, 17 names, exact match) |

---

*Document generated for SecScan AI SaaS Product*
