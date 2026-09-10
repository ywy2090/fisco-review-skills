#!/usr/bin/env bash
# verify_env.sh — pin a revision and materialise an isolated repro workspace.
#
# Verification has two hard requirements that are easy to get wrong by hand:
# evidence must be read at one immutable revision, and a reproduction must not
# mutate the tree under review. This script sets both up and prints shell
# exports for the caller to `eval`:
#
#   eval "$(bash verify_env.sh 5549)"                       # from a PR number
#   eval "$(bash verify_env.sh --head <oid> --base <oid>)"   # from raw OIDs
#   eval "$(bash verify_env.sh --head <oid> --no-worktree)"  # static-only pass
#
# Exports: ARTIFACT_DIR RUN_ID VERIFY_ROOT VERIFY_PIN VERIFY_BASE_PIN HEAD_OID
#          BASE_OID REPRO_WORKTREE (empty when --no-worktree)
#
# Two directories, deliberately separate: VERIFY_ROOT holds throwaway scratch
# (the repro worktree) and may be deleted, while ARTIFACT_DIR holds the
# verification evidence and must survive — see `references/report.md`.
#
# When a PR number is given, the family's per-PR artifact directory is reused so
# verification lands beside the review artifacts it belongs to. That script
# takes a per-PR lock which it does NOT auto-release, so this script also
# exports RUN_ID and prints the release command; the caller is responsible for
# releasing it (see the trap line in `references/intake.md`).

set -euo pipefail

PR=""
HEAD_OID=""
BASE_OID=""
MAKE_WORKTREE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --head) HEAD_OID="$2"; shift 2 ;;
    --base) BASE_OID="$2"; shift 2 ;;
    --no-worktree) MAKE_WORKTREE=0; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) PR="$1"; shift ;;
  esac
done

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [[ "$REPO" != "FISCO-BCOS/FISCO-BCOS" ]]; then
  echo "❌ 请在 FISCO-BCOS 主仓库内运行并确保 gh 已认证（当前 repo='${REPO:-unknown}'）；" >&2
  echo "   纯本地 artifact 复核可直接读 SKILL.md 用 git 取证，不必运行本脚本。" >&2
  exit 1
fi
command -v jq >/dev/null 2>&1 || { echo "❌ 缺少 jq" >&2; exit 1; }

MAIN_REMOTE=$(git remote -v | awk '/github\.com[:\/]FISCO-BCOS\/FISCO-BCOS/ {print $1; exit}')
[[ -n "$MAIN_REMOTE" ]] || { echo "❌ 未找到指向 FISCO-BCOS/FISCO-BCOS 的 remote" >&2; exit 1; }

VERIFY_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/fisco-verify-${PR:-manual}.XXXXXX")
chmod 700 "$VERIFY_ROOT"
printf 'pid=%s started=%s pr=%s owner=%s\n' "$$" "$(date -u +%FT%TZ)" "${PR:-manual}" "$(id -un)" \
  >"$VERIFY_ROOT/OWNERSHIP"

# Artifact dir: prefer the family's per-PR directory (it is where the sibling
# review artifacts live), otherwise a sibling of VERIFY_ROOT that survives
# scratch cleanup.
ARTIFACT_DIR=""
RUN_ID=""
SHARED_INIT="${FISCO_SKILLS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}/fisco-review-shared/scripts/init_artifact_dir.sh"
if [[ -n "$PR" ]]; then
  if [[ -f "$SHARED_INIT" ]]; then
    SHARED_OUT=""
    if SHARED_OUT=$(bash "$SHARED_INIT" "$REPO" "$PR" 2>/dev/null); then
      # The family idiom is to eval these assignments; `%q` quoting is handled
      # by the shell, unlike a textual parse.
      eval "$(printf '%s\n' "$SHARED_OUT" | grep -E '^(ARTIFACT_DIR|RUN_ID|MANIFEST)=')"
      ARTIFACT_DIR=${ARTIFACT_DIR:-}
      RUN_ID=${RUN_ID:-}
      [[ -n "$ARTIFACT_DIR" && -d "$ARTIFACT_DIR" ]] || ARTIFACT_DIR=""
    fi
    if [[ -z "$ARTIFACT_DIR" ]]; then
      echo "⚠️ 未能取得 shared per-PR artifact 目录（可能已被锁或脚本报错），本轮改用独立目录；" >&2
      echo "   如出现 'PR artifact directory is locked'，用 release_artifact_lock.sh <dir> <RUN_ID> 释放。" >&2
    fi
  else
    echo "⚠️ 未找到 $SHARED_INIT，本轮使用独立 artifact 目录。" >&2
  fi
