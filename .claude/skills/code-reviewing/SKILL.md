---
name: code-reviewing
description: |
  Code review methodology and quality standards for comprehensive code analysis.
  Use to understand WHAT and HOW to review code: 11 review dimensions, process, quality standards.

  Use when: "проверь код", "code review", "ревью кода", "review this code", "check code quality"
---

# Code Review Methodology

Comprehensive code review methodology for ensuring production-ready quality and maintainable architecture.

## Review Dimensions

Perform systematic analysis across these 11 dimensions:

### 1. Architectural Patterns

- Evaluate adherence to established architectural patterns (MVC, MVVM, Clean Architecture, etc.)
- Assess design patterns usage (Factory, Strategy, Observer, etc.)
- Verify layer separation and dependency direction
- Check for architectural anti-patterns (circular dependencies, god objects, tight coupling)

### 2. Separation of Concerns

- Validate single responsibility principle compliance
- Examine module boundaries and cohesion
- Review business logic vs presentation logic separation
- Assess data layer abstraction and persistence logic isolation

**Good practices:**
- One file = one responsibility (UserService in one file, PaymentService in another)
- Functions < 50 lines; if larger, break into smaller functions
- Maximum 3 levels of nesting; use early returns to reduce nesting
- High-level modules should not depend on low-level details

### 3. Code Readability & Maintainability

- Evaluate naming conventions (variables, functions, classes)
- Assess code organization and file structure
- Check for appropriate use of comments and documentation
- Review complexity metrics (cyclomatic complexity, nesting depth)
- Verify consistent code style and formatting

**Good practices:**
- Meaningful comments focus on "why" rather than obvious "what"
- DRY principle: extract repeated code into functions/modules
- Readable > clever: clear code is better than short but cryptic code
- No magic numbers: extract to named constants (`MAX_UPLOAD_SIZE` not `5242880`)
- For every literal carried over from a spec or task, ask **on which value the format was verified**.
  A plain value crossing into a language that interprets characters (glob, regex, SQL, shell, a
  separator inside a composite key) is a conversion with its own correctness question, and faithful
  transcription propagates the defect with the spec's authority behind it — every downstream check
  then confirms the match rather than the meaning
- A separator is an unwritten claim about the alphabet of the parts. A template tested against a
  literal from its own author proves only self-consistency; the defect surfaces at the first foreign
  producer and looks there like that producer's bug

### 4. Error Handling & Logging

- Examine error propagation strategy
- Verify appropriate use of try-catch blocks
- Check error messages clarity and actionability
- Assess graceful degradation and fallback mechanisms

**Good practices (error handling):**
- Always use try-catch for operations that can fail (API calls, DB operations, file I/O)
- Don't swallow errors: always re-throw after logging (unless explicitly handling)
- Fail fast: validate inputs early; throw errors immediately when invalid
- User-friendly errors: show generic message to users, log details internally

**Logging review checklist:**
- Key operations have logs (external calls, auth events, state transitions, business operations)
- Structured format used (JSON / logger library), not string concatenation or `console.log`
- Every log includes context: userId, action, resourceId (not just a bare message)
- Correlation/request ID propagated through call chain
- Log levels used correctly (info for success, warn for recoverable, error for failures)
- Error logs include stack traces
- No secrets or PII in logs (passwords, tokens, API keys, emails, phone numbers)
- No empty catch blocks (`catch (e) {}` — silent error swallowing)
- No logging inside tight loops (generates thousands of duplicate lines)

**Automatic severity mappings.** Two rules govern every row below, and without them the table is
not deterministic — reviewers override it ad hoc, and an override nobody specified is not a rule.

- **Precondition (applies to every row):** the pattern is INTRODUCED or MODIFIED by the change under
  review. Baseline = the same paths at the revision the change starts from. A pattern inherited
  unchanged is reported one level lower and labelled `pre-existing`; a pattern the change makes worse
  (more call sites, wider scope) is scored on the delta, not the absolute state. A row whose
  precondition does not hold is context, not a finding
- **Applicability, not existence:** each row asks "for which operations is this correct, and does it
  apply only there", never "is it present". A safety mechanism and its precondition belong in one
  question — bounded retry around a non-idempotent external write is not a pass, it is the defect

| Pattern | Severity |
|---------|----------|
| Secrets or PII logged (tokens, passwords, emails in plaintext) | critical |
| Empty catch block — error swallowed without logging | major |
| External call (API, DB) without any logging | major |
| Absent input treated as a decision — a blank encodes "chose the default" and "answered nothing" identically | major |
| Terminal negative result (an empty answer that a re-run would reproduce) raised or retried as a failure | major |
| Skip or anti-overwrite guard with no named path to force the action — a blocked update reports success | major |
| Ambiguous input resolved silently by the parser ("last one wins") instead of rejected | major |
| Bounded retry applied to a write that is not idempotent | major |
| Missing correlation/request ID in service handling requests | minor |
| `console.log` / `print` used instead of structured logger | minor |

