#!/usr/bin/env bash
# 原稿の字数を数える。OUTLINE.md の字数目安に対して、いまどこにいるかを測るための計器。
#
# 目安を書いただけで測る手段が無ければ、それは守られない。
# `.claude/rules/autonomous-loop.md`「測れない停止条件は、書いてあっても発動しない」と同じ話である。
#
# 空白・改行を除いた文字数を数える（日本語の原稿なのでバイト数では意味を成さない）。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MS="$ROOT/manuscript"

[ -d "$MS" ] || { echo "manuscript/ が無い"; exit 1; }

total=0
printf '%-40s %8s\n' "ファイル" "字数"
printf '%s\n' "------------------------------------------------"
for f in "$MS"/*.md; do
  [ -e "$f" ] || continue
  n=$(perl -CSD -pe 's/\s//g' "$f" | perl -CSD -ne '$c+=length($_); END{print $c+0}')
  total=$((total + n))
  printf '%-40s %8d\n' "$(basename "$f")" "$n"
done
printf '%s\n' "------------------------------------------------"
printf '%-40s %8d\n' "合計" "$total"
printf '\n目安 47,500 字に対して %d%%（OUTLINE.md §3）\n' "$((total * 100 / 47500))"
