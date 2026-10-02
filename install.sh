#!/usr/bin/env bash
# Install the workflow into a project: .claude/ (Claude Code) and optionally
# .codex/ + .agents/skills/ (Codex). Safe to re-run: identical files are skipped,
# files you changed are kept unless --force (then backed up first).
#
#   ./install.sh [--target DIR] [--codex] [--force] [--dry-run]
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$PWD"; CODEX=0; FORCE=0; DRY=0

usage() { sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:?--target needs a directory}"; shift 2 ;;
    --codex) CODEX=1; shift ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1"; usage 2 ;;
  esac
done

[ -d "$TARGET" ] || { echo "Target directory does not exist: $TARGET"; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"
[ "$TARGET" = "$SRC" ] && { echo "Target is the workflow repository itself; pass --target <your project>"; exit 2; }

# --- prerequisites -----------------------------------------------------------
missing=0
command -v python3 >/dev/null || { echo "Missing: python3 (3.11+)"; missing=1; }
if command -v python3 >/dev/null && ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  echo "Missing: python3 >= 3.11 (found $(python3 -V 2>&1))"; missing=1
fi
command -v git >/dev/null || { echo "Missing: git"; missing=1; }
command -v node >/dev/null || echo "Warning: node not found — reflex hooks will not fire until Node.js is installed"
if command -v python3 >/dev/null && ! python3 -c 'import yaml' 2>/dev/null; then
  echo "Warning: PyYAML not found — task gates (task-accept, owns-check, wave-check) will fail."
  echo "         Install it: python3 -m pip install pyyaml"
fi
[ "$missing" -eq 0 ] || exit 2
git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || echo "Warning: $TARGET is not a git repository; owns-check and task-accept need git"

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$TARGET/.workflow-backup/$STAMP"
added=0; same=0; kept=0; replaced=0
KEPT_LIST=()

run() { if [ "$DRY" -eq 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

# Copy one file with the skip / keep / force-and-backup policy.
place() {
  local rel="$1" from="$SRC/$1" to="$TARGET/$1"
  if [ ! -e "$to" ]; then
    run mkdir -p "$(dirname "$to")"; run cp -p "$from" "$to"; added=$((added + 1))
  elif cmp -s "$from" "$to"; then
    same=$((same + 1))
  elif [ "$FORCE" -eq 1 ]; then
    run mkdir -p "$(dirname "$BACKUP/$rel")"; run cp -p "$to" "$BACKUP/$rel"
    run cp -p "$from" "$to"; replaced=$((replaced + 1))
  else
    kept=$((kept + 1)); KEPT_LIST+=("$rel")
  fi
}

place_tree() {
  local dir="$1"
  while IFS= read -r -d '' f; do
    place "${f#"$SRC"/}"
  done < <(find "$SRC/$dir" -type f -not -name '.DS_Store' -not -path '*/__pycache__/*' -print0 | sort -z)
}

echo "Installing workflow into $TARGET"
for d in skills agents commands shared scripts reflexes; do place_tree ".claude/$d"; done

# --- .claude/settings.json: add our hooks, keep everything else -------------
SETTINGS="$TARGET/.claude/settings.json"
if [ ! -e "$SETTINGS" ]; then
  place ".claude/settings.json"
elif [ "$DRY" -eq 1 ]; then
  echo "  [dry-run] merge workflow hooks into .claude/settings.json"
else
  python3 - "$SRC/.claude/settings.json" "$SETTINGS" <<'PY'
import json, sys
src, dst = (json.load(open(p)) for p in sys.argv[1:3])
hooks = dst.setdefault("hooks", {})
added = 0
for event, groups in src["hooks"].items():
    present = {h.get("command") for g in hooks.get(event, []) for h in g.get("hooks", [])}
    for group in groups:
        if all(h["command"] not in present for h in group["hooks"]):
            hooks.setdefault(event, []).append(group); added += 1
if added:
    json.dump(dst, open(sys.argv[2], "w"), indent=2, ensure_ascii=False)
    open(sys.argv[2], "a").write("\n")
print(f"  settings.json: {added} hook group(s) added")
PY
fi

# --- root documents: only when absent ---------------------------------------
for doc in ENGINEERING.md CLAUDE.md AGENTS.md; do
  if [ -e "$TARGET/$doc" ]; then
    echo "  $doc exists — not touched; compare with $SRC/templates/$doc and merge what you need"
  else
    run cp "$SRC/templates/$doc" "$TARGET/$doc"; added=$((added + 1))
  fi
done

# --- .gitignore: runtime data of the workflow -------------------------------
GI="$TARGET/.gitignore"
for line in 'work/*/logs/working/' '.codex/data/' '.workflow-backup/' '__pycache__/'; do
  if ! { [ -e "$GI" ] && grep -qxF "$line" "$GI"; }; then
    if [ "$DRY" -eq 1 ]; then echo "  [dry-run] .gitignore += $line"; else echo "$line" >> "$GI"; fi
  fi
done

# --- Codex ------------------------------------------------------------------
if [ "$CODEX" -eq 1 ]; then
  for f in workflow.md context.md README.md sync-workflow.py hooks.json .gitignore \
           hooks/workflow-hooks.py hooks/post-compact-restore.sh hooks/README.md \
           test_sync_workflow.py test_workflow_hooks.py; do
    place ".codex/$f"
  done
  if [ "$DRY" -eq 1 ]; then
    echo "  [dry-run] python3 .codex/sync-workflow.py --write"
  else
    adopt=""
    [ -e "$TARGET/.codex/workflow-manifest.json" ] || adopt="--adopt-existing"
    (cd "$TARGET" && python3 .codex/sync-workflow.py --write $adopt) \
      || echo "  Codex entrypoints not generated — see the message above and .codex/README.md"
  fi
fi

# --- report -----------------------------------------------------------------
echo
echo "Done: added $added, unchanged $same, replaced $replaced, kept local $kept."
if [ "$kept" -gt 0 ]; then
  echo "Your local versions were kept (re-run with --force to replace them; originals go to .workflow-backup/):"
  printf '  %s\n' "${KEPT_LIST[@]}" | head -40
  [ "$kept" -gt 40 ] && echo "  … and $((kept - 40)) more"
fi
[ "$replaced" -gt 0 ] && echo "Backups of replaced files: $BACKUP"
if [ "$DRY" -eq 0 ]; then
  echo
  (cd "$TARGET" && bash .claude/scripts/check-setup.sh) || true
fi
echo
echo "Next: open the project in Claude Code and run /build <task> or /new-user-spec."
[ "$CODEX" -eq 1 ] && echo "Codex: start a new session, trust the project, check /hooks; use \$source-command-build."
exit 0
