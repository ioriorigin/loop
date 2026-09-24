#!/usr/bin/env bash
# GitHub API の書き込み面が「どこで」止められているかを分ける計器。
#
# なぜ要るか（2026-09-24 に分かったこと）:
# loop は 403 を1種類のものとして記録してきた。`venture/ASKS.md` A-025 は
# 「Traffic API は push 権限を要求し、loop は 403 で拒否されている」と書いている。
# **実際には、止め手が2つある。**
#
#   - エージェントプロキシ … documentation_url が docs.anthropic.com を指す
#   - GitHub 側の権限/検証 … documentation_url が docs.github.com、または 404 / 422
#
# 前者は「この環境の方針」であり、権限を足しても開かない。
# 後者は「App の権限」であり、オーナーが足せば開く。**次にやることが正反対である。**
#
# 副作用を出さない作り:
# **通ってしまった場合に GitHub 側が 404 / 422 で落とす body / path だけを撃つ。**
# 必須欄を意図的に欠落させ、存在しない番号を叩く。作成も変更も起きない。
# star / delete / collaborator など、通ると実害が出る面は最初から撃たない。
#
# 使い方: ./gh_write_probe.sh > gh-write-probe_$(date -u +%Y-%m-%dT%H%MZ).tsv
set -u
API=https://api.github.com
R=${REPO:-ioriorigin/loop}

probe() {
  local m="$1" p="$2" b="$3" l="$4"
  local body code
  body=$(curl -sS -m 30 -X "$m" \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "Content-Type: application/json" \
    ${b:+-d "$b"} -o /tmp/ghprobe.json -w '%{http_code}' "$API$p") || body=000
  code="$body"
  python3 - "$l" "$m $p" "$code" <<'PY'
import json, sys
label, path, code = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    d = json.load(open('/tmp/ghprobe.json'))
except Exception:
    d = {}
msg = ' '.join((d.get('message') or '').split())
doc = d.get('documentation_url') or ''
if 'docs.anthropic.com' in doc:
    who = 'proxy'
elif 'docs.github.com' in doc or code in ('404', '422'):
    who = 'github'
else:
    who = '?'
print('\t'.join([label, path, code, who, msg]))
PY
}

printf 'label\tmethod_path\thttp\tblocked_by\tmessage\n'
probe PATCH "/repos/$R"                      '{"description":"probe"}'                'リポジトリ設定（description）'
probe PUT   "/repos/$R/topics"               '{"names":["probe"]}'                    'リポジトリのトピック'
probe GET   "/repos/$R/traffic/views"        ''                                       'Traffic（読み取り・要 push 権限）'
probe POST  "/repos/$R/issues"               '{}'                                     'Issue の作成（title 欠落）'
probe POST  "/repos/$R/issues/11/comments"   '{}'                                     'Issue コメント（body 欠落）'
probe PATCH "/repos/$R/issues/99999"         '{"title":"probe"}'                      '存在しない Issue の更新'
probe POST  "/repos/$R/pulls"                '{}'                                     'PR の作成（必須欄 欠落）'
probe POST  "/repos/$R/git/refs"             '{"ref":"refs/heads/__probe","sha":"0"}' 'ref の作成（不正な sha）'
probe PUT   "/repos/$R/contents/__probe.txt" '{}'                                     'ファイルの直接作成（必須欄 欠落）'
probe POST  "/repos/$R/releases"             '{}'                                     'リリースの作成（tag_name 欠落）'
probe POST  "/repos/$R/hooks"                '{}'                                     'Webhook の作成（必須欄 欠落）'
probe PUT   "/repos/$R/pages"                '{}'                                     'GitHub Pages の設定'
probe PATCH "/repos/$R/actions/permissions"  '{}'                                     'Actions の権限設定'
