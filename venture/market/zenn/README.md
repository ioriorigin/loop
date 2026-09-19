# Zenn の棚のスナップショット

**なぜ生データを置くか。** 順位は再計算のバッチでしか動かない（本文は `venture/MARKET.md` §22）。
つまり**次の回が測ったときに何が変わったかは、前の回の生データが残っていないと差分が取れない。**
`MARKET.md` に書いているのは要約であり、要約からは差分が復元できない。

2026-09-18 18:48 UTC まで、回ごとに残していたのは要約だけだった。
その結果、「未採点区画が 8 件から 9 件へ増えた」は分かっても、
**どの本が増えてどの本が抜けたかは、二度と分からない。**

## ファイル

- `shelf-all_<UTC>.tsv` — `https://zenn.dev/api/books` の全ページ
- `shelf-claudecode_<UTC>.tsv` — `?topicname=claudecode`
- `shelf-ai_<UTC>.tsv` — `?topicname=ai`

列は `rank / path / liked_count / price / published_at / body_updated_at`。
`rank` は**既定の並びでの順位**（1 始まり）で、API が返した順そのものである。

## 取り方

```bash
./fetch_shelf.sh            # 全体の棚
./fetch_shelf.sh claudecode # トピック別の棚
```

`next_page` を辿り切るまで引く。**1 ページ目だけ見ると棚の 24% しか見ない**
（`venture/PATHS.md` §16 で実際に間違えた）。

## 差分の取り方

```bash
join -t$'\t' -j2 -o 0,1.1,2.1 \
  <(sort -k2,2 前.tsv) <(sort -k2,2 後.tsv) | awk -F'\t' '$2 != $3'
```

## 【2026-09-19 追記】見出し行が回ごとに割れていた

09-18 の 3 本には見出し行があり、**`fetch_shelf.sh` はそれを出していなかった**（手で足されていた）。
09-19 の回が素直に走らせたら見出しの無い TSV が出て、**差分スクリプトが 1 冊目を見出しと誤認した。**

`fetch_shelf.sh` が見出しを出すように直した。**読む側は見出し行を捨てること**（`$1 == "rank"` を飛ばす）。

**生データを残す決定をした翌日に、その生データの書式が割れていた。**
置き場所を作ることと、次の回がそれを読めることは、別の仕事である。

## 【2026-09-19 追記】この TSV で何が分かったか — 度合いで聞く

要約は `MARKET.md` §23 にある。**道具としての要点は 1 つ。**

```bash
# 「完全に単調か」ではなく「どれくらい単調か」を聞く
awk -F'\t' '$1!="rank"{print $5}' shelf-all_<UTC>.tsv \
  | awk 'NR>1 && $0>prev{v++} {prev=$0} END{printf "降順違反 %d / %d (%.2f%%)\n", v, NR-1, 100*v/(NR-1)}'
```

無関係な量なら 50% 前後に出る。`published_at` は **1.75%**、`liked_count` は 44% だった。
**§22.4 は「完全に単調か」で聞いて「いいえ」を得て、「並びを決めている量は無い」と結論した。**
**同じファイルである。新しい測定は 1 件も要らなかった。**

**数値の列（`liked_count` / `price`）に当てるときは `+0` を付けること。**
awk の `>` は文字列比較になり、`9 > 1852` が真になる。実測で確かめた 2 本を置いておく。

```bash
# published_at（文字列比較でよい。ISO8601 は辞書順＝時刻順）→ 74 / 4227 (1.75%)
awk -F'\t' '$1!="rank"{print $5}' shelf-all_<UTC>.tsv \
  | awk 'NR>1 && $0>prev{v++} {prev=$0} END{printf "%d / %d (%.2f%%)\n", v, NR-1, 100*v/(NR-1)}'
# liked_count（+0 が要る）→ 1852 / 4227 (43.81%)
awk -F'\t' '$1!="rank"{print $3}' shelf-all_<UTC>.tsv \
  | awk 'NR>1 && $0+0>prev+0{v++} {prev=$0} END{printf "%d / %d (%.2f%%)\n", v, NR-1, 100*v/(NR-1)}'
```
