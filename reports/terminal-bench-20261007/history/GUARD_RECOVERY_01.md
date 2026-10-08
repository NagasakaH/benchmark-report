> 実行当時の履歴。文中のserver証拠パスは非公開原本を指す。現在の状態は[最終報告](../REPORT.md)を参照。

# 16進ダンプ引用による反復ガード停止の解析

2026-10-08 00:35 JST、full-runner04は36試行完了後、`db-wal-recovery-iq4-r1`の15番目APIで停止した。検出は`repeated_character_128:0:reasoning`。runner・relay・watchdogと専用推論コンテナは終了済み、GPU faultなし、停止後の両GPUは約57MiB/負荷0。swap約65.6MiB、RAM余裕約88GiB。LibreChat/Mongoは稼働を維持した。

保存SSEではSQLiteページを解析し、バッククォート内でゼロを128文字引用した時点で検出された。直前のuserメッセージ（端末出力）の16進ダンプにはゼロ160連続がある。14 APIはDONE/finish/usage/timings付きで正常完了。15番目はガードがストリームを切ったため未完であり、元からのエンジン停止・生成暴走とは断定できない。HarborはCancelledError、verifier未実行。**この中断をモデルの不正解や正常試行に算入しない。**

## 証拠と修正

serverの`guard-interruption-01/`に停止時status・旧コード・full-runner04ログ・元run/job全ファイルのSHA256と解析を保存。元run/job/raw SSEはその場に保全し、上書きしない。

Terminal-Benchだけで`TerminalBenchEvidence`を使用する。user/tool入力に同長以上のゼロ列が実在し、出力がインラインコードの16進引用である場合だけ、ゼロ128連続の検出に限定例外を設ける。1列は入力の最長列以内かつ最大512文字、1要求の累計4096文字以内。今回は上限160文字。他の文字反復・文句反復・入力にない反復・SSE未完・NaN・資源ガードの停止を維持。既存StreamEvidenceのデフォルトは変更しない。今後3モデルに共通適用し、過去36件との監視条件差を最終報告へ明記する。

Mac/serverともCPU安全テスト12件（メモリ4＋ストリーム8）成功。元の15応答をCPUで再生し、14完全応答は引き続き合格、15番目の引用は限定例外に一致する一方、SSE未完の判定は維持されることを確認。`offline-review.json`とテスト出力参照。これは将来の応答が正常に完了する保証ではない。

## 制御再検証

初期PID2628288、ログ`guard-recovery-01.log`、`--guard-recovery-probe`で中断した1件だけを新規Docker環境・別ラベル`db-wal-recovery-iq4-r1-guard-recovery01`で検証。モデル設定・課題・採点・時間制限は変更しない。成績改善の再実行ではない。既済36件とbuild-cython-extの9保留を引き継ぐ。

生存更新中は追加負荷禁止。成功終了時は`pilot_complete/recovery_probe=guard01`になる。採点の正否によらず、完全SSE・資源・ガードをレビューしてから残りを再開する。再停止なら追加自動再試行しない。通常再開時にもblocked_tasksを保持する修正を併せて実施した。

## 制御再検証結果

00:45 JSTにreward1、API6件すべて完全SSEで終了。実行102.48秒＋準備3.68秒、swap最大65.602MiB、RAM最小71.196GiB、GPU faultなし。正常終了37件。今回は引用例外の発動0件であり、ライブで同じ引用経路を通った証拠ではない。限定例外の動作証拠はCPU保存応答再生とテストに限る。元試行の途中成績と比較して能力改善を主張しない。

`probe-review.json`と`probe-status.json`に保存し、通常runnerを`full-runner-05.log`へ再開。37件を保持、同じschedule_labelの元試行を再実行せず、build-cython-extの9保留も保持する。今後再発すれば解析へ戻る。
