# Changelog — fisco-review

Versioned as a pair with `fisco-respond` (reviewer checklist lives here at `references/checklist.md`); the two bump their `version:` fields in lockstep.

Semver policy: **MAJOR** = change to the finding taxonomy / severity semantics / report format (a finding produced under v1 may be interpreted differently under v2); **MINOR** = additive (new checklist items, new modes, new code conventions); **PATCH** = wording, link, or budget tweaks.

## [2.2.1] - 2026-10-12
### Changed (structural, PATCH — no new rules, no renumbering, findings read identically)
- **Family index at the top of `references/checklist.md`** — a question→items map (10 families) so the batch-appended cohorts (33-39, 40-53) stay reachable by question without reordering; items stay numbered for citation stability. The index also fixes the **hard cap: 55 numbers** — a new item may only enter by retiring/folding an overlapping one, unless a golden-set miss maps to no existing item (the 32→39 no-measured-gain lesson, now made binding).
- **Three folds (aliases kept, nothing renumbered)** — #49 (gate bidirectionality) folded into #20 as its second question; #44 (fix side effects caller sweep) folded into #29 as its second half; #27 (bulk copies under guard) folded into #26 as the second shape of container-copy economics. Folded numbers remain one-line aliases so ledgers, golden entries and `lessons-pending.md` revival targets keep resolving. Reading surface drops ~15% with zero rule loss.
- **#55 marked as the wiring member of the #4/#38/#52 test-vacuity family** (the family asks whether a test proves anything; #55 asks whether the declared judge is even wired in).
- **Delegation executor-precondition paragraph compressed ~40%** — same four rules (measured 100% format compliance / judgement-sorted recall / phase matching / +18pp cross-model option), fewer words.