fi
if [[ -z "$ARTIFACT_DIR" ]]; then
  ARTIFACT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/fisco-verify-artifacts-${PR:-manual}.XXXXXX")
  chmod 700 "$ARTIFACT_DIR"
  [[ -z "$RUN_ID" ]] && RUN_ID="verify-${PR:-manual}-$$-$(date +%s)"
fi
[[ -L "$ARTIFACT_DIR" ]] && { echo "❌ ARTIFACT_DIR 是 symlink，拒绝使用" >&2; exit 1; }

# Resolve the pin from the tracker (authoritative) or from the caller.
if [[ -n "$PR" ]]; then
  META=$(gh pr view "$PR" --json headRefOid,baseRefOid) \
    || { echo "❌ 拉取 PR #$PR metadata 失败（网络或 gh 权限）" >&2; exit 1; }
  [[ -z "$HEAD_OID" ]] && HEAD_OID=$(jq -er '.headRefOid' <<<"$META")
  [[ -z "$BASE_OID" ]] && BASE_OID=$(jq -er '.baseRefOid' <<<"$META")
fi
[[ "$HEAD_OID" =~ ^[0-9a-f]{40}$ ]] || { echo "❌ head OID 非法: '${HEAD_OID:-empty}'" >&2; exit 1; }
[[ "$BASE_OID" =~ ^[0-9a-f]{40}$ ]] || { echo "❌ base OID 非法: '${BASE_OID:-empty}'" >&2; exit 1; }

VERIFY_PIN="refs/verify/pr-${PR:-manual}/head-$HEAD_OID"
VERIFY_BASE_PIN="refs/verify/pr-${PR:-manual}/base-$BASE_OID"
fetch_or_local() {   # <oid> <pin-ref> <label>
  if git fetch "$MAIN_REMOTE" "$1:$2" 2>/dev/null; then return 0; fi
  if [[ "$(git cat-file -t "$1" 2>/dev/null)" == "commit" ]]; then
    git update-ref "$2" "$1"
    return 0
  fi
  echo "❌ 无法取得 $3（$1）：远端 fetch 失败且本地无此 object" >&2
  return 1
}
fetch_or_local "$HEAD_OID" "$VERIFY_PIN" head || exit 1
fetch_or_local "$BASE_OID" "$VERIFY_BASE_PIN" base || exit 1
[[ "$(git rev-parse "$VERIFY_PIN")" == "$HEAD_OID" ]] \
  || { echo "❌ pin 解析与预期 OID 不一致，中止" >&2; exit 1; }
[[ "$(git rev-parse "$VERIFY_BASE_PIN")" == "$BASE_OID" ]] \
  || { echo "❌ base pin 解析与预期 OID 不一致，中止" >&2; exit 1; }

REPRO_WORKTREE=""
if [[ "$MAKE_WORKTREE" == "1" ]]; then
  REPRO_WORKTREE="$VERIFY_ROOT/worktree"
  git worktree add --detach "$REPRO_WORKTREE" "$VERIFY_PIN" >/dev/null
  printf 'repro worktree at %s (detached at %s)\n' "$REPRO_WORKTREE" "${HEAD_OID:0:12}" >&2
  printf '%s\n' "$REPRO_WORKTREE" >"$VERIFY_ROOT/worktree_path"
fi

printf 'export ARTIFACT_DIR=%q\n' "$ARTIFACT_DIR"
printf 'export RUN_ID=%q\n' "$RUN_ID"
printf 'export VERIFY_ROOT=%q\n' "$VERIFY_ROOT"
printf 'export VERIFY_PIN=%q\n' "$VERIFY_PIN"
printf 'export VERIFY_BASE_PIN=%q\n' "$VERIFY_BASE_PIN"
printf 'export HEAD_OID=%q\n' "$HEAD_OID"
printf 'export BASE_OID=%q\n' "$BASE_OID"
printf 'export REPRO_WORKTREE=%q\n' "$REPRO_WORKTREE"
printf 'export SKILL_DIR=%q\n' "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cat >&2 <<EOF
# cleanup: git worktree remove --force "$REPRO_WORKTREE"; rm -rf "$VERIFY_ROOT"
#   (ARTIFACT_DIR is evidence — keep it; copy it out before rm -rf.)
EOF
if [[ -n "$PR" && -f "$SHARED_INIT" && -n "$RUN_ID" ]]; then
  cat >&2 <<EOF
# release the shared per-PR lock when done (the init script does not auto-release):
#   trap 'bash "$(dirname "$SHARED_INIT")/release_artifact_lock.sh" "$ARTIFACT_DIR" "$RUN_ID"' EXIT
EOF
fi
