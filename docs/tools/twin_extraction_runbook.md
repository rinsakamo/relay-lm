---
relaylm_doc_type: runbook
relaylm_authority: twin_extraction_offline_tooling_operations
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: offline_tooling
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - twin_extraction_prompts.md
relaylm_not_authoritative_for:
  - MEM/SOUL bootstrap ingestion
  - RelaySLP or RelayMEM runtime behavior
  - repository-wide current implementation status
---
# Twin Extraction 運用ランブック

## 適用範囲

このランブックは `scripts/relaylm_twin_extraction_preprocess.py` / `scripts/relaylm_twin_extraction_batch_runner.py` / `scripts/relaylm_twin_extraction_merge.py` の実行手順を扱う。抽出プロンプト仕様の正は [Twin Extraction プロンプト仕様](twin_extraction_prompts.md) であり、本ランブックはその実行手順のみを記録する。

これらのツールは caller-invoked で有界なオフライン前処理ツールであり、RelayLMランタイム(`relaylm/` パッケージ)には接続しない。daemon化・ポーリング・スケジューラは持たない。MEM/SOULへの書き込みやbootstrap投入は行わない(このツールが作るのはレビュー用の単一JSONまで)。

## 重要な運用上の注意: private_only素材をクラウドLLMに送らない

`--source` の前処理結果には、病院経営に関する第三者特定情報や経営数値の生データが含まれうる。抽出プロンプトの `sensitivity: private_only` 判定はバッチ実行後(LLM応答後)にしか付かないため、**バッチ実行前の時点で、private_only になりうる素材を含むバッチをクラウドLLMエンドポイントに送るかどうかは事前に決めておくこと**。判断に迷うバッチは、`--base-url` にローカルLLM(既定は LM Studio `http://127.0.0.1:1234/v1`)のみを使うこと。

## 実行手順

### 0. 入出力ディレクトリ

実データ・抽出結果・バッチファイルはコミットしない。`.gitignore` の `runtime/twin_extraction/` 配下に入出力を置く運用を推奨する:

```bash
mkdir -p runtime/twin_extraction/{x,chatgpt}/batches runtime/twin_extraction/results
```

### 1. 前処理

X archive:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_preprocess.py \
  --source x \
  --input /path/to/data/tweets.js \
  --out-dir runtime/twin_extraction/x/batches \
  --since 2024-01 --until 2026-07 \
  --batch-size 150
```

ChatGPTエクスポート:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_preprocess.py \
  --source chatgpt \
  --input /path/to/conversations.json \
  --out-dir runtime/twin_extraction/chatgpt/batches \
  --batch-size 4
```

標準出力のサマリは件数のみ(`total_seen` / `kept` / `excluded_retweet` / `excluded_date_filtered` / `excluded_empty` / `excluded_other` / `batch_count` / `batch_size`)。ポスト・発話本文は一切含まれない。

### 2. dry-run(LLM呼び出しなし)

本実行の前に、送信予定のバッチ数とペイロードサイズのみを確認する:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_batch_runner.py \
  --model <model-name> \
  --prompt-file scripts/twin_extraction_prompts/x_extraction_prompt.txt \
  --batch-dir runtime/twin_extraction/x/batches \
  --out-dir runtime/twin_extraction/x/run \
  --dry-run
```

### 3. 本実行(有界)

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_batch_runner.py \
  --base-url http://127.0.0.1:1234/v1 \
  --model <model-name> \
  --prompt-file scripts/twin_extraction_prompts/x_extraction_prompt.txt \
  --batch-dir runtime/twin_extraction/x/batches \
  --out-dir runtime/twin_extraction/x/run \
  --max-batches 20 \
  --retries 1
```

ChatGPT側は `--prompt-file scripts/twin_extraction_prompts/chatgpt_extraction_prompt.txt` と `--batch-dir runtime/twin_extraction/chatgpt/batches` を指定して同様に実行する。

応答JSONのパースに失敗したバッチは `--out-dir/failed/` に記録され、実行は続行される(fail-closed)。成功したバッチの抽出結果は `--out-dir/results/` に保存される。進行ログはバッチID・件数・status・所要時間のみで、本文は出力されない。

