#!/usr/bin/env bash
# 共通処理。時刻の表記をここに集約する。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEM="$ROOT/memory"

ts_utc()  { date -u "+%Y-%m-%d %H:%M:%S UTC"; }
ts_jst()  { TZ=Asia/Tokyo date "+%Y-%m-%d %H:%M:%S JST"; }
ts_both() { echo "$(ts_utc) / $(ts_jst)"; }
today()   { date -u "+%Y-%m-%d"; }
logfile() {
  local d f
  d="$MEM/log/$(date -u '+%Y/%m')"
  f="$d/$(today).md"
  mkdir -p "$d"
  if [ ! -f "$f" ]; then
    printf '# %s の記録\n' "$(today)" > "$f"
  fi
  echo "$f"
}
