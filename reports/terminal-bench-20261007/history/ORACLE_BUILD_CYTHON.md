> 実行当時の履歴。文中のserver証拠パスは非公開原本を指す。現在の状態は[最終報告](../REPORT.md)を参照。

# build-cython-ext: 公式oracle不合格による保留

2026-10-07。メモリ復旧後のfull-runner-03は、モデルを呼び出す前のこの課題のoracleで停止した。GPU問題ではない。

公式oracleを元環境と診断用環境で実行し、いずれも11テスト中10合格、reward0。課題・solution・verifierは変更していない。下位のpyknotidテストの出力が外側のテストに省略されるため、同じ公式Dockerイメージと解答をCPU1/RAM2GiBの診断コンテナで再現して出力を回収した。

下位18テスト中17合格。`test_reconstructed_space_curve`が`pyknotid/representations/representation.py:338`の`data['pos']`で`KeyError: 'pos'`。インストールされたplanarityは1.0.0、networkxは3.7。依存API互換性の可能性はあるが、どの版が直接原因かは未確定。検証シェルのexit0は合格を意味せず、rewardとpytest出力で判断した。

全モデル共通でこの課題9試行を保留し、モデルの不正解に含めない。別課題への差替えも行わない。固定した残り19課題を同じ条件で進める。最終報告の分母は実際に採点可能だった課題・試行数とし、20課題180試行を完了したとは表記しない。保留課題を再開する場合は公式oracleを通す方法と変更条件を別途レビューする。

server証拠は`oracle-analysis-build-cython/`と`oracle/oracle-build-cython-ext*`。再開の明示的判断は`blocked-tasks.json`に保存し、runnerは`--resume-reviewed-oracle-block`でその課題だけを保留して継続する。
