import re, glob, html, json
RATE = 3450/22.15
rows=[]
for f in sorted(glob.glob('dp_*.html'))+['dp1.html']:
    raw=open(f,encoding='utf-8',errors='replace').read()
    m=re.search(r'dp_(\w{10})\.html',f); asin=m.group(1) if m else 'B0HB5K3Q83'
    txt=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',raw)))
    t=re.search(r'<span id="productTitle"[^>]*>(.*?)</span>',raw,re.S)
    title=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',t.group(1)))).strip() if t else '?'
    pg=re.search(r'(\d{1,4})ページ',txt); pages=int(pg.group(1)) if pg else None
    d=re.search(r'発売日 : ?([0-9/]+)',txt) or re.search(r'発売日 ([0-9/]{8,10})',txt)
    date=d.group(1) if d else None
    buy=re.search(r'または USD\s*([\d.]+)',txt)
    usd=float(buy.group(1)) if buy else None
    rows.append(dict(asin=asin,title=title,pages=pages,date=date,usd=usd,
                     jpy=int(round(usd*RATE/10)*10) if usd else None))
json.dump(rows,open('dp_rows.json','w'),ensure_ascii=False,indent=1)
for r in rows:
    print(f"{r['asin']}  ¥{str(r['jpy'] or '-'):<6} {str(r['pages'] or '-'):>4}p  {str(r['date'] or '-'):<10} {r['title'][:50]}")
