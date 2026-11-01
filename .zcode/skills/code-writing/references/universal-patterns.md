# Code Patterns & Best Practices

Universal coding standards for generating high-quality code. Always applied as baseline for all projects.

---

## Naming Conventions
- **Functions/Methods**: verbs (`createUser`, `fetchData`, `validateEmail`)
- **Variables**: descriptive nouns (`userData`, `totalPrice`, `isActive`)
- **Constants**: UPPER_SNAKE_CASE (`API_KEY`, `MAX_RETRIES`)
- **Files**: kebab-case for JS/TS, snake_case for Python
- **Classes**: PascalCase (`UserService`, `PaymentProcessor`)
- **Avoid abbreviations** unless universally known (`id`, `url` OK; `usr`, `calc` NOT)

## Code Organization
- **One file = one responsibility** (UserService in one file, PaymentService in another)
- **Functions should be small**: < 50 lines; if larger, break into smaller functions
- **Limit nesting**: Maximum 3 levels deep; use early returns to reduce nesting
- **Group related code**: Put imports together, constants together, functions by feature
- **Dependency direction**: High-level modules should not depend on low-level details

## Dependency Management
- **Verify imports exist before using**: Read source files to confirm exports match expected usage
- **Check function signatures**: Ensure function/method signatures match how you're calling them
- **Use Context7 for library docs**: Get up-to-date API documentation for correct usage patterns
- **Prefer well-maintained packages**: Check npm/PyPI activity, security advisories, last update date
- **Pin major versions**: Use `^` (caret) for npm to allow patch updates, avoid breaking changes

## Separation of Concerns
Extract from code into separate files:
- **Configuration**: `.env` file (API keys, URLs, timeouts, feature flags)
- **All UI text**: Never hardcode user-facing strings — extract to separate files (`messages/`, `locales/`, `constants/`) for easy updates, translations, and consistency
- **LLM/Agent text content**: Never hardcode prompts, templates, and other text content for LLMs/agents in code — extract to separate files (`prompts/`, `templates/`) for easy iteration, review, and reuse
- **Business logic**: Keep separate from framework code (routes, controllers)

## Security
- **Store all secrets in environment variables** (`.env`) — API keys, passwords, tokens
- **Validate all input**: Check types, formats, ranges before processing
- **Sanitize user data**: Before database operations, API calls, or displaying
- **Add to .gitignore**: `.env`, `*.key`, `credentials.json`, `secrets/`
- **Create .env.example**: With empty/dummy values for documentation

## Validation
- **Validate at API boundaries**: Check input in controllers, API routes, function entry points
- **Use schema validation libraries**: Zod, Yup, io-ts for runtime type checking and validation
- **Validate on BOTH frontend AND backend**: Defense in depth - never trust client-side validation alone
- **Sanitize before database operations**: Prevent SQL injection, NoSQL injection attacks
- **Fail fast with clear errors**: Return specific validation errors to help users fix input
- **Check values you cannot work without at the process boundary**: an empty config value travels
  outward and returns as the remote side's rejection, phrased in the remote side's terms — your own
  defect arriving disguised as someone else's outage. Fail in your own voice, pointing at your own place

## Error Handling
- **Use try-catch** for operations that can fail (API calls, DB operations, file I/O)
- **Log with context**: Include user_id, action, resource_id, error message, stack trace
- **Don't swallow errors**: Always re-throw after logging (unless explicitly handling)
- **Fail fast**: Validate inputs early; throw errors immediately when invalid
- **User-friendly errors**: Show generic message to users, log details internally

**Absence is not a decision, and a silent success is the most expensive outcome.** The failure
mode to design against is not the raised error — that one announces itself — but the path that
returns "fine" while nothing happened:
- **A blank optional field encodes a business choice**: it collapses "chose the default" and
  "answered nothing" into one byte pattern, and every consumer downstream inherits the ambiguity.
  Make the choice explicit at the input AND in the stored record — two separate fixes
- **A terminal negative result is not a failure**: an empty answer from a call that would return
  the same thing on re-run is finished work. `if not result: raise` reads as defensive programming
  while reclassifying a finished answer as unfinished — and where the call costs money, that turns
  every re-run into a repeat charge. Record the terminal negative as durably as a success
- **Every skip / anti-overwrite guard needs a named path to force the action**: a blocked update
  looks like success from outside — the call is acknowledged, no error is raised, and stale data
  goes out. State how the guard is lifted deliberately
- **Never resolve ambiguous input silently**: "last one wins" is a loss wearing the costume of a
  rule. Reject in the layer where the conflict still exists — validation written on top of a parser
  that already resolved it inspects a reality the conflict was edited out of. And define
  "duplicate" by the same normalisation the value is later looked up by
- **Idempotent insert is silent in two opposite cases**: "the work is already done" and "I computed
  the wrong key". While those are indistinguishable in code, the duplicate guard also guards your
  own bugs from discovery
