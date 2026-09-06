# FISCO-BCOS review reference

Distilled from the engine-split review history (PRs #5544/#5547–#5550, rounds 1–3 by kyonRay, author responses by ywy2090) plus the codebase's own conventions. Read this before reviewing the diff.

## Module map

- `engine/bcos-engine/` — `EngineServiceImpl` (legacy production Engine API service), `EngineServiceCommon.{h,cpp}` (shared validators + `engine_common`), `EngineTracker` (forkchoice state, `PayloadCache`), `PayloadCache`, and Eth/Op service slices landing in later PRs.
- `libinitializer/` — `Initializer.cpp` / `EngineServiceInitializer`: the composition root; decides which Engine service boots (`executor_version` gates, cutover points).
- `bcos-rpc/bcos-rpc/web3jsonrpc/utils/EngineHelper.cpp` — the Engine API **JSON wire dialect** (serialise/parse). `EngineEndpoint.cpp` — method→version routing.
- `bcos-framework/bcos-framework/engine/` — shared framework headers: `Errors.h` (fault taxonomy), capability/version definitions.
- `opstack-executor/`, `bcos-evm/` — block execution lanes (often not materialised in the checkout; note that in the verification boundary).
- Tests: `engine/test/unittests/engine/`, per-module `test/unittests/`.

## Code conventions

Repo-specific rules this codebase is expected to follow. Not a generic defect list — these describe FISCO-BCOS's own idiom.

- **License header**: every file carries the full Apache grant + SPDX and `@file`/`@brief` Doxygen. Truncated headers on new files are a hard violation.
- **Constants**: `c_` prefix (e.g. `c_maxPayloadEntries`). A `k` prefix (`kMaxForcedTxCount`) violates convention — flag even single occurrences.
- **Errors**: domain errors are `DERIVE_BCOS_EXCEPTION` types thrown via `BOOST_THROW_EXCEPTION` with `bcos::errinfo_comment` — not bare `std::invalid_argument`/`std::logic_error`/`std::bad_optional_access` (i.e. no raw `.value()` where a descriptive throw is the neighbour's idiom). Framework `Errors.h` files are **declarations-only**; a helper with a body there is out of place.
- **Shape**: class declaration in `.h`, implementation in `.cpp`. A 1,000+-line header-only service departs from the codebase's idiom and drags includes into every TU; if deliberate, the CMake consequences (PRIVATE→PUBLIC link) must be justified.
- **Namespaces**: internal helpers sit in `bcos::engine::detail`; don't introduce a new sibling snake_case namespace (`engine_common`) next to an established idiom without a stated reason.
- **Logging**: `BCOS_LOG(WARNING)` + `LOG_BADGE`/`LOG_KV`; rate-limit hot paths with a CAS-gated `steady_clock` (see the 10 s warning in `EngineServiceImpl`).
- **Concurrency**: never hold a `shared_mutex`/`unique_lock` across `co_await` — resumption can move threads and make the unlock UB; the codebase deliberately copies under the lock and releases before awaits. Same-thread-unlock-only guards are documented.
- **CMake**: declare usage requirements where they are used — `PRIVATE` for headers only an implementation file includes; move the dependency to the *test* target when only tests need it. Flag committed dangling symlinks / external fixtures (e.g. a `t8n` corpus) that make the suite fail or depend on a sibling checkout.
- **Tests**: BOOST suites under `test/unittests/`; unit tests must exercise the same dialect the production path uses.

## Verification discipline (read first)

These eight govern how every defect class below is applied — which signals to distrust, and what to prove independently before trusting a claim. Throughout, `→ 本仓库：` marks the concrete FISCO-BCOS instance (an example, not the rule itself).

1. **Claim honesty** — does the description understate the diff? A change framed as a pure refactor/extraction is falsified by any change to what the still-produced component answers; enumerate behaviour changes (answer codes, comparison width, version windows) even when each is defensible. → 本仓库："extraction with no cutover" 却改写了仍生产的 `EngineServiceImpl` 的 newPayload/getPayload 语义。

2. **Coverage honesty** — a coverage report is a hint, not proof; state whether tests were run and which modules were unreadable (e.g. out-of-checkout execution lanes).

3. **Comments are claims, not evidence** — a code comment is an assertion to verify, never a fact to trust. When a comment states an invariant, constraint, or "intentional / safe / cannot happen", find the code that substantiates it; a comment the code contradicts is a stale/incorrect comment and is itself a finding. Never accept a comment on faith, and never dismiss a suspected bug by citing a comment unless the code independently proves it. Upstream-parity and provenance claims live by the same rule: a comment, commit message, or description line saying "matches op-geth" / "same as upstream" is an assertion — accepting it requires independently checking the cited behaviour against the code, not against the citation. → 本仓库：`EngineTracker::applyForkchoice` 的 "Same predicate as the store below" 注释声称检查与存储同谓词，实际 gate 用 `hash!=0 && number.has_value()`、store 用 `hash!=0` —— 注释是错的，谓词不对称是真实的。

4. **Test coverage must be a superset of what the code enforces** — a "this is covered" claim that names a field count or a happy path is not the same as proving the tested field set ⊇ the field set the code actually compares/validates. Diff the two sets; the code's strictest rule is often the least-pinned one. → 本仓库：wire 往返测试覆盖 16 字段却漏 `withdrawals` 列表——恰是 `compareWithBuiltPayload` 用最严规则比较的字段；且只测 V3，漏了生产自名的 V5→V4 版本对。

5. **Copy-vs-origin audit** — every near-copy a PR adds (function body, comment block, commit sequence) is diffed against its declared origin; truncated sentences, dropped loops/branches, altered predicates, and dropped comments are findings cited by origin `file:line`. A copied comment that stops mid-rationale is a dropped-mechanism fingerprint, not noise. → 本仓库：`EthEngineService.inl` 的 merge 注释停在 "idempotent VALID"，恰好漏掉 Impl 里解释 drain 循环的那句和循环本体（#5548 F1）；`buildPayload` 拷贝静默丢掉 XOR-state-root 共识风险 TODO、txRoot TODO 与 forced-transaction 契约注释（F2）。

6. **Primitive-contract grep** — every storage/sync primitive's in-code WARNING/contract comment (`MultiLayerStorage.h` 的 "must drain the deque first" 等) is grepped against every new caller the PR introduces; the contract header documents the failure mode, and a caller that doesn't honour it is a finding. → 本仓库：push_front / merge_back 的 deque 语义警告对两个 Engine 服务的提交序列各漏一次（#5548 F1）。

7. **Adversarial audit of round-requested fixes** — when a prior round's response ADDS infrastructure (a limiter, a gate, a helper, a shared comment), the next round audits the added thing's own coupling and failure modes, not only whether it satisfies the original finding. Verification that is acceptance-shaped ("all five sites now warn ✓") is how a shared rate-limit gate's cross-site suppression survived to the next reviewer (→ #5548 F5).

8. **Residual-gap language may not stay prose** — every "not exercised / residual gap / only the pre-merge throw is tested" sentence in a verification boundary or "not a problem" note must end as either a finding or an explicit accepted-risk statement naming who owns it. → 本仓库：round-4 写下 "mid-merge-throw is not directly exercised" 却未转成 finding，下一个 reviewer 以此为据点开 HIGH（#5548 F1）。

## Defect classes — correctness & concurrency

High-consequence bugs: consensus fork, data loss, data races, UB, lost user transactions, mis-configuration that rejects the whole chain.

9. ****Commit failure must not be masked as success** — consume mutable state only *after* the durable write succeeds; a retry after a failed write must re-do the write, never answer success. The tell: a consumed / moved-from artifact that turns a re-arrival into a false success. → 本仓库：`view/header/receipts` 应在 `prewriteBlockToBuffer`+`mergeBackStorage` 成功后才 reset；先消费后落盘会让 I/O 抛错后的重试返回 VALID。

10. ****Field comparison completeness** — a comparator that checks a derived/commitment value (a root hash) but not the field(s) it derives from (the list) accepts a tampered payload under the same key; and tests must exercise the real serialisation round-trip, not a struct copy. → 本仓库：`compareWithBuiltPayload` 比 `withdrawalsRoot` 但不比 `withdrawals` 列表；测试应走 `EngineHelper` 而非 struct copy。

11. ****Terminal statuses** — a status the client keeps retrying but can never move past (because the recovery mechanism is absent) is terminal; keep the fail-closed answer but make it visible (rate-limited log naming the gap) and disclosed. → 本仓库：无 EL sync 的节点答 `SYNCING`。

12. ****Sentinel/predicate symmetry** — when a sentinel is treated as "unset" for one purpose but still validated for another, both must use the same predicate; tests that hand-set flags to force the pass conceal the asymmetry. → 本仓库：全零 hash / `(0,0)` eip1559 参数。

13. ****Lock scope across awaits** — a lock held across a suspension point is UB when resumption moves threads; release before awaiting. → 本仓库：`co_await` 前释放 `x_state`。

14. ****Canonical source of a semantic value** — each semantic (chain id, mode selector, epoch) must come from its canonical config field, not a lookalike field with a different meaning; a permissive parser (accepting `-1`, trailing garbage) is a bug. → 本仓库：EVM chain id 取 `[web3] chain_id` 而非 `[chain] chain_id`（默认 `"chain"`）；`stoull(...,0)` 接受 `-1`。

15. ****Skip, don't evict** — a candidate that can't be included this block must be skipped (kept pooled), not removed; check cascade effects (nonce gaps); classify errors by typed category, never by parsing a string tag. → 本仓库：nonce 级联逐出；`"[tx=0x"` 字符串标签。

16. ****Typed fault propagation** — error/culprit info must flow through typed fields so every consumer can classify; a string tag no code emits is a live bug. → 本仓库：`OpCulpritTxHash`。

17. ****Determinism & stale keys** — a deterministic key must cover every input it derives from; replacing a key must not leave the old mapping live. → 本仓库：payload id 未含 sealed txpool 内容。

18. ****Fail-closed symmetry** — a validation flag that fails closed for some inputs but is only consulted in a narrow branch leaves an asymmetric gap; apply the same fail-closed rule to all equivalent inputs. → 本仓库：`headCanonical` 只在 same-height 分支被查，首次/+1 推进 fail-open（`safeCanonical`/`finalizedCanonical` 则 fail-closed）。

19. ****Shared state mutated outside the lock** — mutating shared state outside the critical section (a non-atomic counter between release and re-acquire) is a data race; make it atomic or move it inside the guard. → 本仓库：`nextPayloadID()` 锁外自增 `m_nextPayloadSequence`。

20. ****Version/shape requirements are cumulative, not layered** — a higher version's response or wire shape usually *embeds* the lower version's full field set; a gate or requirement keyed only to the lower version (e.g. `v == N` or `v < N`) drops its protection exactly where the shape is widest. When you see a version-bounded predicate, ask whether the upper bound exists because higher versions genuinely don't need the check, or because the author assumed they don't. → 本仓库：`requireGetPayloadShape` 的 `requestVersion < V4` 上界让 V4/V5 跳过 V3 字段检查，而 V4/V5 响应内嵌完整 V3 字段集。

## Defect classes — consistency & hygiene

Lower-consequence: duplicated or divergent logic, dead code, API-shape hazards. Often deferrable to a follow-up, but still reportable.

21. ****Duplicate implementations of one job** — two copies of one function already diverge at merge time; move the shared logic into one place and call from both. An equivalence test that pins two copies against a third preserves the drift. → 本仓库：`getPayload`/`makeStatus`。

22. ****Advertised capability must be callable** — every advertised method must be callable and have a matching retrieval path; avoid duplicates across lists; a version-window narrowing is a behaviour change to disclose. → 本仓库：`engine_forkchoiceUpdatedV4`/`getPayloadVn`/`newPayloadVn`。

23. ****Reference-lifetime accessors** — an accessor returning `T&`/`const T&` into a mutex-guarded member races with writers and dangles past the guard's scope; return by value. Grep for `const <Type>& <name>() const` accessors returning a member reference. → 本仓库：`forkchoiceState()`。

24. ****Same-name definitions split their callers by binding** — two definitions of one helper in the same translation unit do not merely duplicate: each unqualified call site resolves to *one* of them, via ordinary unqualified lookup / ADL / a shadowing local, and the copies can silently diverge in behaviour with no compiler error. When you find a duplicate, trace every call site to which definition it actually binds, and state the split; the bug is the split, not the copying. → 本仓库：`decodeEip1559Params` 一份在匿名命名空间（`engine_common` 内），一份在 `OpBaseFee.h`；`validatePayloadAttributes` 绑定前者（`size < 8`），`detail::encodeOptimismExtraData` 的无限定查找命中后者（`size != 8`）。

25. ****Dead code / stale comments** — unused members, duplicate helpers, comments naming consumers that don't exist in-tree, tests asserting a pre-fix outcome, clang-format-only churn outside scope.

26. ****`optional::value_or` on a const lvalue deep-copies** — `const std::optional<std::vector<T>>&` + `.value_or(std::vector<T>{})` selects the by-value overload: the whole container is allocated-copied-freed to read one `.size()`. Grep `value_or(std::vector` under a `const&` parameter; the non-copying form is the ternary on `has_value()`. → 本仓库：`payloadAttributes.transactions.value_or(...)` 在 `reserve()` 里每次 payload 构建深拷贝至多 ~16 MB（#5548 F3）。

27. ****Bulk container copies inside an exclusive guard** — count the copies a PR introduces under any exclusive lock/mutex guard: whole-map/vector snapshots for rollback, whole-cache duplicates, per-entry receipt vectors at bounded capacity ×N. A copy count of 3 (snapshot cache + snapshot map + internal duplicate) in one critical section is the finding, even when each is individually correct and bounded. → 本仓库：`commitRetainedPayload`/`publishBuiltPayload` 在 tracker 排他锁内做三份全容器拷贝（#5548 F7）。

## Scorecard dimensions (this repo's convention)

| Dimension | Asks |
|---|---|
| Correctness | live-path defects, re-execution, terminal answers |
| Tests | do they exercise the production dialect; is the regression invisible to CI |
| Comments/readability | dense and upstream-pinned; describe invariants the code still keeps |
| Scope discipline | behaviour changes riding inside a stated refactor/extraction |
| Description honesty | description vs what the diff does |

## Deep-mode delegation contract (full pass)

When full mode delegates modules to parallel sub-agents:

- **File ownership** — one module per agent (implementation files + that module's own tests). Shared headers/tests (`EngineServiceCommon.h`, `Types.h`, gold-pinned suites) are *consult-only*: locate via grep/sed, never full-read unless a finding depends on them. Forbidden: reading files outside the agent's module. **Cross-file symmetry is NOT the agent's job** — sibling-helper step-set parity (#33) and duplicated consensus literals (#37) live in the *other* file, so the aggregator owns them as a dedicated post-pass (see Aggregation gate). An agent trying to diff a sibling in a consult-only file is fighting the slice; don't ask it to.
- **Budgets (hard caps)** — each agent gets **≤2M tokens and ≤35 tool calls** (this skill's own #5549 runs measured 2.4–5.6M tokens per agent at 3–5× the old soft cap; the cap is now hard). When an agent exceeds it, the aggregator stops it (TaskStop) and the **main thread reads the un-covered files directly** — the overrun is a hand-off, not a license to keep spending. Each file read at most once (chunked `Read` with offset/limit); report ≤450 words; ≤5 "checked, not a problem" entries, **each quoting the lines that establish safety** (a one-line impression is not evidence). No exhaustive negative-space verification: if proving a negative would cost more reads, list it under "could not determine" instead. **Outline-first**: before a chunked full read, grep the file's declaration / `BOOST_AUTO_TEST_CASE` / function boundaries and target the reads at the regions a checklist item can fire in — bulk linear reading of a 1,000+-line file is the budget's biggest sink. Findings quote **exact line numbers** as read; each "could not determine" names the minimal read set that would resolve it (file + region), so the aggregator can resolve it in one call — parking is reserved for facts genuinely outside the materialized tree.
- **Inputs** — the aggregator's known-items list (prior findings + statuses at head, verified-clean items, deliberate behaviours). Report ONLY new findings; do not re-derive or re-report known items.
- **Cross-cutting tasks (every agent)** — in addition to their module's logic bugs, each agent: (a) runs claim-audit (checklist item 1) for their module's scope — verify the PR description's claims against the diff and report any undisclosed behaviour change; (b) checks the "Code conventions" section for the files they touch (license header, `c_` vs `k` constant naming, exception idiom, `.h`/`.cpp` shape); and (c) for each file the PR *fixed* (prior findings marked fixed/partial), re-applies the checklist items those findings were classified under, over the whole region the fix changed — a fix must be re-audited, not just confirmed to contain the named mechanism. Conventions checks are grep-driven, not full-reads: locate the file head (license), constant declarations, and `BOOST_THROW_EXCEPTION` / `std::` throw sites, then read only the matching snippets — keeps recall without re-reading whole files.
- **No answer-injection** — for a fresh review, hand agents the checklist and the PR's own claims, never candidate answers. Do not name suspected bugs in the prompt (e.g. "is the withdrawals list compared?"), which contaminates recall measurement and teaches the agent the answer.
- **Findings must carry** — severity (repo semantics in SKILL.md), `file:line` in the *materialized head tree* (never the working tree), a ≤6-line verbatim code quote as evidence, problem, why-it-matters with a reachable scenario, recommended fix.
- **Aggregation gate** — the aggregator re-verifies every admitted finding at its location in the materialized tree before the final report; drops or downgrades anything whose quoted evidence does not match the code. An agent's "checked clean" claims are held to the same quoted-code standard as its findings. **Zero-finding tripwire**: an agent that returns no findings after >1.5M tokens spent is linear-reading, not targeting — stop it and take over its files. **Missing-line rescan**: before writing the report, re-scan the changed functions that touch a primitive (`rlp::decodeHeader`, `memcpy`, a bounds check) for *asymmetric defence* (checklist #35) — sub-agents over-report crash candidates and under-report the absent guard; the aggregator owns the pattern-diff that catches the missing line. **Cross-file symmetry pass**: the aggregator enumerates the diff's same-domain sibling-helper pairs (a new function and its existing sibling doing the same job on another lane, e.g. `rebuildOpEthHeader` vs `finalizeEthBlockHeader`) and diffs their step sets (checklist #33), and greps consensus literals across module boundaries for value-level duplication (#37). This is a single continuous read that file-slicing cannot reproduce — it recovers the #5549 F2/F7 class the sliced agents missed.
- **Layout used for engine PRs** — (a) data structures & concurrency: `PayloadCache`, `EngineTracker`; (b) shared validators/helpers: `EngineServiceCommon.*`, framework `Errors.h` additions; (c) the service: `EngineServiceImpl.h` incl. live commit/getPayload/build flows. Adjust per PR; keep agents disjoint.

## Defect classes — portability & protocol boundaries

28. ****Include-case parity** — for every new header, the filename must match every include of it byte-for-byte. A case mismatch compiles on macOS/Windows and breaks every Linux TU — a compile break invisible to a case-insensitive CI, so flag as HIGH even when the author's platform is green.
29. ****Protocol-contract returns** — when a function's bool/int return encodes success/failure for a protocol (EVMC host interface, DMC resume protocol), verify every caller consumes it. A discarded return whose failure path only logs and then falls through to success-path bookkeeping is a HIGH fail-open finding.

## Mechanical checks (run over every touched file)

Mostly grep-level; each covers a finding a multi-agent full round missed. Target closure lives in SKILL.md step 7, not repeated here.

30. ****Copy count for lock/perf fixes** — a fix justified by lock scope or latency is audited by counting the copies it moves (what is copied, where it lands, inside or outside the lock), not by confirming the mechanism exists. → 本仓库：a copy-out「fix」doubled the block-body copy and left the original inside the lock.
31. ****Linkage-scope placement of extracted helpers** — a helper extracted into a TU with an unnamed namespace must land inside it; a file-scope definition after the namespace close gives external linkage to a function whose parameter types are internal. → 本仓库：`retainStaged` defined after the namespace close.
32. ****Column-limit sweep** — `grep -cE "^.{101,}$"` over every touched file against the repo's `ColumnLimit`; renames that lengthen identifiers routinely push previously-wrapped lines over. → 本仓库：an exception-type rename pushed 7 lines over.

## Defect classes — cross-file & structural (from the #5549 post-mortem)

These seven came out of the #5549 retrospective: two independent reviews of the same head, where this skill's rounds missed eight of the external reviewer's ten findings. The gaps fell into two families — rules this skill already had but the delegation boundary cut off (33, 38), and rules that did not exist at all (34, 35, 36, 37, 39). Read them as corrections to the checklist's own structure, not as extra trivia.

33. **Sibling-helper step-set parity** — a new function that is the same-domain sibling of an existing helper (same semantic job on a different lane: `rebuildOpEthHeader` vs `finalizeEthBlockHeader`, `buildOpPayload` vs the Impl's `buildPayload`) is diffed **step-for-step** against its sibling, not read in isolation. A step the sibling performs and the new function drops — a `setEthBlockVersion`, a `setXxx` field, a constant, a validation pass — is a finding even when the new function compiles and its own tests pass. This is the cross-file case that copy-vs-origin audit (#5) misses when the two functions live in *different files owned by different delegation agents*; the symmetry lives in the other file, and "consult-only" must not become "skip the diff". → 本仓库：`rebuildOpEthHeader` dropped `setEthBlockVersion`, the step `finalizeEthBlockHeader` performs and documents as required before the RLP hash; the parity suite derived its expected hash from the same helper, so no test could see it (#5549 F2).

34. **Concurrency contract → shared-state inventory** — the inverse of #13. #13 asks "does an existing lock span a `co_await`?"; this asks the question #13 cannot: "the class documents concurrent calls (RPC threads, no serial executor) — enumerate every shared mutable member and name who guards it." A member guarded by neither a mutex nor an internal try-lock/fail-closed contract is a finding. The tell is a class with *one* mutex for one member and a *second* shared object (a scheduler with staged block state) driven through multi-step sequences with no serialization at all. Lock-scope auditing only ever inspects locks that already exist; it never surfaces the shared object that has no lock. → 本仓库：`OpEngineService` guards `m_lastExecutedHeader` but drives `m_delegate` through `reset → executeBlock → commitBlock` unserialized, answered by a rationale comment, not a mutex or a test (#5549 F3).

35. **Intra-function defensive-pattern symmetry** — within one function, the same primitive (`rlp::decodeHeader`, a `memcpy` target, a bounds check) called at N sites must apply the same defence at every site. The signal here is a *missing* line, not an anomalous one: "four sites check `payloadLength > remaining`, two don't" is the finding, and the two that don't are what a reviewer skimming for crashes overlooks. After you find one explicit guard, diff the remaining call sites of the same primitive for the absent guard; a decodeHeader whose `payloadLength` equals the fixed width but is not checked against the remaining buffer is a heap over-read feeding a comparison. → 本仓库：`bindEnvelopeAccessList`/`bindEnvelopeBlobHashes` memcpy 20/32 bytes after checking the RLP length equals the width but not that it fits the buffer, while four sibling sites in the same function had the bound check (#5549 F5).

36. **Public-header → include → link-visibility → install connectivity** — a newly public (installed) header is audited as a three-hop chain, not a text blob: (1) the header's own `#include` list, (2) whether each included target is `PRIVATE` or `PUBLIC` on its library, (3) whether the header — and any `.inl` it unconditionally includes — is installed. A public header (or an `.inl` it pulls in) that includes a `PRIVATE`-linked dependency's header breaks the first out-of-tree consumer: it links and then fails to compile. Moving the include from the `.h` to the `.inl` does **not** fix it while the `.h` unconditionally `#include`s the `.inl` — the include *chain*, not the file that literally holds the line, is what must be free of the `PRIVATE` dependency. → 本仓库：`OpEngineService.h` → `.inl` → `<bcos-rlp-protocol/EthBlockHeader.h>` with `rlp-protocol` PRIVATE on `engine` (#5549 F6).

37. **Value-level duplication of consensus literals** — duplicate-implementations (#21) catches two copies of a *function*; it misses two copies of a *value* under different names: the same 32-byte hash, nonce, or constant defined file-locally in one file and as an inline literal in another. Consensus inputs — anything stamped into a header whose `keccak256(rlp(header))` is the block hash — are the high-stakes case: two definitions that drift are a chain split, and the diff that introduces one looks local and harmless. Grep the literal across the module; if it appears under two names, hoist it to one shared home. A cross-reference comment is not the fix; a single definition is. → 本仓库：empty-ommers `0x1dcc4de8…`, PoS zero nonce, and empty-requests `0xe3b0c442…` duplicated between `OpEngineService.cpp` and `finalizeEthBlockHeader` (#5549 F7).

38. **Self-referential oracle detection** — a test whose expected value is produced by the *same helper under test* (`rebuildOpEthHeader` + `computeHash` deriving the expected `blockHash`) cannot distinguish a correct from a wrong implementation; it is self-consistent by construction. On any "parity"/"golden" test ask two questions: (a) does the expected value come from the code under test or from an independent source (op-geth output, a hard-coded vector)? (b) is that independent source actually reachable — committed and not gitignored, and not behind a skip gate that the CI flag disables? A parity suite with an absent oracle plus a self-derived expectation is doubly vacuous. → 本仓库：`OpEngineServiceParityTest` derived its expected hash from `rebuildOpEthHeader`, and the only external oracle (the t8n corpus) was gitignored and unprovisioned (#5549 F1+F2).

39. **Two-notions-of-one-semantic** — one semantic value (a version, a chain id, an epoch) used under *two different notions* in the same build is a determinism bug, not a naming preference. A payload id derived from the raw method version while the cache entry stores the shape version (`min(V,3)`) mints two ids for one build where upstream mints one. The fix is to name the notion the semantic actually is at each site (method vs shape) and derive from the canonical one. → 本仓库：`derivePayloadId` got the raw FCU method version while the cache entry stored `payloadShapeVersion(version)` (#5549 F8).
