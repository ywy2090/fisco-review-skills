#!/usr/bin/env bash
# Acquire or release the per-review file lock (mkdir-based, atomic).
# Usage:
#   lock.sh acquire <dir> [timeout_sec] [ttl_min]
#   lock.sh release <dir>
#
# acquire: mkdir -p <dir>, then atomically mkdir <dir>/.lock and record PID +
# timestamp inside. On contention, polls every 2 s up to timeout (default 30 s);
# breaks a stale lock older than ttl (default 30 min) whose recorded PID is dead.
# Exits 0 on acquire, 1 on timeout, 2 on usage error.
# release: rm -rf <dir>/.lock.
set -euo pipefail

cmd="${1:-}"
dir="${2:-}"

case "$cmd" in
  acquire)
    [ -n "$dir" ] || { echo "lock.sh acquire: missing <dir>" >&2; exit 2; }
    timeout="${3:-30}"
    ttl_min="${4:-30}"
    mkdir -p "$dir"
    lock="$dir/.lock"
    deadline=$(( $(date +%s) + timeout ))
    while ! mkdir "$lock" 2>/dev/null; do
        pid="$(cat "$lock/pid" 2>/dev/null || true)"
        ts="$(cat "$lock/ts" 2>/dev/null || true)"
        now=$(date +%s)
        if [ -n "$ts" ] && [ $(( now - ts )) -gt $(( ttl_min * 60 )) ]; then
            if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
                echo "breaking stale lock: $lock (pid=${pid:-none}, age=$((now - ts))s)" >&2
                rm -rf "$lock"
                continue
            fi
        fi
        if [ "$now" -ge "$deadline" ]; then
            echo "lock held: $lock (pid=${pid:-none})" >&2
            exit 1
        fi
        sleep 2
    done
    echo "$$" > "$lock/pid"
    date +%s > "$lock/ts"
    echo "acquired $lock"
    ;;
  release)
    [ -n "$dir" ] || { echo "lock.sh release: missing <dir>" >&2; exit 2; }
    rm -rf "$dir/.lock"
    echo "released $dir/.lock"
    ;;
  *)
    echo "usage: lock.sh acquire|release <dir> [timeout_sec] [ttl_min]" >&2
    exit 2
    ;;
esac
