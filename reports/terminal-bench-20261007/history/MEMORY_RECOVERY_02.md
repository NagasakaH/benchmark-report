> 実行当時の履歴。文中のserver証拠パスは非公開原本を指す。現在の状態は[最終報告](../REPORT.md)を参照。

# 2回目の資源停止後の復旧手順

2026-10-07 21:18 JST以降。`SWAP_RECURRENCE.md`の解析に基づく条件変更であり、同じ起動条件の再試行ではない。

## 1. 残留swapの解消（1回のみ実施）

全推論コンテナ停止、runnerロック獲得、GPU-FAULTなし、MemAvailable約88GiBを確認。swap対象が`/swap.img` 8GiB・優先度-1だけであることを確認したうえで、約0.5GiBの退避ページを`swapoff /swap.img`でRAMへ戻し、finallyで`swapon /swap.img`を実行。同じ容量・優先度で再有効化、使用量0を確認。LibreChat/Mongo等のプロセスは停止していない。sysctl・fstab・BIOS・ドライバー変更なし。証拠はserver `memory-recovery-02/swap-return.json`。

これは本試験中に繰り返す自動swap清掃ではない。以降のswap上限512MiBは維持し、再発時は解析へ戻る。

## 2. 推論前のメモリ準備

各試行の前に、直前の既済ベンチモデルだけが稼働し、要求がないことを確認してrouterのモデル指定unload APIで解放する。別モデルや使用中の要求を検出したら新規負荷を止める。推論コンテナなし・両GPU VRAM100MiB未満を2回確認する。

その後、この比較で使うIQ3/IQ4/27B本体・draftの6ディレクトリ内の1MiB超ファイルにだけPOSIX_FADV_DONTNEEDを適用。ファイル削除・全体drop_cachesはしない。MemFree70GiB以上と従来の資源ガードを確認した後にモデル要求を開始する。before/released/afterとファイル一覧は各runの`memory-preparation.json`へ保存。

全モデルに同じ境界処理を適用するが、過去8試行とは起動前キャッシュ条件が異なる。既済の成績は保持し、起動時間・切替時間の比較は条件別に示す。ゲームベンチの条件とも同一ではない。

## 3. 安全テストと検証

`scripts/test_terminal_bench_memory.py`の4テスト（別モデルを止めない、busyモデルを止めない、対象ファイルのみadviceし削除しない、空きRAM不足で起動を拒否）はMac/serverとも成功。

`--memory-recovery-probe`は中断したIQ3 r3だけを新規課題環境で実行する。証拠ラベルは`openssl-selfsigned-cert-iq3-r3-memory-recovery02`、初期PID2223107。元runを上書きしない。完了後はstate=pilot_complete, recovery_probe=memory02となる。API・資源・採点をレビューするまで残り全体へ自動移行しない。不正解でも環境が正常なら成績として保持する。根本原因の解決は未証明。

## 検証結果と再開

IQ3 r3代替はreward1、API4件すべて完全SSE、実行94.40秒、swap最大26.828MiB、MemAvailable最小38.369GiBで完了。既済9/180となった。server `memory-recovery-02/review.json`と`probe-status.json`に保存。

さらにidleなIQ3を正式モデル指定unload APIで解放し、HTTP200・推論コンテナなし・VRAM解放後に対象ファイルcacheを準備する実動作を確認。MemFree88.113GiB、swap26.828MiB。`memory-recovery-02/unload-integration/memory-preparation.json`へ保存。

この証拠に基づき残り171試行を再開する。以後の記録は`preparation_s`（前モデル解放/cache準備）と`elapsed_s`（Harbor起動〜採点終了）、その合計を分ける。oracle検証時間は別。今回の代替試行では準備時間はmemory-preparation.jsonの時刻差から取得できる。swap回収は再実行しない。長時間での有効性はこれから確認する。