### 5. Type Safety (TypeScript/typed languages)

For TypeScript or other typed codebases:

- Validate type definitions completeness and accuracy
- Check for inappropriate use of `any` type (TypeScript) or equivalent loose typing
- Assess interface and type alias design
- Review generic type usage and constraints
- Verify null/undefined handling and optional chaining
- Check for type assertions and their justification

### 6. Testing Coverage

- Evaluate unit test presence and quality
- Assess test coverage for critical paths
- Review test organization and naming
- Check for integration and E2E test needs
- Verify mocking strategies and test isolation
- Assess edge case and error scenario coverage

**Good practices:**
- Tests needed for: business logic, validations, transforms, error handling
- Tests not needed for: simple getters/setters, one-line configs, trivial updates
- Rule: if mocking >3 dependencies → wrong test type, use integration test

**Who authored the expected value?** For each assertion, ask where the expected value came from:
captured real data, an independent derivation, or the spec. A literal copied from the implementation's
own output makes the test a mirror of the code — it cannot detect divergence from the requirement, and
it reliably protects an existing divergence from being fixed, while being outwardly indistinguishable
from a real conformance check. You are judging a finished guard, so the question is evidential, not
stylistic: name the second source, or the assertion has one.
Full set of questions — provenance, anti-vacuity, non-empty input, traversal scope, differential
oracle: `.claude/skills/test-master/references/proving-a-check.md` (fallback: `~/.claude/skills/test-master/references/proving-a-check.md`).

**Judging a guard requires breaking the code, not reading the test.** Reading tells you what the guard
was written to do; only mutating tells you what it detects, and the gap between the two is exactly where
a sincere "this now covers all of X" lives. Wherever a claim takes that form, the only discriminating
evidence is a new member of X the claimer never saw. Run your own recipe and your own mutant yourself
before reporting the verdict — a recipe handed to someone else is an untested instrument, and a guard
rebuilt on the same idiom that just failed is worse than none, because it converts an open finding into
a documented closed one. Procedure, isolation, restore and cache-invalidation rules:
`.claude/skills/test-master/references/mutation-testing.md` (fallback: `~/.claude/skills/test-master/references/mutation-testing.md`). Never mutate a shared working tree: a
captured mutation is a fabricated defect arriving through the channel reviewers trust absolutely.

### 7. Dependencies Management

- Review new dependencies necessity and appropriateness
- Check for dependency version conflicts
- Assess bundle size impact
- Verify security vulnerabilities (outdated packages)
- Evaluate licensing compatibility

**Good practices:**
- Verify imports exist before using: read source files to confirm exports match expected usage
- Check function signatures: ensure signatures match how you're calling them
- Prefer well-maintained packages: check npm/PyPI activity, security advisories
- Pin major versions: use `^` (caret) for npm to allow patch updates
- **Check every inherited default at the point of use, not the point of definition:** a limit, timeout,
  page size or retry count taken from a library, config or a caller's constant answers the question its
  author asked, not this one — and a parameter that is not passed leaves no trace in the diff
- **A guarantee asserted by an intermediary is not a guarantee:** a router, proxy, gateway or SDK wrapper
  moves enforcement from the vendor to whichever backend it picked this time. Re-verify the contract where
  it is used, positioned where the violation happens rather than where its consequences surface — the
  failure to design against is the accepted response whose content quietly does not match its declared shape
- **An API reference answers "how to call", never "how much is allowed":** a product limit an architecture
  rests on is a separate lookup, usually in user-facing rather than technical docs, and its absence from
  the technical reference is not evidence that no limit exists. Reading current state ("ten in use") yields
  facts, never the rule that interprets them
- **A format documented but unvalidated is a suggestion:** the moment a script becomes a reader, every
  tolerated variant becomes a bug — validation belongs on the receiving side the day the format is written

### 8. Security Considerations

- Check for security vulnerabilities (injection, XSS, CSRF)
- Verify secrets management (no hardcoded credentials)
- Assess input validation and sanitization
- Review authentication and authorization logic
- Check for sensitive data exposure

