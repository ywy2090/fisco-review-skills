# Golden regression set

A "golden set" is a list of **known-missed findings with ground truth** — a finding an earlier version of this skill failed to report at a specific head, discovered independently by the external reviewer (kyonRay). Each entry is a retrievable test: when the skill is changed, the change must name the golden entry it makes the skill hit (Maintenance rule in SKILL.md). A checklist item added without a golden entry (or a concrete finding) is unverified growth.

This is the **graduated** tier. The intake tier — candidates with a trigger count that have not earned an item yet, plus the migration table for the corpus merged in v2.1.0 — is [lessons-pending.md](lessons-pending.md): a rule lives there until it can name ground truth here.

The canonical source is the #5549 post-mortem: two independent reviews of head `ffedf65203a31` — kyonRay's single-pass review vs this skill's parallel-subagent full round. kyonRay filed 10 findings; this skill filed 9, shared 2, and **missed 8**. Those 8 are the golden set. Each entry: what was missed, the checklist rule it now maps to, and the signal that should trigger it.

## Golden entries (the 8 missed #5549 findings)

| # | Missed finding (kyonRay) | Severity | Now maps to | Trigger signal |
|---|---|---|---|---|
| G1 | `rebuildOpEthHeader` drops `setEthBlockVersion` that its sibling `finalizeEthBlockHeader` performs | HIGH | #33 sibling-helper step-set parity | a new function is the same-domain sibling of an existing helper in a *different file* |
| G2 | shared `m_delegate` scheduler driven through reset/executeBlock/commitBlock with no serialization while the class documents concurrent RPC calls | HIGH | #34 concurrency contract → shared-state inventory | a class has one mutex for one member and a *second* shared object driven unserialized |
| G3 | `bindEnvelopeAccessList`/`bindEnvelopeBlobHashes` memcpy 20/32 bytes after checking RLP length equals the width but not that it fits the buffer | MEDIUM | #35 intra-function defensive-pattern symmetry | same primitive at N sites, some bound-checked and some not |
| G4 | newly public `OpEngineService.h`→`.inl`→`<bcos-rlp-protocol/EthBlockHeader.h>` with rlp-protocol PRIVATE on engine | MEDIUM | #36 public-header → include → link-visibility → install | a public header (or its `.inl`) includes a PRIVATE-linked dependency |
| G5 | empty-ommers / zero-nonce / empty-requests literals duplicated between `OpEngineService.cpp` and `finalizeEthBlockHeader` | MEDIUM | #37 value-level duplication of consensus literals | same 32-byte consensus literal under two names across files |
| G6 | payload id derived from raw method version while the cache stores the shape version | LOW | #39 two-notions-of-one-semantic | one semantic value used under two notions in one build |
| G7 | parity suite derives its expected blockHash from the same `rebuildOpEthHeader`+`computeHash` under test, and the only external oracle (t8n corpus) is gitignored/unprovisioned | HIGH (as F1+F2) | #38 self-referential oracle detection | a "golden"/"parity" test whose expectation comes from the code under test |
| G8 | PROVENANCE.md "## SHA256" heading sits above an unrelated divergence matrix; the sums are 240 lines away | LOW | #25 dead code / stale comments (document form) | a doc's heading points at content that isn't there |

## Non-golden findings this skill caught that kyonRay did not (do not over-fit)

