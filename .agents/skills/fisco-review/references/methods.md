# Verification methods (executable procedures)

Procedures, not defect classes: each of these is *run* on the pin and produces a receipt (the exact command and its before/after result). They are the counter-evidence layer under the checklist — a claim of "verified" is only as good as the method that produced it.

Grafted from the sibling v2.x reviewer corpus (`fisco-review-pr` 2.13.x with the `fisco-review-shared` bundle), keeping its method ids for the migrated procedures so cross-references stay traceable. Old M2/M4/M6/M9/M12 are **not** migrated: M9's rule now lives in checklist #12/#18, and the include/CMake apparatus is folded into the compact M13 below.

## Isolation contract (applies to every method that mutates code)

Any experiment that deletes, disables or alters production code runs in a **detached worktree at the pinned revision**, with its own out-of-tree build directory — never in the review checkout:

- create the worktree from the pin, then assert `git rev-parse` and a clean status;
- one change per experiment, restarting from a clean worktree each time (a mutation that stacks on a previous mutation proves nothing);
- clean up only what this run created (own branch/worktree; never a global `worktree prune`);
- if the worktree cannot be created, the build dir cannot be isolated, or cleanup fails → the corresponding evidence is **`blocked`**, not "verified". An experiment you cannot isolate is an experiment you cannot cite.

## M1 — Negative control

**Trigger.** Any claim of the form "X is covered / wired / cannot happen" that rests on a test, an include, a gate or an assertion — and any fix whose evidence is "the test now passes".

**Steps.** On the pin: (1) record the positive baseline — the exact command and its observed result; (2) delete or disable the 1–3 load-bearing lines (the include, the gate, the assertion, the wiring call); (3) re-run the *same* command unchanged.

**Completion.** Passes after the line is gone ⇒ the test/gate has a blind spot: that is a finding naming the blind spot, at the severity of the behaviour it fails to protect. Fails after the line is gone ⇒ the tool is trustworthy; record the receipt under "Checked, and not a problem".

**Provenance.** Old corpus `methods.md` M1 (include-cleanup incidents, 2026-08-18).

## M3 — Quantitative suspect tracking

**Trigger.** A rule-shaped defect the author has addressed by sweeping sites ("we reviewed every caller of X").

**Steps.** Track the suspect count across rounds with the *same* rule set; then widen the rule deliberately (one predicate, one path class at a time) and re-count.

