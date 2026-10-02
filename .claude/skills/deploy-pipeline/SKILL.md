---
name: deploy-pipeline
description: |
  Sets up CI/CD pipelines, deployment configuration, and automated deploy workflows.
  GitHub Actions, platform-specific deploy (Vercel, Railway, Fly.io, AWS, VPS),
  secrets management in CI.

  Use when: "подготовь деплой", "настрой автодеплой", "настрой CI/CD",
  "setup deploy", "configure deployment", "настрой пайплайн"
---

# Deploy Pipeline

## Gathering Deployment Context

Read project-knowledge to understand the deployment target:
- `.claude/skills/project-knowledge/references/deployment.md`
- `.claude/skills/project-knowledge/references/architecture.md`
- `.claude/skills/project-knowledge/references/patterns.md`

If deployment target is not documented, ask the user:
- Target platform (Vercel, Railway, Fly.io, AWS ECS, VPS, NPM, Chrome Web Store)
- Environment details (URLs, project/service IDs, server access)
- Required secrets and where to obtain them

After gathering answers, immediately update `deployment.md` before proceeding with setup.

## CI/CD Convention

Create `.github/workflows/ci.yml` following this structure:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check-skip:
    runs-on: ubuntu-latest
    outputs:
      should_skip: ${{ steps.check.outputs.should_skip }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - id: check
        run: |
          FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only HEAD)
          if echo "$FILES" | grep -vqE '\.(md|txt)$|^\.claude/|^\.spec/|^docs/'; then
            echo "should_skip=false" >> $GITHUB_OUTPUT
          else
            echo "should_skip=true" >> $GITHUB_OUTPUT
          fi

  test:
    needs: check-skip
    if: needs.check-skip.outputs.should_skip != 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # setup, install, lint, type-check, test, build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # platform-specific deploy action
```

Adapt: add language setup, install steps, platform-specific deploy action.

## Platform Selection

| Platform | Choose when |
|----------|------------|
| Vercel | Next.js, React, static sites, serverless |
| Railway | Full-stack apps needing managed DB |
| Fly.io | Docker containers, global edge |
| AWS ECS | Enterprise, full infrastructure control |
| Custom VPS | Persistent sessions, multi-device |
| NPM | Node.js packages or CLI tools |
| Chrome Web Store | Browser extensions |

For VPS deployments: server-specific details (IPs, SSH keys, paths) go to `deployment.md`.

## Secrets Convention

Document all required secrets in `.claude/skills/project-knowledge/references/deployment.md`. For each secret:
- Name (CI / secret-store key)
- Where to obtain value (dashboard URL or CLI command)
- Which workflow uses it
- **How the pointer is proven to resolve to the right record, and what the step does when
  authentication fails.** A pointer is a path into a store — a file, a vault entry, a manager item,
  an env var name — and pointers go stale by pointing at *something valid that belongs to someone
  else*. A nearby word in an unrelated entry ("admin", the service's name) is enough to make a wrong
  parse succeed, and the result surfaces much later as an object with the wrong owner, not as a
  failed login. So record: the unique marker that identifies the correct record (entry id, key name,
  fingerprint, account the credential belongs to), the command that checks it without printing the
  secret, and the step's behaviour on an auth failure — **stop and report, never fall back to a
  default identity and never continue with a partially applied deploy**.

Where a privilege has to be granted as part of the deploy (a role, a scope, an ACL entry), record
the **exact label the operator sees in the UI**, not only the API name. Rights whose API name has no
entry in the UI label map hide in the console under a generic group such as "additional
permissions", and a grant procedure written without that mapping does not match what the person is
looking at.

Guide user to add secrets in the repository or platform secret store. Create `.env.example` with application-level variable names.

## Verification

Setting a pipeline up is not evidence that it runs. Two separate questions — *did the step do its
job*, and *did the automation fire on its own* — and neither is answered by "the command exited 0".

### Verification of a deploy step

Tool-independent: applies equally to a CI job, an `rsync`/`cp` to a server, or a manual runbook step.

- **Check the exit status, not the presence of output.** A step wrapped in a line count, a `tee`, or
  any pipe reports the *last* command's status, so a failure reads as "copied 0 files" rather than as
  an error. Use `set -euo pipefail`, or check the status of the command that matters explicitly.
- **Zero is not a verdict.** After the step, assert the expected end state: the artifact is present,
  its checksum matches the source, the service came up on the new version. Do the comparison
  **before** the restart — a check that runs after it cannot undo it.
- **Directory-sync deploys ship the whole accumulated drift, not your change.** Make a dry run
  (`--dry-run`, `diff -r`) a required step and keep its output as part of the record, not as a glance.
- **Never stage through a shared temporary directory.** Another run's file with the same name gets
  shipped, and a failed write there does not stop the deploy. Unpack and build into a
  per-run unique path.
- **Write verification commands for the widest future reader** — a receipt committed to git, a
  colleague's terminal, a CI log — not for the person typing them now: absolute paths, no interactive
  flags, no dependence on the current directory, shell aliases or an already-loaded environment.
- **Changing the shell or environment of a service account invalidates the guards attached to it**
  (forced command, restricted shell, `command=` in `authorized_keys`). Re-run the negative security
  checks *after* the change and *as that account*; run before, they are green by inertia.

### Verification of the automation itself

Only an event nobody ordered proves the automatic part:

- A scheduler's first run started by `enable --now` is the manual start. The proof is a run whose
  timestamp falls on a tick nobody triggered, plus its effect at the destination.
- A successful manual end-to-end pass along the production path proves the path. It is routinely
  remembered by the team as "the automation is on" — record explicitly which half was shown.
- A privilege created by a migration is not a privilege held by anyone. Grant it as an owned deploy
  step and verify the holder, not the existence of the right.
- A procedure that was written but not executed is not a satisfied precondition — and several steps
  later it looks like one. Mark it unexecuted where the next step will read it.

Until that unrequested event is observed, record the pipeline as *installed, not proven*, and name
the single observation that would close it.

## Documentation Updates

After configuring, update project-knowledge references. Append to existing content.

**deployment.md:** deploy target, pipeline overview, required secrets table, manual deploy command, rollback steps.

**patterns.md (Git Workflow section):** CI triggers, pipeline jobs, skip logic pattern, PR workflow.

## Decision Framework

**Add deploy job?**
YES if: deployment target defined, user requests it, stable main branch.
NO if: early development, manual deploys preferred, manual review step needed (Chrome Web Store).

**Use matrix strategy?**
YES if: NPM package, cross-platform library.
NO if: single-environment app, internal tool.

**Add staging?**
YES if: project uses main + dev branches (default workflow).
NO if: Vercel preview deploys sufficient.
