> 実行当時の履歴。文中のserver証拠パスは非公開原本を指す。現在の状態は[最終報告](../REPORT.md)を参照。

# 160桁折り返しのSQLiteダンプ引用による停止

2026-10-08 10:10 JST、full07は141試行完了後、sqlite-db-truncate-27b-r3の4番目APIで停止。3 APIはDONE/finish/usage付きで完了し、4番目はrepeated_character_128:0:reasoningで中断した。HarborはCancelledError、verifier未実行。この試行は採点外で原本保持し、モデル不正解には数えない。

入力は4096バイトのSQLiteファイルをprint(data.hex())した端末出力。160桁で折り返され、物理行の最長ゼロ列は160だが、連結した実データには7770連続のゼロがある。出力は「hex at the end is:」に続くインラインコード引用で、ゼロ162文字に達した時点で停止した。v1の限定引用例外は154文字まで実際に適用されたが、160超で拒否した。生成暴走とも正常完了可能とも断定できない。

## 限定修正と検証

TerminalBenchEvidenceの入力認識だけを拡張し、user/tool入力内の、160桁の完全な16進バイト行が続く場合に折り返しを復元する。最終行は160未満の偶数桁を許す。空行・非hex行・異なる幅を跨いで連結しない。assistant入力を根拠にしない。元の入力も従来どおり参照する。

出力のインラインhex引用に限る条件、1列最大512文字・入力根拠以内・要求合計4096文字、他の文字/句反復、SSE/API/資源ガードは保持する。policyはinput_grounded_inline_zero_hex_v2_wrapped160。過去141正常試行との監視条件差を最終報告に明記する。

Mac/serverの17 CPUテストが成功。今回4応答と前回15応答を保存SSEから再生し、17完全応答が通り、元中断2応答は引用判定が通っても未完SSEとして拒否された。vLLMは本番と同じDONE/finish/usage、Strataは加えてtimingsを検証。初回診断でvLLMにもtimingsを要求して失敗したため、本番条件に揃えて再検証した。生のSSEは変更していない。

server guard-interruption-02/に元status/full07/旧コード、run/job原本SHA256、analysis.json、offline-review.json、tests.txt、replay-review.pyを保存。停止後はベンチ推論・課題コンテナなし、GPU faultなし、swap約77.6MiB、MemAvailable約88GiB。LibreChat/Mongoは稼働維持。

## 制御検証

--guard-recovery-probe-02で中断した1件だけを新規Docker・別ラベルsqlite-db-truncate-27b-r3-guard-recovery02で検証する。旧full07/元試行を再起動・上書きしない。141既済・build-cython-extの9保留を引き継ぐ。モデル/課題/採点/公式時間制限を維持する。

pilot_complete/recovery_probe=guard02ならAPI完全性、資源、採点をレビューし、通常不正解も成績として保持する。schedule_labelで元試行に対応付けてから新full-runner-08.logへ再開する。再停止なら盲目再試行せず解析へ戻る。CPU再生成功は制御検証や長期安定の成功を意味しない。


最優先10月8日10:24JST更新: guard02制御検証はreward1、8 API完全SSE（raw再生確認）、実行274.19秒＋準備2.26秒、swap最大81346560bytes、MemAvailable最小77382983680bytes、GPU faultなし。引用例外発動0なので折返し認識の動作証拠はCPUテスト/再生に限定。guard-interruption-02/probe-review.jsonとprobe-status.json保存、142既済・9保留とschedule_label対応を確認しfull-runner-08.logへ通常再開、初期PID3858495。現PID/stateはserver正本から確認。旧full07/guard02 probe/元試行を再起動・上書きしない。生存更新中は観測のみ。