The skill is not uniformly worse — it filed 7 findings kyonRay missed at the same head: DACaps fed raw envelope bytes instead of estimated-DA (now #14-adjacent), corrupt-field parity assertions are cause-blind, `executionRequests` missing fails open vs the sibling, FCU V4 window contradicted by the caps comment, dead `m_ledger` member, `k_`-prefixed constants, capacity-fault tagging differs between lanes. These are recorded to resist the temptation to collapse the checklist back onto only kyonRay's shape — the skill has its own strengths, the goal is to close the 8 misses without losing these.

## How to use the golden set

1. **When changing the skill** (new checklist item, delegation rule, mode): state which golden entry it makes the skill hit. If none, it is unverified growth and should not be added without a fresh, named finding — a rule with an incident but no ground truth goes to [lessons-pending.md](lessons-pending.md) as a candidate instead, and graduates (gaining both an item and an entry here) only after ≥2 triggers across ≥2 PRs or ≥2 independent modules.
2. **When the skill next reviews a PR**: after the report, check whether any golden signal was present in the diff and whether the skill hit it. A golden signal present but unhit is a regression regardless of what else the report says.
3. **Cost discipline**: the golden set is the reason the delegation budget is now a hard cap and cross-file symmetry moved to the aggregator — G1/G5 are cross-file, and the parallel round that missed them also ran 2.4–5.6M tokens per agent. Recall and cost are tracked together.

## Golden entries from the #5615 multi-model runs (2026-10-12 graduated)

A second golden cohort with a different provenance: not one missed review, but **nine executor arms** (three external models × single-pass/agentic/skill-guided modes) run against the same PR #5615 head (`b561cbecb`) and scored against this skill's own 65-finding full-blind ledger as ground truth. Ground truth was produced by the native (GLM) executor running this same skill; the arms' union reached 53/65. The 12 never-found findings are the regression set — when this skill (or its executor) changes, these are the entries that must start hitting. Experiment record: `.agents/experiments/model-ab-5615/` (frozen packages sha256, per-arm outputs, mechanical evidence gate, `reports/skill-battle.md`).

| # | Never-found finding | Severity | Now maps to | Trigger signal |
|---|---|---|---|---|
| G9 | `parseOpEip1559Params` accepts >uint32 fields the loader refuses; truncation at extraData encoding | MEDIUM (F7) | #46 numeric width/parse strictness | a config parser whose acceptance is wider than the encoder's field width |
| G10 | dual-declaration check re-implements the fold rule; fold result discarded | MEDIUM (F9) | #42 gate-vs-producer reconciliation | two code paths enforcing one rule, one re-derived instead of shared |
| G11 | profile suite pins a test-local fork ladder; production selection pinned by nothing | MEDIUM (F26) | #52 pinned expectations must be discriminating | a test's fixture world stands in for the production table |
| G12 | t8n corpus readers hard-fail on plain clone, bypassing the `FISCO_REQUIRE_T8N_CORPUS` gate contract | MEDIUM (F33) | #55 declared coverage must have a consumer | a corpus gate whose failure mode differs between CI and clean clone |
| G13 | two genesis-state-root implementations cross-pinned on a single one-account vector | MEDIUM (F34) | #21/#42 duplicate implementations + fixture strength | two impls of one job "verified" against one shared trivial vector |
| G14 | 3 of 4 new Python suites have no CI runner | MEDIUM (F37) | #55 | a suite that exists, passes locally, and is run by nothing |
| G15 | run.sh leaves the variant applied on two failure paths ("restore on ANY exit" claim false) | MEDIUM (F39) | #45 residual state on early exit | a cleanup claim covering paths the script does not actually take |
| G16 | mutant binaries stay built after the source restore | MEDIUM (F40) | #45 | restore semantics checked on sources only, not on built artifacts |
| G17 | oracle JSON claims a judging test that does not exist | MEDIUM (F31) | #55 | an artifact that names its consumer without the consumer existing |
| G18 | vacuous self-comparing assertion (hash of X vs hash of X) | LOW (F53) | #38 self-referential oracle | both sides of an equality derived from the same expression |
| G19 | withdrawals-root expectations derived from the same helper the seal uses | LOW (F59) | #38 | expectation helper == production helper |
| G20 | optional-field matrix omits the computed-only cell it claims complete | LOW (F60) | #40 wire-shape matrix | a matrix that enumerates input cells but not derived-only cells |

Plus two **process** goldens that measure the executor, not the checklist — both failed by at least one arm and both now fenced by step 8's v2.2.0 rules: a unit-level BLOCKER surviving into the final report (hard-target reconciliation), and a severity change citing no clause (severity-change citation). The attribution probe (dependency-drift CI red mis-filed as diff defect by all arms) graduates as checklist #54.
