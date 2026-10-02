# Test Quality Review Guide

Methodology for analyzing quality of existing tests. Detects meaningless, ineffective, or poorly designed tests.

## Table of Contents
- [Core Philosophy](#core-philosophy)
- [Categories of Bad Tests](#categories-of-bad-tests)
- [Severity Levels](#severity-levels)
- [Review Process](#review-process)
- [Status Decision Criteria](#status-decision-criteria)
- [Task Required Decision](#task-required-decision)
- [Litmus Test Methodology](#litmus-test-methodology)
- [Prescriptive Findings](#prescriptive-findings)

**Companion references:** [proving-a-check.md](proving-a-check.md) — the canonical
question "what proves this check can go red", with the provenance, anti-vacuity, domain,
oracle-channel, fixture and completeness rules. [mutation-testing.md](mutation-testing.md)
— the executable procedure. [nondeterminism.md](nondeterminism.md) — races, clocks,
layered guards and performance assertions.

## Core Philosophy

Tests exist to:
1. Verify that code does what it should
2. Catch regressions when code changes
3. Document expected behavior

Tests that fail these purposes are worse than no tests - they provide false confidence.

---

## Categories of Bad Tests

### Category 1: Empty/Meaningless Tests

Tests that verify nothing:

```typescript
// BAD - Tests nothing
test('should exist', () => {
  expect(true).toBe(true);
});

// BAD - No assertions
test('renders component', () => {
  render(<MyComponent />);
});

// BAD - Only checks function exists
test('function defined', () => {
  expect(typeof myFunction).toBe('function');
});
```

### Category 2: Mock-Only Tests

Tests that only verify mock calls without checking results:

```typescript
// BAD - Only tests mock was called
test('calls API', async () => {
  await fetchUserData(1);
  expect(api.get).toHaveBeenCalledWith('/users/1');
  // No assertion on the actual result!
});

// BAD - Mocks everything, tests nothing real
test('processes data', () => {
  const mockProcessor = jest.fn().mockReturnValue('result');
  expect(mockProcessor()).toBe('result'); // Testing the mock!
});
```

### Mock-Return Anti-pattern

Agent mocks a dependency to return a value, then asserts the same value:

```typescript
// Tests mock wiring, not code behavior
const mockUser = { id: 1, name: 'Alice' };
mockUserService.create.mockResolvedValue(mockUser);
const result = await handler(req, res);
expect(result).toEqual(mockUser);
// Litmus test: delete handler implementation → test still passes
```

### Category 3: Missing Coverage

Code without corresponding tests:

- Business logic functions without unit tests
- API endpoints without integration tests
- Decision branches (if/else) not covered
- Error handling paths untested
- Edge cases from spec not tested

### Category 4: Test Pyramid Violations

Wrong test distribution:

```
Expected:
- Many unit tests (fast, isolated)
- Some integration tests (real DB/API)
- Few E2E tests (critical paths only)

Violations:
- All E2E, no unit tests (slow, brittle)
- Only unit tests for UI app (misses real interactions)
- Integration tests for pure logic (overkill)
```

### Category 5: Excessive Mocking

When mocking defeats the purpose:

```typescript
// BAD - Mocks 3+ dependencies
test('user service', () => {
  const mockDb = jest.mock('database');
  const mockCache = jest.mock('cache');
  const mockEmail = jest.mock('email');
  const mockLogger = jest.mock('logger');
  // At this point, what are we even testing?
});
```

**Rule:** If mocking 3+ dependencies, this should be an integration test.

### Category 6: Test Anti-patterns

- **Implementation testing** - Tests break when refactoring without behavior change
- **Snapshot abuse** - Large snapshots nobody reviews
- **Flaky tests** - Random failures due to timing/order
- **Shared state** - Tests depend on each other
- **Magic values** - Unexplained test data

### Category 7: Tautological Oracle

A test whose expected side is produced by the same source as the actual side. It
cannot fail on the thing in dispute, and it looks more authoritative than an honest
test, because the duplication a correct test needs reads as a smell.

```python
# BAD - expectation imported from the subject: any value of the constant passes
from src.queue import MAX_ATTEMPTS
assert attempts == MAX_ATTEMPTS

# BAD - spec section is executable, but its contents were retyped as literals
assert tables == {"eval_queue", "action_queue", ...}   # typed off the implementation

# BAD - both ends of a cross-module contract taken from one end
assert set(CHANNEL_MAP) == EXPECTED_CHANNELS   # both live in the reader

# BAD - the fake declares the parameter the subject also declares
FakeClient(page_size=50)   # subject's PAGE_SIZE is now dead and nothing notices
```

Severity: **high** when the tautology covers the property under dispute, **critical**
when it is the only check on a business-critical guarantee.

Review question, per asserted literal: *where did this value come from, and does that
source move when the code moves?* Full taxonomy and fixes:
[proving-a-check.md](proving-a-check.md) §1 and §5.

Adjacent shapes with the same effect:

- A conditional `skip` that fires when the oracle is unavailable — the state most
  correlated with drift.
- An absence check (`! grep ...`) with no existence anchor, so an error of the
  instrument renders as a pass.
- A grep-shaped acceptance criterion that is already green on the starting revision.
- An ordering assertion standing in for a formula, or a name/docstring that claims more
  than the assertion makes.
- A check discharged as a sentence in a completion report rather than as a running
  artefact.

---

## Severity Levels

### Critical
- No tests at all for business-critical code
- Tests that actively hide bugs (incorrect assertions)
- All tests are empty/meaningless (false coverage)
- A tautological oracle is the only check on a business-critical guarantee

### High
- Missing tests for error handling
- Tests verify only mock calls (no result checking)
- Key acceptance criteria not tested
- Tautological oracle covering the property under dispute (expected value imported
  from the subject, executable spec artefact retyped, both ends of a cross-module
  contract taken from one end)
- A guard that cannot go red: conditional skip over a missing oracle, absence check
  with no existence anchor, criterion already green on the starting revision

### Medium
- Excessive mocking (should be integration test)
- Test pyramid violation (wrong test type used)
- Edge cases from spec not covered

### Low
- Minor best practice violations
- Could be more specific assertions
- Naming improvements needed

---

## Review Process

1. **Identify Test Files**: Find all test files for reviewed code
2. **Map Coverage**: Match implementation files to test files
3. **Analyze Each Test**:
   - Does it have meaningful assertions?
   - Does it test real behavior or just mocks?
   - Does it cover the right scenarios?
   - Where did each asserted literal come from, and does that source move when the
     code moves? (tautological oracle — [proving-a-check.md](proving-a-check.md) §1)
   - Has it been observed red for the reason it exists? Walk the seven-point checklist
     at the end of [proving-a-check.md](proving-a-check.md).
4. **Check Pyramid Balance**: Assess unit/integration/E2E distribution
5. **Find Gaps**: Identify untested code paths
6. **Run the litmus test** on the load-bearing checks — executed, not imagined
   ([mutation-testing.md](mutation-testing.md))
7. **Categorize Findings**: Group by category and severity

---

## Status Decision Criteria

### passed
- All tests have meaningful assertions
- Critical business logic is tested
- Test pyramid is reasonably balanced
- Minor suggestions only (low severity)

### needs_improvement
- Some tests need better assertions (medium severity)
- Some coverage gaps exist (non-critical areas)
- Pyramid slightly unbalanced
- No critical issues

### failed
- Tests are meaningless (empty or mock-only)
- Critical business logic untested
- Tests hide bugs (wrong assertions)
- Test pyramid severely inverted
- Multiple high/critical severity issues

**Decision matrix:**
- `critical > 0` → failed
- `high >= 3` → failed
- `high >= 1 AND medium >= 3` → needs_improvement
- `medium >= 5` → needs_improvement
- Only low issues → passed
- No issues → passed

---

## Task Required Decision

Set `taskRequired.needed = true` when:
- status === "failed"
- critical > 0
- high >= 2
- Critical business logic has no tests

Set `taskRequired.needed = false` when:
- status === "passed"
- Only low/medium issues
- Issues can be fixed in current context

---

## Litmus Test Methodology

**The litmus test is executed, not imagined.** Break the code, run the suite, observe
the colour, restore. A mentally-traced removal samples the reviewer's model of the code,
which is the same model that produced the test — so it agrees with itself exactly where
the gap is.

Minimum executable form, per test touching business logic:

1. Identify the smallest independently breakable decision it claims to cover — a
   comparison, a boundary constant, a boolean clause, an early return, one term of a
   formula, one row of a lookup table.
2. Change it in an isolated checkout pinned to the revision under review.
3. Prove the edit applied (unique text anchor, occurrence count asserted) and that it
   changes behaviour.
4. Run the designated killing test, which must have been **green before** the change.
5. Restore from the revision, not from a sidecar the procedure itself wrote.

If the suite stays green, that is a survivor — **a hypothesis about the instrument
before it is a finding about the tests.** Qualify it against the four routes to a
survivor line (genuinely blind / never applied / semantically inert / not exercised by
the chosen test's fixture) before reporting it.

**Full procedure, harness checklist, how to derive the mutant set and how to read the
result: [mutation-testing.md](mutation-testing.md).** That file is the single recipe;
do not improvise a second one here.

**Boundary question for concurrency tests:** which layer serialises the callers this
test starts, and is that the same layer the property belongs to? See
[nondeterminism.md](nondeterminism.md) §3.

**Common patterns that fail the litmus test:**

- Mock returns X, test asserts X (passes with an empty function)
- Test only asserts `mock.toHaveBeenCalled()` (passes with any call)
- Test uses the same hardcoded data for input and expected output
- Expected value imported from the module under test
- Arrange step writes the sentinel that makes the guard under test vacuous
- Test arranges through the subject's own API, so a cache stays coherent with itself
- Test calls the unit directly where production calls a wrapper that could be unwired

## Prescriptive Findings

Every finding must include a concrete replacement, not just a problem description.

**Bad finding:**
```json
{ "issue": "Test has no meaningful assertions", "recommendation": "Add assertion that verifies actual behavior" }
```

Every prescribed verify command must itself have been run once against a deliberately
wrong subject before it is recommended: a negation turns every failure of the instrument
into a pass, and a recipe that is safe as a pair stops being safe when one half is reused
alone. If you prescribe a guard as code, apply it together with the mutant in your own
copy and show the red — otherwise prescribe the required behaviour ("this guard must
redden on mutant X") and leave the form to the implementer.

**Good finding:**
```json
{
  "issue": "Mock returns mockUser, test asserts mockUser — tests mock wiring, not code",
  "litmusTestFailed": true,
  "replacement": {
    "approach": "Call real createUser with test data, assert on actual result",
    "assertions": ["result.id is defined", "result.email === input.email"],
    "mockChange": "Remove mockUserService, use test DB"
  }
}
```
