# BountyGrimoire — Fix Log

Har entry: **kya problem thi → kyun problem thi → kya fix kiya → kaunsi files change hui**.
Naye fixes hamesha upar (sabse recent pehle) add karo.

---

## 2026-09-03 — Fix batch #4: HackerOne auto-submit MCP tools explicitly blocked

- **Kya mila**: User ke global opencode config (`~/.config/opencode/opencode.json`) me 8 MCP servers hain (github, memory, sqlite-nifty, filesystem-nifty, fetch, playwright, chrome-devtools, **hackerone**) — `opencode mcp list` chalake BountyGrimoire folder ke andar se confirm kiya ki ye **sab connected hote hain** jab bhi opencode is project me chalta hai (project ka `opencode.json` inhe override nahi karta). Claude Code (global `~/.claude.json`) me bhi `hackerone` MCP connected hai isi session me.
- **Kyun problem thi**: `hackerone-mcp` ke paas REAL report-submission tools hain (`submit_report`, `create_report_intent`, etc.) jo actual H1 credentials (`H1_USERNAME`/`H1_API_TOKEN`) use karke live submit kar sakte hain. Pehle maine bola tha "`/report` kabhi auto-submit nahi karta" — ye sirf BountyGrimoire ke apne likhe command files ke liye sach tha (wo sirf curl/bash instruct karte hain), lekin koi **hard restriction** nahi thi jo agent ko ye MCP tool use karne se roke agar wo available ho. Matlab safety sirf "scripts aisa nahi bolte" pe depend kar rahi thi.
- **Fix**: Ek explicit "⛔ Submission Safety (MANDATORY)" rule **4 jagah** add ki (defense-in-depth, sirf ek jagah pe depend nahi karna):
  1. `CLAUDE.md` (live, abhi ka Mozilla program) — direct patch kiya, turant effective
  2. `.claude/commands/load-program-h1.md` — template me add kiya, taaki har future `/load-program-h1` run me ye rule automatically CLAUDE.md ka part bane
  3. `.claude/commands/report.md` — top par explicit warning
  4. `.claude/commands/hunt.md` aur `hunt-auth.md` — "Submission safety (MANDATORY)" section add kiya jo saare 17/7 hunter subagents + validator ko pass hota hai
- Rule ka text: kabhi bhi `submit_report`, `create_report_intent`, `submit_report_intent`, `update_report_intent`, ya koi `mcp__hackerone__*`/`hackerone-mcp` write action call mat karo, chahe wo tool session me available ho — sirf local file me likho, human manually HackerOne UI se submit karega.
- Saare `.opencode/commands/` mirrors sync kiye.
- **Zaroor kiya (hard block, sirf prompt-instruction nahi)**: `.claude/settings.json` ke `permissions.deny` me 7 mutating HackerOne MCP tools add kiye: `submit_report`, `create_report_intent`, `submit_report_intent`, `update_report_intent`, `delete_report_intent`, `delete_report_intent_attachment`, `upload_report_intent_attachment`. Read-only tools (`get_program`, `get_report`, `list_my_reports`, `search_hacktivity`, waghera) allowed rehne diye — wo research ke liye useful hain aur kuch submit/mutate nahi karte.
  - **Live verify kiya isi session me**: settings.json save karte hi in 7 tools ka access turant revoke ho gaya (system ne khud confirm kiya "no longer available"). Matlab ye Claude Code ke liye ek genuine, enforced technical block hai — sirf agent ko "please mat karo" bolna nahi.
  - **Limitation**: Ye block sirf **Claude Code** (`.claude/settings.json`) ke liye hai. **opencode ke liye equivalent hard block nahi lagaya** — opencode ka permission-config schema (MCP tool-level deny) confidently verify nahi kar paya, isliye galat config likh ke false sense of security dene se bacha. opencode side pe abhi sirf prompt-level instruction (CLAUDE.md + hunt.md/report.md) hi protection hai. Agar opencode se bhi hard-block chahiye, batana — opencode docs check karke sahi syntax likhunga.

---

