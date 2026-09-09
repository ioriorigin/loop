#!/usr/bin/env python3
"""ココナラの検索結果から、出品の価格と評価件数を取り出す。

なぜ評価件数まで取るか。**価格だけ見ると「売れているか」が分からない。**
2026-09-05 の Amazon の棚で、レビュー0件の本に星が付いた表が出たとき、
数字の大小ではなく **2欄の関係の破れ**で抽出器の嘘に気づいた。同じ形の検算をここでも持つ。

抽出したものは3つの不変条件で検算する（破れたら、その行は捨てずに **数える**）。
  1. 価格は正の整数で、ココナラの下限 500 円以上（規約上の最低出品価格）
  2. 1ページの出品数は 60 件（検索結果の1ページの定員。**実測して置いた。想定は 20 だった**）
  3. 評価件数が 0 の出品に、星の点数が付いていない

usage: juchu_parse.py <html ディレクトリ>
"""
import re
import sys
import glob
import os
import statistics

ITEM = 'c-serviceListItemRow'
PRICE = re.compile(r'c-serviceListItemColContentFooterPrice_price.*?<strong[^>]*>([\d,]+)</strong>', re.S)
RCNT = re.compile(r'c-serviceListItemColContentFooterPriceRating_count[^>]*>\s*\((\d+)\)', re.S)
RSCORE = re.compile(r'c-serviceListItemColContentFooterPriceRating_score[^>]*>\s*([\d.]+)', re.S)
SID = re.compile(r'href="/services/(\d+)"')
TITLE = re.compile(r'c-serviceListItemColContentHeader_title[^>]*>\s*(.*?)\s*</', re.S)


