#!/bin/bash
# 棚の全ページを引いて、rank / slug / liked_count / published_at を出す
shelf="$1"   # "" = 全体, それ以外は topicname
if [ -z "$shelf" ]; then base="https://zenn.dev/api/books?page="; else base="https://zenn.dev/api/books?topicname=${shelf}&page="; fi
rank=0; page=1
while :; do
  resp=$(curl -sS --max-time 30 "${base}${page}")
  n=$(printf '%s' "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(len(d.get("books",[])))' 2>/dev/null)
  [ -z "$n" ] && { echo "PARSE_FAIL page=$page" >&2; break; }
  printf '%s' "$resp" | python3 -c '
import sys,json
d=json.load(sys.stdin)
start=int(sys.argv[1])
for i,b in enumerate(d.get("books",[]),start=start+1):
    u=b.get("user") or {}
    print("%d\t%s/%s\t%s\t%s\t%s\t%s" % (i, u.get("username"), b.get("slug"), b.get("liked_count"), b.get("price"), b.get("published_at"), b.get("body_updated_at")))
' "$rank"
  rank=$((rank+n))
  np=$(printf '%s' "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("next_page") or "")')
  [ -z "$np" ] && break
  page="$np"
done
echo "TOTAL=$rank" >&2
