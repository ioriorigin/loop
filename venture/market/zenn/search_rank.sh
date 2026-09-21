#!/usr/bin/env bash
# Zenn の検索結果の中で、指定した slug が何位に出るかを測る。
#
# なぜ要るか: 棚（一覧）での順位は測ってきたが、**読者が実際に通る経路は検索である。**
# 棚に載っていることと、探している人に見つかることは別の量である。
#
# 使い方: ./search_rank.sh <source: articles|books> <slug> <クエリ> [最大ページ数]
# 出力: TSV（query / source / slug / rank / rows / found / truncated / distinct / dups）
#
# **2026-09-21 改訂その1 — 旧版は見つけた時点で走査を打ち切り、その打ち切り位置を「件数」として出していた。**
# 旧版の5列目は `total_scanned` という名前で、見つからなかった回は真の総数だったが、
# **見つかった回は「見つかるまでに数えた件数」でしかなかった。**
# 同じ列に2つの意味が入り、読む側は区別できない。実際「94 位 / 96 件」と書かれた欄の
# 真の総数は 234 件で、**その数字は PR コメント（REPORT.md）として外へ出ている。**
#
# **2026-09-21 改訂その2 — その「真の総数」も、真の総数ではなかった。**
# ページを繰って集めた行には**重複がある。** 実測（同日 13:0x UTC）:
#
#   q=エージェント  行 249 / 相異なる 244 / 重複 5
#   q=Claude Code   行 234 / 相異なる 232 / 重複 2
#   q=AI            行 520 / 相異なる 513 / 重複 7
#   q=Claude        行 301 / 相異なる 296 / 重複 5
#
# **重複はページの境目で起きる**（1ページ目の末尾と2ページ目の先頭に同じ slug が出る）。
# オフセット方式のページングで並びが安定していないときの典型で、
# **重複した数だけ、どこかの行が落ちている可能性がある。**
# 5回繰り返しても同じ 244 件だったので、**この重複は乱数ではなく決定的である**——
# つまり「繰り返せば埋まる」たぐいのものではない。
#
# **したがって、この道具が出す数は3つに分けて書く。**
#   rows     = 返ってきた行数（これまで total と呼んでいた数。**件数ではない**）
#   distinct = 相異なる slug の数（**分母として書いてよいのはこちら**）
#   dups     = rows - distinct（**0 でなければ、落ちた行があるかもしれないという警告**）
#
# **rank は相異なる順位で数える。** 重複を1件ずつ数えると順位が水増しされる。
set -u
SRCK="${1:?source (articles|books)}"
SLUG="${2:?slug}"
QUERY="${3:?query}"
MAXPAGE="${4:-20}"

SRCK="$SRCK" SLUG="$SLUG" QUERY="$QUERY" MAXPAGE="$MAXPAGE" \
PAGES_DIR="${ZENN_SEARCH_PAGES_DIR:-}" python3 <<'PY'
import json, os, subprocess, sys

src   = os.environ["SRCK"]
slug  = os.environ["SLUG"]
query = os.environ["QUERY"]
maxp  = int(os.environ["MAXPAGE"])
pdir  = os.environ.get("PAGES_DIR") or ""
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

def fetch(page):
    # 回帰テストがネットワーク無しで検出力を持つための口。本番では未設定である。
    if pdir:
        try:
            with open(os.path.join(pdir, "page-%d.json" % page), encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""
    r = subprocess.run(
        ["curl", "-sS", "-G", "-H", "User-Agent: " + UA,
         "--data-urlencode", "q=" + query,
         "--data-urlencode", "source=" + src,
         "--data-urlencode", "page=%d" % page,
         "https://zenn.dev/api/search"],
        capture_output=True, text=True)
    return r.stdout

rows = 0
seen = []          # 出現順。相異なる順位を数えるのに使う
seen_set = set()
truncated = "no"
page = 1

while True:
    if page > maxp:
        truncated = "yes"
        break
    body = fetch(page)
    if not body:
        break
    try:
        d = json.loads(body)
    except Exception:
        break
    items = d.get(src) or []
    if not items:
        break
    rows += len(items)
    for it in items:
        s = it.get("slug")
        if s not in seen_set:
            seen_set.add(s)
            seen.append(s)
    # **見つけても止まらない。** 止めると分母が「見つかるまでの件数」に化ける（改訂その1 の欠陥）
    #
    # **終わりの判定は next_page で行う。** 旧版は「48 件未満なら最終ページ」という
    # 目安だけを見ていた。API が中途のページで 48 件未満を返す設計なら、そこで黙って打ち切る
    # ——**打ち切りを総数と偽らない**と書いた当の場所に、別の打ち切りが残っていた。
    # 実測（2026-09-21 13:1x UTC）では両者は一致したが、**一致することと同じ量であることは別である。**
    nxt = d.get("next_page")
    if not nxt:
        break
    if len(items) < 48:      # 目安のほうは残す。next_page が嘘をついた回に無限に回らないため
        break
    page += 1

rank = seen.index(slug) + 1 if slug in seen_set else None
distinct = len(seen)
print("\t".join([
    query, src, slug,
    str(rank) if rank else "NA",
    str(rows),
    "yes" if rank else "no",
    truncated,
    str(distinct),
    str(rows - distinct),
]))
PY