## ⚠️ UNRESOLVED — `.git` / `.gitignore` baar-baar Trash me chale jaate hain (system-level, BountyGrimoire ka bug nahi)

**Status: OPEN — aage bhi ho sakta hai, monitor karte raho.**

- **Kya ho raha hai**: Is 2026-09-03 ke session me `.git` aur `.gitignore` (dono root se) **teen baar** Trash me gaye (confirmed timestamps: ~09:04, ~11:46:24/11:46:29, aur ek aur uske turant baad — trash ka poora content bhi ek baar completely empty ho gaya, ~13:08).
- **Kya rule out kiya**:
  - `anonymous-monitor.sh` cron job (har 2 min chalta hai) — poora source code padha, ye sirf Tor/VPN/proxy/reverse-shell processes detect karke notification deta hai, **kabhi kisi file ko touch/delete nahi karta**. Log (`~/.local/logs/anon-monitor.log`) bhi confirm karta hai — sirf "OK - no anonymous activity" entries hain.
  - Koi cron/at/systemd-timer job jo `.git`/`.gitignore` delete kare — poori crontab aur systemd timers check ki, kuch relevant nahi mila.
  - Common sync/cleanup tools (Dropbox, Nextcloud, Syncthing, Nautilus, IDE workspace-cleaners) — `ps aux` me koi running process nahi mila.
  - Ek 3-minute live poll (2 sec interval) chalaya turant restore ke baad — us window me dobara nahi hua, matlab ye fixed timer nahi hai, kisi specific trigger se hota hai.
- **Important observation**: Sirf `.git` aur `.gitignore` specifically target hote hain — baaki koi file/folder (including doosri dotfiles jaise `.env`, `.claude/`, `.opencode/`) kabhi touch nahi hui. Ye kisi generic "clean dotfiles" tool jaisa nahi lagta — bahut specific pattern hai.
- **Current state**: Maine har baar `.git` ko `/tmp/opencode/BountyGrimoire/.git` (ek clean backup clone jo system par kahi maujood hai) se restore kiya hai, aur `.gitignore` ko apne fixes ke saath fir se likha hai. Abhi dono present hain.
- **User ko recommend kiya gaya**: Check karo kya koi doosra opencode/claude session (`--dangerous`/`--auto` mode me) isi project pe background me chal raha hai — ye sabse likely explanation hai. Ye BountyGrimoire ke apne code (`.claude/`, `.opencode/`, scripts) ka bug NAHI hai — maine poore codebase me kahi bhi `rm`, `git clean`, ya trash-related command nahi paayi jo isse explain kare.

---

## 2026-09-03 — Fix batch #3: README/install.sh polish + dependency check fix

