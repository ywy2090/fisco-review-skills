# FISCO-BCOS Review Skills

Three agent skills for the FISCO-BCOS C++ PR workflow. `fisco-review` and `fisco-respond` are a
versioned pair (current: **v2.1.0**); `fisco-verify-findings` is versioned independently
(current: **v1.2.0**).

| Skill | Purpose |
|---|---|
| [`fisco-review`](.agents/skills/fisco-review/) | Review a FISCO-BCOS PR/branch (engine, executor, consensus, RPC, initializer) as the reviewer. Produces BLOCKER/HIGH/MEDIUM/LOW findings in the repo's severity-scored, round-based format. |
| [`fisco-respond`](.agents/skills/fisco-respond/) | Process review findings on your own PR: triage each finding, fix with a regression test, reply on each thread in one sentence (`Fixed in <sha> — ...` / `Not changed — ...`), and post a round summary reply carrying the evidence. |
| [`fisco-verify-findings`](.agents/skills/fisco-verify-findings/) | Decide whether a review finding **actually exists** before you act on it: evidence read at one frozen revision, a re-runnable reproduction, and a verdict (`confirmed` / `confirmed_symptom_mechanism_differs` / `refuted` / `stale` / `unreproducible` / `undecidable`). Runs before `fisco-respond`: verify first, then triage, fix and reply. |

## Install

Works with any Agent Skills-compatible host (Claude Code, OpenCode, Codex, Cursor, 60+ others):

```bash
npx skills add ywy2090/fisco-review
```

Or clone and copy the skill you need:

```bash
git clone https://github.com/ywy2090/fisco-review.git
cp -r fisco-review/.agents/skills/fisco-review         ~/.claude/skills/
cp -r fisco-review/.agents/skills/fisco-respond        ~/.claude/skills/
cp -r fisco-review/.agents/skills/fisco-verify-findings ~/.claude/skills/
```

## Layout

```
.agents/skills/
├── fisco-review/
│   ├── SKILL.md            # workflow, modes (delta/full), report format
│   ├── CHANGELOG.md
│   ├── references/
│   │   ├── checklist.md    # conventions, 53 numbered rules (discipline + defect classes)
│   │   ├── golden-set.md   # graduated misses with ground truth
│   │   ├── lessons-pending.md  # intake tier: candidates, lifecycle, migration table
│   │   └── methods.md      # executable procedures + mutation isolation contract
│   └── scripts/            # fetch_pr.py, lock.sh, verify_tree.sh
├── fisco-respond/
│   ├── SKILL.md            # triage → fix → reply, the Fixed evidence gate
│   ├── CHANGELOG.md
│   └── references/         # self-check.md
└── fisco-verify-findings/
    ├── SKILL.md
    ├── CHANGELOG.md
    ├── evals/
    ├── references/         # intake, method, repro-recipes, report, worked example
    └── scripts/            # validate_verification.py (+70 unit tests), verify_env.sh
```

## Provenance

v2.1.0 merges the predecessor corpus — `fisco-review-pr` 2.13.x, `fisco-handle-reviews`
1.10.x and the shared `checks.md` / `methods.md` bundle — into the `fisco-review` /
`fisco-respond` pair. The migrated material is inventoried in
`fisco-review/references/lessons-pending.md` (one row per source lesson, naming the
checklist item, method or discipline rule it became), so the merge is auditable rather
than assumed. The predecessor corpus is dormant: this pair is the maintained one.

## Versioning

`fisco-review` and `fisco-respond` bump their `version:` fields in lockstep. Semver: MAJOR = finding
taxonomy / report format change; MINOR = additive checklist items; PATCH = wording.
`fisco-verify-findings` is independent: MAJOR = verdict semantics or evidence gates change;
MINOR = new verdict, gate or reproduction recipe. See each skill's `CHANGELOG.md`.

## Independence

`fisco-verify-findings` works standalone: its reproduction recipes use plain `git` and the repo's own
CMake/ctest targets, and its validator needs only Python 3.8+. When `fisco-review-shared` (per-PR
artifact directory + lock) is installed beside it, it reuses that directory so the verification
artifact lands next to the review artifacts it belongs to; without it, it falls back to its own
restricted directory under `$TMPDIR`.
