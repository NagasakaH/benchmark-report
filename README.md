# ローカルLLM ベンチマークレポート

2枚のAMD Radeon AI PRO R9700で実行したTerminal-Bench 2.0の比較記録です。実行手順、測定定義、結果、途中の条件変更を一緒に公開しています。

## 2026-10-07〜08: Terminal-Bench 2.0

**固定20課題・180試行を計画し、19課題・171試行を採点完了。1課題・9試行は公式oracle不合格により保留です。**

| 構成 | 成功 | 成功率 | 3回とも成功した課題 | 平均実行時間 |
| --- | --- | --- | --- | --- |
| Qwen3.8-Flash-Next IQ4_XS / Strata 0.1.40 | 40/57 | 70.2% | 10/19 | 309.5秒 |
| Qwen3.8-Flash-Next IQ3_S / Strata 0.1.38 | 41/57 | 71.9% | 11/19 | 295.1秒 |
| Qwen3.8-27B MXFP4 / vLLM DFlash | 43/57 | 75.4% | 13/19 | 337.1秒 |

Harbor 0.24.0 / Terminus-2、全モデル2GPU・256K・thinking ON/medium。実装・DB・運用寄りに選んだ独自subsetで、公式89課題全体のスコアではありません。量子化以外にもESP・KV・実行基盤が異なるため、量子化単独の比較ではありません。

「平均実行時間」はモデル生成だけでなく、環境/agent準備・cold起動・端末操作・採点・必要なAPI完了待ちを含みます。モデル解放/cache準備は別計測です。

## 読み方

1. [結果の要約](reports/terminal-bench-20261007/SUMMARY.md) / [詳細レポート](reports/terminal-bench-20261007/REPORT.md)
2. [実行環境とモデル条件](docs/environment.md)
3. [実行手順・oracle・停止と復旧](docs/procedure.md)
4. [速度・TTFT・電力の計測方法とシーケンス図](docs/measurement.md)
5. [解釈上の制約と途中の条件変更](docs/limitations.md)
6. [公開データの来歴と検証可能範囲](docs/provenance.md) / [公開前検証](docs/validation.md)

## 数値を再集計する

Python 3.10以上の標準ライブラリだけで動作し、モデルやDockerを起動しません。

```sh
python3 scripts/recompute.py
python3 scripts/validate_publication.py
python3 -m unittest discover -s reference/harness -p 'test_terminal_bench_*.py'
```

[171試行の明細](reports/terminal-bench-20261007/data/trials.json)、[1,613 APIのメトリクス](reports/terminal-bench-20261007/data/api-audit.json)、[固定20課題と公式制限](reports/terminal-bench-20261007/data/tasks-manifest.json)を収録しています。rawプロンプト・解答・SSE本文・モデル重み・認証情報は含めていません。[実行コード参照版](reference/harness/README.md)は当時の専用環境を説明するための資料です。

課題と採点の原典は[Terminal-Bench 2.0](https://github.com/harbor-framework/terminal-bench-2)、実行基盤は[Harbor](https://github.com/harbor-framework/harbor)です。第三者の課題・解答・モデルはこのリポジトリで再配布していません。
