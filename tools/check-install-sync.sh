#!/usr/bin/env bash
# Author-side consistency check: does every skill published in this repo match
# the copies installed on this machine?
#
#   tools/check-install-sync.sh [--quiet] [--all-roots]
#
# Exit 0 = in sync, 1 = drift (details on stdout).
#
#   --quiet      suppress the per-file diff listing and the rsync hints
#   --all-roots  additionally sweep the conventional skill roots under the home
#                directory and report, per published skill, every copy found by
#                frontmatter name — including copies in roots this machine does
#                not load. Drift found there counts toward the exit status,
#                because "the copies disagree" is the condition being watched;
#                the pre-push gate deliberately runs without this flag so that
#                publishing is gated only on the installed copy.
#
# SKILL_SYNC_INSTALLED overrides the installed root (default ~/.agents/skills);
# SKILL_ROOTS overrides the colon-separated sweep list.
#
# Design notes, from four real failures on 2026-10-10:
#  - stderr is never discarded: a `diff` that errors must not read as "no
#    differences" (a suppressed error once reported "0 files differ" for 11).
#  - every line prints the file counts it compared, so a green result is
#    auditable rather than a bare "OK".
#  - bytecode and OS droppings are excluded on both sides, and the repo side is
#    additionally checked for tracked artifacts that should never be published.
#  - a skill's identity is its frontmatter `name:`, never its directory name:
#    a copy can sit under a differently named directory.

set -uo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALLED_ROOT=${SKILL_SYNC_INSTALLED:-$HOME/.agents/skills}
QUIET=0
ALL_ROOTS=0
for arg in "$@"; do
    case "$arg" in
        --quiet)     QUIET=1 ;;
        --all-roots) ALL_ROOTS=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

# The root list lives in tools/skill-roots.txt so this script and
# tools/align-roots-by-symlink.sh cannot drift apart. SKILL_ROOTS overrides it;
# the inline list is only a fallback for a tree without the file.
FALLBACK_ROOTS=".agents/skills:.claude/skills:.codex/skills:.cursor/skills:\
.config/opencode/skills:.hermes/skills:.workbuddy/skills:.cc-switch/skills:.codebuddy/skills"
if [ -n "${SKILL_ROOTS:-}" ]; then
    ROOTS=$SKILL_ROOTS
elif [ -f "$REPO_ROOT/tools/skill-roots.txt" ]; then
    ROOTS=$(grep -v '^[[:space:]]*#' "$REPO_ROOT/tools/skill-roots.txt" \
            | grep -v '^[[:space:]]*$' | paste -sd: -)
else
    ROOTS=$FALLBACK_ROOTS
fi

count_files() {
    find "$1" -type f \
        ! -name '*.pyc' ! -path '*__pycache__*' ! -name '.DS_Store' \
        | wc -l | tr -d ' '
}

# Content hash of a skill tree, name-and-content, order-independent of mtimes.
tree_hash() {
    local dir=$1 tool
    tool=$(command -v shasum || command -v sha256sum) || return 1
    (
        cd "$dir" || return 1
        find . -type f ! -name '*.pyc' ! -path '*__pycache__*' ! -name '.DS_Store' \
            -print0 | LC_ALL=C sort -z \
        | while IFS= read -r -d '' f; do
            printf '%s\n' "$f"
            "$tool" "$f" 2>/dev/null | awk '{print $1}'
        done
    ) | "$tool" 2>/dev/null | awk '{print substr($1,1,12)}'
}

skill_name() {
    grep -m1 '^name:' "$1/SKILL.md" 2>/dev/null \
        | sed 's/^name:[[:space:]]*//; s/[[:space:]]*$//'
}

status=0
printf 'installed root: %s\n' "$INSTALLED_ROOT"