X側とChatGPT側は別々の `--out-dir` で実行する。両方とも `results/` 配下のファイル名は `batch_0001.result.json` のように同じ採番なので、**手動でファイルをコピーして1つのディレクトリにまとめてはいけない**(片方が他方を上書きし、そのソースの抽出結果がマージから消える)。マージCLIは `--results-dir` を複数回指定できるので、そのまま両方のディレクトリを渡す。

### 4. マージ

複数ソースをまとめて1つのレビューJSONにする場合、`--results-dir` を繰り返し指定する(ファイルを事前にコピーする必要はない):

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_merge.py \
  --results-dir runtime/twin_extraction/x/run/results \
  --results-dir runtime/twin_extraction/chatgpt/run/results \
  --out runtime/twin_extraction/twin_extraction_review.json
```

単一ソースのみをマージする場合は `--results-dir` を1回だけ指定する:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_merge.py \
  --results-dir runtime/twin_extraction/x/run/results \
  --out runtime/twin_extraction/twin_extraction_review.json
```

出力される `twin_extraction_review.json` はレビュー用の単一JSON。`style_observations` は自動統合されない(descriptionが類似していても分離したまま保持し、evidence_ids件数からstrengthのみ再計算する)。`fact_candidates` は `statement` と `type` の完全一致のみ統合し、`sensitivity` が1件でも `private_only` の場合は統合後の候補全体を `private_only` に倒す。曖昧一致統合は行わない。

### 5. 本人レビューと後続経路

このツールが作るのは `twin_extraction_review.json` まで。MEM/SOULへの書き込み・bootstrap投入・SLP経路への接続は行わない。[Twin Extraction プロンプト仕様](twin_extraction_prompts.md) の「集約・レビュー手順」に従って手動レビューし、承認された素材のみを別途CW-A1形式・MEM bootstrap経路に反映する。

### 6. review import bridge (P1出力 -> CW-A4 governed import source)

`twin_extraction_review.json` をマージした後、`scripts/relaylm_twin_review_import_bridge.py` でFile-first Character Workspace(CW-A4)が読める `.relaylm/sources/imports/twin-extraction/` へ変換できる。このbridgeもP1と同じくcaller-invoked / bounded / offline / runtime-non-contactであり、`relaylm` パッケージをimportしない。MEM/SOUL/REL/Primary MEMへは直接書き込まない。uppercase source(`SOUL.md`など)も直接書き換えない。

既定ではdry-runで、何も書き込まない:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge.py \
  --review runtime/twin_extraction/twin_extraction_review.json \
  --workspace-root runtime/characters/relm \
  --dry-run
```

`sensitivity: general` のfact_candidatesのみ、明示オプションで承認してimport sourceへ書き出す:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge.py \
  --review runtime/twin_extraction/twin_extraction_review.json \
  --workspace-root runtime/characters/relm \
  --write-imports \
  --approved-facts general-only
```

`private_only` のfact_candidatesは既定では出力されず、このbridgeに自動昇格経路もない。`style_observations` は本リビジョンではdry-run projection/カウントのみで、ファイルへは書き出さない(`--approved-styles` は `none` のみ受け付ける)。stdoutは常にcontent-freeなJSON集計(件数とreason_idsのみ)で、statement/description本文・絶対パス・生の例外テキストは出力されない。書き込み先ファイル名は内容から決定されるstableなハッシュで、timestamp/UUIDは使わない。既存ファイルが同一内容ならidempotent、異なる内容ならfail-closedでconflictエラーになる(exit code非0、部分書き込みなし)。

書き出された `.relaylm/sources/imports/twin-extraction/fact-<hash>.json` は `role: "user"` を持つため、CW-A4(`plan_character_workspace_slp_candidates` の dry-run)がuser assertion evidenceとして読み、memory/scene/relationship候補のdry-run projectionに使える。CW-A4への書き込み(`write_candidates=True`)や後続のMEM/SOUL反映は、このbridgeの範囲外であり別途明示的に実行する。

## 検証コマンド

```bash
python -m compileall relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge_cw_a4_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave8/twin_extraction_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
PYTHONPATH=.:scripts python scripts/relaylm_documentation_current_boundary_smoke.py
```

すべてフィクスチャのみで完結し、LLM・ネットワーク・実アーカイブを必要としない。