**Good practices:**
- Never hardcode secrets: use environment variables (`.env`) for all sensitive data
- Always validate input: check types, formats, ranges before processing
- Sanitize user data: before database operations, API calls, or displaying
- Add to .gitignore: `.env`, `*.key`, `credentials.json`, `secrets/`
- **Redaction keyed on field NAME is blind to the same secret in another carrier:** free text, a log
  message, a URL, an error body, a filename, a metadata field. A detector encodes an assumption about
  what makes its target recognisable, and that assumption belongs to the carrier, not the target — so
  "our redaction is well tested" is fully compatible with a total blind spot, because the tests sample
  the carrier the rules were designed for. Wherever a value crosses representations, the recogniser must
  re-key on whatever the new representation supplies
- **The review artefact is itself a carrier:** never quote a secret, token or PII value into a finding,
  a report, a log excerpt or a scratch note. Evidence about a leak gets promoted from scratch space into
  the record, and an ignore rule contains nothing once someone crosses it on purpose. Cite location and
  shape only — `file:line`, "32-hex token", "phone number in the message body"

### 9. Performance Implications

- Identify potential performance bottlenecks
- Review algorithmic complexity
- Check for unnecessary re-renders (React) or recomputations
- Assess memory leak risks
- Evaluate database query efficiency

**Good practices:**
- Avoid N+1 queries: use batch operations, eager loading, or caching
- Cache expensive computations: use memoization for functions
- Prevent memory leaks: clean up event listeners, timers, subscriptions in cleanup functions
- Use pagination for large datasets: don't load all records at once
- Profile before optimizing: measure actual bottlenecks before making changes

**When a change claims an improvement, check which quantity was measured.** A measurement taken at the
link nearest the change systematically overstates the outcome — the promise is about the end result, the
number is about one step, and the nearest link always improves the most. Ask for the end-to-end figure
over replayed real cases, and for the remainder named out loud. Two further shapes to reject:
- a total and its breakdown computed over different populations — the pair silently asserts that the
  second explains the first, and normalising the breakdown to its own sum hides the disagreement exactly
  when there is one
- attribution by time proximity without a check on the interval's sign: "near" and "after" are different
  claims, and the resulting false positives arrive in the same format and the same report as real findings.
  An aggregate is trusted only after reading several of its individual rows in full

### 10. Cross-File Consistency

For the code under review, verify correctness of function/class usage:

**Process:**
1. When code CALLS a function from another file → Read that file, verify signature matches
2. When code USES a class/method → Read class definition, verify method exists and signature matches
3. When code IMPORTS something → Verify import path is correct
4. When code FILTERS by a set of values (whitelist, status enum, allowed types, a sweep's notion of
   "what belongs here") → enumerate every writer of that field. The set alone is a claim about intent;
   only its intersection with the writers is a claim about behaviour, and the two halves drift
   independently — a set grows entries nothing produces, a producer starts emitting a value nobody added.
   The cheap instrument is an exhaustive grep of the writers, never a careful reading of the set. Same
   for a cleanup or GC operation: a new writer to a shared store defaults into "foreign" until its shape
   is registered with the sweeper, and an existing exemption marks the registration point
5. For every field crossing a module boundary → check BOTH axes: **form** (type, shape, units) and
   **reference frame** (timezone, currency, base, origin, encoding). A contract that fixes only the form
   leaves both sides formally correct with different meanings, and neither side's review nor a corpus
   built on a single reference frame can see it
6. When code BRANCHES on how an object was found (which query, which source) rather than on what it is →
   report it. The path is a property of the query, not of the object; it coincides with the needed property
   only while the queries are few, and the mismatch is invisible on reading because source names describe
   the query author's intent
7. A field one side reads and no side writes → two green test suites and one quietly dead feature: absence
   reads as "no history", not as "broken". Reconnaissance goes by names of external state units, checking
   both roles — writer and reader — for each

**What to check:**
- Function called with correct arguments
- Method exists on the class
- Import paths are valid
- Types match (if TypeScript)

**Report as issue if:**
- Function called with wrong arguments (runtime crash)
- Method doesn't exist (runtime crash)
- Import path broken (load failure)

Read the source files where functions/classes are defined to verify signatures match.

### 11. Resource Management

- Identify heavy resources: ML models, database connection pools, browser instances, API clients, large caches
- Check if heavy resources are created as singletons (one instance shared) or duplicated across files/components
- When code creates a heavy resource (`new Model()`, `ModelClass(...)`, `create_pool()`): search the project for other instantiations of the same class
- Verify resource lifecycle: who creates, who consumes, when disposed
- Check for resource leaks: opened connections/files/handles that are never closed
- A cleanup or shutdown handler that reaches the resource through a **lazy accessor creates what it means
  to destroy**: the destruction path must use an interface incapable of construction — the symmetry comes
  from the absent call, not the author's discipline