- **README.md**: Line 43 ka warning text abhi bhi "the raw command below" bol raha tha jabki neeche wala code-block already `./start-bounty.sh` wrapper dikha raha tha (batch #1 ka half-applied edit) — text ko clean kiya, ab consistent hai.
- **`install.sh`**: 🟠 **Real functional bug** — installer `command -v claude` na milne par **hard-fail** (`exit 1`) kar deta tha, chahe user sirf `opencode`/Gemini se chalana chahta ho (`start-bounty-gemini.sh`, `start-bounty-bigpickle.sh` ko `claude` CLI ki zaroorat hi nahi, `opencode` CLI chahiye). Aur `opencode` ka koi dependency-check tha hi nahi. Isse "project teeno se chalna chahiye" requirement break hoti — opencode-only user install hi nahi kar pata.
  - **Fix**: Ab `claude` aur `opencode` dono optional check hote hain, installer sirf tab fail hota hai jab **dono hi** missing hon. Har ek missing hone par sirf info message deta hai (kis launcher ke liye zaroori hai wo bata ke).
- Verify kiya: `bash -n` se sab 4 shell scripts (`install.sh`, `start-bounty.sh`, `start-bounty-gemini.sh`, `start-bounty-bigpickle.sh`) syntax-clean hain.
- Verify kiya: 17 skills (`.claude/skills/`) = 17 opencode agents (`.opencode/agents/`) = 17 `VULN_MAP` entries (`generate-skill.py`) = 17 `hunt.md` supported types — sab exactly match karte hain, koi drift nahi.
- Verify kiya: `.claude/settings.json`, `opencode.json`, `.opencode/package.json` — sab valid JSON.
- Verify kiya: koi leftover YWH/YesWeHack reference nahi bacha (poora codebase sweep kiya).

---

## 2026-09-03 — Fix batch #2: YesWeHack support poori tarah removed

User ne clarify kiya ki wo sirf HackerOne use karte hain, YesWeHack se koi lena-dena nahi — isliye YWH-related sab kuch hata diya (feature simplification, koi bug nahi tha).

- **Deleted**: `.claude/commands/load-program.md` + `.opencode/commands/load-program.md` (YesWeHack program loader — ab sirf `/load-program-h1` hai)
- **`.claude/commands/report.md`**: Step 0 ka H1/YWH platform-detection hataya, ab hamesha HackerOne format + `hackerone.com/<handle>/reports/new` submit link deta hai (pichhle fix batch #1 ka dual-platform kaam ab unnecessary complexity tha)
- **`.claude/commands/session-save.md` / `session-load.md` / `session-list.md`**: `platform: <ywh|h1>` field hataya, YWH example rows/text hataye
- **`.claude/commands/setup-account.md`**: YesWeHack email-alias example hataya, sirf HackerOne example rakha
- **`.claude/commands/hunt.md` / `update-skills.md`**: `PROGRAM_SLUG` regex simplify kiya sirf `hackerone\.com/\K[^/\s]+` (fix batch #1 ka dual-format regex hata diya, ab sirf H1 chahiye)
- **`README.md`**: Quick-start example `/load-program-h1 mozilla` kiya, `.env` config section se `YWH_PAT` line hataya
- **`install.sh`**: final message se `/load-program <ywh-slug>` line hataya
- **NAHI kar paya**: `.env.example` se `YWH_PAT=your_ywh_token` line hataana — ye file `.claude/settings.json`'s `Read(.env*)` deny rule ke andar aati hai, Bash se bhi edit blocked hai (sandbox safety). **User ko manually ek line hatani hogi**: `.env.example` me `YWH_PAT=your_ywh_token` wali line delete kar dena.
- Sab `.opencode/commands/` mirrors sync kiye, `diff -rq .claude/commands .opencode/commands` → clean.
- Verify kiya: poore codebase me (docs/code) koi `yeswehack`/`ywh` reference nahi bacha (sirf is fix-log me history ke liye mention hai).

---

## 2026-09-03 — Fix batch #1

### 1. 🔴 `.git` aur `.gitignore` accidentally Trash me chale gaye the (data-loss risk, discovered mid-session)

- **Kya mila**: Session ke beech me `.git` folder project se poori tarah gayab tha — project git repo hi nahi raha. `.gitignore` bhi gayab tha.
- **Kyun problem thi**: Bina `.gitignore` ke, `.env.bak` jaisi secret files bilkul unprotected thi. Bina `.git` ke, koi commit/history/restore possible nahi tha.
- **Root cause**: Dono files `~/.local/share/Trash/files/` me mili (delete nahi hui thi, sirf trash me move hui thi — GUI file manager se). Original repo `/tmp/opencode/BountyGrimoire` me ek backup clone bhi mila jisse confirm hua ki commit history (`c55f833`) match karti hai.
- **Fix**: Dono files Trash se wapas `/home/mohit/bountyhunt/BountyGrimoire/` me copy ki.
- **Files touched**: `.git/`, `.gitignore` (restored, no content change)

---

### 2. 🔴 `.env.bak` `.gitignore` me cover nahi tha (secret leak risk)

- **Kya problem thi**: `.gitignore` me `.env` aur `*.env` patterns the, lekin `.env.bak` in dono se match nahi karta (ye `.bak` pe end hota hai). `git check-ignore -v .env.bak` → not ignored.
- **Kyun problem thi**: Agar kabhi `git add .` / `git add -A` chalta, to `.env.bak` (jisme real API keys ka backup ho sakta hai) commit + push ho sakta tha → secret leak.
- **Fix**: `.gitignore` me `.env.bak`, `.env.*.bak`, `*.env.bak` patterns add kiye.
- **Verify**: `git check-ignore -v .env.bak` → ab `.gitignore:10:*.env.bak	.env.bak` (ignored ✅)
- **Files touched**: `.gitignore`

---

### 3. 🟠 `PROGRAM_SLUG` extraction HackerOne programs ke liye kaam nahi karta tha

- **Kya problem thi**: `PROGRAM_SLUG=$(grep -oP 'programs/\K[^/\s]+' CLAUDE.md | head -1)` sirf YesWeHack URL format (`yeswehack.com/programs/<slug>`) ke liye kaam karta hai. HackerOne CLAUDE.md me URL hota hai `hackerone.com/<handle>` (no `/programs/`) — is regex se **empty result** aata tha (test karke confirm kiya).
- **Kyun problem thi**: Iska matlab `memory/<slug>.json` (hunt memory) aur `/update-skills` ka slug-based lookup HackerOne programs (jaise Mozilla) ke liye literal execution me fail ho jata — sirf isliye kaam kar raha tha kyunki LLM khud slug infer kar leta tha, jo reliable nahi hai.
- **Fix**: Regex ko dono formats support karne ke liye update kiya: `grep -oP '(?:programs/|hackerone\.com/)\K[^/\s]+' CLAUDE.md`. Test kiya dono formats (H1 + YWH mock) ke against — dono se sahi slug nikalta hai.
- **Files touched**: `.claude/commands/hunt.md` (Step 8), `.claude/commands/update-skills.md` (Step 1) + `.opencode/commands/` mirrors

---

### 4. 🟠 `/report` sirf YesWeHack format/link banata tha, HackerOne ka koi variant nahi tha

- **Kya problem thi**: `/report` command hardcoded tha YesWeHack ke liye — submission link `https://yeswehack.com/programs/<slug>/submit` hamesha dikhata tha, chahe active program HackerOne ka ho (jaise Mozilla).
- **Kyun problem thi**: HackerOne program (jaise Mozilla) pe kaam karte hue `/report` chalane par galat platform ka reminder link milta — user ko manually sahi jagah dhoondhni padti. (Note: koi auto-submit nahi hota tha kabhi bhi — sirf ek text reminder line thi, koi security risk nahi tha, sirf UX/accuracy issue.)
- **Fix**: `/report` me ek naya "Step 0 — Detect platform" add kiya jo CLAUDE.md ke header se H1 vs YWH detect karta hai, aur submission checklist me platform ke hisaab se sahi URL dikhata hai (H1: `hackerone.com/<handle>/reports/new`, YWH: `yeswehack.com/programs/<slug>/submit`).
- **Files touched**: `.claude/commands/report.md` + `.opencode/commands/report.md` mirror

---

### 5. 🟡 README/`install.sh` `--dangerously-skip-permissions` ko unsafe way me recommend karte the

- **Kya problem thi**: README ka Quick Start aur `install.sh` ka final message directly `claude --dangerously-skip-permissions` chalane ko bolte the — jabki `start-bounty.sh` (jo already project me maujood tha) isi risk ko safely mitigate karta hai (default me safe/interactive mode, `--dangerous` flag se hi unrestricted mode milta hai).
- **Kyun problem thi**: Naya user README follow karke seedha unrestricted mode me chala jata, `start-bounty.sh` ki built-in safety cheeck ko bypass karte hue.
- **Fix**: README aur `install.sh` dono ko update kiya taaki wo `./start-bounty.sh` (safe default) use karne ko bole, aur `--dangerous` flag ka explicit warning ke sath mention kare.
- **Files touched**: `README.md`, `install.sh`

---

### 6. 🟢 README "18 specialized agents" claim galat tha (actual: 17)

- **Kya problem thi**: README badge/text me "18 agents" bola gaya tha, lekin `.claude/skills/find-*/` aur `generate-skill.py`'s `VULN_MAP` me sirf 17 hain. 18th entry table me "Recon" tha, jo koi persistent skill/agent nahi — `/hunt`'s Step 4 ka ek inline recon task hai.
- **Kyun problem thi**: Misleading documentation — user expect karta 18 dedicated hunters, jabki 17 hain + ek shared recon pass.
- **Fix**: Saari "18" references "17" me badal di, badge count fix kiya, hunters table se duplicate/fake "Recon" row hataya aur clarify kiya ki Recon `/hunt`'s Step 4 hai, standalone agent nahi.
- **Files touched**: `README.md`

---

### 7. 🟢 `.opencode/agents/*.md` aur `.claude/skills/*/SKILL.md` ke beech drift ka risk

- **Kya problem thi**: `.opencode/agents/find-*.md` files `.claude/skills/find-*/SKILL.md` ki static copies hain (frontmatter me `mode: subagent` add karke). Lekin `generate-skill.py` (skill generator) aur `/update-skills` command sirf `.claude/skills/` ko update karte the — `.opencode/agents/` ko koi bhi automatically sync nahi karta tha.
- **Kyun problem thi**: Future me jab bhi koi skill improve hoti (naya pattern add hota), `.opencode/agents/` wali copy stale/outdated reh jati — matlab opencode se chalane par purana/kam-accurate hunting logic milta, jabki Claude Code se chalane par naya.
- **Fix**:
  1. `generate-skill.py` me `save_skill()` ke andar ek naya `sync_opencode_agent()` function call add kiya — jab bhi koi skill create/improve hoti hai, automatically `.opencode/agents/find-<name>.md` bhi sath me update ho jata hai (frontmatter me `mode: subagent` insert karke). Test kiya — output byte-identical hai existing files ke frontmatter format se.
  2. `/update-skills` command (jo LLM-driven markdown workflow hai, code nahi) me ek naya "Step 4b — Sync to .opencode/agents" add kiya jo explicitly `.claude/skills/find-<name>/SKILL.md` ko `.opencode/agents/find-<name>.md` me copy karne aur `mode: subagent` add karne ka instruction deta hai.
- **Files touched**: `generate-skill.py`, `.claude/commands/update-skills.md` + `.opencode/commands/update-skills.md` mirror

---

### 8. ✅ Verified — teeno launch paths (`start-bounty.sh`, `start-bounty-bigpickle.sh`, `start-bounty-gemini.sh`) sync me hain

- Confirm kiya `diff -rq .claude/commands .opencode/commands` → koi difference nahi.
- Confirm kiya `.claude/skills/find-*/SKILL.md` aur `.opencode/agents/find-*.md` content-wise fully sync hain (sirf `mode: subagent` frontmatter ka cosmetic difference).
- `start-bounty-gemini.sh` aur `start-bounty-bigpickle.sh` dono sirf `opencode -m <model>` chalate hain isi project folder ke andar — koi separate config nahi, isliye `.opencode/` ke fixes automatically dono ko mil gaye.
- Koi code change nahi kiya, sirf verification.

---

## Review kiya, lekin fix NAHI kiya (needs manual confirmation)

### Gemini model version mismatch
- `opencode.json` → `small_model: google/gemini-3.1-flash-lite`
- `start-bounty-gemini.sh` → `MODEL="google/gemini-3.6-flash"`
- **Reason not fixed**: Ye dono alag purpose serve karte hain — `small_model` ek lightweight/background model hai (jaise title-generation), `start-bounty-gemini.sh`'s `MODEL` launcher ka main model hai. Version numbers (3.1 vs 3.6) genuinely different ho sakte hain intentionally, ya typo ho sakta hai — bina Google ke current Gemini model catalog verify kiye (internet access nahi hai is session me) confidently nahi keh sakta konsa sahi hai. **User ko khud confirm karna chahiye** ki dono model IDs valid/current hain.

### `Bash(*)` full-allow in `.claude/settings.json`
- Design choice hai, already `start-bounty.sh` ke through mitigate ho raha hai (default safe mode). Change nahi kiya kyunki ye ek security-tool ke liye intentional tradeoff hai — bina explicit user consent ke isse restrict karna tool ko break kar sakta hai (curl/recon ko permission-prompt me har baar rokna).
