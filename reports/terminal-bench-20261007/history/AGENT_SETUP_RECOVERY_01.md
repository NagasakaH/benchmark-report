> 実行当時の履歴。文中のserver証拠パスは非公開原本を指す。現在の状態は[最終報告](../REPORT.md)を参照。

# polyglot-c-py: agent準備のHTTP接続障害

2026-10-08 05:11 JST、full-runner05は99試行完了後、polyglot-c-py-iq4-r1のTerminus準備中に停止した。公式oracleは合格済み。tmux/asciinema導入のaptコマンドが120秒で時間切れになり、HarborがRuntimeErrorを返した。agent_execution/verifierはnull、API要求0件。この中断はモデル不正解にも正常試行にも算入しない。

停止中のswap最大74,412,032 bytes、MemAvailable最小94,353,575,936 bytes、GPU faultなし。推論・課題コンテナは終了し、LibreChat/Mongoと通常router/watchサービスは稼働。serverのagent-setup-interruption-01/へ元status・full05ログ・コードと元run/jobのSHA256を保存した。原本はその場に保持。

## CPU診断と限定対策

同じ公式イメージのCPU1/RAM2GiB診断で、Ubuntu archive/securityのHTTP接続失敗を確認。ホストのHTTPSは両方HTTP200。イメージにはCA証明書がなく、そのままHTTPSへ切替えると証明書検証に失敗した。公開CA束を渡すと、TLS検証とapt署名検証を維持したHTTPS更新が成功した。aptの終了コード0だけでは成功とせず、APT::Update::Error-Mode=anyと出力で判定した。

対策はpolyglot-c-pyのTerminusツール準備だけに限定する。公式Ubuntu配布URLのHTTPをHTTPSにした一時source設定と公開CA束を使用し、既存のtmux/asciinemaおよび通常依存パッケージを導入する。元apt設定・課題・解答・verifierを変更せず、一時設定とCA束は終了時に削除する。Harborの120秒コマンド制限、240秒導入予算、公式agent時間制限、モデル設定、SSE/反復/資源ガードを維持。TLS/署名検証を無効化しない。ほかの課題には適用しない。

初回CPU導入は22.86秒で成功し、元sourcesのSHA256一致とtmux/asciinemaの版表示を確認。最初の診断用send-keysコマンドは引用が欠けていたため、端末コマンド実行成功の証拠にはしない。修正したHarbor実処理を使う独立CPU統合確認はoffline-review.jsonに保存する。

## 制御検証と集計

CPU統合確認が合格した場合だけ、--setup-recovery-probeで中断1件をpolyglot-c-py-iq4-r1-setup-recovery01として検証する。99既済とbuild-cython-extの9保留を維持し、元ラベルを上書きしない。終了時はpilot_complete/recovery_probe=setup01。API完全性・資源・採点をレビューし、正否に関係なく正常ならschedule_labelで代替を保持して通常再開できる。異常なら解析へ戻り同条件自動再試行をしない。

この課題の新試行にはagent_setup_transport=ubuntu_https_public_ca_v1を記録し、準備通信条件の差として最終報告へ明記する。過去99件の成績は変更しない。


05:34 JST続報: setup01制御検証は5 API完全SSE（raw再生検証済み）、実行473.71秒＋準備2.08秒、swap最大70.969MiB、MemAvailable最小71.281GiB、GPU faultなしで正常終了。agent準備16.52秒。採点0は提出ディレクトリにcmain/test.py.c/testcを残した通常不正解として保持する。元99件・9保留とschedule_label対応を検証し、probe-review.json/probe-status.jsonへ保存。正常完了100件を引き継ぎfull-runner-06.logで通常再開、初期PID3310982。現在PID/stateはserver正本を確認。旧full05/旧probeを再起動せず、生存更新中は観測のみ。
