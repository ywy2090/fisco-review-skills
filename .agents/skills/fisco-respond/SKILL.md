---
name: fisco-respond
version: 2.3.0
description: Process a review of your own FISCO-BCOS C++ PR — triage each severity-tagged finding, fix it with a regression test, reply on each comment thread with one sentence ("Fixed in <sha> — ..." / "Not changed — ..."), and post a round summary reply carrying the evidence. Use when your FISCO-BCOS PR has review comments or review rounds to address, when a reviewer posts BLOCKER/HIGH/MEDIUM/LOW findings on your diff, or when you must respond to a reviewer before the next round. Not for reviewing a PR (your own or someone else's) — that is fisco-review.
---

# Respond to a FISCO-BCOS review (author side)

This repo's reviews (see the #5544/#5547 engine-split history) are **round-based and severity-scored**. A reviewer posts findings — each with Severity / Scope / Location / Problem / Why it matters / Recommended fix — plus a scorecard (Correctness, Tests, Scope discipline, Description honesty, …). The author replies on **each inline thread**, pushes a new head, and the next round re-checks the old findings at that head before adding new ones, until the stated convergence rule is met. Responding is therefore: triage → fix root-cause + test → reply → disclose → push.

## Workflow

0. **Branch trap.** Confirm the PR branch is the one you are editing. This repo's main checkout can sit on an unrelated branch or worktree — if so, switch to the PR branch (or a worktree of it) before touching code, and always verify code state with `git log`/`git show <sha>` against *your branch's own blobs*, never against working-tree files whose branch you cannot identify.
1. **Ingest the whole review record**, not just the summary: the round label and reviewed head, every inline thread, the scorecard, and the dimensions that were penalised. "Description honesty" and "Scope discipline" scores mean the reviewer audits your PR description against the diff — treat your own description claims as assertions to honour, not prose. Note the reviewer's round ceiling and convergence rule: a new HIGH or BLOCKER in your next head resets convergence.
2. **Reproduce each finding at your current head.** The finding gives file:line and a concrete scenario — verify it fires before you touch code. Classify by Scope in the finding:
   - **Live production path** — must fix; the "no production caller yet" discount never applies here (the reviewer already grepped the wiring, e.g. `EngineServiceInitializer` still constructs the legacy service).
   - **New infra with no production caller, consumed by later PRs in the stack** — may defer, but only up to the reviewer's stated deadline (e.g. "before #5548/#5549 wire this up"); say so explicitly in your reply.
   - **Build-graph / tests / dead code** — fix or justify; LOW items can be follow-ups only when bounded by a known future deletion.
3. **Decide per finding — three outcomes:**
   a. **Fix.** Fix the *root cause*, not the symptom — reviewers state what is not an acceptable fix (e.g. "adding the missing ids to `evicted` without collapsing the duplicated body is explicitly not the fix"). Prefer consolidating duplicated code into one shared helper over patching one of the copies (the record's fixes: shared `putStaged`, single `requireGetPayloadShape`, single `engine_common::makeStatus`). Add a **regression test named after the pinned behaviour** that fails before the fix (`new_payload_honest_retry_does_not_recommit`, `newPayloadV3CompareFieldsSurviveEngineHelper`). If the finding is about a behaviour change, disclose it in-code with an issue reference and in the PR description.
   b. **Partial fix.** If you resolve only part of a finding (e.g. `makeStatus` consolidated but the same finding's `TrackedHeadBlock` duplicate left behind), say exactly which half remains open — reviewers re-read the whole finding at the next head.
   c. **Reject / leave as-is.** Reviewers accept a well-reasoned rejection (the record kept `rlp-protocol` PUBLIC). The thread gets the one sentence (`Not changed — <reason>`); the summary-reply block for that finding must show the design is correct *including consequence analysis* ("engine is a STATIC library; consumers that pull `EngineServiceCommon.o` need the transitive symbols, so PRIVATE would drop the link") — not "I disagree".
4. **Commit discipline.** Small commits, repo message style `type(scope): …`. The record's fix commit is `fix(engine): close review findings on side-by-side infra` — reference the severity tiers (BLOCKER/HIGH/MEDIUM/LOW; the repo's history sometimes wrote these as P0–P2) or the round. Keep test-only fixes as their own commit when cleaner.
5. **Verify — every touched target — then reply on each inline thread.** Verification closure: enumerate every build/test target the fix diff touches and compile + run each one; "suite green" claims must name the affected-target list. A test added in `bcos-rpc` while the loop runs only `test-bcos-engine` has verified nothing (the cited evidence must be the target that actually contains the test). Before posting any reply, check it is truthful against your own branch: the `short-sha` exists (`git log --format=%h <ref>`), the fix is actually present at that commit (`git show <sha> --stat` lists the changed file), and the named test exists and asserts the pinned behaviour.
   The verification plan comes from the **tree, never from your own commit message** — after the named mechanism check, ask the reachability question the reviewer will ask: *who can reach the new code or branch, with what inputs, over which wire/method versions* (answered by greps over the branch, not by re-reading the commit description); a fix that adds a gate, guard, or narrow branch is verified against every honest caller it now touches, not only against the test that pins it. Then reply in the repo's formats — **one sentence inline, all evidence in the round summary reply (step 7)**:
   - Fix: `Fixed in <short-sha> — <one sentence: what changed>`. Append `file:line` only when it is part of that sentence.
   - Partial fix: `Fixed in <short-sha> — <changed part>; <unchanged part> kept as-is because <reason>`.
   - Reject: `Not changed — <one sentence, evidence-based reason>`.
   - **Inline is one sentence. Hard constraint.** The mechanism, the named test, the verification path, the behaviour-change note and the consequence analysis go to the summary reply, not the thread. A finding that seems to need three sentences in the thread is a summary-reply paragraph plus a one-sentence pointer on the thread; a multi-sentence inline reply dilutes the reviewer's one-glance read of "fixed" and reads as neither status nor evidence.
   - Post inline replies as thread replies (`POST repos/$REPO/pulls/$PR/comments` with `body` + `in_reply_to`); the thread already notifies the reviewer, so no `@mention` inline. `Feel free to resolve.` belongs in the summary reply, never inline.
   - GitHub prose is English even when the finding was filed in Chinese.
   - Don't reply with empty bodies, and don't resolve a thread you haven't changed or justified.
   - **A `Fixed` is a conjunction of facts, not a sentiment** — the six conditions in "The `Fixed` evidence gate" below must all hold before this reply leaves; a condition you cannot check leaves the item at `Pending decision`, never at `Fixed`. Post-time bookkeeping (intent + nonce, timeout recovery, post-write re-read) lives in the same section.
6. **Disclose before the next round.** If the fix changes what the live service answers (status codes, comparison width, version windows), update the PR description (the repo tracks such leftover semantics in a "Leftover semantics" note) and the ChangeLog if Engine API behaviour is tracked there. Re-check your test-plan checkboxes. **Verify the disclosure against the code before pushing**: a disclosed behaviour (the description says "answers SYNCING", "compares 16 fields") must equal what the code does — a mis-disclosure blocks the reviewer's convergence and reads as a new finding.
7. **Push a new head, then post the round summary reply.** The summary is a PR issue comment — not another thread reply — and it is where every detail the inline replies deliberately omit belongs: per-finding status, the mechanism, the named test, the verification path, the behaviour-change disclosure, and the rejection's evidence. Its first line is `@<reviewer> — <overall handling status>` and it names the head you just pushed (the reviewer re-checks every prior finding at that sha); `Feel free to resolve.` appears here and nowhere else. When several reviewers filed findings, post one summary per reviewer, each opening with its own `@mention`.
   Shape (the reviewer re-checks prior findings against it):

   ```markdown
   @<reviewer> — <overall handling status, naming the pushed head sha>

   ## Reply summary

   | # | Finding | Status | Commit |
   |---|---------|--------|--------|
   | 1 | <finding> | Fixed | <sha> |
   | 2 | <finding> | Not changed | — |

   ## Finding <N> — <status>

   <what changed, 1–2 sentences>

   - **Verify**: <file:line or `git show` command>
   - **Behaviour change**: <compatibility impact, or "none">
   - **Test coverage**: <test names, and what each asserts>
   - **Rationale**: <reference semantics, or the rejection's evidence>

   ## Verification

   - <affected build/test targets and their results>
   - <finding-to-verification mapping>

   ## Follow-ups

   - <what was deferred, why, and the owner/condition>
   ```

   Status vocabulary: `Fixed` / `Fixed incidentally` / `Partially adopted` / `Not changed` / `Acknowledged, logged for follow-up` / `Pending decision`. State which prior findings are closed at `<sha>` and which you deliberately left, so the reviewer can re-check quickly instead of rediscovering.

## The `Fixed` evidence gate

Grafted from the author-side corpus (`fisco-handle-reviews` 1.10.x), which treated a `Fixed` claim as a conjunction of six machine-checkable facts. The vocabulary here is `Fixed` / `Not changed`; the gate is what makes either word mean something.

1. **Reproduced first.** The finding fired at your head before you touched code (step 2). A fix for a finding you never reproduced is a guess — say `Not changed — could not reproduce at <sha>` instead.
2. **Every touched target built and run.** Step 5's closure, naming the affected-target list; the regression test named after the pinned behaviour fails before the fix and passes after.
3. **The commit is on the PR's live head chain.** Re-read it after pushing (`git merge-base --is-ancestor <sha> HEAD` against the pushed head, or `git ls-remote` on the branch). A commit that exists only locally is not a fix, and the sha in your reply must be one the reviewer can fetch.
4. **Class-level findings have a completed category scan.** The invariant was swept across its entry points and the sweep's result is in the summary — the reviewer re-reads the whole finding at the next head, so "the named instance is patched" is not the claim being checked.
5. **Every cited `file:line` was re-read at the final commit.** Fix commits drift line numbers (three drifts were caught in one round at #5544); verify the location *before* naming it in the reply, never after. Where quotes are carried (summary evidence, ledger entries), run the reviewer side's `fisco-review/scripts/verify_findings.py` on your own evidence once before pushing — it is model-agnostic, costs nothing, and in the #5615 runs caught every drifted or hand-edited quote that a confident re-read had passed.
6. **An independent verifier confirms the high tier.** For a `HIGH`/`BLOCKER` fix, or any fix that changes what the live service answers, a verifier who reads the finding, the final commit/diff, the head source and the test output — and **must not read your drafted reply or your reasoning** — confirms the fix. A confident explanation is not a substitute for an independent read; a result that is not `confirmed` leaves the item open, and the verifier re-runs after the head moves.
7. **CI-red attribution is verified against a clean checkout's dependency set, not against your machine.** "Green locally, red on CI, therefore flaky/environment" is exactly wrong for the dependency-drift class: a red caused by a port/package installing (or no longer installing) a header your local cache happens to have is *deterministic* on every clean checkout and invisible on yours — and the author is the one machine that can never see it. Before writing "environment issue", check the failing include/log against the CI environment's installed dependency set (which package and port provides that path, and does that port revision ship it); if you cannot rule drift out, say so and name the check, instead of filing it as flake. The #5615 head carried exactly this red for days behind "all targets green locally": `<test/utils/rlp.hpp>` resolved through the local evmone@0.21.0 install but not CI's same-version install.

For **`Not changed`** the standard is falsification, not preference: either the mechanism you cite disproves the finding's premise, or a compatibility judgement names who is affected and why that is acceptable. "It compiles" is not evidence for a CMake/include finding, and a premise you did not check is a rejection that will be reopened.

**Reply bookkeeping.** Before posting, persist the intent: target head, the source comment's `updated_at` + body hash, the thread id, the body hash, the authorization time. Append an invisible `<!-- fisco-reply:<nonce> -->` marker to the body so a "server accepted, client timed out" outcome is recoverable from the remote by nonce — **never re-post blindly**; a duplicate reply is worse than a late one. After a successful write, re-read the source version once; if it changed while you were posting, state `posted_then_source_changed` in the summary rather than claiming the reply answers the current version. Generate each body *from* the ledger, never write the reply first and backfill the evidence — and do not resolve a thread you have neither changed nor justified.

The review directory and its ledgers are the evidence the next round reads. Keep them untracked and never clean them up with a wildcard.

## Traps from this repo's history

- **Undisclosed behaviour change inside a refactor/extraction PR** — the biggest scorecard hit. A "file split, no cutover" description that rewrites the live service's answers fails Description honesty and Scope discipline. Disclose first.
- **An equivalence test that pins duplication** (`engine_common_make_status_matches_legacy`) keeps the bug in place — delete the duplicate instead of pinning two copies against a third.
- **A fix that closes one half of a finding** and misses the second half the same finding named.
- **A regression test that asserts the outcome but not the invariant the finding named** (a retry test that asserts VALID twice but never counts commits). Strengthen it when the reviewer's scenario depends on the invariant.
- **Fixing on the wrong branch/worktree** — you verify a fix against files that are not the PR branch, or commit to the wrong ref. Always `git log`/`git show` against your branch before and after the fix.
- **A multi-sentence inline reply, or no round summary at all** — the two halves of one miss, and this skill's most repeated. Inline is one sentence (`Fixed in <sha> — …` / `Not changed — …`); the mechanism, the test name, the verification path and the behaviour-change note are summary-reply material. The reviewer reads the thread for status and the summary for evidence — a thread carrying both reads as neither.
- **Rejecting without verifiable reasoning** — the reviewer re-checks at the head; make your justification derivable from code.
- **A rejection whose *form* is right but whose *technical claim* is wrong** — a rejection that states a mechanism and a consequence is only as good as its technical premise. Verify the premise independently (e.g. does `PRIVATE` on a static library really drop the transitive link, or does `$<LINK_ONLY:...>` keep it? does the version really not need the lower version's check?), not just that the argument reads coherently. A false premise, stated confidently, survives the round and gets repeated.
- **A severity dispute that argues by adjective** — "this isn't a BLOCKER, it's only reachable in config X" is the author-side mirror of a downgrade without citation. When disputing a tier, quote the reviewer's severity clause (fisco-review's severity semantics) and show which condition of it your situation fails; a coherent-sounding downgrade that cites no clause is exactly what the reviewer's round-2 hard-target reconciliation is trained on, and it reopens the thread with interest. Same for upgrades hidden inside fixes — a fix that quietly raises the stakes of the surrounding code discloses that, it does not absorb it.
- **"Environment flake" as an unfalsifiable rejection** — the CI-red attribution trap (evidence-gate item 7) stated as a trap: the two most common wrong answers to a CI red are "my machine is green, so CI is broken" and "it's flaky, re-run" — both unfalsifiable, both preserving the red. The falsifiable answers name a mechanism: which dependency, which port revision, which include path, which runner difference. Re-running a red is cheap; *recording why it was red* is the part that survives the round.

These are the headline traps from the record; the complete fix-reintroduction checklist lives in `references/self-check.md`.

## Self-check before pushing

Re-read your fix diff against the self-check reference in `references/self-check.md` (code conventions + fix-reintroduction traps) — a fix that introduces a new instance of a listed class will reopen the round.

**Optional, but historically paid for itself: a fix-face blind re-review.** For a multi-fix head, run the reviewer side's pipeline over just the fix delta (`git diff <last-reviewed>..<fix-head>`) with no access to your reasoning or your reply drafts — the commit messages are that delta's spec. The measured rate of fix-introduced defects is not negligible: the #5615 fix-face blind pass caught 9 transcription-level compile breaks (dangling braces, orphaned `catch`, a declaration eaten by column reflow) that the author's own re-reads had passed, one of them introduced by the author's own reformatting fix. Same discipline as evidence-gate item 6: fresh eyes, no drafted-answer contamination.

## Reply self-check before posting

Per thread: exactly one sentence — `Fixed in <short-sha> — …`, `Fixed in <short-sha> — <changed part>; <unchanged part> kept as-is because <reason>`, or `Not changed — <reason>`. No test name, no verification path, no rationale, no second sentence in the thread. Then the round summary reply: it exists, it opens with `@<reviewer> — …` naming the pushed head, it carries every finding's status plus the mechanism / test coverage / verification / rationale you kept out of the threads, and it is the only place `Feel free to resolve.` appears. A reply you cannot compress to one sentence is not a longer reply — it is a summary block you have not written yet.

## Maintenance

When you edit this skill, bump the frontmatter `version:` per the semver policy in [CHANGELOG.md](CHANGELOG.md) and add a dated entry there. Versioned as a pair with `fisco-review` — bump both in lockstep.
