# 公開前の検証記録

2026-10-08に以下を実施しました。推論モデルや課題Dockerの再実行は行っていません。

| 検査 | 結果 |
| --- | --- |
| 公開JSON再集計 | 19課題171試行・各57・保留9、成功40/41/43を確認 |
| API数値 | 1,613件のusage・TTFT・速度等が元の集計JSONと一致 |
| 試行対応 | 6件の採点外中断に対応する代替ラベル、一意なschedule_labelを確認 |
| CPU回帰テスト | stream13件＋メモリ準備4件、計17件成功 |
| Python構文 | 公開した全Pythonファイルをcompileで確認 |
| Mermaid | 3図をMermaid 12.1.0＋DOM環境でparse成功。GitHub上のピクセル単位の表示検証ではない |
| ローカルMarkdownリンク | validate_publication.pyで参照先の存在を確認 |
| コード来歴 | 当日のserver最終版とローカル原版のSHA256一致を確認し、公開変換を記録 |
| 公開物の完全性 | PUBLICATION_SHA256.json、source-manifest.jsonと照合 |
| 公開内容 | 指定ファイルだけ選択し、資格情報・秘密鍵・raw要求/応答を除外。token形式/私有パス/旧LANアドレスのスキャンも実施 |

SSE本文の再監査や1秒電力標本からの再積分は公開データだけでは実施できません。検証範囲は[来歴](provenance.md)、計測の限界は[計測方法](measurement.md)を参照してください。
