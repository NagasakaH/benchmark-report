# Terminal-Bench 2.0 部分結果 — 2026-10-08

固定20課題・180試行のうち、**19課題・171試行（各モデル57）を採点完了、1課題・9試行は保留**。20課題全完了ではない。独自に選んだsubsetであり、公式89課題全体のスコアではない。serverを正本とし、原本試行・中断ログ・採点は変更していない。

| 構成 | 成功 / 57 | 成功率 | 3/3成功課題 / 19 | 1回以上成功課題 / 19 | r1 / r2 / r3（各19） |
| --- | --- | --- | --- | --- | --- |
| IQ4_XS | 40 | 70.2% | 10 | 16 | 15 / 12 / 13 |
| IQ3_S | 41 | 71.9% | 11 | 16 | 13 / 15 / 13 |
| 27B MXFP4 | 43 | 75.4% | 13 | 15 | 14 / 15 / 14 |

27Bはこの標本で成功数と3/3成功課題数が最多。IQ3_SとIQ4_XSの差は1試行、27Bとの差も2～3試行で、一般的な優劣や量子化の効果を断定できない。同じ課題の3回は独立した課題57個に相当せず、実行基盤・ESP・KV・投機生成も異なる。少なくとも1回成功した課題はIQ4/IQ3が16、27Bが15で、課題ごとに得意不得意がある。

## 条件

- Harbor 0.24.0 / Terminus-2 2.0.0。Qwen Codeは使用していない。公式課題repo commit `2fd12b88aafdd04a52c298e3940bcb189f9766d6`。20課題は結果を見る前に固定（easy2 / medium16 / hard2、実装・DB・運用寄り）。
- 全モデル2GPU、context 262144、1応答上限16384。thinking ON / medium。全1,613上流要求の実送信設定を監査し、temperature 1.0、top_p .95、top_k 20、min_p 0、repetition_penalty 1、presence_penalty 0、enable_thinking/preserve_thinking=trueを確認。OFF/low/high比較はしていない。mediumは同じ推論トークン数・計算量を保証しない。
- 各課題公式CPU1/RAM2GiB、公式時間制限、新規Docker、逐次実行。課題ごとに公式oracle合格後にモデルを実行。成績を改善する試行のやり直しはしない。反復ごとのモデル順序はIQ4→IQ3→27B、IQ3→27B→IQ4、27B→IQ4→IQ3。形式修正・出力上限への対応など標準agentの継続動作は評価対象。
- localhost測定adapterが上流SSEを記録し、同じcontent/reasoning/tool_callsをHarbor向けJSONに戻す。要求パラメータ・raw SSE・応答・trajectory・verifierをserverに保存。

| 構成 | 実行基盤 | ESP / KV / 投機生成 |
| --- | --- | --- |
| IQ4_XS | Qwen3.8-Flash-Next UD-IQ4_XS / Strata 0.1.40 | ESP OFF、INT8 KV、resident experts、MTP spec4/minp .5 |
| IQ3_S | Qwen3.8-Flash-Next GSQ-RCO-IQ3_S / Strata 0.1.38 | ESP ON（係数1.0、layers4–44、project/per-layer）、INT8 KV、MTP spec4/minp .5 |
| 27B MXFP4 | Qwen3.8-27B / vLLM Radiance 0.9.3 | TP2、FP8 KV、DFlash2 FP8 draft7、prefix cache ON、R4D |

vLLM起動既定temperature .7は実要求1.0で上書き。これは配備構成全体の比較であり、量子化だけの比較ではない。

## 各課題の反復結果

各セルはr1/r2/r3のreward（1=成功、0=不正解）。保留を0に置換しない。

