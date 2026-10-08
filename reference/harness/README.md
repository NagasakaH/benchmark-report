# 実行コードの公開参照版

今回serverで使った最終版とローカル版のSHA256を照合したコードを収録しています。初期から最終版まで同一コードで走ったという意味ではありません。[条件変更](../../docs/limitations.md)と合わせて参照してください。

- `terminal_bench_runner.py`: 逐次実行、oracle、準備、監視、採点、drain。
- `terminal_bench_relay.py`: 非stream→SSE→非stream adapterと計測。
- `terminal_bench_stream.py`: 入力に根拠のあるinline hex引用例外v2。
- `terminal_bench_watchdog.py`: 独立監視。
- `terminal_bench_apt_https.py`: agentツール導入の限定対策。
- `terminal_bench_aggregate.py`: 非公開raw証拠一式を監査した集計コード。
- `iq3s_stability_replay.py`: 元の共通helperから`StopRun`、`repetition_reason`、`StreamEvidence`だけを変更せず抽出。無関係な旧replay runnerは含めていません。
- `test_terminal_bench_*.py`: モックによる4件のメモリ準備テスト＋13件のstreamテスト。

公開時にホストrootを`/opt/benchmark`、routerのLANアドレスをloopbackへ置換しました。認証キーの値は含めていません。置換前/後のhashと変換内容は[source-manifest.json](source-manifest.json)。パスやrouter、model aliases、所有コンテナ、GPU PCI位置、専用venv、監視service、モデル/draftディレクトリ、資格情報ファイル、公開CAなどに依存します。公開コードをそのまま実行して推論環境が再現できるわけではありません。

このアーカイブのaggregateは元のraw SSE・telemetry・Harbor結果一式を必要とします。公開データだけの検算には[recompute.py](../../scripts/recompute.py)を使ってください。

推論なしのテスト:

```sh
python3 -m unittest discover -s reference/harness -p 'test_terminal_bench_*.py'
```
