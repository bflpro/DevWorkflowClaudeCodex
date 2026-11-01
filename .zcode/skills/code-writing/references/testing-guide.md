# Testing Guide for Code Writing

Condensed testing rules for TDD workflow. For full testing strategy, see `.claude/skills/test-master/SKILL.md` (fallback: `~/.claude/skills/test-master/SKILL.md`).

---

## Test Quality Rules (apply when writing any test)

### Litmus Test
Before finishing any test, ask: "If I remove the core logic line being tested, does this test still pass?"
If yes — test is useless. Rewrite.

**Prove the check can redden.** You are writing the guard, so the burden is yours: a guard is
an input, a traversal and a predicate, and attention goes only to the third. An input that can
degrade to empty, or a traversal that skips an indirection, produces exactly the same green as
a passing assertion. Route "could not evaluate" — skip, empty corpus, missing fixture, unreadable
file — into the same channel as "evaluated and failed"; a self-disabling check is worse than a
missing one, because it occupies the slot where a check is believed to be. Full set of questions:
`.claude/skills/test-master/references/proving-a-check.md` (fallback: `~/.claude/skills/test-master/references/proving-a-check.md`).

### Real Data Over Mocks

**Name the author of the expected value before you write it.** As the test's writer you choose
its oracle: captured real data, an independent derivation, or the spec — never a literal copied
from the implementation's own output. Code and fixture written by the same hand in the same
sitting are one artefact, not two, and their agreement is a tautology that pins the deviation
instead of the requirement. Provenance rules in full:
`.claude/skills/test-master/references/proving-a-check.md` (fallback: `~/.claude/skills/test-master/references/proving-a-check.md`).

Priority order:
1. Real dependencies (test DB, real file system) → integration test
2. Minimal mocks (1-2 external services) → unit test
3. Heavy mocking (3+) → wrong test type, switch to integration

### No Mock-Return Pattern
```typescript
// BAD — tests mock, not code
mockService.getData.mockReturnValue(42)
const result = await handler()
expect(result).toBe(42)

// GOOD — tests actual computation
const result = await calculateTotal(100, 0.2)
expect(result).toBe(80)
```

### Test the Contract
```typescript
// BAD — tests implementation detail
expect(db.query).toHaveBeenCalledWith('SELECT * FROM users WHERE id = 1')

// GOOD — tests what goes in → what comes out
const user = await getUser(1)
expect(user.name).toBe('Alice')
```

---

## Decision: Do I Need Tests?

**YES — write tests for:**
- Business logic (calculations, validations, transforms)
- Decision-making code (if/else, switch, state machines)
- Data processing and formatting
- Error handling logic

**NO — skip tests for:**
- Simple getters/setters
- One-line text or config changes
- Trivial updates with no logic

## Decision: Which Test Type?

| Type | When to Use | Mock Strategy |
|------|-------------|---------------|
| **Unit** | Business logic, pure functions, validations | Mock DB, APIs, file system, time |
| **Integration** | API endpoints, DB operations, external services | Real DB (test), mock external services |
| **E2E** | Critical user journeys (auth, payment, core flows) | Real everything (use sandbox/test mode) |

**Rule:** If mocking >3 dependencies → wrong test type. Use integration or E2E instead.

**When to Prioritize E2E over Unit:**
- UI apps → E2E + Integration > Unit
- Browser extensions → E2E (real browser) > Unit
- CLI tools → Unit + Integration
- API/Backend → Unit + Integration

## TDD Flow

```
1. Write tests for requirements + edge cases
2. Run tests → all should FAIL (no implementation)
3. Write code to make tests pass
4. Run tests → all should PASS
5. Refactor if needed (tests stay green)
```

## Writing Good Tests

**DO:**
- One test = one scenario (happy path, error case, edge case — separate tests)
- Test behavior, not implementation details
- Use descriptive names: `test_user_creation_fails_when_email_invalid`
- Test actual results: `expect(calculateTotal(100, 0.2)).toBe(80)`
- Test real state changes: `cart.add({id: 1}); expect(cart.items).toHaveLength(1)`
- Keep tests fast: unit < 100ms, integration < 1s

**Write quality tests:**
- Write meaningful assertions that verify actual behavior
- Verify results, not just that mock was called
- Add assertions when rendering components
- Keep tests independent — each test sets up its own state
- Isolate test state — each test manages its own data

## Test Structure Pattern

```
// Arrange — set up test data and conditions
// Act — execute the function/action being tested
// Assert — verify the result
```

Group tests by feature or function. Use `describe` blocks for grouping, `it`/`test` for individual cases.

## What test-reviewer Checks

The test-reviewer agent will verify:
- Tests have meaningful assertions (not trivial)
- Tests cover requirements and edge cases
- Test names are descriptive
- Mocking is appropriate (not excessive)
- Tests are independent and isolated
- Test pyramid is balanced for the feature
