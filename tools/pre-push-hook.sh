#!/usr/bin/env bash
# pre-push gate: refuse to publish a skill whose installed copy differs from the
# tree being pushed. The hook itself is not versioned, so this file is the hook's
# body and the caller is three lines (see the README's "Wiring the gate"):
#
#   REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT=""
#   if [ -n "$REPO_ROOT" ] && [ -x "$REPO_ROOT/tools/check-install-sync.sh" ]; then
#     "$REPO_ROOT/tools/pre-push-hook.sh" >&2 || exit 1
#   fi
#
# Put that block in the hook git actually runs — `git config core.hooksPath` if
# it is set, otherwise .git/hooks/pre-push — and before that hook's final
# `exit 0`. Keep the bypass here (not in the caller) so a bypass always prints.
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
