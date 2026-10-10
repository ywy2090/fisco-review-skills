# Lessons pending graduation

The intake tier of this skill's learning loop. Two tiers, two jobs:

- **`golden-set.md`** — graduated, with ground truth: a retrievable test (an external reviewer's finding this skill missed, at a named head). Every new checklist item must name one.
- **this file** — candidates, with a trigger count and an incident, that are **not yet** encoded anywhere. A candidate becomes a checklist item when it has been seen often enough to be a class, not an incident.

Grafted from the sibling corpus's lessons lifecycle (`fisco-review-shared/lessons_pending.md` + `reflection.md`), whose accumulated entries are the source of the items added in v2.1.0.

## Lifecycle rules

- **Add** — `trigger_count` starts at 0; record the incident (PR + round) and the *miss mode* (why it was not caught), not just the rule.
- **Count** — at most **one increment per `(PR, round, lesson)`**. A lesson firing in three rounds of the same PR is one PR; it does not prove generality.
- **Graduate** — ≥2 triggers across ≥2 PRs (or ≥2 independent modules), **and** the rule has been written into `checklist.md` / `methods.md`. Graduation adds an item number *and* a golden-set entry carrying the ground truth. Graduation without ground truth is how a checklist grows without getting more accurate.
- **Expire** — 0 triggers across 5 judgeable review rounds ⇒ tombstone below with the date and a revival target (the item it would merge into if it ever recurs).
- **Capacity** — no hard cap, but the Maintenance rule stands: an item without a golden entry (or a named lesson id, as in the v2.1.0 migration) is unverified growth and should not be added.
- **Which round counts** — a round that reached a verdict on a diff, not a question about the skill. Skill-development sessions do not increment anything.

## Where the migrated corpus went (v2.1.0 migration table)

Every entry of the sibling corpus that is now encoded here. This is the audit trail for the merge — an entry with no home below must appear as a pending candidate instead.

| Old lesson | Fate | New home |
|---|---|---|
| L-20260818-001 macro propagation vs template timing (PR #5434, re-fired 2026-09-04 on a bare `#undef ERROR`) | graduated | checklist **#51** |
| L-20260818-002 assert→throw needs every caller's error channel reviewed | graduated | checklist **#44** |
| L-20260818-003 the reviewer's causal attribution must itself be verified | graduated | checklist **#53** (the discipline block's ninth rule) |
| L-20260818-004 coroutine `task::Task` default argument dangles after `co_await` (×20 — the corpus's most frequent) | graduated | checklist **#43** |
| L-20260818-005 API name vs behaviour | graduated | checklist **#48** |
| L-20260818-007 TODO/NOTE freshness | graduated | checklist **#25** (existing) |
| L-20260819-001 verify before publishing: a subagent's output is not a fact (a false CRITICAL was published on #5438) | graduated | SKILL.md step 8 (aggregation gate) |
| L-20260820-002 header-only/INTERFACE library needs a TU that includes all new main headers | graduated | checklist **#50** |
| L-20260826-001 fail-closed flip leaves sibling default sites in the same TU | graduated | checklist **#18** (existing) + #44 |
| L-20260826-002 one entry wired ≠ the rule unified | graduated | checklist **#21** (existing) + M10 |
| L-20260826-003 close-out checked a different site than the one named | graduated | checklist **#25** (existing) + respond's self-check |
| L-20260826-004 leading zeros are a mandatory canonical cell | graduated | **M8** |
| L-20260826-005 one sentinel, two meanings | graduated | checklist **#12** (existing) |
| L-20260826-006 exception type is not a unique pin | graduated | **M11** + checklist **#52** |
| L-20260827-001 clang-format whitelist; clean configure after a build-system edit; judge by exit code (PR #5549) | graduated | **M13** |
| L-20260827-002 RLP walker cursor: `decodeHeader` crops the head byte for string heads, not for sub-0x80 inline items (PR #5496-r5) | graduated | checklist **#41** |
| L-20260904-001 gate-vs-producer divergence behind two self-consistent gates (PR #5544 r6 CRITICAL) | graduated | checklist **#42** + M10 |
| L-20260904-003 wire round-trip / cross-site predicate / minimal-target ownership / equivalence-test smell (PR #5547 F2/F5/F7/F8) | graduated | #10, #12, #21, #38 (existing) |
| L-20260904-004 reentry and duplicate-submission findings floor at the high tier (PR #5547 replay F1) | graduated | SKILL.md severity semantics + checklist **#45** |

## Pending candidates

### L-20260818-006 — `if constexpr` and `requires` coexist: enumerate the full truth table (pending, ×0, tombstoned once)
A missed pairing silently selects the wrong branch: an arity check under `if constexpr` combined with a `requires`-constrained overload has to be enumerated as a matrix, not reasoned about pairwise. **Incident:** PR #5434 morebtcg F5 + kyonRay r2 (`SchedulerSerialImpl.h`). **Fate:** expired once at zero triggers; listed here rather than tombstoned because its revival target is an existing item. **Would encode as:** an extension of checklist **#49** (version/constraint gates) — merge in if it recurs, do not open a new number.

### L-20260904-002 — inheritance granularity is function-level, not file-level (pending, ×1)
Inheriting a prior round's conclusion for a *file* is too coarse: the prior round must have named the target function, and the PR-body classification ("pure extraction, no cutover") must be reconciled against the diff before scoping. **Incident:** PR #5547 — `Impl.h` inherited #5544's conclusions on a 1+1-line delta while #5544 had never read the legacy submission semantics; the "no cutover" claim hid four behaviour changes. **Status:** the second half is already encoded (discipline #1 claim honesty, and the per-head re-review design makes the first half unreachable — this skill re-reviews at each head rather than inheriting). **Would encode as:** a rule in step 1 if cross-PR conclusion inheritance is ever introduced.

## Tombstones (expired)

- **L-20260818-006** — expired at zero triggers (2026-09-04 in the source corpus); revival target checklist #49. Kept live above as a candidate because the target item exists here.
