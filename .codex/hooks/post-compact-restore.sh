#!/usr/bin/env bash
# Compatibility entrypoint; use it with SessionStart(compact), not PostCompact.
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HOOK_DIR/workflow-hooks.py" session-start
