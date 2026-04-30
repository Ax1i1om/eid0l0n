#!/usr/bin/env bash
# EID0L0N (skill name: `eidolon`) — cross-host installer for OpenClaw and Hermes.
#
# Usage:
#   bash scripts/install.sh                  # auto-detect, install everywhere it can
#   bash scripts/install.sh --openclaw       # OpenClaw only
#   bash scripts/install.sh --hermes         # Hermes only
#
# Onboarding is agent-driven (no install-time wizard). Idempotent; safe to re-run.

# Install paths and host conventions (post-2026-04-30 audit-driven decision):
#
#   ~/.openclaw/skills/<name>/    OpenClaw "managed/local" tier (4 of 6 by load
#                                 precedence per docs.openclaw.ai/concepts/agent-workspace).
#                                 Workspace skills (~/.openclaw/workspace/skills/)
#                                 and project agent skills (<workspace>/.agents/skills/)
#                                 take priority. We install to tier 4 because:
#                                  - it's the only tier that's user-machine-global
#                                    rather than per-project
#                                  - eidolon state is workspace-scoped via cwd, not
#                                    skill-scoped, so ranking doesn't matter
#                                  - publishing to ClawHub later switches install path
#                                    to `openclaw skills install eidolon` (ClawHub
#                                    registry) which lands in the same tier
#
#   ~/.hermes/skills/<name>/      Hermes auto-discovers this directory ("primary
#                                 directory and source of truth" per the skills
#                                 docs) — no config-patch step required.
#
# See docs/HOST-COMPATIBILITY.md for the full per-host contract.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_NAME="eidolon"   # snake_case, OpenClaw-compatible. EID0L0N is display-only.

c_dim() { printf "\033[2m%s\033[0m" "$*"; }
c_ok()  { printf "\033[32m%s\033[0m" "$*"; }
c_warn(){ printf "\033[33m%s\033[0m" "$*"; }
c_err() { printf "\033[31m%s\033[0m" "$*"; }
c_b()   { printf "\033[1m%s\033[0m" "$*"; }

want_openclaw=auto
want_hermes=auto
for arg in "$@"; do
  case "$arg" in
    --openclaw) want_openclaw=yes; want_hermes=no ;;
    --hermes)   want_hermes=yes;   want_openclaw=no ;;
    --help|-h)
      sed -n '2,9p' "$0"
      exit 0
      ;;
    *) c_err "unknown flag: $arg"; echo; exit 2 ;;
  esac
done

echo
c_b "EID0L0N — installer"; echo
c_dim "  εἴδωλον · the image-form of a person, made present in their absence."; echo
echo

copy_bundle() {
  local dest="$1"
  mkdir -p "$dest"
  for item in SKILL.md scripts references assets; do
    cp -R "$REPO_ROOT/$item" "$dest/"
  done
  # Strip dev artifacts that shouldn't ship to the host's skill dir.
  find "$dest" \( -name __pycache__ -o -name "*.pyc" -o -name .DS_Store \) -exec rm -rf {} + 2>/dev/null || true
  echo "  $(c_ok "✓") copied skill bundle → $dest"
}

patch_openclaw_json() {
  local cfg="$HOME/.openclaw/openclaw.json"
  mkdir -p "$(dirname "$cfg")"
  if [[ ! -f "$cfg" ]]; then
    echo '{"skills":{"entries":{}}}' > "$cfg"
  fi
  python3 - "$cfg" "$SKILL_NAME" <<'PY'
import json, os, shutil, sys, time
cfg_path, name = sys.argv[1], sys.argv[2]
try:
    with open(cfg_path) as f:
        cfg = json.load(f)
except (json.JSONDecodeError, OSError) as e:
    bak = f"{cfg_path}.bak.{int(time.time())}"
    if os.path.exists(cfg_path):
        shutil.copyfile(cfg_path, bak)
        print(f"  ⚠ openclaw.json was corrupt ({e}); backed up to {bak}")
    cfg = {"skills": {"entries": {}}}
cfg.setdefault("skills", {}).setdefault("entries", {})
entry = cfg["skills"]["entries"].setdefault(name, {})
entry.setdefault("enabled", True)
with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
print(f"  ✓ patched {cfg_path} (skills.entries.{name}.enabled = true)")
PY
}

