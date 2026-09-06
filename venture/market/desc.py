# 商品ページから「レビュー数・星・紹介文」を取り、紹介文の特徴を機械判定する。
#
# **当て先を間違えると全件が同じ値になる**（2026-09-06 実測）。
#   - 素朴な `5つ星のうち([\d.]+)` は関連商品カルーセルの星に当たり、全15冊が ★4.2 になった
#   - レビュー数は `acrCustomerReviewText`、星は `acrPopover` の title 属性が正しい印
#   - **要素ごと存在しないのが「0 件」である。** 値 0 と欄の不在を同じに読んではいけない
# 検算: 出た数字が venture/MARKET.md §7（検索結果ページ由来）と一致するか見る。
#
# usage: cd <dp_*.html のあるディレクトリ> && python3 desc.py
import re, glob, html, json

def flat(s):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))).strip()

# 特徴の定義は上位2件を読んだ後に作った。事後の当てはめであることを忘れないこと。
FEATS = {
    'シリーズの巻':   r'シリーズ|第\s*\d\s*巻|\d\s*巻目',
    '物語形式':       r'物語|ストーリー|わたしは|田中さん',
    '初心者向け':     r'非エンジニア|初心者|プログラミング(知識|歴)?\s*(ゼロ|は前提にしません)|素人|小学生',
    '読者を列挙':     r'こんな方におすすめ|以下のような方|おすすめです',
    '目次を掲載':     r'【目次】|目次 第1章|第1章 ',
}

rows = []
for f in sorted(glob.glob('dp_*.html')):
    asin = re.search(r'dp_(\w{10})', f).group(1)
    raw = open(f, encoding='utf-8', errors='replace').read()
    t = re.search(r'<span id="productTitle"[^>]*>(.*?)</span>', raw, re.S)
    rc = re.search(r'acrCustomerReviewText[^>]*>\s*\(?([\d,]+)', raw)
    st = re.search(r'id="acrPopover"[^>]*title="5つ星のうち([\d.]+)', raw)
    d = re.search(r'<div id="bookDescription_feature_div".*?'
                  r'(?=<div id="detailBullets|<div id="rich_product_information|<hr)', raw, re.S)
    desc = flat(d.group(0)) if d else ''
    rows.append(dict(asin=asin, title=flat(t.group(1)) if t else '?',
                     reviews=int(rc.group(1).replace(',', '')) if rc else 0,
                     stars=st.group(1) if st else None, desc=desc,
                     feats={k: bool(re.search(p, desc)) for k, p in FEATS.items()}))

json.dump(rows, open('desc_rows.json', 'w'), ensure_ascii=False, indent=1)
print(f"{'ASIN':<12}{'rev':>5} {'★':<5} " + ' '.join(FEATS))
for r in sorted(rows, key=lambda r: -r['reviews']):
    marks = ' '.join(('o' if r['feats'][k] else '.').ljust(len(k)) for k in FEATS)
    print(f"{r['asin']:<12}{r['reviews']:>5} {r['stars'] or '-':<5} {marks}  {r['title'][:34]}")
    # 内部矛盾の検算: レビュー 0 件に星は付かない
    if r['reviews'] == 0 and r['stars']:
        print(f"  ** 矛盾: レビュー 0 件なのに星がある。当て先を疑え（{r['asin']}） **")
