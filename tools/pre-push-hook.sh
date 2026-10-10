#!/usr/bin/env bash
# pre-push gate: refuse to publish a skill whose installed copy differs from the
# tree being pushed. The hook is not versioned, so keep this file versioned and
# point .git/hooks/pre-push at it:
#
#   ln -sf ../../tools/pre-push-hook.sh .git/hooks/pre-push
#
# Deliberate bypass: SKILL_SYNC_OVERRIDE=1 git push

set -uo pipefail

root=$(git rev-parse --show-toplevel)

if [ "${SKILL_SYNC_OVERRIDE:-0}" = "1" ]; then
    echo "pre-push: skill sync check skipped (SKILL_SYNC_OVERRIDE=1)"
    exit 0
fi

if ! out=$("$root/tools/check-install-sync.sh" 2>&1); then
    printf '%s\n' "$out" >&2
    cat >&2 <<'EOF'

pre-push: the skills installed under ~/.agents/skills differ from the copies
committed here. Publishing now would either ship a tree nobody installed or
hide an installed fix. Inspect, sync installed -> repo, then push:

  tools/check-install-sync.sh
  rsync -a --exclude __pycache__ --exclude .DS_Store \
        ~/.agents/skills/<skill>/ .agents/skills/<skill>/

Deliberate bypass (e.g. publishing a doc-only change while a skill edit is
still in flight): SKILL_SYNC_OVERRIDE=1 git push
EOF
    exit 1
fi

exit 0
