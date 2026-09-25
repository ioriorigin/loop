#!/usr/bin/env python3
"""BOOTH のカテゴリを「欲しいもの数」順に取り、上位の商品 JSON から wish_lists_count を取る。
robots: ../robots/booth.pm_*.txt（/terms /carts /cart のみ Disallow）。1 リクエストごとに 1.5 秒あける。
使い方: fetch_booth.py <カテゴリ名> <ページ数> <詳細を取る件数>
"""
import sys, re, html, json, time, urllib.parse, urllib.request, datetime
cat, pages, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
UA = {"User-Agent": "Mozilla/5.0 (loop market survey; github.com/ioriorigin/loop)"}
def get(u):
    time.sleep(1.5)
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode()
rows = []
for p in range(1, pages + 1):
    s = get(f"https://booth.pm/ja/browse/{urllib.parse.quote(cat)}?sort=wish_list&page={p}")
    ids = re.findall(r'data-product-id="(\d+)"', s)
    names = re.findall(r'data-product-name="([^"]*)"', s)
    prices = re.findall(r'data-product-price="([^"]*)"', s)
    for i, nm, pr in zip(ids, names, prices):
        rows.append([i, pr, html.unescape(nm)])
ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
out = open(f"booth-{cat}_{ts}.tsv", "w")
out.write("rank\tid\tlist_price\twish_lists_count\tprice_text\tshop\tname\n")
for k, (i, pr, nm) in enumerate(rows, 1):
    w = pt = shop = ""
    if k <= n:
        try:
            d = json.loads(get(f"https://booth.pm/ja/items/{i}.json"))
            w, pt, shop = d.get("wish_lists_count", ""), d.get("price", ""), d.get("shop", {}).get("name", "")
        except Exception as e:
            w = f"ERR:{e}"
    out.write(f"{k}\t{i}\t{pr}\t{w}\t{pt}\t{shop}\t{nm}\n")
print(out.name, len(rows))
