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
