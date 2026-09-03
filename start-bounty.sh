#!/usr/bin/env bash
# =============================================================================
# start-bounty.sh — Safe launcher for BountyGrimoire (Claude Code)
#
# Loads program/platform credentials from .env, then launches Claude Code
# inside the BountyGrimoire project so its skills + commands are available.
#
# SECURITY NOTE:
#   BountyGrimoire's README suggests `claude --dangerously-skip-permissions`.
#   That gives Claude unrestricted shell access — a real risk on a personal
#   machine. This launcher does NOT pass that flag by default. It uses the
#   project's .claude/settings.json allow-list (Bash(*) etc.) but lets Claude
#   prompt before executing destructive/sensitive operations.
#
#   If you understand the risk and run this ONLY against authorized in-scope
#   targets inside a dedicated VM, you can opt in with:
#       ./start-bounty.sh --dangerous
# =============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Load .env
if [ -f "$DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$DIR/.env"
  set +a

  # IMPORTANT: .env ships with a PLACEHOLDER ANTHROPIC_API_KEY=sk-ant-...
  # (from .env.example). If the user has a real claude.ai OAuth login (Claude
  # Pro/Max/Team), exporting a fake key here makes Claude Code see BOTH auth
  # methods and fail with 401 on remote settings. The placeholder is NOT a real
  # key, so unset it here and let Claude use the OAuth login instead.
  if [ -n "${ANTHROPIC_API_KEY:-}" ] && [[ "$ANTHROPIC_API_KEY" == sk-ant-* ]]; then
    unset ANTHROPIC_API_KEY
    echo "[✓] Loaded .env (placeholder ANTHROPIC_API_KEY removed — using claude.ai OAuth login)"
  else
    echo "[✓] Loaded .env"
  fi
fi

echo "[✓] BountyGrimoire ready at $DIR"
echo ""
echo "  Inside Claude Code use:"
echo "    /load-program-h1 <handle>   # load a HackerOne program scope/rules"
echo "    /hunt <target>              # launch 17 parallel hunter agents + validator"
echo "    /report                     # generate a submission-ready report"
echo ""

if [ "$1" = "--dangerous" ]; then
  echo "[WARN] Running with --dangerously-skip-permissions (UNRESTRICTED)."
  echo "[WARN] ONLY authorized in-scope targets. Ideally inside a VM."
  echo ""
  exec claude --dangerously-skip-permissions
else
  echo "[i] Using interactive permissions (safe). Add --dangerous to skip prompts."
  exec claude
fi