| 課題 | IQ4_XS | IQ3_S | 27B |
| --- | --- | --- | --- |
| cancel-async-tasks | 0/0/0 | 0/1/0 | 1/1/0 |
| cobol-modernization | 1/1/1 | 1/1/1 | 1/1/1 |
| constraints-scheduling | 1/1/1 | 1/1/1 | 1/1/1 |
| custom-memory-heap-crash | 1/1/1 | 1/1/1 | 1/1/1 |
| db-wal-recovery | 1/1/0 | 0/1/0 | 0/0/0 |
| fix-git | 1/1/1 | 1/1/1 | 1/1/1 |
| git-multibranch | 0/1/1 | 1/1/1 | 1/1/1 |
| kv-store-grpc | 1/1/1 | 1/1/1 | 1/1/1 |
| large-scale-text-editing | 1/0/1 | 1/1/0 | 1/1/1 |
| log-summary-date-ranges | 1/1/1 | 1/1/1 | 1/1/1 |
| modernize-scientific-stack | 1/1/1 | 1/1/1 | 1/1/1 |
| nginx-request-logging | 1/0/1 | 1/1/1 | 1/1/1 |
| openssl-selfsigned-cert | 1/1/1 | 1/0/1 | 1/1/1 |
| polyglot-c-py | 0/0/0 | 0/0/0 | 0/0/0 |
| query-optimize | 0/0/0 | 0/1/1 | 0/1/1 |
| regex-log | 1/1/1 | 1/1/1 | 1/1/1 |
| sanitize-git-repo | 1/0/0 | 0/0/0 | 0/0/0 |
| sqlite-db-truncate | 1/1/1 | 1/1/1 | 1/1/1 |
| write-compressor | 1/0/0 | 0/0/0 | 0/0/0 |
| build-cython-ext | 保留3 | 保留3 | 保留3 |

全モデルともpolyglot-c-pyは0/3。write-compressorはIQ4のみ1/3、IQ3/27Bは0/3。db-wal-recoveryはIQ4 2/3、IQ3 1/3、27B 0/3。これらは採点の結果として保持した。

公式agent時間切れはIQ4 3件、IQ3 4件、27B 3件。うちIQ4 write-compressor r1と27B large-scale-text-editing r2は提出物が採点成功（reward1）なので成功に含む。時間切れを一律不正解・環境障害にはしていない。

## 実時間と準備時間

elapsed_sはrunnerが記録した実行区間で、Harbor起動・agent準備・推論・採点・終了処理、および時間切れ時の上流API完了待ちを含む。公式agent実行時間制限そのものとは異なる。preparation_sは直前モデル解放と対象ファイルcache準備を別記する。

| 構成 | 実行平均 / 中央値 秒 | 成功平均 / 不正解平均 秒 | 実行計 時間 | 準備計 秒（記録数） | 実行＋既知準備 時間 |
| --- | --- | --- | --- | --- | --- |
| IQ4_XS | 309.5 / 207.8 | 243.7 / 464.1 | 4.900 | 268.8 (54/57) | 4.975 |
| IQ3_S | 295.1 / 198.8 | 244.6 / 424.4 | 4.672 | 331.5 (55/57) | 4.764 |
| 27B MXFP4 | 337.1 / 246.1 | 307.8 / 427.2 | 5.338 | 337.0 (54/57) | 5.432 |

初期8試行はcache準備条件が異なり、準備時間は未記録（IQ4 3、IQ3 2、27B 3）。未記録を0秒と解釈していないため「実行＋既知準備」は完全な総時間ではない。memory-recovery02の準備だけはmemory-preparation.json時刻差から復元した。全試行のphase別時間は `data/trials.json` にある。

最初の採点試行Harbor開始は10月7日20:35:23 JST、最後のrunner終了は10月8日13:43:40 JST、間隔17.138時間。この間隔はoracle・調査・中断・再開待ち等も含み、事前準備や終了後レビューを含まない。

## トークン・cache・応答速度

上流トークンは全APIのusage合計（繰り返し入力、thinkingを含むcompletion、長さ上限応答、時間切れ後のdrainも含む）。Harbor集計はagent側が取り込んだusageで、上限到達時の例外や中断で少なくなる。両方を保存し、計算量比較には上流実測を用いる。Harbor lite_llm.pyはfinish_reason=lengthでLLMResponse返却前にOutputLengthExceededErrorを発生させる。

| 構成 | API数 | 上流input | 上流output | cache報告 | Harbor input / output |
| --- | --- | --- | --- | --- | --- |
| IQ4_XS | 526 | 6,338,373 | 685,972 | 5,963,170 (94.1%) | 6,296,109 / 550,504 |
| IQ3_S | 492 | 5,092,801 | 628,759 | 4,731,427 (92.9%) | 4,927,388 / 505,141 |
| 27B MXFP4 | 595 | 9,561,014 | 976,771 | 未取得 | 9,420,704 / 731,011 |

