#!/bin/bash
# 記事の棚を引いて rank / path / id / 反応 / 日付 を出す。
# 本の棚（fetch_shelf.sh）と違い、**この API は 100 ページ（4800 件）で打ち切られる。**
# 4800 行ちょうどで終わったら、それは棚の全数ではなく上限である。
topic="$1"   # 例: claudecode
if [ -z "$topic" ]; then base="https://zenn.dev/api/articles?page="; else base="https://zenn.dev/api/articles?topicname=${topic}&page="; fi
rank=0; page=1
printf 'rank\tpath\tid\tliked_count\tbookmarked_count\tcomments_count\tbody_letters_count\tarticle_type\tprincipal_type\tpublished_at\tbody_updated_at\n'
while :; do
  resp=$(curl -sS --max-time 30 "${base}${page}")
  n=$(printf '%s' "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(len(d.get("articles",[])))' 2>/dev/null)
  [ -z "$n" ] && { echo "PARSE_FAIL page=$page" >&2; break; }
  [ "$n" = "0" ] && break
  printf '%s' "$resp" | python3 -c '
import sys,json
d=json.load(sys.stdin); start=int(sys.argv[1])
for i,a in enumerate(d.get("articles",[]),start=start+1):
    print("%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (i, a.get("path"), a.get("id"),
        a.get("liked_count"), a.get("bookmarked_count"), a.get("comments_count"),
        a.get("body_letters_count"), a.get("article_type"), a.get("principal_type"),
        a.get("published_at"), a.get("body_updated_at")))
' "$rank"
  rank=$((rank+n))
  np=$(printf '%s' "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("next_page") or "")')
  [ -z "$np" ] && break
  page="$np"
done
echo "TOTAL=$rank" >&2
[ "$rank" = "4800" ] && echo "WARN: 4800 = 100ページの上限。棚の全数ではない可能性が高い" >&2
