# Changelog — fisco-respond

Versioned as a pair with `fisco-review`; the two bump their `version:` fields in lockstep. Self-contained: the self-check reference lives at `references/self-check.md`.

Semver policy: **MAJOR** = change to the reply format or the triage/fix semantics; **MINOR** = additive (new traps, new checklist references); **PATCH** = wording, link, or budget tweaks.

## [2.2.1] - 2026-10-12
- Lockstep version bump with `fisco-review` 2.2.1 (checklist family index + three folds; no change on this side — the reply format, evidence gate and traps are untouched).

## [2.2.0] - 2026-10-12
### Added (lockstep with fisco-review 2.2.0 — lessons from the #5615 multi-model runs)
- **Evidence-gate items 5 & 7** — item 5 now names the mechanical check: run the reviewer side's `fisco-review/scripts/verify_findings.py` over your own quotes once before pushing (it caught every drifted or hand-edited quote that a confident re-read had passed). New item 7: **CI-red attribution is verified against a clean checkout's dependency set, not your machine** — "green locally, red on CI, therefore flaky" is exactly wrong for the dependency-drift class (the red is deterministic on every clean checkout and invisible on the author's machine; #5615's head carried such a red for days behind "all green locally": `<test/utils/rlp.hpp>` present in the local evmone@0.21.0 install, absent from CI's same-version install).
- **Two new traps** — a severity dispute that argues by adjective (mirror of the reviewer's downgrade-without-citation rule: quote the severity clause and show which condition fails; upgrades hidden inside fixes disclose, not absorb); "environment flake" as an unfalsifiable rejection (the falsifiable answer names a mechanism — which dependency, which port revision, which include path — and re-running a red is cheap, *recording why it was red* is what survives the round).
- **Self-check: fix-face blind re-review (optional, historically paid-for)** — reviewer pipeline over just the fix delta with no access to the author's reasoning; the #5615 fix-face blind pass caught 9 transcription-level compile breaks the author's own re-reads had passed, one introduced by the author's own reformatting fix.

## [2.1.0] - 2026-10-10
### Added (merging the sibling author-side corpus — `fisco-handle-reviews` 1.10.x — into this skill)
- **"The `Fixed` evidence gate" (new section)** — six conditions, all required before a `Fixed` reply leaves: the finding was reproduced at the head first; every touched target was built and run with a regression that fails before the fix and passes after; the commit is on the PR's **live head chain** (re-read after pushing — a local-only commit is not a fix); class-level findings have a completed **category scan**, not just the named instance; every cited `file:line` was re-read at the final commit (fix commits drift lines — three drifts caught in one round at #5544); and an **independent verifier** confirms high-tier or behaviour-changing fixes, barred explicitly from reading the author's drafted reply or reasoning. A condition that cannot be checked leaves the item at `Pending decision` — never at `Fixed`.
- **`Not changed` standard sharpened** — falsification of the finding's premise, or a compatibility judgement naming who is affected and why it is acceptable. "It compiles" is not evidence for a CMake/include finding, and an unchecked premise is a rejection that reopens.
- **Reply bookkeeping (grafted from the corpus's posting protocol)** — persist the intent before posting (target head, source `updated_at` + body hash, thread id, body hash, authorization) and append an invisible `<!-- fisco-reply:<nonce> -->` marker so a timed-out post is recovered from the remote by nonce instead of being re-posted (a duplicate reply is worse than a late one); re-read the source version once after a successful write and report `posted_then_source_changed` rather than claiming the reply answers a version that moved; generate bodies *from* the ledger, never backfill evidence into a written reply.
- **Evidence retention** — the review directory and its ledgers are the evidence the next round reads: keep them untracked, never wildcard-clean them.
- **`references/self-check.md` traps 14–19 (new)** — close-out verified at a *different* occurrence than the one the reviewer named (#5495-r4); sibling default sites left behind after a fail-closed flip (#5496-r3); line drift between fix commits (#5544); evidence retrofitted to a reply; two field names for one quantity (write/read pair mismatch); and a newly added test whose pin is not discriminating (exception type shared by three production sites).

### Notes
- The inline one-sentence format, the round-summary shape and the status vocabulary are **unchanged** — MINOR, additive gates only.

## [2.0.0] - 2026-09-15
### Changed (reply format — the house definition, which this skill had drifted from)
- **Inline replies are one sentence.** `Fixed in <short-sha> — <one sentence: what changed>`, `Fixed in <short-sha> — <changed part>; <unchanged part> kept as-is because <reason>`, `Not changed — <one sentence, evidence-based reason>`. The em dash is the separator; the old `Fixed in <sha>: <change>; covered by the new <test_name> test.` colon-plus-semicolon template is gone, and so is the invented `Leaving <X>:` reject form (the house vocabulary is `Not changed` / `Partially adopted` / `Fixed incidentally` / `Acknowledged, logged for follow-up` / `Pending decision`).
- **The round summary reply is mandatory** and now has a shape in step 7 (first line `@<reviewer> — …`, `## Reply summary` status table, per-finding block with Verify / Behaviour change / Test coverage / Rationale, `## Verification`, `## Follow-ups`). It is a PR issue comment, not another thread reply, and it is where the mechanism, the named test, the verification path, the behaviour-change disclosure and the rejection's evidence live — previously this skill left step 7 as "frame the next round" with no format, so the detail piled up in the threads.
- Inline threading made explicit: `POST repos/$REPO/pulls/$PR/comments` with `in_reply_to`; no `@mention` inline (the thread already notifies), `Feel free to resolve.` only in the summary, GitHub prose English even for a Chinese-language finding.
- New trap entry for the failure this fixes: a multi-sentence inline reply, or no round summary at all — the most repeated miss on the author side (reported three times against the sibling skill's B.3 rule).

## [1.20.1] - 2026-09-06
### Changed
- Lockstep bump with fisco-review 1.20.1 (reachability-probe severity-by-consumer rule + #5549 capacity/txHash example). No independent content change.

## [1.20.0] - 2026-09-06
### Changed
- Lockstep bump with fisco-review 1.20.0 (full-mode trigger tightened to single-pass below >2000 lines/>5 modules; hard delegation budget cap; cross-file symmetry moved to the aggregator; golden-set.md added). No independent content change — the reviewer-side execution-topology fix does not alter the author's triage/fix/reply flow.

## [1.19.0] - 2026-09-06
### Changed
- Lockstep bump with fisco-review 1.19.0 (checklist #33-#39 cross-file & structural defect classes, delegation consult-only symmetry + missing-line rescan, BLOCKER CI-gate severity, step-7 unreadable-dependency rule). No independent content change — the author side gains nothing new because the fixes all live on the reviewer side.

## [1.18.1] - 2026-09-06
### Changed
- Lockstep bump with fisco-review 1.18.1 (checklist numbering-continuity fix + stale-intro correction in `references/checklist.md`). No independent content change.

## [1.18.0] - 2026-09-06
### Added (lockstep with fisco-review 1.18.0; from the #5548 round-1 post-mortem)
- Self-check trap 13: copied comments are re-derived, not re-typed — every sentence of a ported/mechanism comment is verified against this copy's code from C++ semantics; a shared_ptr move nulls the pointer (no moved-from member), and a truncated origin sentence drops the mechanism it explains (external round-1 F6).

## [Unreleased]

## [1.17.2] - 2026-09-05
### Changed
- Lockstep bump with fisco-review (base-drift rule + delegation budget tripwire). No independent content change.

## [1.17.1] - 2026-09-05
### Changed
- Lockstep bump with fisco-review (checklist restructuring + target-closure de-dup). No independent content change — the self-check traps 8-12 were already codename-free.

## [1.17.0] - 2026-09-05

- Verification closure is now explicit in step 5: compile and run **every** build/test target the fix diff touches; "suite green" claims must name the affected-target list (the cited evidence must be the target that contains the test).
- Self-check gains three mechanical rules found while re-auditing a missed review round: copy count for lock/perf fixes (10), linkage-scope placement of extracted helpers (11), and a column-limit sweep on touched files (12).
- Version bumped in lockstep with fisco-review.

## [1.16.0] - 2026-09-05

- Added two fix-reintroduction traps to `references/self-check.md`, both found while repairing the evm-refactor branch on Linux: **discarded protocol-contract returns at a host/vtable boundary** (the EVMC `selfdestruct` bool was treated as decoration since #4216, masking transfer failures and deleting accounts whose balance never moved) and **header case mismatch against its own includes** (five eth/pipeline headers compiled on macOS/Windows and broke every Linux TU).
- Version bumped in lockstep with fisco-review.

## [1.15.4] - 2026-09-05
### Changed
- "a new HIGH resets convergence" now says "HIGH or BLOCKER", matching fisco-review (lockstep).
- Split the dense step-5 verification paragraph into the branch-truth check and the tree-sourced verification plan.

## [1.15.3] - 2026-09-05
### Changed
- Disambiguation: the commit-discipline example now names the canonical severity tiers (BLOCKER/HIGH/MEDIUM/LOW) and notes the repo's old P0–P2 shorthand, instead of leaving two naming systems side by side; removed the opaque `#5468` and `F3` references from steps 3a and 6.

## [1.15.2] - 2026-09-05
### Changed
- Description now carries the negative trigger "Not for reviewing someone else's PR — that is fisco-review", mirroring fisco-review's cross-reference so a bare "review PR" request does not hit both skills.

## [1.15.1] - 2026-09-05
### Fixed
- Self-check: merged the "new code forms a duplicate pair" trap into the duplicate-implementation trap (the former was a special case of the latter, distinguished only by new-vs-existing code), leaving 7 traps; the merged trap now covers code the author just added.
- SKILL.md "Traps" section now cross-references `references/self-check.md` as the complete fix-reintroduction checklist, so the headline list no longer reads as exhaustive.

## [1.15.0] - 2026-09-05
### Changed
- Lockstep with fisco-review 1.15.0 (evidence discipline): step 5 verification plan must come from the tree, never from the fix's own commit message — after the named-mechanism check, walk the reachability question (who/inputs/wire versions) over the branch; step 6 requires the disclosure text to be verified against the code before pushing (mis-disclosure blocks convergence).
- Self-check: two new fix-reintroduction traps — verification plan sourced from the commit message (7), and new code forming a duplicate pair with its neighbours (8).

## [1.14.0] - 2026-09-05
### Changed
- Lockstep bump with fisco-review (checklist reorganized into three tiers and renumbered). No independent content change.

## [1.13.0] - 2026-09-05
### Added
- Traps: a rejection whose form is right but whose technical claim is wrong — verify the premise independently, not just that the argument reads coherently.

## [1.12.0] - 2026-09-05
### Changed
- Made self-contained: added `references/self-check.md` (code conventions + fix-reintroduction traps) and dropped the `../fisco-review/REFERENCE.md` cross-skill dependency.

## [1.11.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (fetch_pr.py robustness, findings.json schema, report-language policy). No independent content change.

## [1.10.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (review tooling, findings ledger, stacked-PR rule, delegation-contract updates; the shared `REFERENCE.md` gained outline-first/exact-line/minimal-read-set contract lines). No independent content change.

## [1.9.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (review file lock with timeout). No independent content change.

## [1.8.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (review lifecycle markers). No independent content change.

## [1.7.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (checklist item 18: comments are claims, not evidence). No independent content change.

## [1.6.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (checklist refactored to principle + example structure). No independent content change.

## [1.5.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (item 3/17 wording + grep-driven conventions checks). No independent content change.

## [1.4.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (per-review artifact directory). No independent content change.

## [1.3.0] - 2026-09-05
### Added
- Workflow step 5 now verifies each reply before posting: the `short-sha` exists, the fix is present at that commit (`git show`), and the named test exists.

## [1.2.0] - 2026-09-05
### Changed
- Lockstep bump with `fisco-review` (checklist items 16–18 + delegation cross-cutting/anti-priming). No independent content change.

## [1.1.0] - 2026-09-05
### Added
- Maintenance note: bump `version:` + add a CHANGELOG entry when editing.
### Changed
- Version bumped in lockstep with `fisco-review` (its checklist item 2 fix + item 15 addition).

## [1.0.0] - 2026-09-05
### Added
- Author-side workflow: triage → fix root-cause + test → reply → disclose → push.
- Branch-trap step (verify the PR branch before editing, against your own branch's blobs).
- Reply formats `Fixed in <short-sha>: …` / `Leaving <X>: <reason + consequence>`.
- Traps list (undisclosed behaviour change, equivalence tests pinning duplication, half-fixes, weak regression tests, wrong-branch fixes, unverifiable rejections).
- Self-check against the shared checklist before pushing.

## [0.x] - pre-1.0 history (not tagged)
- Split from the single reviewer skill into the author-side counterpart; renamed to `fisco-respond`.
