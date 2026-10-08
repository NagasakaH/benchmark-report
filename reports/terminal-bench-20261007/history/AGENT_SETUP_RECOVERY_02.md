> 実行当時の履歴。文中のserver証拠パスは非公開原本を指す。現在の状態は[最終報告](../REPORT.md)を参照。

# query-optimize: agent準備の接続障害

2026-10-08 06:28 JST、full06は108試行完了後、query-optimize-iq4-r1のTerminusツール導入コマンドが120秒で時間切れとなり停止した。公式oracleは合格済み。API要求0、agent_execution/verifierはnullで、採点外の環境中断として元run/jobを保持する。GPU faultなし、推論・課題コンテナは終了、LibreChat/Mongoは継続。

この課題も公式ubuntu:24.04系イメージでtmux/asciinemaが未導入。前回のHTTPS対策はpolyglot-c-pyだけに限定されていたため、query-optimizeには未適用だった。server agent-setup-interruption-02/に停止status/full06/旧runner・原本SHA256・HTTP診断・CPU統合確認を保存する。

対策は既存terminal_bench_apt_https.pyの適用対象にquery-optimizeを追加すること。公開CA束、一時HTTPS source、TLS/apt署名検証、元sources不変、一時ファイル削除、120秒導入制限を保持。課題・解答・verifier・公式時間制限・モデル・SSE/反復/資源ガードは変更しない。既済108件の成績は保持する。長期的なネットワーク障害解決を意味しない。

CPU統合確認合格後のみ、--setup-recovery-probe-02で中断1件をquery-optimize-iq4-r1-setup-recovery02として制御検証する。108既済とbuild-cython-extの9保留を引き継ぐ。正常終了はpilot_complete/recovery_probe=setup02。API・資源・採点をレビューし、正否によらず正常ならschedule_labelで代替として保持して通常full-runner-07.logへ再開する。異常時は同条件自動再試行をせず解析。query-optimizeの全モデル共通でagent_setup_transport=ubuntu_https_public_ca_v1を記録し、準備条件差を最終報告に含める。


最優先10月8日06:36JST更新: full06は108正常完了後query-optimize-iq4-r1のagentツール導入で120秒timeout停止。公式oracle合格済み、API0/agent_execution・verifier nullで採点外。CPUでUbuntu HTTP接続失敗を再現。前回対策がpolyglotだけだったためqueryには未適用。既存HTTPS/公開CA/一時source対策をquery-optimizeに限定追加し、CPUのHarbor実準備15.35秒成功（元source不変/一時ファイル削除/端末コマンド実行）、回帰12テスト合格。AGENT_SETUP_RECOVERY_02.mdとserver agent-setup-interruption-02/{analysis,offline-review}.json参照。元status/full06/runner/原本ハッシュ保全。--setup-recovery-probe-02初期PID3427578、setup-recovery-02.log、query-optimize-iq4-r1-setup-recovery02で中断1件のみ制御検証。108既済と9保留保持。生存更新中は観測だけ。pilot_complete/recovery_probe=setup02なら完全SSE/資源/採点をレビューし、正否によらず正常ならschedule_labelで採用し新full-runner-07.logで通常再開可。異常なら解析し盲目再試行禁止。旧full06/旧probeや原試行を再起動・上書きしない。query-optimizeもagent_setup_transport=ubuntu_https_public_ca_v1として報告に含める。


最優先10月8日06:51JST更新: setup02制御検証は8API完全SSE（raw再生確認）、実行642.63秒+準備2.08秒、swap最大75304960bytes/RAM最小76445171712bytes/faultなしで正常終了。6採点中5合格、SQL速度0.69037秒が基準0.51654秒×1.05を超えreward0。通常不正解として採用し再試行しない。probe-review.json/probe-status.json保存、既済109件・9保留を保持してfull-runner-07.logへ通常再開、初期PID3447069。現PID/stateはserver正本を確認。古いfull06/setup02 probe/元試行は再起動禁止。生存更新中は観測のみ。