27Bはprefix cache ONだがusageにcached_tokensがなく、Harborの0もcache無効・ヒット0の根拠にはならない。finish_reason=lengthの完全応答はIQ4 9件、IQ3 7件、27B 15件。SSE未完とは区別する。

| 構成 | 新準備条件・最初API TTFT 中央値 秒 | 後続API TTFT 中央値 秒 | 観測output tok/s | Strata prefill / decode tok/s |
| --- | --- | --- | --- | --- |
| IQ4_XS | 24.78 (n=54) | 0.98 | 74.6 | 570.6 / 74.5 |
| IQ3_S | 23.79 (n=55) | 0.93 | 70.2 | 604.3 / 70.1 |
| 27B MXFP4 | 104.08 (n=54) | 0.77 | 164.7 | 別定義・下記 |

最初APIのTTFTはcoldモデル起動も含む。後続は各試行中の要求で、入力長や内容はモデルの行動に応じて異なる。観測output速度は総completion_tokens÷総（最初～最後の出力chunk時間）で、純粋な単一token decodeレイテンシではない。Strata速度は総prompt_n/prompt_ms、総predicted_n/predicted_msから算出。

27Bで前後metricsを両方取得できた538/595要求は、prefill時間合計452.401秒、decode時間合計5332.966秒、prompt counter差分9,506,139、generation差分861,635。generation÷decodeは161.6 tok/s。各試行の最初57要求は起動前metricsが取れないので差分から除外した。prompt counterはcache分を含む入力であり、これを452.401秒で割ってStrataの未cache prefill速度と直接比較しない。

27Bは生成速度が速い一方、cold起動の待ち時間と出力量が大きく、今回の試行平均実時間は最長だった。IQ3はIQ4よりdecodeが少し遅いが、総出力が少なく、平均実時間は少し短かった。固定の同一トークン列を処理した速度試験ではない。

## 電力・VRAM・安定性

電力は2GPUのpower1_averageをμWからWに換算し、時刻差で台形積分。下表は**記録されたHarbor稼働区間だけのGPU Wh**であり、ホスト全体・全実験の消費電力量ではない。

| 構成 | 記録区間GPU Wh | 記録時間 / elapsed計 % | 終了後API無記録 秒 | 各GPU最大VRAM GiB | 最小MemAvailable GiB | 最大swap MiB |
| --- | --- | --- | --- | --- | --- | --- |
| IQ4_XS | 699.56 | 98.51 | 174.8 | 31.772/31.772 | 70.43 | 482.93 |
| IQ3_S | 698.89 | 98.62 | 145.0 | 31.635/31.486 | 37.54 | 447.90 |
| 27B MXFP4 | 866.01 | 98.65 | 169.7 | 31.773/31.773 | 38.49 | 482.84 |

Harbor終了後のdrainは資源・watchdog確認が継続するが、1秒テレメトリファイルへの追記がない実装だった。APIが記録末尾から2秒以上続いた試行はIQ4 1件、IQ3 3件、27B 2件で、表の終了後API時間も未積算。ほかに準備・oracle・中断・試行間を含まない。未記録区間を補間せず、完全なエネルギー効率順位には使用しない。記録内の最大間隔は1.139秒。

センサー上の2GPU合計電力最大はIQ4 432W、IQ3 484W、27B 440W、最高温度はそれぞれ80/79/79℃。設定210W/枚とセンサー瞬時値は同一ではなく、電力は観測値として記載する。採点171試行の保存テレメトリでGPU faultは0、資源ガードのRAM8GiB・disk5GiB・swap512MiB内。初期の採点外資源停止を除いた数字であり、全運転が無障害だったという意味ではない。

新メモリ準備以降163試行の最大swapは82.828MiB、最小MemAvailableは37.544GiB。今回の期間では資源停止が再発していないが、根本原因解決や無期限安定性は証明していない。

## 中断・条件変更・保留

元の採点外中断6件を保全し、対応する別ラベル6件だけをschedule_labelで採用した。既済試行の重複はなく、19×3×3=171、各モデル57件、19課題のoracle合格を検証した。

