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

## Maintaining this repo (author side)

Skills are edited in the installed copy (`~/.agents/skills/<skill>/` — that is what an agent
loads) and published from this repo. The two are independent copies, so drift is the default
state unless something checks it:

```bash
tools/check-install-sync.sh       # OK / DRIFT / MISSING per skill; exit 1 on drift
tools/check-install-sync.sh --all-roots   # + where else each skill is installed, and whether it agrees
SKILL_SYNC_OVERRIDE=1 git push    # deliberate bypass; the hook prints that it skipped
```

`--all-roots` sweeps the conventional skill roots under the home directory and, per published
skill, lists every copy found **by frontmatter name** (never by directory name) with one of
`same` / `DIFFERS`, whether it is a `copy` or a `symlink -> target`, and whether the root itself
is a symlink. The classification matters: a root that symlinks to another root cannot drift, and
a skill directory that symlinks into the install root is the same content, not a second copy.
Drift found by the sweep counts toward the exit status; the pre-push gate runs without the flag,
so publishing is gated only on the installed copy.

**Wiring the gate.** Hooks run from wherever `git config core.hooksPath` points — a central
hooks directory (a common setup) makes `.git/hooks/` inert, so install the gate where git
actually looks, and insert it *before* that hook's final `exit 0`, since anything appended
after an unconditional exit never runs:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT=""
if [ -n "$REPO_ROOT" ] && [ -x "$REPO_ROOT/tools/check-install-sync.sh" ]; then
  "$REPO_ROOT/tools/pre-push-hook.sh" >&2 || exit 1
fi
```

The block is inert in every repo that does not ship the checker. Keep the bypass decision
inside `tools/pre-push-hook.sh` (as above) rather than duplicating it in the caller — a
caller-level bypass passes silently, and a silent bypass is the thing this gate exists to
prevent.

The checker prints the file counts it compared and a ready `rsync` command for each drifted
skill. It never discards a tool's stderr — a `diff` that fails must not read as "0 files
differ" (a suppressed error once reported exactly that for 11 changed files) — and it flags
bytecode / `.DS_Store` at either end, since a published tree should carry neither.

Four rules keep this honest:

1. **One working copy per change.** Edit the installed skill and sync outward, or edit here and
   copy inward — not both. The checker can tell that two trees differ; it cannot tell which one
   is newer.
2. **`git fetch` before every push.** A stale `origin/main` rejects the push at best; a
   force-push around it deletes whatever landed meanwhile. Nothing in this repo needs a
   force-push.
3. **A rebase rewrites the commit ids.** When one becomes necessary, cite the skill's version
   and content in notes and CHANGELOGs, never a sha that the rebase is about to invalidate.
4. **After a sync, run the tests — not only the checker.** Byte-identical files can still ship a
   broken suite: `python3 .agents/skills/fisco-verify-findings/scripts/test_validate_verification.py`

**Aligning the roots.** When a root holds a *copy* instead of a link, `tools/align-roots-by-symlink.sh`
replaces it with a relative symlink into the install root — dry run by default, `--apply` to
perform, and every replaced directory is **moved** to `~/.skill-backups/linked-<date>/` (outside
every skill root, so the backups are not loaded as skills). It refuses to touch a copy that has
files the canonical root lacks, or that is newer than it, and reports those as NEEDS REVIEW: the
canonical root is the source of truth, but that is not a licence to delete the only copy of
something. Both scripts read the same `tools/skill-roots.txt`, so they cannot disagree about which
roots exist.

**Freezing.** `tools/freeze-skill.sh [--apply] [--force] <name>...` retires a skill: it verifies
that every other root reaches it by symlink (or holds a content-identical copy), moves the
canonical directory to `~/.skill-backups/frozen-<date>/`, removes those root entries, and prints
the restore command. It refuses to freeze a skill this repo publishes unless `--force`, because
freezing a published skill removes what you ship — a mistake worth a hard gate rather than a
convention.

## Independence

`fisco-verify-findings` works standalone: its reproduction recipes use plain `git` and the repo's own
CMake/ctest targets, and its validator needs only Python 3.8+. When `fisco-review-shared` (per-PR
artifact directory + lock) is installed beside it, it reuses that directory so the verification
artifact lands next to the review artifacts it belongs to; without it, it falls back to its own
restricted directory under `$TMPDIR`.