def parse(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    rows = []
    for chunk in s.split(ITEM)[1:]:
        mp = PRICE.search(chunk)
        if not mp:
            continue
        sid = SID.search(chunk)
        cnt = RCNT.search(chunk)
        sc = RSCORE.search(chunk)
        ttl = TITLE.search(chunk)
        rows.append({
            'id': sid.group(1) if sid else None,
            'price': int(mp.group(1).replace(',', '')),
            'reviews': int(cnt.group(1)) if cnt else 0,
            'score': float(sc.group(1)) if sc else None,
            'title': re.sub(r'<[^>]+>', '', ttl.group(1))[:60] if ttl else '',
        })
    return rows


def main():
    d = sys.argv[1]
    all_rows, per_page, broken = {}, [], {'price': 0, 'star0': 0}
    for f in sorted(glob.glob(os.path.join(d, 'cc_*.html'))):
        rows = parse(f)
        per_page.append((os.path.basename(f), len(rows)))
        for r in rows:
            if r['price'] < 500:
                broken['price'] += 1
                continue
            # レビュー0件に星が付いていたら、その行は別々の出品から拾っている
            if r['reviews'] == 0 and r['score'] is not None:
                broken['star0'] += 1
                continue
            if r['id']:
                all_rows[r['id']] = r

    print('# ページごとの抽出件数（1ページの定員は 60）')
    for name, n in per_page:
        print(f'  {name}  {n}' + ('' if n == 60 else '   <-- 定員と違う'))
    print(f'\n# 不変条件を破った行: 価格 < 500 が {broken["price"]} 件 / '
          f'レビュー0件に星 が {broken["star0"]} 件')

    rows = list(all_rows.values())
    v = sorted(r['price'] for r in rows)
    sold = [r for r in rows if r['reviews'] > 0]
    vs = sorted(r['price'] for r in sold)
    print(f'\n# 重複を除いた出品 {len(rows)} 件')
    print(f'  価格   中央値 {statistics.median(v):,.0f} 円 / 平均 {statistics.mean(v):,.0f} 円 '
          f'/ 最小 {v[0]:,} / 最大 {v[-1]:,}')
    print(f'  四分位 25% {v[len(v)//4]:,} / 75% {v[3*len(v)//4]:,}')
    print(f'  レビュー 中央値 {statistics.median([r["reviews"] for r in rows]):.0f} 件 / '
          f'0 件の出品 {sum(1 for r in rows if r["reviews"] == 0)} 件')
    if vs:
        print(f'\n# **レビューが1件以上ある出品だけ**（＝1件でも売れた証拠がある棚） {len(vs)} 件')
        print(f'  価格   中央値 {statistics.median(vs):,.0f} 円 / 平均 {statistics.mean(vs):,.0f} 円 '
              f'/ 最小 {vs[0]:,} / 最大 {vs[-1]:,}')
        print(f'  四分位 25% {vs[len(vs)//4]:,} / 75% {vs[3*len(vs)//4]:,}')
        tot = sum(r['reviews'] for r in sold)
        print(f'  レビュー総数 {tot} 件 / 出品あたり中央値 '
              f'{statistics.median([r["reviews"] for r in sold]):.0f} 件')

    # 必要件数（1,350,000 円 / 粗利）。
    # **手数料は測れなかった**（curl も WebFetch も料率のページに届かない。403/404）。
    # だから **fee = 0 の下界**で出す。手数料は必要件数を増やす方向にしか効かないので、
    # 下界で桁が決まるなら、実際の料率が何であっても桁は変わらない。
    # PATHS.md §3 が note / Zenn に対して使ったのと同じ論法である。
    # 推測値を置くのと下界を置くのは違う。推測は結論を両方向へ動かすが、下界は片方向にしか使えない。
    fee = 0.0
    need = {}
    print('\n# 年 1,350,000 円に必要な件数（**手数料ゼロの下界**。実際はこれ以上必要になる）')
    for label, val in [('全体の中央値', statistics.median(v)),
                       ('売れた棚の中央値', statistics.median(vs) if vs else 0),
                       ('全体の 75 パーセンタイル', v[3 * len(v) // 4]),
                       ('全体の 90 パーセンタイル', v[int(0.9 * len(v))]),
                       ('置き値 50,000', 50000),
                       ('置き値 150,000', 150000)]:
        if not val:
            continue
        g = val * (1 - fee)
        n = 1350000 / g
        need[label] = n
        print(f'  {label:24s} 単価 {val:>9,.0f} 円  粗利 {g:>9,.0f} 円  '
              f'必要 {n:>7.1f} 件/年  ({n / 12:.1f} 件/月)')

    # **必要件数を、棚が実際に達成している取引数と突き合わせる。**
    # 評価件数は「生涯の取引数」の下界である（全員が評価を書くわけではない）。
    # ここで比べるのは「年あたりの必要件数」対「**生涯**の評価件数」なので、
    # **棚の側に一方的に有利な比較**になっている。それでも届かないなら、結論は強い。
    rv = sorted((r['reviews'] for r in rows), reverse=True)
    print(f'\n# 棚が実際に積んだ取引数（評価件数。**生涯**の値で、年あたりではない）')
    print(f'  最大 {rv[0]:,} / 90% {rv[int(0.1*len(rv))]:,} / 75% {rv[int(0.25*len(rv))]:,} / '
          f'中央 {rv[len(rv)//2]:,}')
    for label in ('全体の中央値', '置き値 50,000', '置き値 150,000'):
        if label not in need:
            continue
        n = need[label]
        k = sum(1 for x in rv if x >= n)
        print(f'  {label:16s} の必要件数 {n:6.1f} 件/年 を、**生涯**で超えている出品は '
              f'{k:>3} / {len(rv)} 件 ({100*k/len(rv):.1f}%)')

    # **価格と件数を別々に見ると、両方とも届いて見える。** 高い出品と、よく売れる出品が
    # 同じ出品だとは限らない。だから**同じ行の上で**掛ける。
    # 価格 x 評価件数 = その出品が生涯に積んだ売上の下界（評価を書かない購入者がいるので下界）。
    print('\n# **同じ出品の上で**掛けた生涯売上（価格 x 評価件数。手数料ゼロの下界）')
    life = sorted((r['price'] * r['reviews'] for r in rows), reverse=True)
    for th, name in [(1350000, '年 135 万円'), (675000, 'その半分'), (135000, 'その 1/10')]:
        k = sum(1 for x in life if x >= th)
        print(f'  **生涯**で {th:>9,} 円を超えた出品: {k:>3} / {len(life)} 件 '
              f'({100*k/len(life):.1f}%)   [{name}]')
    print(f'  生涯売上の中央値 {life[len(life)//2]:,} 円 / '
          f'75% {life[int(0.25*len(life))]:,} 円 / 90% {life[int(0.1*len(life))]:,} 円 / '
          f'最大 {life[0]:,} 円')


if __name__ == '__main__':
    main()
