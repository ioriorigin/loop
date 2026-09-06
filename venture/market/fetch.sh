#!/usr/bin/env bash
# Amazon.co.jp から類書の一次データを取る。
#
# **WebFetch は Amazon 商品ページに HTTP 500/503 を返すが、curl は 200 を返す**（2026-09-05 実測）。
# 道具を1つ試して駄目だったことを「読み出せない」と結論しない。ここがその実例である。
#
# 注意: この環境は US 経由で出るので、価格は USD 表示になる。
#   - 有料本の検索結果には「JPY N が請求されます」が併記される（円の一次値）
#   - KU 登録本は検索結果では USD 0.00 になり、商品ページの「または USD N で購入」が購入価格
#   - 換算レートは同一商品の JPY 表示と USD 表示から実測する（推測しない）
#
# usage: ./fetch.sh <出力ディレクトリ> [検索語...]
set -eu
OUT="${1:?出力ディレクトリを指定}"; shift
mkdir -p "$OUT"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
i=0
for q in "$@"; do
  i=$((i+1))
  curl -s -o "$OUT/s$i.html" -w "s$i http=%{http_code} size=%{size_download} q=$q\n" \
    -A "$UA" -H "Accept-Language: ja-JP,ja;q=0.9" \
    --data-urlencode "k=$q" --data-urlencode "i=digital-text" -G "https://www.amazon.co.jp/s"
  sleep 2
done

# 商品ページは ASIN を標準入力から1行ずつ受け取る
if [ ! -t 0 ]; then
  while read -r asin; do
    [ -n "$asin" ] || continue
    curl -s -o "$OUT/dp_$asin.html" -w "$asin %{http_code} %{size_download}\n" \
      -A "$UA" -H "Accept-Language: ja-JP,ja;q=0.9" "https://www.amazon.co.jp/dp/$asin"
    sleep 1
  done
fi
