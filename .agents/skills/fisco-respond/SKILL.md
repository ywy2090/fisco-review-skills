---
name: fisco-respond
version: 1.20.1
description: Process a review of your own FISCO-BCOS C++ PR — triage each severity-tagged finding, fix it with a regression test, and reply on each comment thread in the repo's "Fixed in <sha>: ..." / "Leaving X: ... because ..." format. Use when your FISCO-BCOS PR has review comments or review rounds to address, when a reviewer posts BLOCKER/HIGH/MEDIUM/LOW findings on your diff, or when you must respond to a reviewer before the next round. Not for reviewing a PR (your own or someone else's) — that is fisco-review.
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
   c. **Reject / leave as-is.** Reviewers accept a well-reasoned rejection (the record kept `rlp-protocol` PUBLIC). Your reply must show the design is correct *including consequence analysis* ("engine is a STATIC library; consumers that pull `EngineServiceCommon.o` need the transitive symbols, so PRIVATE would drop the link") — not "I disagree".
4. **Commit discipline.** Small commits, repo message style `type(scope): …`. The record's fix commit is `fix(engine): close review findings on side-by-side infra` — reference the severity tiers (BLOCKER/HIGH/MEDIUM/LOW; the repo's history sometimes wrote these as P0–P2) or the round. Keep test-only fixes as their own commit when cleaner.
5. **Verify — every touched target — then reply on each inline thread.** Verification closure: enumerate every build/test target the fix diff touches and compile + run each one; "suite green" claims must name the affected-target list. A test added in `bcos-rpc` while the loop runs only `test-bcos-engine` has verified nothing (the cited evidence must be the target that actually contains the test). Before posting any reply, check it is truthful against your own branch: the `short-sha` exists (`git log --format=%h <ref>`), the fix is actually present at that commit (`git show <sha> --stat` lists the changed file), and the named test exists and asserts the pinned behaviour.
   The verification plan comes from the **tree, never from your own commit message** — after the named mechanism check, ask the reachability question the reviewer will ask: *who can reach the new code or branch, with what inputs, over which wire/method versions* (answered by greps over the branch, not by re-reading the commit description); a fix that adds a gate, guard, or narrow branch is verified against every honest caller it now touches, not only against the test that pins it. Then reply in the repo's formats:
   - Fix: `Fixed in <short-sha>: <code-level change>; covered by the new <test_name> test.` Name the actual mechanism and the test — the reviewer verifies both at the next head.
   - Reject: `Leaving <X>: <reason + consequence>.`
   - Don't reply with empty bodies, and don't resolve a thread you haven't changed or justified.
6. **Disclose before the next round.** If the fix changes what the live service answers (status codes, comparison width, version windows), update the PR description (the repo tracks such leftover semantics in a "Leftover semantics" note) and the ChangeLog if Engine API behaviour is tracked there. Re-check your test-plan checkboxes. **Verify the disclosure against the code before pushing**: a disclosed behaviour (the description says "answers SYNCING", "compares 16 fields") must equal what the code does — a mis-disclosure blocks the reviewer's convergence and reads as a new finding.
7. **Push a new head and frame the next round.** State which prior findings are closed at `<sha>` and which items you deliberately left, so the reviewer can re-check quickly instead of rediscovering.

## Traps from this repo's history

- **Undisclosed behaviour change inside a refactor/extraction PR** — the biggest scorecard hit. A "file split, no cutover" description that rewrites the live service's answers fails Description honesty and Scope discipline. Disclose first.
- **An equivalence test that pins duplication** (`engine_common_make_status_matches_legacy`) keeps the bug in place — delete the duplicate instead of pinning two copies against a third.
- **A fix that closes one half of a finding** and misses the second half the same finding named.
- **A regression test that asserts the outcome but not the invariant the finding named** (a retry test that asserts VALID twice but never counts commits). Strengthen it when the reviewer's scenario depends on the invariant.
- **Fixing on the wrong branch/worktree** — you verify a fix against files that are not the PR branch, or commit to the wrong ref. Always `git log`/`git show` against your branch before and after the fix.
- **Rejecting without verifiable reasoning** — the reviewer re-checks at the head; make your justification derivable from code.
- **A rejection whose *form* is right but whose *technical claim* is wrong** — a rejection that states a mechanism and a consequence is only as good as its technical premise. Verify the premise independently (e.g. does `PRIVATE` on a static library really drop the transitive link, or does `$<LINK_ONLY:...>` keep it? does the version really not need the lower version's check?), not just that the argument reads coherently. A false premise, stated confidently, survives the round and gets repeated.

These are the headline traps from the record; the complete fix-reintroduction checklist lives in `references/self-check.md`.

## Self-check before pushing

Re-read your fix diff against the self-check reference in `references/self-check.md` (code conventions + fix-reintroduction traps) — a fix that introduces a new instance of a listed class will reopen the round.

## Maintenance

When you edit this skill, bump the frontmatter `version:` per the semver policy in [CHANGELOG.md](CHANGELOG.md) and add a dated entry there. Versioned as a pair with `fisco-review` — bump both in lockstep.
