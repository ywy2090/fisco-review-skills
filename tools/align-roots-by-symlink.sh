#!/usr/bin/env bash
# Make every conventional skill root show the canonical content by replacing
# copies with relative symlinks into the install root.
#
#   tools/align-roots-by-symlink.sh            # dry run (default): print the plan
#   tools/align-roots-by-symlink.sh --apply    # perform it, moving each replaced
#                                              # directory into BACKUP_ROOT first
#
# Env: CANONICAL (default ~/.agents/skills), BACKUP_ROOT (default
#      ~/.skill-backups), SKILL_FILTER (default 'fisco*' — a glob on the
#      frontmatter name), SKILL_ROOTS (override the root list file).
#
# A copy is replaced only when it is *safe* to replace: its content is equal to
# canonical, or it is an older subset of it (no file of its own that canonical
# lacks, and not newer). A copy with unique files, or one newer than canonical,
# is reported as NEEDS REVIEW and left alone — the canonical root is the source
# of truth, but "source of truth" is not a licence to delete the only copy of
# something. Nothing is ever deleted: replaced directories are moved to
# BACKUP_ROOT (outside every skill root, so they are not loaded as skills).

set -uo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CANONICAL=${CANONICAL:-$HOME/.agents/skills}
BACKUP_ROOT=${BACKUP_ROOT:-$HOME/.skill-backups}
FILTER=${SKILL_FILTER:-fisco*}
APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1
[ -n "${1:-}" ] && [ "$1" != "--apply" ] && { echo "unknown option: $1" >&2; exit 2; }

ROOTS_FILE=${SKILL_ROOTS:-$REPO_ROOT/tools/skill-roots.txt}
STAMP=$(date +%Y%m%d)
BACKUP_DIR="$BACKUP_ROOT/linked-$STAMP"

realpath_of() { (cd "$1" 2>/dev/null && pwd -P) ; }
skill_name() { grep -m1 '^name:' "$1/SKILL.md" 2>/dev/null | sed 's/^name:[[:space:]]*//; s/[[:space:]]*$//'; }
canon_path=$(realpath_of "$CANONICAL")

# files present under $1 but not under $2 (relative paths, bytecode excluded)
unique_files() {
    (cd "$1" && find . -type f ! -name '*.pyc' ! -path '*__pycache__*' ! -name '.DS_Store' | LC_ALL=C sort) \
    | while IFS= read -r rel; do [ -e "$2/$rel" ] || printf '%s\n' "$rel"; done
}
hash_tree() {
    local dir=$1 tool
    tool=$(command -v shasum || command -v sha256sum) || return 1
    ( cd "$dir" || return 1
      find . -type f ! -name '*.pyc' ! -path '*__pycache__*' ! -name '.DS_Store' -print0 \
        | LC_ALL=C sort -z \
        | while IFS= read -r -d '' f; do printf '%s\n' "$f"; "$tool" "$f" 2>/dev/null | awk '{print $1}'; done
    ) | "$tool" 2>/dev/null | awk '{print substr($1,1,12)}'
}

[ "$APPLY" -eq 1 ] && printf 'APPLYING (backups -> %s)\n\n' "$BACKUP_DIR" || printf 'DRY RUN (re-run with --apply to perform)\n\n'

planned=0 reviewed=0
while IFS= read -r rel; do
    case "$rel" in ''|'#'*) continue ;; esac
    base="$HOME/$rel"
    [ -d "$base" ] || continue
    base_real=$(realpath_of "$base")
    [ "$base_real" = "$canon_path" ] && { printf '%-24s canonical root — never rewritten\n' "$rel"; continue; }

    for dir in "$base"/*/; do
        dir=${dir%/}
        name=$(skill_name "$dir")
        [ -n "$name" ] || continue
        # shellcheck disable=SC2254
        case "$name" in $FILTER) ;; *) continue ;; esac
        canon="$CANONICAL/$name"
        [ -d "$canon" ] || { printf '%-24s %-26s SKIP (not in canonical root)\n' "$rel" "$name"; continue; }

        depth=$(awk -F/ '{print NF}' <<<"$rel")
        ups=$(printf '../%.0s' $(seq 1 "$depth"))
        target="${ups}.agents/skills/$name"

        if [ -L "$dir" ]; then
            cur=$(readlink "$dir")
            if [ "$(realpath_of "$dir")" = "$(realpath_of "$canon")" ]; then
                printf '%-24s %-26s already a symlink to canonical\n' "$rel" "$name"
            else
                planned=$((planned+1))
                printf '%-24s %-26s RETARGET %s -> %s\n' "$rel" "$name" "$cur" "$target"
                if [ "$APPLY" -eq 1 ]; then
                    mkdst="$BACKUP_DIR/${rel//\//_}"
                    mkdir -p "$mkdst" && printf '%s\n' "$cur" > "$mkdst/$name.symlink-target"
                    rm -f "$dir" && ln -s "$target" "$dir"
                fi
            fi
            continue
        fi

        if [ "$(hash_tree "$dir")" = "$(hash_tree "$canon")" ]; then
            planned=$((planned+1))
            printf '%-24s %-26s LINK (identical)\n' "$rel" "$name"
        else
            uniq=$(unique_files "$dir" "$canon" | head -5)
            if [ -n "$uniq" ]; then
                reviewed=$((reviewed+1))
                printf '%-24s %-26s NEEDS REVIEW (has files canonical lacks: %s)\n' \
                       "$rel" "$name" "$(printf '%s' "$uniq" | tr '\n' ' ')"
                continue
            fi
            if [ "$dir/SKILL.md" -nt "$canon/SKILL.md" ]; then
                reviewed=$((reviewed+1))
                printf '%-24s %-26s NEEDS REVIEW (newer than canonical)\n' "$rel" "$name"
                continue
            fi
            planned=$((planned+1))
            printf '%-24s %-26s LINK (older subset)\n' "$rel" "$name"
        fi

        if [ "$APPLY" -eq 1 ]; then
            mkdst="$BACKUP_DIR/${rel//\//_}"
            mkdir -p "$mkdst"
            mv "$dir" "$mkdst/$name" && ln -s "$target" "$dir"
        fi
    done
done < "$ROOTS_FILE"

printf '\n%s%d to change, %d needing review\n' "$([ "$APPLY" -eq 1 ] && echo 'done: ' || echo 'plan: ')" "$planned" "$reviewed"
[ "$reviewed" -eq 0 ] || printf 'reviewed items were left untouched.\n'
