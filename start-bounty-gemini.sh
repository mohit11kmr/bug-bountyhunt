#!/usr/bin/env bash
# =============================================================================
# start-bounty-gemini.sh — Launch BountyGrimoire in opencode with Gemini
#
# Starts opencode inside the BountyGrimoire project (so .opencode/commands +
# .opencode/agents are available) pinned to Google's gemini-3.6-flash model.
#
# SECURITY NOTE: same as start-bounty.sh — only run against authorized
# in-scope targets (see CLAUDE.md), ideally inside a dedicated VM.
#   Add --dangerous to auto-approve permissions (skips confirmation prompts).
# =============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

MODEL="google/gemini-3.6-flash"

if [ -f "$DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$DIR/.env"
  set +a
  echo "[✓] Loaded .env"
fi

echo "[✓] BountyGrimoire ready at $DIR (opencode, model: $MODEL)"
echo ""
echo "  Inside opencode use:"
echo "    /load-program-h1 <handle>   # load a HackerOne program scope/rules"
echo "    /hunt <target>              # launch 17 parallel hunter agents + validator"
echo "    /report                     # generate a submission-ready report"
echo "    /models                     # switch model on the fly"
echo ""

if [ "$1" = "--dangerous" ]; then
  echo "[WARN] Running with --auto (UNRESTRICTED permissions)."
  echo "[WARN] ONLY authorized in-scope targets. Ideally inside a VM."
  echo ""
  exec opencode -m "$MODEL" --auto
else
  echo "[i] Using interactive permissions (safe). Add --dangerous to skip prompts."
  exec opencode -m "$MODEL"
fi
