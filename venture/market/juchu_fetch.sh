#!/usr/bin/env bash
# 受託・請負の**単価**の一次データを取る。
#
# なぜ要るか。`venture/PATHS.md` §6 の限界4——「受託の単価 ¥50,000 / ¥150,000 は
# **一次情報から取っていない。置いた値である**」。閾値を通った3形のうち2形がこの置き値の上に立っていた。
#
# 取れる先と取れない先（2026-09-09 実測。**道具は2系統ずつ当てた**。OPERATING.md §7b）。
#   ココナラ  https://coconala.com/search   curl 200 / サーバ側で価格が描かれている  → 使う
#   ランサーズ https://www.lancers.jp/...    curl 405 / WebFetch も不可              → 使えない
#   クラウドワークス https://crowdworks.jp/  curl 200 だが**予算は JS 側**（円表記が2件しか無い） → 使えない
#
# **ココナラの表示価格は「そのサービスの最低プランの価格」である。** 実際の取引額はこれ以上になる。
# つまりこれは**下界**であり、必要件数の側から見ると**上界**（＝いちばん厳しい見積り）になる。
# 推測値を置くのとは向きが違う。下界は「これ以下では無い」方向にしか使えない。
#
# usage: ./juchu_fetch.sh <出力ディレクトリ>
set -eu
OUT="${1:?出力ディレクトリを指定}"
mkdir -p "$OUT"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# loop が実際に作れるものに寄せた検索語。棚を広く取るのではなく、
# **自分が出品しうる棚**を測る（PATHS.md の候補8・9 が想定しているのはそれである）。
i=0
for q in "システム開発" "業務自動化" "技術記事執筆"; do
  i=$((i+1))
  for p in 1 2 3 4; do
    curl -sL -o "$OUT/cc_${i}_${p}.html" \
      -w "cc_${i}_${p} http=%{http_code} size=%{size_download} q=${q} page=${p}\n" \
      -A "$UA" -H "Accept-Language: ja-JP,ja;q=0.9" \
      --data-urlencode "keyword=$q" --data-urlencode "page=$p" \
      -G "https://coconala.com/search"
    sleep 2
  done
done
