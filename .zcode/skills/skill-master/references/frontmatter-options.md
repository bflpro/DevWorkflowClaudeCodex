# Optional Frontmatter Fields

These fields are NOT required for most skills. Use only when needed.

## Field Reference

| Field | Default | Description |
|-------|---------|-------------|
| `argument-hint` | None | Autocomplete hint shown after skill name |
| `disable-model-invocation` | `false` | If `true`, skill only triggers manually via `/skill-name` |
| `user-invocable` | `true` | If `false`, skill hidden from `/` menu, only the model can invoke |
| `allowed-tools` | All tools | Restrict which tools the skill can use |
| `model` | `inherit` | Override model: `GLM-5.3`, `GLM-5.3-Flash`, `inherit` |

## When to Use Each Field

### argument-hint

Shows hint in autocomplete to guide user input.

```yaml
---
name: fix-issue
argument-hint: "[issue-number]"
---
```

User sees: `/fix-issue [issue-number]`

### disable-model-invocation

Prevents Claude from auto-triggering the skill. Only manual `/skill-name` works.

```yaml
---
name: dangerous-operation
disable-model-invocation: true
---
```

Use for: destructive operations, expensive API calls, operations requiring explicit user consent.

### user-invocable

Hides skill from `/` menu. Only Claude can invoke it programmatically.

```yaml
---
name: internal-helper
user-invocable: false
---
```

Use for: helper skills that shouldn't appear in user-facing menu, internal utilities.

### allowed-tools

Restricts which tools the skill can access.

```yaml
---
name: read-only-analyzer
allowed-tools: Read, Grep, Glob
---
```

Use for: read-only analysis skills, security-conscious operations, preventing accidental edits.

### model

Overrides the model used for this skill.

```yaml
---
name: quick-lookup
model: GLM-5.3-Flash
---
```

Options:
- `inherit` — use orchestrator's model (default, recommended)
- `GLM-5.3` — standard work (routine tier)
- `GLM-5.3-Flash` — fastest, use for simple lookups

Use sparingly. `inherit` is usually best.