- **Run new code with per-item output, never a quiet summary**: no output is not a sign of progress,
  it is an absence of information, and the explanation that fills it is the one already in your head.
  A quiet run makes a hang indistinguishable from slowness; a verbose one turns it into one test name

## The Environment Lies About What Executes

The bytes you read and the bytes that run are two different claims, and the cheap check only
covers the first. Nothing here raises an error — each failure produces plausible wrong behaviour.

- **Derived-artefact caches**: bytecode (`.pyc`), build output, container layers, package caches.
  Restoring a file is not restoring behaviour — any operation that returns a system to a prior
  state must invalidate every derived artefact, or the rollback happened only in the layer that
  was easiest to verify
- **Regeneration must clear its output directory when the output shape can change**: overwrite is
  keyed on the paths the NEW code produces, so it leaves behind everything the old code produced.
  Every stale file is individually well-formed and correctly named. Reconcile the aggregate against
  the source; do not sample the parts
- **Text that crossed a system boundary needs explicit normalisation before comparison**: two
  strings that render identically are not equal (macOS stores filenames in NFD, so a glob written
  in NFC matches nothing). Compare codepoints — "it looks the same on screen" is precisely the
  evidence that must not be trusted
- **Locale-dependent text tools answer in the environment's language, not the data's**: verify a
  search tool against the actual alphabet of the corpus before trusting a negative result from it
- **Anything that "finds its own path" has an origin**: the process working directory and the
  source file's directory coincide only until the code is moved out of the project tree
- **A destruction path must use an interface that cannot construct**: reaching a resource through a
  lazy accessor inside a cleanup handler materialises the very thing being cleaned up. Symmetry
  between create and destroy comes from the absent call, not from the author's discipline

## Logging
- **Use structured logging format**: JSON with consistent fields for easy parsing and searching
- **Include context in every log**: userId, action, resourceId, timestamp, error message
- **Use appropriate log levels**:
  - `debug`: Development-only details (verbose, disabled in production)
  - `info`: Key operations completed (user login, order created, payment processed)
  - `warn`: Recoverable issues (retry succeeded, deprecated API used, rate limit approaching)
  - `error`: Failures requiring attention (API call failed, database error, auth failure)
- **Log errors with stack traces**: Helps debug production issues quickly

**What to log:**
- Entry/exit of key business operations (`order.created`, `payment.processed`)
- External calls (API, DB, queues) with duration: `api.call.completed { service: "stripe", duration_ms: 230 }`
- Authentication and authorization events (login, logout, permission denied, token refresh)
- State transitions (order status changes, workflow steps)
- Startup/shutdown: config loaded (without secret values), connections established, service ready

**What to exclude from logs:**
- Passwords, API keys, tokens, session IDs
- PII at info level and above: email, phone, full name, IP address (use hashed/masked versions)
- Full request/response bodies (log summary or truncated version instead)
- High-frequency events without sampling (health checks, heartbeats)

**Correlation ID**: Propagate requestId/correlationId through the entire call chain. Every log entry for the same user request should share one ID for easy tracing.

**Anti-patterns:**
- Logging inside tight loops (thousands of identical log lines)
- `console.log` / `print` in production code (use a proper logger)
- `catch (e) {}` — empty catch blocks that swallow errors silently
- Logging large objects with `JSON.stringify(entireObject)` (log relevant fields only)

## Testing
- **Test public APIs**, not internal implementation
- **Mock external services**: API calls, database, file system
- **One test = one scenario**: happy path, errors, edge cases separately
- **Descriptive test names**: `test_user_creation_fails_when_email_invalid`
- **Keep tests fast**: unit < 100ms, integration < 1s

## Performance
- **Avoid N+1 queries**: Use batch operations, eager loading, or caching instead of loops with queries
- **Cache expensive computations**: Use memoization for functions, Redis for shared state across requests
- **Be mindful of bundle size**: Check impact of new dependencies on frontend load time
- **Prevent memory leaks**: Clean up event listeners, timers, intervals, subscriptions in cleanup functions
- **Use pagination for large datasets**: Don't load all records at once, implement cursor or offset pagination
- **Profile before optimizing**: Measure actual performance bottlenecks before making changes (don't guess)

## Code Quality
- **Write meaningful comments** (in English):
  - Focus on "why" and "what for" rather than obvious "what"
  - For complex logic, "what it does" is also valuable
  - **When to write comments:** Complex business logic, non-obvious decisions, constraints, edge cases, security areas
  - **When NOT to write comments:** Obvious self-documenting code, every function, repeating type information
  - **Format:** JSDoc/TSDoc for public APIs, inline comments for complex logic
  - When updating code → update comments too
- **DRY principle**: Extract repeated code into functions/modules
- **Readable > clever**: Clear code is better than short but cryptic code
- **Consistent formatting**: Use project's linter/formatter settings
- **No magic numbers**: Extract to named constants (`MAX_UPLOAD_SIZE` not `5242880`)
