#!/usr/bin/env bash
# 共通処理。時刻の表記をここに集約する。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEM="$ROOT/memory"

ts_utc()  { date -u "+%Y-%m-%d %H:%M:%S UTC"; }
ts_jst()  { TZ=Asia/Tokyo date "+%Y-%m-%d %H:%M:%S JST"; }
ts_both() { echo "$(ts_utc) / $(ts_jst)"; }
# 日付は JST で切る。実行環境は UTC だが自分の文脈は日本時間にある。
# UTC で切ると JST の「1日」が 09:00 を境に2ファイルに割れ、「昨日の自分」が定義できなくなる。
today()   { TZ=Asia/Tokyo date "+%Y-%m-%d"; }
logfile() {
  local d f
  d="$MEM/log/$(TZ=Asia/Tokyo date '+%Y/%m')"
  f="$d/$(today).md"
  mkdir -p "$d"
  if [ ! -f "$f" ]; then
    printf '# %s の記録\n' "$(today)" > "$f"
  fi
  echo "$f"
}