## [2.2.0] - 2026-10-12
### Added (aggregation-gate hardening + execution-model lessons — all from the #5615 multi-model runs)
- **`scripts/verify_findings.py` (new)** — the aggregation gate's mechanical floor: per-finding file-existence, line-bounds and verbatim-quote checks (exact at ±15, then whitespace-normalized), exit 2 on any `QUOTE_NOT_FOUND`/`FILE_NOT_FOUND` so it can gate the report. Accepts both the ledger `findings.json` and module/aggregate `findings` outputs. In the #5615 runs the equivalent gate caught every hallucinated quote across three executors at zero judgement cost.
- **Step 8 hardening (three rules + one tripwire)** — (a) a severity change must quote the severity clause the finding no longer satisfies (the mirror of `fisco-respond`'s rejection-premise standard; an #5615 executor re-graded a deterministic repo-wide ctest death BLOCKER→HIGH citing nothing); (b) **hard-target survival reconciliation** — every sub-agent BLOCKER/HIGH is either in the final report or in the drop/downgrade ledger with cited evidence; in neither = the review's own bug (an #5615 executor's aggregation silently dropped a unit-level BLOCKER it had itself found); drops get a one-line verification-boundary entry — a recorded decision, not a deletion; (c) **carpet-bombing tripwire** — an agent returning >25 findings for one module is reporting reading notes (one #5615 module yielded 156 entries, 18 positive-verification notes); the aggregator takes over triage.
- **checklist items 54–55 (new)** — 54 third-party header resolution path (an include resolving through an installed package's header is a dependency contract; the #5615 attribution probe: `<test/utils/rlp.hpp>` via evmone@0.21.0 port drift — all executors and the first human pass mis-filed the CI red as a PR defect); 55 declared coverage must have a consumer (oracle naming a nonexistent judging test, suites with no CI runner, tests compiled into no target — the #5615 never-found class).
- **Golden set cohort 2 (G9–G20 + 2 process goldens)** — the 12 findings nine executor arms never reached, each mapped to the item that should now catch it (F7→#46, F9→#42, F26→#52, F33/F37/F31→#55, F34→#21/#42, F39/F40→#45, F53/F59→#38, F60→#40), plus the two aggregation-gate process goldens. Experiment record: `.agents/experiments/model-ab-5615/`.
- **Delegation: executor-model precondition (stated, not assumed)** — #5615 measured this skill's full mode on three external executors with identical inputs: format compliance 100% everywhere, recall 44.6%/24.6%/16.9% sorted by executor judgement, aggregation gate the decisive loss point. Operational rules written in: match the executor to the phase (fast/shallow executors are wrong for the tool loop however strong their single pass), the sub-agent layer's practical ceiling is ~half the key so the main-thread recovery passes are budgeted work, and a cross-model second opinion (+18pp key coverage in the same runs) is the sanctioned big-PR option — the gate stays single.

### Notes
- No change to the finding format, severity semantics, report shape, or disposition vocabulary — MINOR per policy; existing ledgers keep their references (numbering continues at 54, nothing renumbered).
- Ground truth for this cohort is the PR #5615 full-blind ledger this skill's native executor produced (65 findings, 13.9M tokens) — recorded in `references/golden-set.md` with the experiment directory as the retrievable record.

## [2.1.0] - 2026-10-10
### Added (merging the sibling reviewer corpus — `fisco-review-pr` 2.13.x + `fisco-review-shared` — into this skill)
- **`references/methods.md` (new)** — the executable procedures that lived only in the sibling corpus, carried over with the mutation **isolation contract** (detached worktree at the pin, one change per experiment with a clean restart, out-of-tree build dir, cleanup ownership; "cannot isolate ⇒ `blocked`, never verified"). Migrated: **M1** negative control, **M3** suspect tracking, **M5** layered production/test verification, **M7** tool blind-spot declaration, **M8** wire-shape matrix, **M10** single-source-of-rule audit, **M11** fixture reverse-decode / unique signal. New **M13** folds the corpus's include/CMake apparatus (M2/M4/M6/M12) plus the clang-format + clean-configure lesson into one compact procedure. M9 is not migrated — its rule now lives in checklist #12/#18.
- **checklist items 40–52 (new)** — thirteen classes the sibling corpus had and this checklist lacked, each naming the incident behind it: wire-shape matrix, RLP walker cursor, gate-vs-producer reconciliation, coroutine frame lifetime, caller sweep on an error-channel change, residual state/return semantics, numeric width-sign-units, object state & move/copy, API name vs behaviour, gate bidirectionality, compile coverage for header-only targets, macro propagation in public headers, discriminating pins. Numbering continues at 40 — **nothing existing is renumbered**, so prior ledgers, golden entries and in-flight findings keep their references.
- **checklist item 53 (new)** — causal attribution is verified, not accepted (the corpus's most-repeated lesson, ×12): trace X→Y, because getting the direction right does not make every sub-claim right. It is the verification-discipline block's ninth rule but is numbered **53** at the end of the file: inserting it as "9" would have duplicated numbers 9–20 and broken every existing "checklist item N" citation — the same collision the 1.19.0 entry below had to repair by renumbering.
- **`references/lessons-pending.md` (new)** — the learning loop's intake tier: candidates with `trigger_count`, the graduate/expire rules (≥2 triggers across ≥2 PRs or ≥2 independent modules; expire at zero after 5 judgeable rounds; at most one increment per `(PR, round, lesson)`), and the **migration table** mapping every sibling-corpus lesson to its home here so the merge is auditable. `golden-set.md` stays the graduated tier; Maintenance now accepts "a golden entry **or** a named lesson id".
- **Coverage honesty (step 7)** — a diff touching a risk surface (consensus/wire field, installed header or build graph, tx-admission lane) records its coverage cells in a `coverage.json` beside the ledger; any `unreviewed` cell sets `completeness: "gaps"` and is named in the Verification boundary instead of being absorbed into a completion claim. Outside a risk surface completeness still rests on target closure — additive, no matrix inflation.
- **Traceability and cost** — findings may carry `checklist_ids` (making step 6's "re-apply the items this finding was classified under" mechanical), and each round persists a `metrics.json` (tokens/durations/pages, `null` when unavailable, never estimated) so cost-vs-recall stays measurable across rounds.

### Notes
- The finding format, severity semantics, report shape and disposition vocabulary are **unchanged** — that is why this is a MINOR bump: existing reports and ledgers stay valid. The sibling corpus's machine-checkable coverage matrix and fail-closed `INCOMPLETE` verdict are deliberately **not** adopted (measured cost-vs-recall plus vocabulary churn); the coverage cells above are the proportionate part of that machinery.
- Source corpus: `fisco-review-pr` 2.13.0, `fisco-handle-reviews` 1.10.0, `fisco-review-shared` checks 2.5.2 / methods 2.4.1 / commands 1.3.0.

## [2.0.0] - 2026-09-15
### Changed (lockstep with fisco-respond 2.0.0 — the shared author-reply format)
- The reply format this side cites now matches the house definition: `Fixed in <sha> — …` / `Not changed — …`, one sentence inline with the evidence in the round summary reply. Step 9's per-finding response line and step 3's "author replies" pull changed from the old colon form (`"Fixed in <sha>: …"`, `"Leaving X: because …"`), so the reviewer side no longer reads a format the author side has stopped writing.
- No change to the finding taxonomy, severity semantics, or report format; the pair's version moves because the round protocol's reply format is shared, and the version is stamped into every report footer.

## [1.20.1] - 2026-09-06
### Changed
- Reachability probe (step 6) now carries the severity-by-consumer rule with the #5549 capacity/txHash example: an asymmetry is only half the finding — trace the consumer's path in *each* shape before grading. Filed LOW as "the consumer checks `OpRejectIsCapacity` before evicting", the hash-less capacity fault actually fell through `culprit.has_value()` to `-32603` — the "safe" branch was dead code, and the real severity was HIGH (kyonRay round-3 F1).

## [1.20.0] - 2026-09-06
### Changed (from the #5549 execution post-mortem: parallel sub-agents cost 3-5× budget with lower recall than a single pass)
- Full-mode trigger tightened from "≥3 modules or >~1000 lines" to ">2000 lines across >5 modules"; below that the main thread reads the whole diff directly (single-pass), on the evidence that file-slicing cut cross-file symmetry and 2.4-5.6M tokens/agent did not buy recall.
- Delegation budget is now a hard cap (≤2M tokens / ≤35 calls): exceeding it stops the agent and the main thread takes over its un-covered files. Added a zero-finding tripwire (>1.5M tokens with no findings = linear-reading, stop and take over).
- Cross-file symmetry (sibling-helper step-set parity #33, value-level duplication #37) moved from the agents to the aggregator as a dedicated post-pass — it is a single continuous read file-slicing cannot reproduce.
- Added `references/golden-set.md` (the 8 missed #5549 findings as a retrievable regression set); Maintenance now requires a new checklist item to name the golden entry it catches.

## [1.19.0] - 2026-09-06
### Added (from the #5549 post-mortem: this skill's rounds missed 8 of the external reviewer's 10 findings at the same head)
- Defect classes 33-39, a new "cross-file & structural" tier: sibling-helper step-set parity (33, from F2 `setEthBlockVersion`); concurrency contract → shared-state inventory, the inverse of #13 (34, from F3 unserialized delegate); intra-function defensive-pattern symmetry, the missing-line signal (35, from F5 memcpy bound); public-header → include → link-visibility → install connectivity (36, from F6 PRIVATE rlp-protocol); value-level duplication of consensus literals (37, from F7 duplicate hash constants); self-referential oracle detection (38, from F1+F2 self-derived expected hash); two-notions-of-one-semantic (39, from F8 method-vs-shape version).
- Delegation contract: consult-only is not a black box — an owned function that is the same-domain sibling of a helper in a consult-only file must diff that sibling's step set; the aggregator gains a missing-line rescan over primitive-touching functions (checklist #35).
- Severity: BLOCKER now covers a repo-wide build/CI gate that fails deterministically for the whole test target and outlives the PR (the corpus/CMake-gate case).
- SKILL.md step 7: a finding whose disposition depends on an unreadable file may only be marked "could not determine", never fixed/rejected (the Round-2 reviewer's `OpScheduler.h` gap).

## [1.18.1] - 2026-09-06
### Fixed
- Restored the checklist's globally continuous item numbering broken by the 1.18.0 insertions: the new Verification-discipline items 5-8 and the two new consistency items left duplicate numbers in the doc. Correctness is now 9-20, consistency & hygiene 21-27, portability & protocol boundaries 28-29, mechanical checks 30-32 (Verification discipline stays 1-8), so every "checklist item N" citation resolves to exactly one rule.
- Verification-discipline intro now reads "These eight" (the section grew from 4 to 8 items in 1.18.0).

## [1.18.0] - 2026-09-06
### Added (from the #5548 round-1 post-mortem: our rounds 1-4 missed F1-F7 that the external reviewer filed)
- Verification discipline 5-8: copy-vs-origin audit (truncated copied comments are dropped-mechanism fingerprints, F1/F2); primitive-contract grep against new callers (F1); adversarial audit of round-requested fixes, not acceptance-shaped verification (F5); residual-gap language must become a finding or a named accepted risk (F1).
- Defect classes 22-23: `optional::value_or` on a const lvalue deep-copies (F3); bulk container copies inside an exclusive guard counted as a hunt over new code, not only over fixes (F7).

## [Unreleased]

## [1.17.2] - 2026-09-05
### Changed
- Added the base-drift rule to step 1 (symmetric partner of head-drift): pin the diff base from the tracker's `base.sha`, not a local ref — a stale local base ref turns a 46-file PR into a 1500-file diff.
- Corrected the delegation budget to a realistic tripwire (~300k–1M tokens, ≤40 tool calls) and added an aggregator check for the three runaway signals (re-reading, full-reading instead of grep-first, no-evidence tool calls) instead of a hard quota.

## [1.17.1] - 2026-09-05
### Changed
- Restructured the checklist tail: the two ad-hoc sections ("Additions", "Mechanical checks") are now continuous tiers — 22-23 (portability & protocol boundaries) and 24-26 (mechanical checks) — removing the 1-4 numbering collision with verification discipline.
- De-duplicated "target closure": it now lives once in SKILL.md step 7 (workflow); the checklist's mechanical-checks copy was removed and the section points at step 7.
- Removed the round-3 finding codenames (F1-F4) from rule text and demoted the concrete examples to `→ 本仓库：` instances, matching the rest of the checklist.

## [1.17.0] - 2026-09-05

- Three convergence-gate rules, all from one missed round (a blocker landed in absorbed-and-unaudited commits walked past two green rounds): **unreviewed surface is a convergence blocker** (absorbed commits must be audited before a round may claim convergence — a review miss, not an author error), **verification target closure** (step 7: compile+run every target the diff touches; "suite green" names the affected-target list), and the **converged-round fast path now has three preconditions** — zero unaudited surface, the approval round is a full round (full-surface re-hunt at the terminal head), and every disclosure verified against the code.
- Checklist gains the four mechanical checks: affected-target closure, copy count for lock/perf fixes, linkage-scope placement of extracted helpers, column-limit sweep.
- Version bumped in lockstep with fisco-respond.

## [1.16.0] - 2026-09-05

- Checklist additions from the evm-refactor Linux repair: include-case parity for new headers (HIGH when broken — a compile break invisible on case-insensitive CI) and protocol-contract returns (a discarded success/failure return at a host/vtable boundary is a HIGH fail-open finding when its failure path falls through to success bookkeeping).
- Version bumped in lockstep with fisco-respond.

## [1.15.4] - 2026-09-05
### Changed
- Defined "convergence rule" and "round ceiling" in the Rounds section (both were referenced but never stated; round ceiling now has a definition + example of 2–3 rounds).
- Extracted the per-review lock into `scripts/lock.sh` (acquire/release, timeout + stale-TTL); step 2 and the finish marker now call it instead of restating the mkdir/poll/TTL mechanics.
- Split the dense delta-mode paragraph; made "Unresolved sweep" a `- ` sub-bullet of step 8 to match step 6.

## [1.15.3] - 2026-09-05
### Changed
- Disambiguation pass: full mode now has a concrete trigger (≥3 modules or >~1000 changed lines); a "round" is explicitly distinguished from a "delta/full" execution mode; the stacked-PR boundary gets a `git log <stack-base>..<head>` recipe; materialization closure covers transitive headers; the delegation tool-call budget is a soft cap; Scope adds "shared infra consumed by later stack PRs"; the disposition is enumerated (APPROVE / CHANGES_REQUESTED / COMMENT); convergence names BLOCKER alongside HIGH; the description drops "someone else's" so self-review also triggers.
- Step 5: when the head has advanced, the prior ledger is located by globbing `.agents/reviews/pr-<number>-*/findings.json`; verified-clean items and deliberate behaviours persist in a sibling `known-clean.json` (not `findings.json`, which is findings-only).

## [1.15.2] - 2026-09-05
### Changed
- De-duplicated the "non-findings must quote the code that establishes safety" rule: Review shape item 5 is the single canonical definition; step 6 and step 8 now point at it, and the delegation contract's aggregation-gate line no longer repeats it.
- Step 6 split into a lead plus two sub-bullets — "A fix is not a re-review" and "Reachability probe" — so four distinct lessons are no longer packed into one paragraph; removed the round-specific `K1` codename, keeping the concrete example.

## [1.15.1] - 2026-09-05
### Fixed
- `findings.json` schema correction: the quoted `premise` field is now required only for `rejected` items (a head-re-checkable technical premise); `wontfix` items carry a `deferred_until`/`reason` field instead, since a won't-fix decision is a scope/deferral call, not a code premise. This aligns step 5 with the delta-mode premise-recheck rule, which already targeted rejections only.

## [1.15.0] - 2026-09-05
### Changed
- Evidence discipline made symmetric (all six from the #5547 round-3/4 retrospective):
  - Delta claim-verification now has a standard for **rejections**: a rejection's stated technical premise is re-verified at the head; a premise that no longer holds reopens the finding (the F7/K8 lesson — a wrong CMake-semantics rationale survived three rounds as a frozen `rejected` status).
  - `findings.json` rejected/wontfix items require a quoted `premise` field; the ledger carries conclusions AND evidence, and every round re-checks premises.
  - Non-findings ("checked, and not a problem") are held to the finding evidence standard: quote the lines that establish safety, not a one-line impression (the K7 lesson).
  - Convergence blocks on **mis-disclosed** behaviour changes — a disclosure whose text contradicts the code (verified disclosure-vs-code, not disclosure-existence).
  - Fix re-audit adds the reachability probe: who can reach the new code, with what inputs, over which wire/method versions — answered from the tree, never from the fix commit's own message (the K1 lesson).
  - Unresolved sweep default flips to **resolve**: parking is reserved for facts genuinely outside the materialized tree.
- Checklist: verification-discipline item 3 now names upstream-parity/provenance claims (comments, commit messages, description lines) as assertions to verify independently; delegation budgets require clean bills to quote code and reserve parking for out-of-tree facts.

## [1.14.0] - 2026-09-05
### Changed
- Reorganized the defect checklist into three tiers — Verification discipline (meta-rules, read first), then Defect classes (correctness & concurrency), then Defect classes (consistency & hygiene) — and renumbered items 1-21 continuously. No items added or removed; only grouping and numbering shifted. The → 本仓库： marker legend now lives in the verification-discipline intro.

## [1.13.0] - 2026-09-05
### Added
- Checklist items 19-21: same-name definitions split their callers by binding; version/shape requirements are cumulative; test coverage must be a superset of what the code enforces.
- Workflow step 1: head drift is the review's own bug — re-fetch the tracker head before writing the report and mark any new commits as unreviewed.
- Workflow step 6 + delegation cross-cutting (c): a fix is not a re-review — re-apply the original finding's checklist items over the whole region the fix changed.

## [1.12.0] - 2026-09-05
### Changed
- Moved `REFERENCE.md` to `references/checklist.md` (skill-creator canonical layout); updated SKILL.md links.
- Slimmed steps 2–3 to point at `scripts/verify_tree.sh` / `scripts/fetch_pr.py` instead of re-explaining their mechanism.

## [1.11.0] - 2026-09-05
### Fixed
- `fetch_pr.py`: create the output dir (`os.makedirs`) and fail with a friendly message on HTTP 404/403/timeout instead of a bare traceback.
- Workflow step 1 now instructs fetching the fork/PR head if the sha is not local.
### Added
- `findings.json` schema spelled out (array of {id, severity, origin, scope, title, location, status, fix_sha}; status enum).
- Report-language policy made explicit: English report body (repo history) + Chinese lifecycle markers (user-facing), intentionally split.

## [1.10.0] - 2026-09-05
### Added
- Review-record tooling: `scripts/fetch_pr.py` (one run saves pr/commits/reviews/comments/issue-comments/codecov into the review dir and prints the pin summary) and `scripts/verify_tree.sh` (hash-verify the materialized tree against head before any read). From the #5549 round-1 post-run retrospective.
- Findings ledger: each review dir keeps `findings.json`; every round updates statuses at its head and the known-items list is generated from it — also the cross-session record for resuming a review later.
- Stacked-PR rule: the review target is the PR's own commits; stack commits inherit the base PR's ledger and are only re-verified, never re-reviewed.
- Converged-round fast path (all prior findings closed at an unchanged head → status table + convergence + scorecard delta).
- Post-aggregation unresolved sweep: every "could not determine" is resolved with one targeted read or parked in the verification boundary with the read set that would resolve it.
- Delegation: outline-first reads, exact line numbers, minimal-read-set per unresolved item; the aggregator pre-resolves build/CI/config files into known-items.
- Materialize now includes headers-only of directly-included modules (interface closure) so cross-module questions resolve in-session.
### Changed
- Head confirmation works for fork PRs (verify the sha exists locally; the head ref is not a local ref).
- Delta mode states the head-unchanged case explicitly (claim-verification against the fix diffs only).
- Report language pinned to the repo's review history (English).

## [1.9.0] - 2026-09-05
### Added
- Review file lock with timeout: `mkdir <dir>/.lock` (atomic, records PID + timestamp) acquired before materializing; 30 s acquire timeout (poll ~2 s, fail fast); stale-lock TTL 30 min (break if PID dead); released at the finish marker. Prevents concurrent reviews of the same PR@sha from clashing.

## [1.8.0] - 2026-09-05
### Added
- Review lifecycle markers: print `准备开始 review PR #<number>` + PR identity (title, base→head@sha, diffstat) at the start, and `review PR #<number> 结束` as the final line of every review.

## [1.7.0] - 2026-09-05
### Added
- Checklist item 18: comments are claims, not evidence — verify every comment's asserted invariant against the code; never accept a comment on faith or dismiss a bug by citing one. Counters the over-dismissal seen in the v1.6.0 evaluation (agents dismissed real findings by citing "documented as intentional" without code evidence).

## [1.6.0] - 2026-09-05
### Changed
- Refactored the defect checklist into a principle + `→ 本仓库：` example structure so each item is domain-neutral rather than hard-coding FISCO-BCOS symbols.
- Merged the two commit-failure items (old 2 and 15) into one generic "commit failure must not be masked as success"; abstracted the over-fitted items (old 8, 16, 3, 9, 10) to generic principles with FISCO-BCOS demoted to examples. 18 → 17 items.

## [1.5.0] - 2026-09-05
### Changed
- Checklist item 3 now also covers field-comparison completeness (a root/commitment compared but the committed field itself left unchecked, e.g. the withdrawals list).
- Checklist item 17 reworded to a greppable signal (`const T&` accessor returning a member reference) after it failed to fire for `forkchoiceState()`.
### Added
- Delegation contract: conventions checks are grep-driven (locate + read hit snippets), not full re-reads, to keep recall within budget.

## [1.4.0] - 2026-09-05
### Added
- Per-review intermediate-artifact directory `.agents/reviews/pr-<number>-<head-short-sha>/` (materialized tree + fetched PR record + known-items + findings), kept untracked.

## [1.3.0] - 2026-09-05
### Added
- Workflow step 1 now confirms the PR commit: verify the tracker's `head.sha` equals the local branch tip (`git rev-parse`) before reviewing.

## [1.2.0] - 2026-09-05
### Added
- Checklist items 16–18: head canonical fail-open, reference-lifetime accessors, shared state mutated outside the lock.
- Delegation contract: cross-cutting tasks — every agent also runs claim-audit (item 1) and the conventions axis (license header, `c_`/`k` naming, exception idiom, `.h`/`.cpp` shape).
- Delegation contract: no answer-injection rule — hand agents the checklist + PR claims, not candidate answers.

## [1.1.0] - 2026-09-05
### Fixed
- Checklist item 2 corrected: consumed artifacts must be cleared *after* durable commit I/O, not before — the pre-I/O clearing masks an I/O throw as a false VALID on retry.
### Added
- Checklist item 15: commit durability / failure-masking.
- `Origin` values clarified: INTRODUCED (this PR) vs PRE-EXISTING (already on base).
- Maintenance note: bump `version:` + add a CHANGELOG entry when editing.
### Changed
- Trimmed description to what/when (moved the mode-switch trigger out of the description).

## [1.0.0] - 2026-09-05
### Added
- Review modes: delta (default, round re-check) vs full (parallel deep pass), with cost guidance.
- Branch materialization step: extract the reviewed head via `git archive`; never read the working tree when reviewing another branch.
- Known-items list as standard input to sub-agents (prior findings + verified-clean items + deliberate behaviours).
- Finding `Evidence:` requirement (verbatim ≤6-line quote) and the aggregation gate.
- Deep-mode delegation contract in `REFERENCE.md` (file ownership, budgets, layout).
### Changed
- Finding format now requires code evidence; "checked clean" claims are treated as unverified unless quoted.

## [0.x] - pre-1.0 history (not tagged)
- Created as a single reviewer skill from the #5547 review record; split into reviewer (`fisco-review`) + author (`fisco-respond`) sides; renamed to shorter names; added modes / branch-trap / delegation contract.