published=()
for skill_path in "$REPO_ROOT"/.agents/skills/*/; do
    name=$(basename "$skill_path")
    [ -f "$skill_path/SKILL.md" ] || continue
    published+=("$skill_path")
    live="$INSTALLED_ROOT/$name"

    if [ ! -d "$live" ]; then
        printf 'MISSING  %-24s not installed under %s\n' "$name" "$INSTALLED_ROOT"
        status=1
        continue
    fi

    n_repo=$(count_files "$skill_path")
    n_live=$(count_files "$live")
    diff_out=$(diff -rq --exclude='__pycache__' --exclude='*.pyc' \
                   --exclude='.DS_Store' "$live" "$skill_path" 2>&1)
    diff_rc=$?

    if [ -z "$diff_out" ] && [ "$diff_rc" -eq 0 ]; then
        printf 'OK       %-24s identical (installed %s / repo %s files)\n' \
               "$name" "$n_live" "$n_repo"
    else
        status=1
        printf 'DRIFT    %-24s installed %s / repo %s files (diff exit %s)\n' \
               "$name" "$n_live" "$n_repo" "$diff_rc"
        if [ "$QUIET" -eq 0 ]; then
            printf '%s\n' "$diff_out" | sed 's/^/           /'
            printf '           sync installed -> repo:\n'
            printf '             rsync -a --exclude __pycache__ --exclude .DS_Store "%s/" "%s"\n' \
                   "$live" "$skill_path"
        fi
    fi
done

if [ "$ALL_ROOTS" -eq 1 ]; then
    printf '\nsweep of the conventional roots (SKILL_ROOTS overrides; %s entries)\n' \
           "$(printf '%s' "$ROOTS" | tr ':' '\n' | wc -l | tr -d ' ')"
    IFS=':' read -r -a root_list <<<"$ROOTS"
    for skill_path in "${published[@]}"; do
        skill=$(skill_name "$skill_path")
        ref_hash=$(tree_hash "$skill_path")
        printf '  %s  (repo hash %s)\n' "$skill" "$ref_hash"
        seen=0
        for rel in "${root_list[@]}"; do
            base="$HOME/$rel"
            [ -d "$base" ] || continue
            root_note=""
            [ -L "$base" ] && root_note=" [root is a symlink -> $(readlink "$base")]"
            # Globs, not `find`: find does not descend symlinked directories, so a
            # root that is a symlink (or a skill dir that is one) would be skipped
            # silently — a miss that reads as "no other copy exists".
            for dir in "$base"/*/; do
                dir=${dir%/}
                [ -f "$dir/SKILL.md" ] || continue
                [ "$(skill_name "$dir")" = "$skill" ] || continue
                seen=$((seen + 1))
                h=$(tree_hash "$dir")
                if [ "$h" = "$ref_hash" ]; then mark='same   '; else mark='DIFFERS'; status=1; fi
                kind="copy"
                [ -L "$dir" ] && kind="symlink -> $(readlink "$dir")"
                printf '    %s  v%-8s  %-22s %s%s\n' "$mark" \
                       "$(grep -m1 '^version:' "$dir/SKILL.md" 2>/dev/null \
                          | sed 's/^version:[[:space:]]*//; s/[[:space:]]*$//')" \
                       "$rel" "$kind" "$root_note"
            done
        done
        [ "$seen" -eq 0 ] && printf '    (no other root holds a copy)\n'
    done

    # A backup-looking directory inside a root is loaded as a skill whenever it
    # carries a SKILL.md — the skill's identity is its frontmatter name, not its
    # directory name, so `foo.bak-20260101/` becomes a second `foo`. This has
    # bitten twice on this machine; the scan is cheap and belongs with the sweep
    # rather than in the pre-push gate (another host's stray backup must not
    # block a skills-repo push).
    printf '\nbackup-looking directories inside the roots\n'
    for rel in "${root_list[@]}"; do
        base="$HOME/$rel"
        [ -d "$base" ] || continue
        for entry in "$base"/*/; do
            entry=${entry%/}
            name=$(basename "$entry")
            case "$name" in
                *.bak*|*.old|*.orig|*_bak|*.disabled|*backup*|*Backup*|*copy) ;;
                *) continue ;;
            esac
            if [ -f "$entry/SKILL.md" ]; then
                printf '  LOADED AS DUPLICATE  %s/%s  name=%s\n' \
                       "$rel" "$name" "$(skill_name "$entry")"
                status=1
            else
                printf '  inert (no SKILL.md)  %s/%s\n' "$rel" "$name"
            fi
        done
    done
fi

# Published trees must carry no bytecode or OS droppings, even untracked ones.
stray=$(find "$REPO_ROOT/.agents/skills" -type f \( -name '*.pyc' -o -name '.DS_Store' \) 2>/dev/null | wc -l | tr -d ' ')
tracked=$(git -C "$REPO_ROOT" ls-files | grep -cE '__pycache__|\.pyc$' || true)
if [ "$stray" -ne 0 ] || [ "$tracked" -ne 0 ]; then
    status=1
    printf 'HYGIENE  repo tree has %s stray file(s), %s tracked bytecode path(s)\n' "$stray" "$tracked"
fi

[ "$status" -eq 0 ] && [ "$QUIET" -eq 0 ] && printf '\nin sync.\n'
exit $status
