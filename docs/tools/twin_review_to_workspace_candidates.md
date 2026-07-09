---
relaylm_doc_type: runbook
relaylm_authority: twin_review_to_cw_a4_workspace_candidate_flow
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: offline_tooling
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - twin_extraction_prompts.md
  - twin_extraction_runbook.md
  - ../architecture/cw_a4_slp_workspace_maintenance_candidates.md
relaylm_not_authoritative_for:
  - Twin Extraction P1 preprocessing/batch-runner/merge tool execution steps
  - PR2 review import bridge internal write/security contract
  - CW-A4 SLP candidate/proposal planning contract
  - MEM/SOUL bootstrap or RelaySLP runtime behavior
  - repository-wide current implementation status
---
# Twin Review Import -> CW-A4 Workspace Candidate Flow

## 適用範囲

このランブックは、P1 Twin Extraction が作る `twin_extraction_review.json` から、PR2 review import bridge (`scripts/relaylm_twin_review_import_bridge.py`) を経由して、CW-A4 (`scripts/relaylm_cw_a4_workspace_slp_candidates.py` / `relaylm.character_workspace.plan_character_workspace_slp_candidates`) が memory/scene/relationship candidate・proposal を計画するところまでの**連携手順のみ**を扱う。

各ツール自体の詳細な実行手順の正はそれぞれ以下にある。本書はそれらを繋ぐ全体フローと確認手順のみを記録し、重複しては説明しない:

