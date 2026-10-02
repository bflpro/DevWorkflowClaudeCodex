---
description: Initialize project with template, git, and GitHub
allowed-tools:
  - Bash(*)
  - Read
  - Edit
  - TodoWrite
---

# Init Project

## 1. Check Uncommitted Changes

If inside a git repo with uncommitted changes — ask user whether to commit first, continue without commit, or stop.

## 2. Apply Template

Move existing files to `old/` (find next available name: `old`, `old2`, `old3`...):

```bash
OLD_DIR="old"
N=2
while [ -e "$OLD_DIR" ]; do OLD_DIR="old${N}"; ((N++)); done
mkdir "$OLD_DIR"
find . -maxdepth 1 ! -name '.' ! -name '..' ! -name '.git' ! -name "$OLD_DIR" -exec mv {} "$OLD_DIR/" \;
```

Copy template:

```bash
# cwd здесь — НОВЫЙ проект, поэтому путь к шаблону абсолютный.
# Источник — клон DevWorkflowClaudeCodex или любой проект, куда workflow уже установлен;
# путь задаётся переменной WORKFLOW_SOURCE. Домашняя копия — запасная.
# Нет ни того, ни другого — остановиться и спросить путь у человека, не создавать пустышку.
if [ -n "${WORKFLOW_SOURCE:-}" ] && [ -d "$WORKFLOW_SOURCE/.claude/shared/templates/new-project" ]; then
  cp -rp "$WORKFLOW_SOURCE/.claude/shared/templates/new-project/." .
elif [ -d ~/.claude/shared/templates/new-project ]; then
  cp -rp ~/.claude/shared/templates/new-project/. .
else
  echo "Template not found: set WORKFLOW_SOURCE=<path to DevWorkflowClaudeCodex clone>"; exit 1
fi
# Затем поставить сам workflow в новый проект:
#   "$WORKFLOW_SOURCE/install.sh" --target .   (добавить --codex для Codex)
```

After copy:
- Verify `.claude/skills/project-knowledge/` exists
- Security check: look for sensitive files in `$OLD_DIR/` (`.env*`, `*.key`, `*.pem`, `credentials.json`, `secrets/`) not covered by `.gitignore`. If found — add to `.gitignore` before proceeding.

## 3. Init Git and GitHub

1. Init git if not initialized
2. Verify `gh` CLI is installed and authenticated
3. Ask user for GitHub repository name
4. Create repo: `gh repo create {name} --private --source=. --remote=origin`
5. Initial commit and push to current branch
6. Create `dev` branch, push it

## 4. Final Report

Show user:
- GitHub URL
- Branches created
- Old files location (`old/`) if any existed
- Next step: run `project-planning` skill to fill project documentation
