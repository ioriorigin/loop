#!/usr/bin/env bash
# Zenn の検索結果の中で、指定した slug が何位に出るかを測る。
#
# なぜ要るか: 棚（一覧）での順位は測ってきたが、**読者が実際に通る経路は検索である。**
# 棚に載っていることと、探している人に見つかることは別の量である。
#
# 使い方: ./search_rank.sh <source: articles|books> <slug> <クエリ> [最大ページ数]
# 出力: TSV（query / source / slug / rank / total_scanned / found）
set -u
SRC="${1:?source (articles|books)}"
SLUG="${2:?slug}"
QUERY="${3:?query}"
MAXPAGE="${4:-5}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

rank=0
found=""
page=1
while [ "$page" -le "$MAXPAGE" ]; do
  body=$(curl -sS -G -H "User-Agent: $UA" \
    --data-urlencode "q=$QUERY" --data-urlencode "source=$SRC" --data-urlencode "page=$page" \
    "https://zenn.dev/api/search") || break
  read -r n hit <<<"$(printf '%s' "$body" | SLUG="$SLUG" SRC="$SRC" OFF="$rank" python3 -c '
import json,sys,os
d=json.load(sys.stdin)
items=d.get(os.environ["SRC"]) or []
off=int(os.environ["OFF"]); slug=os.environ["SLUG"]
hit=0
for i,it in enumerate(items,1):
    if it.get("slug")==slug:
        hit=off+i; break
print(len(items), hit)
')"
  [ -z "${n:-}" ] && break
  rank=$((rank + n))
  if [ "${hit:-0}" -gt 0 ]; then found="$hit"; break; fi
  [ "$n" -lt 48 ] && break        # 最終ページ
  page=$((page + 1))
done

printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$QUERY" "$SRC" "$SLUG" "${found:-NA}" "$rank" "$([ -n "$found" ] && echo yes || echo no)"
