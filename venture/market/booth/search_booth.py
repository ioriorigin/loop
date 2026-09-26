#!/usr/bin/env python3
"""BOOTH の検索結果を「欲しいもの数」順に取り、上位 n 件の wish_lists_count と価格を取る。
robots: ../robots/booth.pm_*.txt（/terms /carts /cart のみ Disallow）。1 リクエストごとに 1.5 秒あける。
使い方: search_booth.py <検索語> <詳細を取る件数>
"""
import sys, re, html, json, time, urllib.parse, urllib.request, datetime
q, n = sys.argv[1], int(sys.argv[2])
UA = {"User-Agent": "Mozilla/5.0 (loop market survey; github.com/ioriorigin/loop)"}
def get(u):
    time.sleep(1.5)
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode()
s = get(f"https://booth.pm/ja/search/{urllib.parse.quote(q)}?sort=wish_list")
tot = re.search(r'([\d,]+)\s*件', s)
ids = re.findall(r'data-product-id="(\d+)"', s)
names = re.findall(r'data-product-name="([^"]*)"', s)
prices = re.findall(r'data-product-price="([^"]*)"', s)
ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
fn = f"search-{q.replace(' ', '_')}_{ts}.tsv"
out = open(fn, "w")
out.write(f"# query={q} total={tot.group(1) if tot else '?'} sort=wish_list\n")
out.write("rank\tid\tlist_price\twish_lists_count\tcategory\tname\n")
for k, (i, nm, pr) in enumerate(zip(ids, names, prices), 1):
    w = c = ""
    if k <= n:
        try:
            d = json.loads(get(f"https://booth.pm/ja/items/{i}.json"))
            w = d.get("wish_lists_count", ""); c = (d.get("category") or {}).get("name", "")
        except Exception as e:
            w = f"ERR:{e}"
    out.write(f"{k}\t{i}\t{pr}\t{w}\t{c}\t{html.unescape(nm)}\n")
print(fn, len(ids), tot.group(1) if tot else '?')
