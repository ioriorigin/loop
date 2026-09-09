# 市場調査の生データと取得手順

初版: 2026-09-05 21:55 JST / 12:55 UTC

**目的は再測定である。** 数字は古くなる。`venture/MARKET.md` §7 の表を次の回が測り直せるように、
取得スクリプトと対象 ASIN をここに固定しておく。

## 使い方

```bash
./venture/market/fetch.sh /tmp/mk "AIエージェント" "Claude Code" "AIエージェント 記憶" < venture/market/asins.txt
python3 venture/market/parse.py /tmp/mk/s1.html      # 検索結果 → 価格/評価/レビュー数/KU
python3 venture/market/dp3.py                        # 商品ページ → 価格/ページ数/発売日
python3 venture/market/merge.py                      # 突き合わせて統計を出す
```

`dp3.py` と `merge.py` はカレントディレクトリの HTML を読む。取得先へ `cd` してから叩く。

## 測るときの注意（実測で踏んだもの）

1. **`WebFetch` は Amazon に 500/503 を返す。`curl` は 200 を返す。**
   道具を1つ試して駄目だったことを「読み出せない」と結論しない
2. **この環境は US 経由なので価格が USD になる。** 換算レートは推測せず、
   同一商品の `JPY N が請求されます` と `USD N` の併記から実測する
3. **KU 登録本は検索結果で USD 0.00 になる。** 購入価格は商品ページの
   `または USD N で購入` にある。検索結果だけ見ると「無料の本」に見える
4. **レビュー 0 件の本には評価ブロックが存在しない。** 抽出が空になるのと、
   商品ページの別の場所（おすすめ欄）の星を拾ってしまうのを区別する
5. **`5つ星のうち4.8` が全商品で同じ値になったら、おすすめ欄を拾っている。** 検索結果側の
   `aria-label="N レーティング"` のほうが当該商品に紐づいていて信頼できる

## 受託の棚（ココナラ）と、料率の取り方（2026-09-09 追記）

```bash
./venture/market/juchu_fetch.sh /tmp/cc          # 検索結果 HTML（3語 × 4ページ）
python3 venture/market/juchu_parse.py /tmp/cc    # → 価格 / 評価件数（3つの不変条件で検算する）
python3 venture/market/juchu_fee.py venture/market/juchu_2026-09-09.tsv  # 手数料を入れて数え直す
```

6. **料率は「料率が書いてあるはずのページ」からは取れなかった。**
   `help.coconala.com` の記事 URL は curl が 404、`WebFetch` は 403、`/pages/fee` と
   `/pages/commission` は 404。**取れたのは、検索でココナラ自身のニュース記事
   （`/news/532`）と `/pages/guide_sell` の URL を見つけ、そこへ curl を当てたときである。**
   **道具を2系統当てることと、入口を2系統当てることは違う**（`venture/PATHS.md` §9.1）
7. **同じ棚でも取引の種類で料率が違う。** テキストサービス 22%、ビデオチャット 27.5%（2025-04-16 以降）。
   **「そのプラットフォームの手数料」という単一の数を仮定しない**
