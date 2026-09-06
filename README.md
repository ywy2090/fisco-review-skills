# FISCO-BCOS Review Skills

Two agent skills for the FISCO-BCOS C++ PR workflow, versioned as a pair (current: **v1.20.1**).

| Skill | Purpose |
|---|---|
| [`fisco-review`](.agents/skills/fisco-review/) | Review a FISCO-BCOS PR/branch (engine, executor, consensus, RPC, initializer) as the reviewer. Produces BLOCKER/HIGH/MEDIUM/LOW findings in the repo's severity-scored, round-based format. |
| [`fisco-respond`](.agents/skills/fisco-respond/) | Process review findings on your own PR: triage each finding, fix with a regression test, and reply per thread in the `Fixed in <sha>: ...` / `Leaving X: ... because ...` format. |

## Install

Works with any Agent Skills-compatible host (Claude Code, OpenCode, Codex, Cursor, 60+ others):

```bash
npx skills add ywy2090/fisco-review
```

Or clone and copy the skill you need:

```bash
git clone https://github.com/ywy2090/fisco-review.git
cp -r fisco-review/.agents/skills/fisco-review  ~/.claude/skills/
cp -r fisco-review/.agents/skills/fisco-respond ~/.claude/skills/
```

## Layout

```
.agents/skills/
├── fisco-review/
│   ├── SKILL.md            # workflow, modes (delta/full), report format
│   ├── CHANGELOG.md
│   ├── references/         # checklist.md, golden-set.md
│   └── scripts/            # fetch_pr.py, lock.sh, verify_tree.sh
└── fisco-respond/
    ├── SKILL.md
    ├── CHANGELOG.md
    └── references/         # self-check.md
```

## Versioning

Both skills bump their `version:` fields in lockstep. Semver: MAJOR = finding taxonomy / report format change; MINOR = additive checklist items; PATCH = wording. See each skill's `CHANGELOG.md`.
