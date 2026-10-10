#!/usr/bin/env bash
# Freeze a skill out of the load roots: move its canonical directory into the
# backup area and remove the symlinks the other roots hold to it.
#
#   tools/freeze-skill.sh <name> [<name>...]            # dry run (default)
#   tools/freeze-skill.sh --apply <name> [<name>...]    # perform it
#
# Safety, because this is the one operation that removes something from a load
# root: it refuses to freeze a skill whose content exists *only* in a load root,
# and it refuses when a root holds a real directory that differs from canonical.
# Unlike the aligner it does not care about "older subset": freezing says the
# skill is retired, so every copy is going away — the point of the check is only
# that nothing unique is lost, and that nothing else is silently left behind.
#
# Everything moved is kept: the directory lands in
# $BACKUP_ROOT/frozen-<date>/<name>, and the tool prints the restore command.

set -uo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CANONICAL=${CANONICAL:-$HOME/.agents/skills}
BACKUP_ROOT=${BACKUP_ROOT:-$HOME/.skill-backups}
ROOTS_FILE=${SKILL_ROOTS:-$REPO_ROOT/tools/skill-roots.txt}

APPLY=0
FORCE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --apply) APPLY=1; shift ;;
        --force) FORCE=1; shift ;;
        -*) echo "unknown option: $1" >&2; exit 2 ;;
        *) break ;;
    esac
done
[ $# -ge 1 ] || { echo "usage: $(basename "$0") [--apply] [--force] <skill-name>..." >&2; exit 2; }

STAMP=$(date +%Y%m%d)
BACKUP_DIR="$BACKUP_ROOT/frozen-$STAMP"

realpath_of() { (cd "$1" 2>/dev/null && pwd -P) ; }
hash_tree() {
    local dir=$1 tool
    tool=$(command -v shasum || command -v sha256sum) || return 1
    ( cd "$dir" || return 1
      find . -type f ! -name '*.pyc' ! -path '*__pycache__*' ! -name '.DS_Store' -print0 \
        | LC_ALL=C sort -z \
        | while IFS= read -r -d '' f; do printf '%s\n' "$f"; "$tool" "$f" 2>/dev/null | awk '{print $1}'; done
    ) | "$tool" 2>/dev/null | awk '{print substr($1,1,12)}'
}
roots=()
while IFS= read -r rel; do
    case "$rel" in ''|'#'*) continue ;; esac
    [ -d "$HOME/$rel" ] && roots+=("$rel")
done < "$ROOTS_FILE"

[ "$APPLY" -eq 1 ] && printf 'APPLYING (backups -> %s)\n\n' "$BACKUP_DIR" || printf 'DRY RUN (re-run with --apply to perform)\n\n'

refused=0
for name in "$@"; do
    canon="$CANONICAL/$name"
    canon_real=$(realpath_of "$canon")
    if [ -d "$REPO_ROOT/.agents/skills/$name" ] && [ "$FORCE" -eq 0 ]; then
        printf '%-26s REFUSE (this repo publishes it — freezing removes what you ship; --force to override)\n' "$name"
        refused=1; continue
    fi
    if [ ! -d "$canon" ]; then
        printf '%-26s REFUSE (no canonical directory at %s)\n' "$name" "$canon"
        refused=1; continue
    fi

    plan=(); problem=""
    for rel in "${roots[@]}"; do
        [ "$(realpath_of "$HOME/$rel")" = "$(realpath_of "$CANONICAL")" ] && continue
        p="$HOME/$rel/$name"
        [ -e "$p" ] || [ -L "$p" ] || continue
        if [ -L "$p" ]; then
            tgt=$(realpath_of "$p")
            # resolve through one more hop for links that point at links
            if [ "$tgt" = "$canon_real" ]; then
                plan+=("link  $rel")
            else
                problem="$problem $rel(link->$tgt)"
            fi
        else
            if [ "$(hash_tree "$p")" = "$(hash_tree "$canon")" ]; then
                plan+=("copy  $rel")
            else
                problem="$problem $rel(real dir differs)"
            fi
        fi
    done

    if [ -n "$problem" ]; then
        printf '%-26s REFUSE (content elsewhere is not accounted for:%s)\n' "$name" "$problem"
        refused=1; continue
    fi

    printf '%-26s %d root entr%s to clean, canonical %s\n' \
           "$name" "${#plan[@]}" "$([ "${#plan[@]}" -eq 1 ] && echo y || echo ies)" "$canon"
    for entry in "${plan[@]}"; do printf '    %s\n' "$entry"; done

    if [ "$APPLY" -eq 1 ]; then
        mkdir -p "$BACKUP_DIR"
        mv "$canon" "$BACKUP_DIR/$name" || { echo "  move failed" >&2; refused=1; continue; }
        for rel in "${roots[@]}"; do
            p="$HOME/$rel/$name"
            [ -L "$p" ] && rm -f "$p"
        done
        # identical real copies, if any, also move into the backup
        for rel in "${roots[@]}"; do
            p="$HOME/$rel/$name"
            if [ -d "$p" ] && [ ! -L "$p" ] && [ "$(realpath_of "$p")" != "$canon_real" ]; then
                mkdir -p "$BACKUP_DIR/${rel//\//_}" && mv "$p" "$BACKUP_DIR/${rel//\//_}/$name"
            fi
        done
        printf '    -> frozen. restore: mv "%s" "%s"\n' "$BACKUP_DIR/$name" "$canon"
    fi
done

printf '\n%s\n' "$([ "$refused" -eq 0 ] && echo 'ok' || echo 'some names were refused — see above')"
exit "$refused"