- P1前処理・バッチ実行・マージの詳細手順: [Twin Extraction 運用ランブック](twin_extraction_runbook.md)
- 抽出プロンプト仕様: [Twin Extraction プロンプト仕様](twin_extraction_prompts.md)
- review import bridge の書き込み境界・安全性の詳細: [Twin Extraction 運用ランブック 6章](twin_extraction_runbook.md#6-review-import-bridge-p1出力--cw-a4-governed-import-source)
- CW-A4 candidate/proposal planningの契約: [CW-A4 SLP Workspace Maintenance Candidates](../architecture/cw_a4_slp_workspace_maintenance_candidates.md)

このランブックが**行わないこと**は [非ゴール](#非ゴール) の通り。特に、MEM/SOUL/RELへの直接適用・Primary MEM semantic page作成・uppercase source (`SOUL.md` など) の直接書き換えはこのフローのどの段階でも行われない。

## 前提

- P1 Twin Extraction ツール群 (`scripts/relaylm_twin_extraction_preprocess.py` / `_batch_runner.py` / `_merge.py`) と PR2 review import bridge (`scripts/relaylm_twin_review_import_bridge.py`) が利用可能であること。
- CW-A4 CLI (`scripts/relaylm_cw_a4_workspace_slp_candidates.py`) が利用可能であること。
- CW-A4 は `.relaylm/sources/conversations`, `.relaylm/sources/corrections`, `.relaylm/sources/imports` をsource evidenceとして読む。PR2 bridgeの出力先である `.relaylm/sources/imports/twin-extraction/*.json` もこれに含まれる。
- CW-A4 の `--write-candidates` は allowlisted な candidate/proposal artifacts のみを書く:
  - `memory/inbox/*.md`
  - `scenes/_inbox/*.md`
  - `relationships/_inbox/*.md`
  - `proposals/memory/*.json`
  - `proposals/scene/*.json`
  - `proposals/relationship/*.json`
- CW-A4 は uppercase source、`.relaylm/build`、`.relaylm/state`、`.relaylm/queue` を直接変更しない境界を持つ。この境界はPR2 bridge単体でも、この連携フロー全体でも維持される。

## 全体フロー

```text
P1前処理 (X archive / ChatGPT export -> batches)
  -> P1 batch runner (local LM Studio / OpenAI-compatible endpoint)
  -> P1 merge (twin_extraction_review.json)
  -> 本人レビュー・承認
  -> PR2 bridge --write-imports --approved-facts general-only
       (.relaylm/sources/imports/twin-extraction/*.json)
  -> CW-A4 --dry-run (candidate/proposal projectionの確認)
  -> CW-A4 --write-candidates (allowlisted inbox/proposal artifactsの書き込み)
  -> 生成物の人間レビュー
  -> (必要な場合のみ) CW-A2 compiler rebuild
```

MEM/SOUL/RELへの反映は、この図のどのステップにも含まれない。それは別途、明示的な承認フローで行う。

## 実行手順

### 1. P1前処理・バッチ実行・マージ

[Twin Extraction 運用ランブック](twin_extraction_runbook.md) の「実行手順」1〜4節に従い、X archive / ChatGPT export から `twin_extraction_review.json` を作る。この段階はローカル前処理・オフラインLLM呼び出しのみで、`relaylm` パッケージにもRelayLMランタイムにも接続しない。

### 2. 本人レビュー

`twin_extraction_review.json` を本人が確認し、どの `fact_candidates` を import source として承認するかを決める。`sensitivity: private_only` の項目はこの段階以降もimport sourceへは書き出されない(bridgeに自動昇格経路がない)。`style_observations` は本リビジョンではdry-run projectionのみで、ファイルへは一切書き出されない。

### 3. PR2 bridge: review -> import source

承認済みの `general` fact のみを、CW-A4が読める governed import source に変換する。

dry-run(既定、何も書き込まない):

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge.py \
  --review runtime/twin_extraction/twin_extraction_review.json \
  --workspace-root runtime/characters/relm \
  --dry-run
```

承認済み書き込み:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge.py \
  --review runtime/twin_extraction/twin_extraction_review.json \
  --workspace-root runtime/characters/relm \
  --write-imports \
  --approved-facts general-only
```

書き込み先は `runtime/characters/relm/.relaylm/sources/imports/twin-extraction/fact-<hash>.json`。この段階の書き込み・安全性の詳細([O_EXCL]/no-clobber commit/all-or-nothingロールバック/metadata検証など)は [Twin Extraction 運用ランブック 6章](twin_extraction_runbook.md#6-review-import-bridge-p1出力--cw-a4-governed-import-source) を参照。stdoutは常にcontent-freeな件数集計のみ。

### 4. CW-A4 dry-run

書き出されたimport sourceを、CW-A4がuser assertion evidenceとしてどう読むかを、何も書き込まずに確認する:

```bash
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_candidates.py \
  --workspace-root runtime/characters/relm \
  --dry-run
```

出力JSONの `source_evidence_count` が0より大きく、`memory_candidates_count` または `memory_inbox_additions_count` が1以上であることを確認する。この段階でもファイルは一切書き込まれない。

### 5. CW-A4 write-candidates

dry-runの内容で問題なければ、allowlisted な candidate/proposal artifacts を書き込む:

```bash
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_candidates.py \
  --workspace-root runtime/characters/relm \
  --write-candidates
```

### 6. 生成物確認

`--write-candidates` が書き込みうる先は以下のみ:

- `memory/inbox/`
- `scenes/_inbox/`
- `relationships/_inbox/`
- `proposals/memory/`
- `proposals/scene/`
- `proposals/relationship/`

これ以外のパス(uppercase source、`.relaylm/build`、`.relaylm/state`、`.relaylm/queue` を含む)は変更されない。生成された各ファイルは、次節の人間レビューを経るまで暫定候補(inbox/proposal)のままであり、MEM/SOUL/RELの正式な内容ではない。

### 7. 明示的な人間レビューが必要

このフローが作るのはあくまで candidate/proposal であり、承認待ちの中間生成物である。生成された `memory/inbox/*.md` / `scenes/_inbox/*.md` / `relationships/_inbox/*.md` / `proposals/**/*.json` は、本人が内容を確認し、個別に承認する前提で扱う。承認・MEM/SOUL/RELへの反映の具体的な経路は本書の範囲外であり、別途明示的な作業として行う。

### 8. CW-A2 compiler rebuildが必要になる場合

CW-A4はCW-A2の `.relaylm/build/**` 投影を直接更新しない。承認済みの変更をランタイム投影(KV-cacheティアなど)へ反映する必要がある場合、[CW-A4 SLP Workspace Maintenance Candidates](../architecture/cw_a4_slp_workspace_maintenance_candidates.md) が示す通り、CW-A2 compilerを別途明示的に実行する。この再ビルドはこのランブックの範囲外であり、このフロー自体はCW-A2 compilerを呼び出さない。

## 非ゴール

このフローは以下を一切行わない:

- MEM/SOUL/RELへの直接適用
- Primary MEM semantic page作成
- M3e/M3g writer呼び出し
- RelaySLP queue作成
- O2/O3 worker起動
- `SOUL.md` / `STYLE.md` / `MEMORY.md` などuppercase sourceの直接書き換え
- `private_only` fact_candidateの自動採用
- レビューUI
- fuzzy merge
- 実X/ChatGPTログのコミット
- Cloudflare/mobile dogfood入口
- user management / family tester

## 検証コマンド

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_extraction_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_import_bridge_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_twin_review_to_cw_a4_flow_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_candidates_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_review_fix_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

すべてフィクスチャのみで完結し、LLM・ネットワーク・実アーカイブを必要としない。
