# 実行手順と再現範囲

このページは今回行った手順と再実施に必要な条件を記述します。公開データの再集計はCPUだけでできます。モデルを使った再実施には別途、重み・runtime・専用Docker環境・router等の構築が必要です。[参照コード](../reference/harness/README.md)は既存ホスト専用runnerの記録で、clone後そのまま推論を起動できる配布物ではありません。

## 公開データの再集計

```sh
git clone https://github.com/NagasakaH/benchmark-report.git
cd benchmark-report
python3 scripts/recompute.py
python3 scripts/validate_publication.py
python3 -m unittest discover -s reference/harness -p 'test_terminal_bench_*.py'
```

再集計は171試行の重複、19課題×3モデル×3回、成功数、実時間、上流token、TTFT、観測output速度、保存された試行単位電力量と集計JSONの整合性を確認します。raw SSE本文/telemetry全標本を公開していないため、SSE完全性の再判定や元の1秒標本からのWh再積分はこの公開データだけではできません。

## 推論試験を行った順序

1. **課題を先に固定する。** [manifest](../reports/terminal-bench-20261007/data/tasks-manifest.json)の20課題を、モデルの成績を見る前に選択。別課題への差替えをしない。上流課題は固定commitから取得し、instruction hashと公式制限を照合する。
2. **モデル/runtimeを固定する。** [環境表](environment.md)の2GPU/256K・thinking・sampling設定を用意する。課題へモデルや資格情報、ホストDocker socketを渡さない。認証はホスト側adapterが扱う。
3. **oracleで環境と採点を確認する。** 各課題の最初に公式oracleを1回実行。プロセスのexit 0だけでなく、exceptionなし、verifier reward=1を確認してモデルに進む。build-cython-extは診断時も含め2回失敗したため、全モデル共通で9試行を保留。
4. **逐次スケジュールを作る。** 各課題でr1: IQ4→IQ3→27B、r2: IQ3→27B→IQ4、r3: 27B→IQ4→IQ3。新規Docker、試行自動リトライ0。採点結果を見て成功試行を選び直さない。
5. **専用モデルの解放とcache準備。** 新手順では直前のベンチ所有モデルだけをidle確認後に正式モデル指定unload APIで解放。別モデル/利用中なら停止して解析する。推論コンテナなし、両GPU VRAM<100MiB/busy≤1を2回確認。比較3モデル本体/draftの6ディレクトリ内の1MiB超ファイルだけにPOSIX_FADV_DONTNEED。MemFree≥70GiBを確認する。準備時間とbefore/released/afterを保存。
6. **adapterとHarborを起動する。** 上流SSEを測定し、完全な同一内容を非stream JSONで返す。モデルalias以外は共通設定。Harborの端末操作・形式修正は評価対象。開始から採点/終了までelapsedを記録する。
7. **監視する。** Harbor生存中は約1秒ごとGPU/資源記録、約3秒ごと資源ガード、独立watchdogの90秒更新停止検知。MemAvailable≥8GiB、swap≤512MiB、disk≥5GiB。GPU fault latchやAPI異常を検出したら新規負荷を止め、同条件で盲目に再実行しない。
8. **公式時間切れを処理する。** 通常成績として採点を保持。上流APIが進行中なら新規要求を送らず、完全なSSE証拠を回収して終了する。drainは公式agent制限を延長しない。[この区間の電力記録欠落](measurement.md)を含めて報告する。
9. **環境中断と採点を分ける。** 資源/ガード/agent導入障害の元試行は採点外で原本保全。原因解析・CPU検証→中断1件だけ別ラベルで制御検証→レビューを経て再開。正常ならreward0でも採用し、schedule_labelで代替と結び付ける。今回の対応は6件。
10. **最終監査と終了処理。** oracle19、採点171、schedule_label一意、全上流要求設定、raw SSE1,613、テレメトリを確認。保留9件を分母から除外した部分結果を作成。所有idleモデルだけunloadし、通常health・全モデルunloaded・両GPU解放を確認。定期監視をPAUSEDにする。

当初の8件は新cache準備以前です。途中に行った1回限りのswapoff/swaponは障害復旧操作で、再現手順に反復的なswap清掃を組み込んでいません。過去の観測条件を全試行で同一だったことに書き換えていません。

## Harborの実行形

以下は当時の構造を示す例です。`TASK_DIR`、`JOB_DIR`、モデルalias、adapter URL等は専用環境に合わせて用意します。

```sh
harbor run -p "$TASK_DIR" -a oracle -n 1 -k 1 -r 0 -o "$JOB_DIR" --job-name oracle-task
harbor run -c trial-config.json
```

当時のconfigの作り方は[runner](../reference/harness/terminal_bench_runner.py)の`cfg`を参照。`n_concurrent_trials=1`、`n_attempts=1`、`retry.max_retries=0`、Terminus-2の`model_info.max_input_tokens=262144`、`llm_call_kwargs.max_tokens=16384`です。公式課題の制限は上書きしません。

## 2課題だけのagent導入対策

polyglot-c-pyとquery-optimizeはagentのtmux/asciinema導入時にUbuntu HTTP接続がtimeoutしました。元apt sourcesは変えず、一時sourceをHTTPSに置換し、公開CA束を使ってTLS・apt署名検証を維持しました。同じ120秒の導入制限、リトライなし、一時ファイルを終了時に削除します。

Harbor 0.24.0の`harbor/agents/terminus_2/tmux_session.py`で、ツール導入の`environment.exec`の直前に次の限定hookを入れた専用venvを使用しました。

```python
import os
if system_info["package_manager"] == "apt-get" and os.environ.get("TB_AGENT_APT_HTTPS") == "1":
    from terminal_bench_apt_https import prepare_install
    install_command = await prepare_install(self.environment, tools_needed)
# 既存のenvironment.exec(..., timeout_sec=self._TOOL_INSTALL_TIMEOUT_SEC)を継続
```

runnerがこの2課題だけに`TB_AGENT_APT_HTTPS=1`とhelperのPYTHONPATHを渡します。公開CAファイルは`terminal_bench_apt_https.py`の所定パスへ別途用意する必要があります。[対策1](../reports/terminal-bench-20261007/history/AGENT_SETUP_RECOVERY_01.md)・[対策2](../reports/terminal-bench-20261007/history/AGENT_SETUP_RECOVERY_02.md)にCPU検証と制御試行の結果を記録しています。
