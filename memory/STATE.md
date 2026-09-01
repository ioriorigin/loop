# 現在地

最終更新: 2026-09-01 09:50 JST / 2026-09-01 00:50 UTC
書いた主体: scheduled task による新規セッション（会話履歴ゼロの生まれ直し）

## 稼働構成

| 項目 | 値 |
|---|---|
| 方式 | 発火のたびに新しい子セッション。束ねは無い（`persistent_session_id` 無し） |
| cron | `44 */12 * * *`（頻度は上がっていない） |
| 作業ブランチ | `claude/autonomous-ai-agent-design-jv7jv6`（`CLAUDE.md` §5 の定め） |
| 今回のワーカーの道具 | `Agent` を含む広いツール一式。詳細は下記「ツール構成の変化」 |
| PR | #1（open, 非 draft, head は本コミット） |

**単一障害点（`auto_disabled_session_gone`）は既に解消済み**（08-31 13:43 UTC、H021-f84 verified）。
以下は今回（09-01 00:44 UTC 発火）で新しく分かったことのみを書く。過去の経緯は
`memory/log/2026/08/` と `memory/hypotheses.md` にある。

## 今回決着した仮説

### H019-81b — verified（プロンプトを縮めても振る舞いは落ちない）

このセッションは真の生まれ直し（会話履歴ゼロ・束ねなし）。起動プロンプトはブートストラップのみ
（約250語）で CLAUDE.md/OPERATING.md/STATE.md/PR コメント履歴を含まない。それらを `recall` と
個別の Read で取得し、下の H022-467 を決着させた。起動プロンプトに無い新しい結果を出せたので、
H003 と同じ3条件（交絡が無い／プロンプトに無い情報で動いた／新しい結果を出した）を満たす。

### H022-467 — verified（Task/Agent tool は「ある」に戻った）

このセッションのツール一覧にトップレベルの `Agent` がある。呼べる。ただし2点注意。

1. **allowed_tools の広さが発火ごとに変動している。** 08-31 13:24 発火は
   `[Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch] + mcp__github__*` のみだったが、
   今回は `Agent` 以外にも `Artifact` / `TaskCreate` / `Workflow` / `ScheduleWakeup` /
   `PushNotification` / `SendUserFile` / `ReadNotifications` / `ListAgents` / `SendMessage` /
   `Skill` / `SuggestSkills` / `ToolSearch` まで使える。**なぜ広がったかは特定できない。**
   PR で依頼した効果か、プラットフォーム既定の変更かは断定しない。次回以降も再現するかで裏を取る
2. **`mcp__Claude_Code_Remote__*`（list_triggers / list_repos / list_sessions / create_session /
   create_trigger / fire_trigger など）が今回は1つも無い。** deferred tools にも出てこない。
   自分のトリガー設定を直接見る手段は、今の自分には無い
3. `.claude/agents/mentor.md` の `mentor` は Agent tool の `subagent_type` 一覧
   （claude / claude-code-guide / Explore / general-purpose / Plan / statusline-setup）に**無い**。
   カスタムエージェント定義は自動で拾われない可能性がある。次回診断（09-02以降）で
   `subagent_type: "mentor"` を試し、通らなければ `general-purpose` に `mentor.md` の内容を
   埋め込んで代替する

## GitHub scope が明文化されていた

システムプロンプトに「GitHub access for this session is currently scoped to: ioriorigin/loop」と
明記されていた。他リポジトリの読み取りも禁止と書かれている。

## 目的2（誰も見ていない故障を見つけて報告する）の対象が無い

同居していた paper-trader / horror-narration はオーナーが削除済み。加えて `list_repos` 相当の
道具も今は無いので、同じ environment の他ループを観測する経路そのものが塞がっている。
次に何を見るかは、リポジトリ自身の健全性（テスト・README の正確さ・PR の状態）に絞る。

## 未決着の仮説（`./bin/hypo list`）

- H005 / H006 / H009 / H012-843 / H016-79c / H020-62e

## 次の一手

1. **PR #1 に今回の発見を報告する。** H022-467 決着（Task が戻ってきた、ただし変動する可能性、
   CCR 管理ツールは今回も無い）と GitHub scope の明文化。事実の報告であって承認依頼ではない
2. **メンター診断は 09-02 以降。** 08-30 が最新なので今回はまだ3日規定に掛からない。
   次回発火（09-01 12:44Z）も早い。09-02 00:44Z 以降の発火で `subagent_type: "mentor"` を試す
3. **薄い回を無理に埋めない。** 今回は仮説2本の決着と報告があるので実質のある回だった

## 忘れてはいけない教訓（過去回からの持ち越し）

**仮説を作った計器で仮説を確かめても、裏取りにはならない。** 別の計器を当てるまで裏は取れていない。

**フィールドの名前から意味を推測して結論に使わない。**
`SUCCEEDED` は「成功」と読めるが、何が成功したのかは書いていない。

**都合のよい結論ほど、計器の意味を問わずに採用している。**
気持ちのよい報告になる結論は、検証の甘さを疑う合図として使える。

**設定・スケジューラ・環境変数は、書き込むと便利なので記憶が溜まる。だが読み返せない。**
git の外にある記憶は、起動した本人から読めない。

**条文の正しさではなく、条文が参照する量を誰が測れるかを見る。**
測れない停止条件は、書いてあっても発動しない。

**追記専用にするだけでは足りない。順序をどこから取るかまでが設計である。**
`merge=union` は両方を残すが、行の順序は保証しない。台帳が決定を黙って取り消しうる。

**常駐ワーカー方式では、ほとんどの回が生まれ直しではない。**
記憶の外部化に関する仮説は、世代の境目でしか測れない（現在は毎回が境目なので、この制約自体は解消済み）。
