#!/usr/bin/env bash
#
# init-feature-folder.sh — Create full feature folder structure
#
# Usage: ./init-feature-folder.sh <feature-name> [work-dir]
#   feature-name  — required, kebab-case slug (e.g., "add-auth", "fix-login-bug")
#   work-dir      — optional, path to work directory (default: ./work)
#
# Creates:
#   work/{feature-name}/
#     user-spec.md          (from template)
#     tech-spec.md          (from template, if available)
#     decisions.md          (from template or header)
#     tasks/
#     logs/userspec/
#       interview.yml       (from template)
#     logs/techspec/
#     logs/tasks/
#     logs/working/
#     logs/checkpoint.yml   (from template, for feature-execution recovery)

set -euo pipefail

# --- Arguments ---
FEATURE_NAME="${1:-}"
WORK_DIR="${2:-./work}"

if [[ -z "$FEATURE_NAME" ]]; then
  echo "Error: feature-name is required" >&2
  echo "Usage: $0 <feature-name> [work-dir]" >&2
  exit 1
fi

# --- Paths ---
# Templates are resolved relative to THIS script, not to $HOME: the script and its
# templates ship in the same repository, so a clone is self-sufficient. $HOME is kept
# only as a fallback for a copy that lacks a template (e.g. an older personal install).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HOME_SHARED="$HOME/.claude/shared"

# resolve <relative-path-under-shared> → prints the first existing candidate, or nothing
resolve() {
  if [[ -f "$SHARED_DIR/$1" ]]; then
    echo "$SHARED_DIR/$1"
  elif [[ -f "$HOME_SHARED/$1" ]]; then
    echo "$HOME_SHARED/$1"
  fi
}

USER_SPEC_TEMPLATE=$(resolve "work-templates/user-spec.md.template")
TECH_SPEC_TEMPLATE=$(resolve "work-templates/tech-spec.md.template")
DECISIONS_TEMPLATE=$(resolve "work-templates/decisions.md.template")
CHECKPOINT_TEMPLATE=$(resolve "work-templates/checkpoint.yml.template")
INTERVIEW_TEMPLATE=$(resolve "interview-templates/feature.yml")
FEATURE_DIR="$WORK_DIR/$FEATURE_NAME"
TODAY=$(date +%Y-%m-%d)

# --- Validation ---
if [[ -z "$USER_SPEC_TEMPLATE" ]]; then
  echo "Error: template not found: work-templates/user-spec.md.template" >&2
  echo "       looked in: $SHARED_DIR and $HOME_SHARED" >&2
  exit 1
fi

EXISTED=false
if [[ -d "$FEATURE_DIR" ]]; then
  EXISTED=true
fi

# --- Create directory structure (mkdir -p is safe for existing dirs) ---
mkdir -p "$FEATURE_DIR/tasks"
mkdir -p "$FEATURE_DIR/logs/userspec"
mkdir -p "$FEATURE_DIR/logs/techspec"
mkdir -p "$FEATURE_DIR/logs/tasks"
mkdir -p "$FEATURE_DIR/logs/working"

# --- Copy and fill templates (only if file doesn't already exist) ---

# user-spec.md
if [[ ! -f "$FEATURE_DIR/user-spec.md" ]]; then
  sed -e "s/\[DATE\]/$TODAY/g" \
      -e "s/\[Название фичи\/фикса\]/$FEATURE_NAME/g" \
      "$USER_SPEC_TEMPLATE" > "$FEATURE_DIR/user-spec.md"
fi

# tech-spec.md (optional — tech-spec-planning skill will create/overwrite if needed)
if [[ ! -f "$FEATURE_DIR/tech-spec.md" ]] && [[ -n "$TECH_SPEC_TEMPLATE" ]]; then
  sed -e "s/\[DATE\]/$TODAY/g" \
      "$TECH_SPEC_TEMPLATE" > "$FEATURE_DIR/tech-spec.md"
fi

# decisions.md
if [[ ! -f "$FEATURE_DIR/decisions.md" ]]; then
  if [[ -n "$DECISIONS_TEMPLATE" ]]; then
    sed -e "s/{Feature Name}/$FEATURE_NAME/g" \
        "$DECISIONS_TEMPLATE" > "$FEATURE_DIR/decisions.md"
  else
    echo "# Decisions: $FEATURE_NAME" > "$FEATURE_DIR/decisions.md"
  fi
fi

# interview.yml (from template)
if [[ ! -f "$FEATURE_DIR/logs/userspec/interview.yml" ]]; then
  if [[ -n "$INTERVIEW_TEMPLATE" ]]; then
    cp "$INTERVIEW_TEMPLATE" "$FEATURE_DIR/logs/userspec/interview.yml"
  else
    echo "Warning: interview template not found: interview-templates/feature.yml" >&2
  fi
fi

# checkpoint.yml (for feature-execution recovery after context compaction)
if [[ ! -f "$FEATURE_DIR/logs/checkpoint.yml" ]]; then
  if [[ -n "$CHECKPOINT_TEMPLATE" ]]; then
    sed -e "s/{feature}/$FEATURE_NAME/g" \
        "$CHECKPOINT_TEMPLATE" > "$FEATURE_DIR/logs/checkpoint.yml"
  fi
fi

if [[ "$EXISTED" == true ]]; then
  echo "Updated feature folder: $FEATURE_DIR/ (added missing structure)"
else
  echo "Created feature folder: $FEATURE_DIR/"
fi
