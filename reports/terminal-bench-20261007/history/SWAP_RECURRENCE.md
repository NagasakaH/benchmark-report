> 実行当時の履歴。文中のserver証拠パスは非公開原本を指す。現在の状態は[最終報告](../REPORT.md)を参照。

# 2026-10-07 21:07 JST: swapガードの再発（中間記録）

## 現状

本試験runner PID2177923は停止、state=needs_analysis。正常終了8/180試行、課題はまだopenssl-selfsigned-certのみ。IQ4 3/3合格、27B 3/3合格、IQ3 1/2合格。課題数不足・IQ3未完了のため能力順位は判断しない。IQ3 r2の元中断とr3の中断はモデル不正解に含めない。

## 確認できた事実

- IQ3 r3は起動前swap481.402MiB、ガード発火時512.754MiB。増加約31.35MiBで上限512MiBを超過した。前回の4.21GiBへの急増と同じ大きさではない。
- 発火時MemAvailable約40.51GiB、MemFree約0.78GiB、Cached約40.63GiB。MemAvailableの大きさだけでswap発生を否定できない。
- IQ3の5ファイルへのPOSIX_FADV_DONTNEEDは実施済み。しかし実行時点ではIQ4がまだ稼働中で、Cached約85.09→81.62GiB、MemFree約1.27→4.74GiBにとどまった。前の単独再検証のMemFree約88GiBという条件は再現していない。
- モデル停止後もswap約510MiBが残留。読み取り可能なプロセスのVmSwap合計は約490.67MiB。大きいものはLibreChat側MainThread約212MiB、gnome-shell約106.5MiB、mongod約79.8MiB。残留分を実行中モデルのswapと同一視しない。
- GPU-FAULTなし。kernelにSVM復元worker/遅延fputの長時間CPU処理警告はあるが、これだけでGPU障害の根本原因とは断定しない。
- HTTP500は資源ガードによる起動中モデルの停止後に記録された。元API、harbor、telemetry、cache-adviceは元runのまま保存。
- 推論・課題コンテナとrunnerは終了。router /health=200、/runningは空、両GPU VRAM約57.2MiB、負荷は観測時1→0%。LibreChatとMongoは稼働継続。

## 証拠

server正本 `swap-interruption-02/` にstatus、runnerログ、kernel/router/モデルログ、meminfo、process-swap、cleanup-healthを保存。元runは`runs/openssl-selfsigned-cert-iq3-r3/`。

## 続行条件

現方式で自動再試行しない。swapガード値も引き上げない。次の検討は、前モデルを安全に解放してからファイルキャッシュを整える段階的切替と、既存プロセスに残ったswapの扱いを分ける。現在はモデルがなくても上限まで約2MiBしかなく、通常再開できる余裕がない。

swapoff/swapon・sysctl変更・全体drop_cachesはまだ実施していない。既存プロセスを止めてswapを減らす方法は採用しない。メモリ準備条件を変える場合は前後の状態と変更内容を保存し、既済試行との起動時間条件差を明記する。根本原因解決や180試行完了とは扱わない。heartbeatは解析継続のためACTIVE、GPU負荷のrunnerは停止のまま。
