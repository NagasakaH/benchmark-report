# 来歴と公開データ

## 保存と公開範囲

実行場所のserverがraw証拠の正本です。終了時の171採点試行から派生JSON/Markdownを作成し、今回の公開版に必要なデータを移植しました。元の成績を変更せず、絶対パスを結果ディレクトリからの相対パスへ正規化しています。

| ファイル | 内容・検証できること |
| --- | --- |
| [aggregate.json](../reports/terminal-bench-20261007/data/aggregate.json) | モデル別の集計・元監査の結果 |
| [trials.json](../reports/terminal-bench-20261007/data/trials.json) | 全171件のreward、repetition、例外、時間、準備条件、資源要約、Harbor token |
| [api-audit.json](../reports/terminal-bench-20261007/data/api-audit.json) | 全1,613件のusage、TTFT、出力時間、timings、metrics差分、保存SSE監査フラグ |
| [tasks-manifest.json](../reports/terminal-bench-20261007/data/tasks-manifest.json) | 事前固定20課題、commit、公式制限、instruction hash |
| [source-sha256.json](../reports/terminal-bench-20261007/data/source-sha256.json) | 元のraw監査に使用した3,760ファイルのハッシュ。本文は非公開 |
| [source-manifest.json](../reference/harness/source-manifest.json) | 公開参照コードのserver原版/公開版ハッシュと変換 |
| [PUBLICATION_SHA256.json](../PUBLICATION_SHA256.json) | 公開ファイル自体のSHA256（この一覧自体を除く） |

元の監査は19課題oracle合格、171公式rewardとの一致、schedule_label一意、1,613上流要求の固定パラメータ、raw SSEのJSON/error/DONE/finish/usage、Strata timingsと保存値一致を確認しました。元監査の全SSE検査は歴史的な反復検知ポリシーを再実行するものではありません。既知の反復ガード修正には別途CPU回帰テスト/保存応答再生があります。

公開JSONに含む`audit.passed`や`done`は保存された監査記録です。raw本文を同梱しないため、これだけで第三者が同じSSE検証を独立に繰り返せるわけではありません。`source-sha256.json`は元証拠が別途提供された場合の照合用で、hashだけで内容の正しさを証明するものではありません。

公開スクリプトで再現できるのは、数値の集計、構造上の整合性、公開コードhash、ローカル文書リンク、モックによる安全処理/streamテストです。元telemetryの全標本がないのでWhの元標本からの積分は再現できず、試行別積分値の合計を検算します。

rawプロンプト・task instruction本文・oracle解答・model出力・資格情報・運用サービスの内部ログを含めていません。文書中の復旧履歴のserver証拠パスは非公開原本を指し、GitHub上のリンクではありません。モデル重みや第三者ソフトウェア、課題の権利/利用条件は各配布元に従います。

## 終了状態

2026-10-08 13:43 JST、19課題171試行でrunner正常終了、9件保留。所有idleモデルunload、両GPU解放、通常サービスHTTP200、全モデルunloadedを確認。監視automationはPAUSED。公開作業は推論・ベンチ再実行を伴っていません。
