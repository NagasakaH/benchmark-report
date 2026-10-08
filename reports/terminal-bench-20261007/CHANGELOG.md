# Terminal-Bench 変更履歴

## 2026-10-08 最終レビュー

- 13:43 JST: full08正常終了、19課題171試行・9保留。結果40/57、41/57、43/57（IQ4/IQ3/27B）。
- 全1,613保存SSE・公式採点171・oracle19・実送信パラメータ・schedule_labelの一意性をCPU監査。3,760証拠ファイルをSHA256記録。
- 終了した所有IQ3のみidle確認後unload、両GPU解放と通常サービスhealthを確認。loopback誤アドレスの初回probeも証拠を保持しLANアドレスで再確認。
- preparation/elapsed/既知合計、上流usage/Harbor usage、cold/後続TTFT、計測できたGPU Whとdrain未記録を区別してREPORT/SUMMARY作成。
- build-cython-extは公式解答/採点を維持した検証済み環境修復なし。依存版候補は未検証として保留9件維持。

## 実行中の条件変更（原本は各証拠ディレクトリに保持）

- 10月7日: swap停止2回。1回限りのswap回収後、全比較モデルに所有idleモデルunloadと対象6ディレクトリcache準備を導入。初期8件との差を明記。MEMORY_RECOVERY_02.md / SWAP_RECURRENCE.md。
- 10月7日: build-cython-ext oracle2回不合格、9件hold_without_score。ORACLE_BUILD_CYTHON.md。
- 10月8日00:47: guard01制御再検証を採用し37件からfull05再開。過去36件と引用ガード条件差。GUARD_RECOVERY_01.md。
- 05:34: polyglotのHTTPS導入対策検証を採用し100件からfull06。AGENT_SETUP_RECOVERY_01.md。
- 06:51: query-optimizeにも同じ限定対策を適用し109件からfull07。AGENT_SETUP_RECOVERY_02.md。
- 10:24: guard02の160桁hex折返し認識を検証し142件からfull08。過去141件と条件差。GUARD_RECOVERY_02.md。
- 採点外中断6件と別ラベル代替6件を対応付け、通常不正解の改善再試行はしない。全体の引用例外実発動は0件で、機能の証明はCPUテスト/保存応答再生に限定。
