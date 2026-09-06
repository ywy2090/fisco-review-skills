#!/usr/bin/env bash
# Hash-verify a materialized review tree against head blobs.
# Usage: verify_tree.sh <head-ref> <tree-dir>
# Prints one line per mismatch/missing file and exits 1 if any; prints
# "OK: <n> files match <head-ref>" otherwise.
set -euo pipefail

head_ref="$1"
tree="$2"

if [ ! -d "$tree" ]; then
    echo "tree dir not found: $tree" >&2
    exit 2
fi

fail=0
n=0
while IFS= read -r -d '' f; do
    rel="${f#"$tree"/}"
    want="$(git rev-parse "$head_ref:$rel" 2>/dev/null | cut -c1-40)" || {
        echo "MISSING-IN-HEAD $rel"
        fail=1
        continue
    }
    got="$(git hash-object "$f" | cut -c1-40)"
    if [ "$got" != "$want" ]; then
        echo "MISMATCH $rel (head=$want tree=$got)"
        fail=1
    fi
    n=$((n + 1))
done < <(find "$tree" -type f -print0)

if [ "$fail" -eq 0 ]; then
    echo "OK: $n files match $head_ref"
else
    exit 1
fi
