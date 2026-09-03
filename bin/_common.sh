#!/usr/bin/env bash
# 共通処理。時刻の表記をここに集約する。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEM="$ROOT/memory"

# 記憶を置くブランチ（CLAUDE.md §5）。**押す先を各スクリプトに書き写さない。**
# ハーネスが別のブランチを割り当てて起動する回が実在する（2026-09-02 の対話回）。
# そこへ押した記録は `round gaps` が読む場所から外れ、次の自分から見えなくなる。
# 押してよい唯一の場所を1か所に持つ。
WORK_BRANCH="claude/autonomous-ai-agent-design-jv7jv6"

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

# push --dry-run が失敗したとき、その理由を分類する。
# 「押す権限が無い」と「単に遅れている」を混同してはいけない。
# non-fast-forward は pull で解ける良性の状態であり、これを最重要異常として報告すると
# .claude/rules/autonomous-loop.md の「preflight が push 不能を報告したら、その回は
# 作業をせず原因究明だけに充てる」が誤発動し、1回分を丸ごと潰す。
# 2026-08-30 12:24 UTC に実際に発生した。誤警報はコストである。
# preflight から切り出してあるのは、テストできる形にするため（bin/selftest H 節）。
#
# 2026-09-02 追記: 3つ目の分類 noref を足した。
# コンテナが作り直され、`main`（README.md 1本だけ）の浅いクローンで起動した回が実在する。
# ローカルに作業ブランチの ref が無いので、push は**リモートに触れる前に**ローカルで落ちる。
#   error: src refspec claude/... does not match any
# これは良性である。だが分類が2つしか無かったため unknown に落ち、
# preflight は「push できない（原因不明）。**今すぐ原因を潰せ。**」と報告した。
# stale を unknown に落として1回を潰した 2026-08-30 の欠陥と、**同じ型が3つ目の理由で再発した。**
# 分類の穴は「知らない理由が来たとき最悪側に倒れる」形で必ず出る。
push_err_kind() {
  local msg="${1:-}"
  if printf '%s' "$msg" | grep -qiE 'non-fast-forward|fetch first|behind its remote'; then
    echo stale
  elif printf '%s' "$msg" | grep -qiE 'src refspec .* does not match any'; then
    # ここは**ローカル ref の不在に限る。** 「remote が無い」（does not appear to be a
    # git repository）を巻き込みたくなるが、あれは良性ではない。良性側の分類を広げると、
    # 本物の異常が「ブランチを作れば直る」と読まれて素通りする。分類は狭いほうへ倒す。
    # ローカルに ref が無い。git はリモートへ接続する前に落ちるので、
    # **認証が生きているかどうかは、この失敗からは何も分からない。**
    # stale（認証は生きていると言える）と混同しないこと。ブランチを作ってから測り直す。
    echo noref
  elif printf '%s' "$msg" | grep -qiE 'authentication|permission denied|403|could not read username|repository not found|access denied|support for password authentication'; then
    echo auth
  else
    echo unknown
  fi
}