installed_openclaw=0
installed_hermes=0

if [[ "$want_openclaw" != no ]]; then
  if command -v openclaw >/dev/null 2>&1 || [[ -d "$HOME/.openclaw" ]]; then
    c_b "→ Installing for OpenClaw"; echo
    copy_bundle "$HOME/.openclaw/skills/$SKILL_NAME"
    patch_openclaw_json
    installed_openclaw=1
  elif [[ "$want_openclaw" == yes ]]; then
    c_err "  OpenClaw not detected (no 'openclaw' command, no ~/.openclaw/ dir)"; echo
    exit 1
  fi
fi

if [[ "$want_hermes" != no ]]; then
  if command -v hermes >/dev/null 2>&1 || [[ -d "$HOME/.hermes" ]]; then
    c_b "→ Installing for Hermes"; echo
    copy_bundle "$HOME/.hermes/skills/$SKILL_NAME"
    installed_hermes=1
  elif [[ "$want_hermes" == yes ]]; then
    c_err "  Hermes not detected (no 'hermes' command, no ~/.hermes/ dir)"; echo
    exit 1
  fi
fi

if [[ $installed_openclaw -eq 0 && $installed_hermes -eq 0 ]]; then
  c_warn "No host agent detected."; echo
  echo "  To use this skill standalone, set:"
  echo "    export PATH=\"$REPO_ROOT/scripts:\$PATH\""
  echo "  Then check state:  python3 $REPO_ROOT/scripts/setup.py status"
  echo "  And backends:      python3 $REPO_ROOT/scripts/setup.py detect-backends"
  echo
fi

echo
c_b "→ Dependencies"; echo
for bin in python3 uv; do
  if command -v "$bin" >/dev/null 2>&1; then
    echo "  $(c_ok "✓") $bin found"
  else
    echo "  $(c_warn "!") $bin not installed"
    case "$bin" in
      uv) echo "      install: brew install uv  (or curl -LsSf https://astral.sh/uv/install.sh | sh)" ;;
    esac
  fi
done

# No interactive setup at install time — onboarding is agent-driven.
# When the user first asks the agent to generate an image, the agent reads
# SOUL.md, asks about a reference (or generates one), and saves the anchor.
echo
c_b "→ Next steps"; echo
echo "  Files are installed. Onboarding happens automatically the next time"
echo "  you ask the agent to generate an image — it will read SOUL.md, ask"
echo "  whether you have a reference image, and offer to generate one for"
echo "  approval if you don't."
echo
echo "  Pick an image-gen backend (any ONE is enough — auto-detected at run time):"
echo "    • $(c_ok "codex")      FREE for ChatGPT Plus/Pro/Team — run \`codex login\` once"
echo "    • $(c_ok "gemini")     export GEMINI_API_KEY=..."
echo "    • $(c_ok "openai")     export OPENAI_API_KEY=..."
echo "    • $(c_ok "fal")        export FAL_KEY=..."
echo "    • $(c_ok "replicate")  export REPLICATE_API_TOKEN=..."
echo "    • $(c_ok "openrouter") python3 $REPO_ROOT/scripts/setup.py set-api --key <YOUR_KEY>"
echo
echo "  See what's currently detected:"
echo "    python3 $REPO_ROOT/scripts/setup.py detect-backends"
echo
echo "  Inspect state any time:"
echo "    python3 $REPO_ROOT/scripts/setup.py status"
echo

if [[ $installed_openclaw -eq 1 && $installed_hermes -eq 1 ]]; then
  c_b "→ Dual-host install detected"; echo
  echo "  Both OpenClaw and Hermes are configured. cwd resolution differs"
  echo "  between hosts (and between Hermes CLI vs. Gateway mode) — see"
  echo "  $REPO_ROOT/docs/HOST-COMPATIBILITY.md for the per-host contract"
  echo "  and Gateway/MESSAGING_CWD caveats."
  echo
fi
