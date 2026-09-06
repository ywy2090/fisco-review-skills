# Golden regression set

A "golden set" is a list of **known-missed findings with ground truth** — a finding an earlier version of this skill failed to report at a specific head, discovered independently by the external reviewer (kyonRay). Each entry is a retrievable test: when the skill is changed, the change must name the golden entry it makes the skill hit (Maintenance rule in SKILL.md). A checklist item added without a golden entry (or a concrete finding) is unverified growth.

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

1. **When changing the skill** (new checklist item, delegation rule, mode): state which golden entry it makes the skill hit. If none, it is unverified growth and should not be added without a fresh, named finding.
2. **When the skill next reviews a PR**: after the report, check whether any golden signal was present in the diff and whether the skill hit it. A golden signal present but unhit is a regression regardless of what else the report says.
3. **Cost discipline**: the golden set is the reason the delegation budget is now a hard cap and cross-file symmetry moved to the aggregator — G1/G5 are cross-file, and the parallel round that missed them also ran 2.4–5.6M tokens per agent. Recall and cost are tracked together.
