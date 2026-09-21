#!/usr/bin/env bash
# Zenn の検索結果の中で、指定した slug が何位に出るかを測る。
#
# なぜ要るか: 棚（一覧）での順位は測ってきたが、**読者が実際に通る経路は検索である。**
# 棚に載っていることと、探している人に見つかることは別の量である。
#
# 使い方: ./search_rank.sh <source: articles|books> <slug> <クエリ> [最大ページ数]
# 出力: TSV（query / source / slug / rank / total / found / truncated）
#
# **2026-09-21 改訂 — 旧版は見つけた時点で走査を打ち切り、その打ち切り位置を「件数」として出していた。**
# 旧版の5列目は `total_scanned` という名前で、見つからなかった回は真の総数だったが、
# **見つかった回は「見つかるまでに数えた件数」でしかなかった。**
# 同じ列に2つの意味が入り、読む側は区別できない。実際「94 位 / 96 件」と書かれた欄の
# 真の総数は 234 件で、**その数字は PR コメント（REPORT.md）として外へ出ている。**
# いまは見つけた後も最後まで走査し、rank と total を別の列に出す。
# 上限ページに達して末尾へ届かなかったときは truncated=yes と言う。**届かなかったことを総数と偽らない。**
set -u
SRC="${1:?source (articles|books)}"
SLUG="${2:?slug}"
QUERY="${3:?query}"
MAXPAGE="${4:-20}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

# 1ページぶんの JSON を取る。ZENN_SEARCH_PAGES_DIR が指されていればそこから読む
# （回帰テストがネットワーク無しで検出力を持つための口。本番では未設定である）。
fetch_page() {
  if [ -n "${ZENN_SEARCH_PAGES_DIR:-}" ]; then
    cat "$ZENN_SEARCH_PAGES_DIR/page-$1.json" 2>/dev/null
    return 0
  fi
  curl -sS -G -H "User-Agent: $UA" \
    --data-urlencode "q=$QUERY" --data-urlencode "source=$SRC" --data-urlencode "page=$1" \
    "https://zenn.dev/api/search"
}

total=0
found=""
truncated=no
page=1
while :; do
  if [ "$page" -gt "$MAXPAGE" ]; then truncated=yes; break; fi
  body=$(fetch_page "$page") || break
  [ -z "$body" ] && break
  read -r n hit <<<"$(printf '%s' "$body" | SLUG="$SLUG" SRC="$SRC" OFF="$total" python3 -c '
import json,sys,os
try:
    d=json.load(sys.stdin)
except Exception:
    print(0,0); sys.exit(0)
items=d.get(os.environ["SRC"]) or []
off=int(os.environ["OFF"]); slug=os.environ["SLUG"]
hit=0
for i,it in enumerate(items,1):
    if it.get("slug")==slug:
        hit=off+i; break
print(len(items), hit)
')"
  [ -z "${n:-}" ] && break
  total=$((total + n))
  # **見つけても止まらない。** 止めると total が「見つかるまでの件数」に化ける（旧版の欠陥）
  [ "${hit:-0}" -gt 0 ] && [ -z "$found" ] && found="$hit"
  [ "$n" -lt 48 ] && break        # 最終ページ
  page=$((page + 1))
done

printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$QUERY" "$SRC" "$SLUG" "${found:-NA}" "$total" "$([ -n "$found" ] && echo yes || echo no)" "$truncated"
