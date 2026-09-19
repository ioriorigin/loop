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

## 【2026-09-19 12:5x UTC 追記】記事の棚を足した。そして**違反率だけでは棚を区別できない**

- `articles-<topic>_<UTC>.tsv` — `https://zenn.dev/api/articles?topicname=...` の全ページ
- 取り方: `./fetch_articles.sh claudecode`
- 列は `rank / path / id / liked_count / bookmarked_count / comments_count / body_letters_count / article_type / principal_type / published_at / body_updated_at`

**本の棚と違う点が2つある。読む前に知っておくこと。**

1. **記事の API は 100 ページ（4800 件）で打ち切られる。** `page=101` は空を返す。
   **4800 行ちょうどで終わったら、それは全数ではなく上限である**（本の棚 4228 件は全数だった）。
   `fetch_articles.sh` はその場合に警告を出す
2. **`published_at` の降順違反率は 1.6% で、本の棚（1.75%）とほぼ同じである。**
   **にもかかわらず、順位相関は本が −0.81、記事が −0.04 で正反対である。**
   本の棚は大域的に日付降順、記事の棚は**日付降順の走りを 77 本つないだ列**で、
   走りの間は反応の多い順に階層化されている（`MARKET.md` §24）

**つまり、上の awk（違反率）を記事の棚に当てると、本の棚と同じ数字が出て、同じ構造だと読める。違う。**
**違反率は局所の量で、順位相関は大域の量である。片方だけでは棚の形が決まらない。**

```bash
# 走りの数を数える（局所と大域の食い違いは、これで見える）
awk -F'\t' '$1!="rank"{print $10}' articles-claudecode_<UTC>.tsv \
  | awk 'NR>1 && $0>prev{r++} {prev=$0} END{printf "走り %d 本 / %d 件（全部日付順なら1本・無作為なら約 %d 本）\n", r+1, NR, (NR+1)/2}'
```
