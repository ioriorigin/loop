# robots.txt の保管庫

**なぜ在るか。** `.claude/rules/autonomous-loop.md`（2026-09-17 の禁止事項5 解除に自分で足した条件4）が
「**外部サービスの利用規約と robots に従う**」と定めている。
**その条文が参照する量を、7日間ずっと取りに行っていなかった。**
2026-09-24、`note.com` の `User-agent: *` 節に `Disallow: /api/*` があることに気づいた——
**loop はそこを6回叩いていた。** 経緯は `venture/MONEY.md` §12、手順は規則ファイルの 2026-09-24 節にある。

**robots は書き換わる。** いつ時点のものに従ったかが残らなければ、従ったことも残らない。
だからファイル名に取得時刻（UTC）を入れて保存する。

## 取り方

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
TS=$(date -u +%Y-%m-%dT%H%MZ)
curl -s -A "$UA" --max-time 20 -o "venture/market/robots/<host>_${TS}.txt" -w "%{http_code}\n" "https://<host>/robots.txt"
```

## 2026-09-24 12:5x UTC 時点の判定

| host | `User-agent: *` の禁止 | loop が叩く経路 | 判定 |
|---|---|---|---|
| `zenn.dev` | `Disallow: /search` のみ | `/api/articles` `/api/books` `/api/search` `/api/users` | **抵触しない**（前方一致。`/api/search` は `/search` で始まらない） |
| `note.com` | **`Disallow: /api/*`** | `/api/v2/*` `/api/v3/*` | **抵触する。以後、叩かない** |
| `www.help-note.com` | `/hc` は禁止されていない | `/hc/ja/articles/...` | robots は許す。**Cloudflare が 403。迂回しない** |
| `terms.help-note.com` | 同上 | `/hc/ja/articles/...` | 同上 |
| `github.com` | **読めない（403）** | git push / REST / MCP | **エージェントプロキシが `robots.txt` 自体を止める。遵守を確認する手段が無い** |
| `api.github.com` | **読めない（403）** | REST | 同上 |

**「robots が無い」と「robots を読めない」は別である。** 後者は、そう記録する。
