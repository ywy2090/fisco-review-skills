# Author-side self-check reference

Read this before pushing a fix. A fix that introduces a new instance of any of these classes reopens the reviewer's next round — check the diff against them, don't just re-run the failing test.

## Code conventions (this repo)

- **License header**: full Apache grant + SPDX + `@file`/`@brief` Doxygen. Truncated headers on new files are a hard violation.
- **Constants**: `c_` prefix (e.g. `c_maxPayloadEntries`); a `k` prefix violates convention.
- **Errors**: domain errors are `DERIVE_BCOS_EXCEPTION` types via `BOOST_THROW_EXCEPTION` with `bcos::errinfo_comment` — not bare `std::invalid_argument`/`std::logic_error`/`std::bad_optional_access`, and no raw `.value()`. Framework `Errors.h` files are declarations-only.
- **Shape**: class declaration in `.h`, implementation in `.cpp`; a 1,000+-line header-only service departs from idiom.
- **Namespaces**: internal helpers in `bcos::engine::detail`; no ad-hoc snake_case sibling namespace.
- **Logging**: `BCOS_LOG(WARNING)` + `LOG_BADGE`/`LOG_KV`; rate-limit hot paths.
- **Concurrency**: never hold a lock across `co_await`; never mutate shared state outside the lock.
- **CMake**: `PRIVATE` for impl-only headers; move test-only deps to the test target.

## Fix-reintroduction traps

A fix most often reopens a round by one of these:

1. **Duplicate implementation** — adding a second copy of something already shared (e.g. a helper, a `makeStatus`, a cache) instead of consolidating into the shared module. This applies to code you just added too, not only to pre-existing copies: a helper added next to a near-identical one (same lock, same backends, same ITT report) is a second implementation that will drift, even when each copy is individually correct.
2. **Commit failure masked as success** — consuming mutable state (a view/header/artifact) *before* the durable write succeeds, so a retry after a failed write answers success without persisting. Clear artifacts only after the write.
3. **Reference-lifetime accessor** — returning `T&`/`const T&` into lock-guarded state instead of by value.
4. **A comment that asserts an invariant the code no longer maintains** — comments are claims, verify each against the code; a stale/incorrect comment is itself a finding.
5. **Dead code / stale comment** — a helper with no caller, a comment naming a consumer that doesn't exist, or a test still asserting the pre-fix outcome.
6. **Shared state mutated outside the lock** — a non-atomic counter or member written between lock release and re-acquire.
7. **Verification plan sourced from the commit message** — your own commit message is an annotation, not evidence. After the named-mechanism check, walk the reachability question over the tree (who calls the new code, with what inputs, on which wire versions); a gate or guard your message says "closes findings" may reject an honest caller no test covers.
8. **Discarded protocol-contract returns at a host/vtable boundary** — a bool/int return that encodes success/failure (e.g. the EVMC `selfdestruct` bool) is behaviour, not decoration. If the only caller discards it, a failure branch that logs and falls through to success-path bookkeeping is fail-open (the commit-failure-masked-as-success family). Consume the return or make the function void; a comment like "just use default" sitting on such a return is itself a finding (trap 4's comment class).
9. **Header case mismatch against its own includes** — a new header whose filename case differs from the include spellings (e.g. `executeMessage.h` included as `ExecuteMessage.h`) compiles on case-insensitive filesystems (macOS/Windows) and breaks every TU on Linux. When adding a header, diff its filename against every include of it byte-for-byte, not case-insensitively.

10. **Copy count for lock/perf fixes** — a fix whose rationale is lock scope or latency is audited by counting the copies it moves (what, where, inside or outside the lock); "assemble outside the lock" that copies the whole body in-lock first is a regression, and the shared_ptr-held shape is the boundary that actually shortens the hold.
11. **Linkage-scope placement of extracted helpers** — an extracted helper whose parameter types live in an unnamed namespace must be defined inside it; a definition after the namespace close exports a symbol no other TU can legally name.
12. **Column-limit sweep on touched files** — `grep -cE "^.{101,}$"` against the repo's `ColumnLimit: 100` before pushing; identifier-lengthening renames push wrapped lines over without any semantic diff.

13. **Copied comments are re-derived, not re-typed** — when porting a rationale comment from an origin file (or writing a mechanism explanation for your own fix), verify every sentence still describes THIS copy's code from the C++ semantics, not from the origin's phrasing: a `shared_ptr` move nulls the pointer and leaves the pointee untouched (no "moved-from member"); a truncated origin sentence drops the loop/branch it explains. A wrong-mechanism comment gets quoted forward into the next reader's model. → 本仓库：#5548 的 blockHash-copy 注释声称 "leaves the blockHash member moved-from"——实际是 commonEntry 为 null、成员未被触碰（外部 round-1 F6 抓到）。

14. **Close-out at the named site** — verifying a claim by showing a *different* occurrence than the one the reviewer named (a neighbouring comment, another copy of the helper, the wrong entry in a list). The named site is what the next round re-reads: `git show` that exact path and, if the review named a comment, that comment's own text at the final commit. → 本仓库：#5495-r4 — the close-out showed another annotation while the reviewer's named `TransactionResponse` comment kept the old wording, and the finding reopened.

15. **A fail-closed flip leaves sibling default sites behind** — after one path stops substituting a default, enumerate the other functions in the same TU that consume the same missing-data family. "This path no longer has a default" is not "the category is gone". → 本仓库：#5496-r3 — `CallRequest` wrote a default fee into one field while the signer read another.

16. **Line drift between fix commits** — a `file:line` cited in a reply is re-read at the final commit; fix commits move lines, and a stale location makes the reviewer's verification fail on a correct fix. → 本仓库：#5544 — three drifts caught in one round.

17. **Evidence retrofitted to the reply** — writing the reply body first and then looking for support. Generate every body *from* the ledger, and self-read each claim against the tree before posting.

18. **Two field names for one quantity** — the fix writes into one field of a read/write pair while the consumer reads the other (fee, nonce, version or config pairs). When a fix touches such a pair, grep both sides and confirm the producer and the consumer name the same field.

19. **A new test whose pin is not discriminating** — asserting an exception *type* that three production sites throw with different `what()`, or a field count, or an outcome without the invariant. Pin the unique signal (message, discriminator value) or mutate the production code to prove the test can see the difference.
