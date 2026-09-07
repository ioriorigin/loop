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

# 目安の字数は OUTLINE.md の TARGET_CHARS マーカー 1 か所だけが定義元である。
# ここへ写し取らない。写し取ると、目安を見直したときに計器だけが古い数字で報告し続ける
# （memory/OPERATING.md §11 の WORK_BRANCH と同じ形の欠陥）。
OUTLINE="$ROOT/OUTLINE.md"
# `|| true` が要る。set -o pipefail のもとでは grep の「該当なし」(exit 1) がパイプ全体の失敗になり、
# 下の「読めなかった」分岐へ到達する前にスクリプトが死ぬ。**未知を扱う分岐は、
# 未知が起きたときに実行されなければ書いていないのと同じである。**
target=$(grep -oE 'TARGET_CHARS=[0-9]+' "$OUTLINE" 2>/dev/null | tail -1 | cut -d= -f2 || true)
if [ -z "$target" ]; then
  # 見つからないことを黙って既定値に潰さない（未知を既定値に落とすな）
  printf '\n合計 %d 字。**目安を読めなかった**（%s に TARGET_CHARS= が無い）\n' "$total" "$OUTLINE"
  exit 3
fi
printf '\n目安 %s 字に対して %d%%（OUTLINE.md の TARGET_CHARS）\n' \
  "$(printf '%d' "$target" | sed ':a;s/\B[0-9]\{3\}\>/,&/;ta')" "$((total * 100 / target))"
