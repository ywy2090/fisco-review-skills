# FISCO-BCOS Review Skills

Three agent skills for the FISCO-BCOS C++ PR workflow. `fisco-review` and `fisco-respond` are a
versioned pair (current: **v2.0.0**); `fisco-verify-findings` is versioned independently
(current: **v1.1.0**).

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
│   ├── references/         # checklist.md, golden-set.md
│   └── scripts/            # fetch_pr.py, lock.sh, verify_tree.sh
├── fisco-respond/
│   ├── SKILL.md
│   ├── CHANGELOG.md
│   └── references/         # self-check.md
└── fisco-verify-findings/
    ├── SKILL.md
    ├── CHANGELOG.md
    ├── evals/
    ├── references/         # intake, method, repro-recipes, report, worked example
    └── scripts/            # validate_verification.py (+59 unit tests), verify_env.sh
```

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
