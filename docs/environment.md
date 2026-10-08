# 実行環境と固定条件

## ホストと課題環境

| 項目 | 記録 |
| --- | --- |
| GPU | AMD Radeon AI PRO R9700 ×2、各32GB級VRAM |
| CPU | AMD Ryzen 7 9700X、8コア16スレッド |
| RAM | 物理96GB、OS MemTotal 96,339,108 KiB |
| OS | Ubuntu 24.04.4 LTS |
| 公開準備時のkernel確認 | 7.0.0-34-generic（10月8日の読取り。試験全期間のkernel履歴検証ではない） |
| GPU設定 | 電力上限210W/枚。センサー値には上限を超える標本もあり、実測値は別記 |
| 課題コンテナ | 公式CPU1、RAM2048MiB、storage10240MiB、課題ごとの公式時間制限 |
| 同時実行 | 課題1、モデル要求1。毎試行、新規Docker環境 |

[課題manifest](../reports/terminal-bench-20261007/data/tasks-manifest.json)にDockerイメージ、agent/verifier制限、instruction SHA256があります。モデルruntimeの[イメージID](../reports/terminal-bench-20261007/data/runtime-images.json)と[Python依存記録](../reports/terminal-bench-20261007/data/requirements-freeze.txt)も保存しています。依存一覧は当時の専用venvの記録で、他のOSへのインストール成功を保証するlockfileではありません。

## エージェントと入力条件

- Harbor **0.24.0**、Terminus-2 **2.0.0**。Qwen Code不使用。
- 課題repo: `https://github.com/harbor-framework/terminal-bench-2`、commit `2fd12b88aafdd04a52c298e3940bcb189f9766d6`。
- 全モデルcontext **262144**、1応答上限 **16384**。共通agent設定・圧縮設定を使い、aliasだけモデルごとに差替え。
- thinking **ON / medium**。OFF/low/high sweepなし。mediumは固定の推論token予算ではなく、モデル間で同じ計算量を保証しない。
- 実際に送信した全1,613要求で以下を検証。

```json
{
  "temperature": 1.0,
  "top_p": 0.95,
  "top_k": 20,
  "min_p": 0.0,
  "repetition_penalty": 1.0,
  "presence_penalty": 0.0,
  "max_tokens": 16384,
  "reasoning_effort": "medium",
  "chat_template_kwargs": {
    "enable_thinking": true,
    "preserve_thinking": true,
    "reasoning_effort": "medium"
  },
  "stream": true,
  "stream_options": {"include_usage": true}
}
```

vLLM起動設定のtemperature 0.7は、実要求の1.0で上書きされています。

## 比較したモデル構成

| 項目 | IQ4_XS | IQ3_S | 27B |
| --- | --- | --- | --- |
| モデル | Qwen3.8-Flash-Next UD-IQ4_XS | Qwen3.8-Flash-Next GSQ-RCO-IQ3_S | Qwen3.8-27B MXFP4 |
| runtime | Strata 0.1.40 | Strata 0.1.38 | vLLM Radiance 0.9.3 |
| ESP | OFF | ON、係数1.0、layers4–44、project/per-layer | 該当なし |
| KV | INT8 | INT8 | FP8 |
| 投機生成 | MTP spec4/minp .5 | MTP spec4/minp .5 | DFlash2 FP8 draft、7 tokens |
| その他 | resident experts | 専用安定構成 | TP2、prefix cache ON、R4D |

これらは通常配備構成の比較です。モデルサイズ/重み、Strata版、ESP、KV精度、投機生成が同時に違うため、IQ4とIQ3の量子化効果だけを分離した実験ではありません。
