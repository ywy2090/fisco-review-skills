#!/usr/bin/env bash
# Author-side consistency check: does every skill published in this repo match
# the copy installed on this machine?
#
#   tools/check-install-sync.sh [--quiet]
#
# Exit 0 = in sync, 1 = drift (details on stdout). The installed root defaults
# to ~/.agents/skills and can be overridden with SKILL_SYNC_INSTALLED (the
# pre-push hook and the tests use that).
#
# Design notes, from three real failures on 2026-10-10:
#  - stderr is never discarded: a `diff` that errors must not read as "no
#    differences" (a suppressed error once reported "0 files differ" for 11).
#  - every line prints the file counts it compared, so a green result is
#    auditable rather than a bare "OK".
#  - bytecode and OS droppings are excluded on both sides, and the repo side is
#    additionally checked for tracked artifacts that should never be published.

set -uo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALLED_ROOT=${SKILL_SYNC_INSTALLED:-$HOME/.agents/skills}
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

count_files() {
    find "$1" -type f \
        ! -name '*.pyc' ! -path '*__pycache__*' ! -name '.DS_Store' \
        | wc -l | tr -d ' '
}

status=0
printf 'installed root: %s\n' "$INSTALLED_ROOT"

for skill_path in "$REPO_ROOT"/.agents/skills/*/; do
    name=$(basename "$skill_path")
    [ -f "$skill_path/SKILL.md" ] || continue
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
        continue
    fi

    status=1
    printf 'DRIFT    %-24s installed %s / repo %s files (diff exit %s)\n' \
           "$name" "$n_live" "$n_repo" "$diff_rc"
    if [ "$QUIET" -eq 0 ]; then
        printf '%s\n' "$diff_out" | sed 's/^/           /'
        printf '           sync installed -> repo:\n'
        printf '             rsync -a --exclude __pycache__ --exclude .DS_Store "%s/" "%s"\n' \
               "$live" "$skill_path"
    fi
done

# Published trees must carry no bytecode or OS droppings, even untracked ones.
stray=$(find "$REPO_ROOT/.agents/skills" -type f \( -name '*.pyc' -o -name '.DS_Store' \) 2>/dev/null | wc -l | tr -d ' ')
tracked=$(git -C "$REPO_ROOT" ls-files | grep -cE '__pycache__|\.pyc$' || true)
if [ "$stray" -ne 0 ] || [ "$tracked" -ne 0 ]; then
    status=1
    printf 'HYGIENE  repo tree has %s stray file(s), %s tracked bytecode path(s)\n' "$stray" "$tracked"
fi

[ "$status" -eq 0 ] && [ "$QUIET" -eq 0 ] && printf '\nin sync.\n'
exit $status