**Automatic severity mappings.** Same two rules as §4: the **precondition** is that the change under
review introduces or modifies the pattern (baseline = the same paths at the starting revision;
inherited-unchanged drops one level and is labelled `pre-existing`; worsened is scored on the delta),
and each row asks for which operations the pattern is correct rather than whether it is present.

| Pattern | Severity |
|---------|----------|
| Same heavy resource class instantiated in multiple files without shared instance | major |
| Heavy resource created inside a loop or per-request handler | critical |
| Resource opened but never closed (connection, file handle, cursor) | major |

## Dimension Prioritization

Focus on dimensions based on code context:

| Context | Prioritize | Reason |
|---------|------------|--------|
| Auth/login code | Security (8), Error Handling (4) | Auth vulnerabilities are critical |
| User input handling | Security (8), Type Safety (5) | Input validation prevents attacks |
| Database queries | Security (8), Performance (9) | SQL injection, N+1 queries |
| New feature | Architecture (1), Testing (6) | Foundation for future changes |
| Refactoring | Cross-File (10), Testing (6) | Avoid breaking existing code |
| Performance fix | Performance (9), Dependencies (7) | Target the actual bottleneck |
| Typed codebase | Type Safety (5), Cross-File (10) | Type errors cause runtime crashes |
| ML/AI pipeline | Resource Mgmt (11), Performance (9) | Heavy models duplicated waste memory |
| Microservice init | Resource Mgmt (11), Architecture (1) | Connection pools and clients should be shared |

## Review Process

1. **Initial Scan**: Quick overview to understand scope and context. **Pin the artefact state you are
   judging** — the commit sha, or a hash per file for an uncommitted tree — and record it in the report.
   A review is a statement about a specific state of an artefact, yet every tool reports the *current*
   state and none reports *which*; findings indexed by `file:line` degrade into confident nonsense
   without emitting a single error. Re-check before issuing the verdict, on the **paths under review,
   not on HEAD**: HEAD moving because unrelated work landed does not invalidate the run, and the
   reviewed files can change with no commit at all. The failure is silent in both directions — fixed
   defects reported as open, defects introduced after the read never looked at
2. **Deep Analysis**: Systematic review of each dimension listed above
3. **Cross-Reference**: Compare implementation against userspec, techspec, and project standards
4. **Issue Categorization**: Classify findings by severity:
   - **critical** → blocking issues that must be fixed
   - **major** → significant concerns that should be addressed
   - **minor** → improvements that are valuable but optional
5. **Recommendation Formulation**: Provide specific, actionable suggestions. **Every fix recipe states
   the scope it reaches by enumeration** — the sites found, the branches of the classifier covered, the
   carriers the pattern can inhabit — or carries the literal note "N not measured". A recipe that pairs a
   verb of widening ("harden all callers", "apply everywhere") with the small count of motivating instances
   describes two different blast radii: the number came from the evidence, the verb from the mechanism, and
   each half is correct on its own. Check also that any proof obligation you attach is not silently a filter:
   a constraint written to make the fix safe also partitions the fix's sites into those that can satisfy it
   and those that cannot, and the dangerous outcome is closing the finding as done

## Quality Standards

Be thorough but pragmatic:
- Focus on issues that materially impact code quality, security, or maintainability
- Distinguish between critical problems and stylistic preferences
- Provide constructive feedback with specific examples
- Acknowledge good practices when present
- Consider project context and constraints from project documentation (if available)
- Balance idealism with practical delivery needs

## Review Report

A review's conclusions must leave a machine-readable trace, not prose alone. A conclusion reached in
prose and a conclusion written into the field that accounting reads are two different artefacts, and
only the second is counted — the discrepancy always points the same way, toward "not done", and it is
indistinguishable from genuine non-performance. Every report carries:

- `reviewed_revision` — the commit sha, or per-file hashes, the findings are indexed against
- `verdict` — an explicit `approved` | `changes_required` field, filled in the same act as the analysis,
  never left to be remembered afterwards
- `findings[]` — each with severity, `file:line`, whether the pattern is `introduced` or `pre-existing`
  (per the severity-table precondition), and the measured scope of the suggested fix, or "N not measured"
- No secret, token or PII value anywhere in the report — location and shape only, per §8

## Communication Style

- Be direct and specific - avoid vague feedback
- Use technical precision appropriate for senior developers
- Provide code examples in recommendations when helpful
- Explain the "why" behind each issue, not just the "what"
- Maintain professional, respectful tone
- Prioritize actionability over completeness

Goal: ensure production-ready code that is secure, maintainable, and aligned with project standards. Be thorough in analysis but efficient in communication.
