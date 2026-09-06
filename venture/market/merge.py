import re, json, html, glob, statistics as st
# search pages -> reviews/rating/ku
srev={}
for f in ['amz.html','s1.html','s2.html','s3.html','s4.html']:
    raw=open(f,encoding='utf-8',errors='replace').read()
    for c in re.split(r'(?=<div[^>]*data-component-type="s-search-result")', raw):
        m=re.search(r'data-asin="([A-Z0-9]{10})"',c)
        if not m: continue
        a=m.group(1)
        rc=re.search(r'aria-label="([\d,]+)\s*レーティング"',c)
        rt=re.search(r'5つ星のうち([\d.]+)',c)
        jp=re.search(r'JPY\xa0([\d,]+)が請求されます',c)
        ku=('Kindle Unlimited' in c) or ('読み放題' in c)
        prev=srev.get(a,{})
        srev[a]=dict(reviews=int(rc.group(1).replace(',','')) if rc else prev.get('reviews',0),
                     rating=rt.group(1) if rt else prev.get('rating'),
                     jpy_paid=int(jp.group(1).replace(',','')) if jp else prev.get('jpy_paid'),
                     ku=ku or prev.get('ku',False))
dp={r['asin']:r for r in json.load(open('dp_rows.json'))}
rows=[]
for a,d in dp.items():
    s=srev.get(a,{})
    rows.append(dict(asin=a,title=d['title'],pages=d['pages'],date=d['date'],
                     price=d['jpy'] or s.get('jpy_paid'),
                     reviews=s.get('reviews',0),rating=s.get('rating'),ku=s.get('ku')))
rows.sort(key=lambda r:(r['date'] or ''))
print("| # | 発売 | 価格 | 頁 | レビュー | ★ | 題名 |")
print("|---|---|---|---|---|---|---|")
for i,r in enumerate(rows,1):
    print(f"| {i} | {r['date'] or '?'} | ¥{r['price'] or '?'} | {r['pages'] or '?'} | **{r['reviews']}** | {r['rating'] or '—'} | {r['title'][:44]} |")
rv=[r['reviews'] for r in rows]; pr=[r['price'] for r in rows if r['price']]
pg=[r['pages'] for r in rows if r['pages']]
print()
print("n=",len(rows))
print("レビュー: 中央値",st.median(rv),"平均",round(st.mean(rv),1),"0件の冊数",sum(1 for x in rv if x==0),"分布",sorted(rv))
print("価格: 中央値",st.median(pr),"平均",round(st.mean(pr)),"分布",sorted(pr))
print("頁: 中央値",st.median(pg),"分布",sorted(pg))