**Completion.** Rule widened **and** suspect count falling ⇒ the *category* is genuinely closed. Rule widened and the count not falling = the fix was instance-level (checklist #42). Never report "all sites fixed" from a single pass with a rule you have not widened once.

**Provenance.** Old corpus `methods.md` M3.

## M5 — Layered verification (production vs test)

**Trigger.** Any "this is verified" claim where the diff spans production and test/vendor/generated code.

**Steps.** Classify every touched path into production / test / vendor / generated, then verify and report each layer separately with layer-specific severity. **Do not treat `src/` and `lib/` as the only production roots** — in this repo `bcos-*`, `engine/`, `opstack-executor/` are production code, and a green test layer says nothing about them.

**Completion.** Each layer has its own verdict and its own evidence; a production claim supported only by test-layer evidence is a coverage finding.

**Provenance.** Old corpus `methods.md` M5.

## M7 — Tool blind-spot declaration

**Trigger.** Any report that uses a tool's silence as evidence (compiler, ctest, grep, coverage, a validator).

**Steps.** State what the tool *can* and *cannot* detect; write the compensating check; put the declaration in the Verification boundary.

**Completion.** Every tool cited in the report has a stated detection envelope. "The suite is green" is never a completeness claim on its own.

**Provenance.** Old corpus `methods.md` M7.

## M8 — Wire-shape matrix

**Trigger.** A diff touching a wire/codec/RLP/ABI/JSON field, a header stamped into a hash, or any type whose serialisation feeds consensus.

**Steps.** Per changed field: **absent / N−1 / N / N+1 / canonical / non-canonical**, plus the type-specific extras. Two cells that are habitually skipped and must not be:

- **integer and count fields include leading zeros in the canonical cell** — marking canonical "optional" is the recorded miss (PR #5495-r11: `rlp::decode(uint64)` without CanonInt);
- where typed and legacy shapes coexist, the **cross-cells** (`typed × preimage`, `typed × wire`, `legacy × …`) are required, not implied.

Also verify the inner payload is fully consumed and the outer input has no residue.

**Completion.** Every cell is one of: verified (with the command), `not_applicable` (with the code fact), or `unreviewed`. Unreviewed cells go to `coverage.json` and the verification boundary — never silently to "complete".

**Provenance.** Old corpus `methods.md` M8 + lesson L-20260826-004.

## M10 — Single-source-of-rule audit

**Trigger.** An invariant with more than one entry point, **or** a validation gate plus the producer that writes the value being validated.

**Steps.** (1) List every entry point that must obey the invariant and draw `rule helper → callers`; (2) record each caller's actual argument provenance — a constant, a default, or a pre-normalised value must be *proven* equivalent to the real input, not assumed; (3) then ask the second half: **is the helper the gate uses the same helper the producer uses?** Two gates that agree with each other can both disagree with the producer; a same-named helper in another TU creates the illusion of a single source. (4) Fixtures whose storage is always empty reinforce the illusion — check what the fixture actually stores.

**Completion.** The entry table covers producer and consumers, each argument's provenance is stated, and gate-vs-producer (not only gate-vs-gate) has been reconciled.

**Provenance.** Old corpus `methods.md` M10 + lesson L-20260904-001 (PR #5544 round 6: a `withdrawalsRootFor` gate agreed with itself while the seal computed `opStorageRoot`, and the MessagePasser fixture storage was always empty — the miss survived a five-agent round).

## M11 — Fixture reverse-decode and unique signal

**Trigger.** A test that hand-builds a fixture (bytes, RLP, JSON, a hand-filled struct) which production code will parse; or a test that pins an error by exception type only.

**Steps.** (1) Re-decode the hand-built fixture with the **production** decoder; (2) require at least one value per implemented discriminator key; (3) where only the exception type is pinned and neighbouring sites throw the same type with different `what()`, pin a unique message or mutate the production code to prove the test can see the difference; (4) a "unique signal" must name a production decoder symbol, never a test-local helper.

**Completion.** The fixture round-trips through production code and each pinned expectation has a discriminator that no sibling site shares.

**Provenance.** Old corpus `methods.md` M11 + lesson L-20260826-006 (PR #5495-r11: `BOOST_CHECK_THROW` on type only, three production sites with distinct `what()`).

## M13 — Include and build-system contract (compact; new in the merge)

**Trigger.** A diff that adds/removes/moves includes, changes an installed header's include set, or edits `CMakeLists.txt` / `vcpkg.json` / the toolchain.

**Steps.** (1) For an include deletion, sweep for still-used symbols that relied on it (comments and literals stripped first); (2) for a new or newly installed header, find its canonical home header and check every include spelling byte-for-byte — case mismatches compile on macOS and break every Linux TU; (3) for a build-system edit, do a **from-zero configure and judge by exit code, not by grep** — a case-sensitive `grep error` misses `CMake Error`; (4) never run clang-format over non-`.h`/`.cpp` files: it splits `rlp-protocol` into `rlp - protocol` and glues `aux_source_directory(. SRC_LIST)`.

**Completion.** Each include has a proven need-or-absence, each spelling matches, and the build-system change has a clean-configure receipt.

**Provenance.** Old corpus `methods.md` M2/M4/M6/M12 + lesson L-20260827-001 (PR #5549).

---

Method ids M2, M4, M6, M9 and M12 are deliberately not migrated (see the header note). If a header-purge or dependency-boundary PR needs the full symbol→header table and transitive-chain trace, the sibling corpus `fisco-review-pr/references/` + `fisco-review-shared/` still carries them.
