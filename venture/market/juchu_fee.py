#!/usr/bin/env python3
"""ココナラの棚の分布を、**手数料を入れた閾値**で数え直す。

なぜ要るか。`venture/PATHS.md` §7.4 は「生涯売上（下界）が ¥1,350,000 を超えた出品」を
45 / 673 件（6.7%）と数えた。**この閾値には手数料が入っていない。**
目標 135 万円は loop の手取りであり、価格 × 評価件数は**販売総額**である。
同じ §7.2 で「手数料は必要件数を増やす方向にしか効かない」と自分で書きながら、
**必要件数の表にだけ適用して、分布の側には適用していなかった。**

料率は 2026-09-09 に一次情報から取れた（`juchu_2026-09-09.tsv` の取得時は取れなかった）。
  https://coconala.com/news/532        「販売時の手数料の料率を…一律 22%（税込）に改定」
  https://coconala.com/pages/guide_sell「手数料率(22%)をかけた額が販売総額から差し引かれます」

**点推定を1つだけ置かない。** 実測の 22% を中心に、0% / 10% / 27.5%（ビデオチャットの料率）を並べる。

usage: juchu_fee.py <tsv>
"""
import sys
import statistics

TARGET = 1_350_000  # 年 135 万円（loop の手取り）
FEES = [0.0, 0.10, 0.22, 0.275]


def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or line.startswith("service_id"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        rows.append((int(parts[1]), int(parts[2])))
    return rows


def main():
    rows = load(sys.argv[1] if len(sys.argv) > 1 else
                "venture/market/juchu_2026-09-09.tsv")
    n = len(rows)
    gross = [(p * r, p, r) for p, r in rows]
    print(f"n = {n} 件\n")

    print("| 手数料 | 手取り {:,} 円に要る販売総額 | 到達した出品 | 割合 | 到達集団の価格中央値 |"
          .format(TARGET))
    print("|---|---|---|---|---|")
    for f in FEES:
        need = TARGET / (1 - f)
        hit = [g for g in gross if g[0] >= need]
        med = statistics.median([g[1] for g in hit]) if hit else float("nan")
        print("| {:.1f}% | ¥{:,.0f} | {} / {} 件 | {:.1f}% | ¥{:,.0f} |"
              .format(f * 100, need, len(hit), n, 100 * len(hit) / n, med))

    print()
    print("| 手数料 | 1件あたりの手取り（表示価格 ¥50,000） | 必要件数/年 | 中央値 ¥10,000 なら |")
    print("|---|---|---|---|")
    for f in FEES:
        net50 = 50_000 * (1 - f)
        net10 = 10_000 * (1 - f)
        print("| {:.1f}% | ¥{:,.0f} | {:.0f} 件 | {:.0f} 件 |"
              .format(f * 100, net50, -(-TARGET // net50), -(-TARGET // net10)))


if __name__ == "__main__":
    main()