| 元schedule_label | 採用ラベル末尾 | 区分 |
| --- | --- | --- |
| openssl-selfsigned-cert-iq3-r2 | -cache-recovery01 | 資源 |
| openssl-selfsigned-cert-iq3-r3 | -memory-recovery02 | 資源 |
| db-wal-recovery-iq4-r1 | -guard-recovery01 | 反復ガード |
| polyglot-c-py-iq4-r1 | -setup-recovery01 | agent導入 |
| query-optimize-iq4-r1 | -setup-recovery02 | agent導入 |
| sqlite-db-truncate-27b-r3 | -guard-recovery02 | 反復ガード |

1. 資源停止2回（swap4.21GiB、512.754MiB）。IQ3だけのcache解放では再発。全推論停止・RAM余裕下でswapoff/swaponを1回のみ実施後、直前の所有idleモデルの正式unload→両GPU解放2回確認→比較6ディレクトリのみPOSIX_FADV_DONTNEED→MemFree70GiB以上という準備を適用。自動swap再回収なし。初期8件との差を保持。
2. 36件後のguard01は入力にあるゼロhexのinline引用を誤検知。user/toolに根拠のある引用のみ、入力最長以内・上限512・要求計4096の例外を追加。過去36件と条件が異なる。
3. 99件後polyglot-c-py、108件後query-optimizeのagentツール導入がUbuntu HTTP接続で120秒timeout。API0・採点外。2課題だけ `agent_setup_transport=ubuntu_https_public_ca_v1`（公開CA、一時HTTPS source、TLS/署名検証維持、元source不変、同じ120秒制限）を適用。制御検証のreward0は通常不正解として採用。
4. 141件後guard02は入力hex160桁折返しを認識できず、inlineゼロ162文字を停止。user/tool内の完全な160桁hex行と最終偶数桁行のみ復元するv2を追加。他ガード・512/4096上限維持。過去141件と条件が異なる。

採点対象の引用例外発動は全APIで0件。v1/v2の例外機能の動作証拠は保存応答CPU再生とテストに限定される（最新17テスト、既知保存19応答のうち完全17合格・未完2拒否）。今回の全1,613応答監査はJSON/error/DONE/finish/usage、Strata timingsおよび保存メトリクスとの一致を確認したもの。過去の反復検知ポリシーを新ポリシーで再判定して採点を変更していない。

build-cython-extの公式oracleは2回とも10/11合格。下位pyknotid test_reconstructed_space_curveはKeyError: pos（representation.py:338）で、planarity 1.0.0/networkx 3.7の依存API不整合が候補だが原因版は未分離。終了レビューでDockerfile・公式solve.sh・verifierと保存CPU診断を再確認した。依存版pinは候補になるものの、元の課題・解答・採点のまま公式oracleを通す検証済み環境対策は得られていない。解答のdata['pos']箇所修正や当該テスト除外は本評価の条件を変えるため採用しない。同条件の盲目再試行も行わず、9件を保留する。修復不可能と断定したわけではない。

## 終了確認と公開データ

full08は2026-10-08 13:43 JSTにawaiting_reviewで正常終了。watchdogログのKeyboardInterruptは正常終了時のSIGINTによるもの。所有IQ3をidle確認後、正式unload APIで解放。両GPU busy0%、VRAM各57.16MiB、通常router/LibreChat HTTP200、全モデルunloadedを確認し、定期監視をPAUSEDにした。

この公開版は元の報告を移植し、ホスト固有のアドレス・パスと内部監視情報を除いた。採点、測定値、制約は変更していない。raw SSE・要求本文・課題解答・資格情報は公開していないため、公開データから可能なのは数値の再集計と整合性確認であり、raw SSE監査の追試ではない。

- [公開集計](data/aggregate.json)、[171試行](data/trials.json)、[1,613 APIの数値](data/api-audit.json)、[元証拠ハッシュ](data/source-sha256.json)
- [保留判断](data/held-review.json)、[変更履歴](CHANGELOG.md)、[実行手順](../../docs/procedure.md)、[計測シーケンスと式](../../docs/measurement.md)
- [来歴と検証範囲](../../docs/provenance.md)。公開版の再集計: リポジトリrootで `python3 scripts/recompute.py`。
