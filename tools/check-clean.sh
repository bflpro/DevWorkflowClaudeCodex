#!/usr/bin/env bash
# Leak guard for the public repository: fails if any tracked file mentions
# the origin company, its services, people, hosts, or upstream authorship.
# Usage: bash tools/check-clean.sh            (scan working tree)
# Exit 0 = clean, 1 = findings printed as path:line:match.
set -euo pipefail
cd "$(dirname "$0")/.."

PATTERN='molyanov|molianov|молянов|малянов|pavel|bfl|бфл|bitrix|битрикс|\bb24|lfsp|wazzup|plusofon|плюсофон|podpislon|подпислон|inovatson|planfact|аргус|\bargus|hermes|sherlock|шерлок|(^|[^а-яё])альтер([^а-яё]|$)|сергей|sergey|storozhenko|стороженко|мазаев|демьянков|банкрот|bankrupt|onedash|beget|kuma push|grafana /d/|/home/bfl|AG-[a-zA-Z]|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'

# This file and LICENSE (legally required notice) are the only exemptions.
files=$(git ls-files --cached --others --exclude-standard \
  | grep -vE '^(tools/check-clean\.sh|LICENSE)$' \
  | grep -vE '/LICENSE$')

n_files=$(printf '%s\n' "$files" | grep -c . || true)
[ "$n_files" -gt 0 ] || { echo "check-clean: no files listed — wrong directory?"; exit 2; }

hits=$(printf '%s\n' "$files" | tr '\n' '\0' \
  | xargs -0 grep -nIiE "$PATTERN" -- 2>/dev/null \
  | grep -vE '127\.0\.0\.1|0\.0\.0\.0|[^0-9]1\.2\.3\.4' \
  | sed -E 's#github\.com/bflpro/DevWorkflowClaudeCodex#<this-repo>#g' \
  | grep -iE "$PATTERN" || true)

if [ -n "$hits" ]; then
  printf '%s\n' "$hits"
  echo "check-clean: $(printf '%s\n' "$hits" | wc -l | tr -d ' ') finding(s) in $n_files files scanned"
  exit 1
fi
echo "check-clean: OK, $n_files files scanned"
