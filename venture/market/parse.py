import re, sys, html

path = sys.argv[1]
raw = open(path, encoding='utf-8', errors='replace').read()
chunks = re.split(r'(?=<div[^>]*data-component-type="s-search-result")', raw)
res, seen = [], set()
for c in chunks:
    m = re.search(r'data-asin="([A-Z0-9]{10})"', c)
    if not m or m.group(1) in seen:
        continue
    asin = m.group(1); seen.add(asin)
    t = re.search(r'<h2[^>]*>.*?<span[^>]*>(.*?)</span>', c, re.S)
    title = html.unescape(re.sub(r'<[^>]+>', '', t.group(1))).strip() if t else '?'
    r = re.search(r'5つ星のうち([0-9.]+)', c)
    rating = r.group(1) if r else None
    rc = re.search(r'aria-label="([\d,]+)\s*レーティング"', c)
    reviews = rc.group(1) if rc else None
    jp = re.search(r'JPY\xa0([\d,]+)が請求されます', c)
    usd = re.search(r'<span class="a-offscreen">USD\xa0([\d.]+)</span>', c)
    ku = ('Kindle Unlimited' in c) or ('読み放題' in c) or ('kindle-unlimited' in c.lower())
    d = re.search(r'a-color-secondary a-text-normal">(\d{4}/\d{1,2}/\d{1,2})<', c)
    pub = d.group(1) if d else None
    res.append(dict(asin=asin, title=title[:70], rating=rating, reviews=reviews,
                    jpy=jp.group(1) if jp else None, usd=usd.group(1) if usd else None,
                    ku=ku, pub=pub))
print(f"{'ASIN':<11}{'JPY':>7} {'USD':>7} {'★':>4} {'件':>6}  KU  {'刊行':<11} 題名")
for o in res:
    print(f"{o['asin']:<11}{(o['jpy'] or '-'):>7} {(o['usd'] or '-'):>7} {(o['rating'] or '-'):>4} {(o['reviews'] or '-'):>6}  {'Y' if o['ku'] else 'N'}   {(o['pub'] or '-'):<11} {o['title']}")
print(f"--- {len(res)} items")
