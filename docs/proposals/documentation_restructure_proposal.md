---
relaylm_doc_type: strategic_vision
relaylm_authority: documentation_restructure_proposal_only
relaylm_status: target
relaylm_proposal_status: under_review
relaylm_pre_adoption_type_compatibility: strategic_vision
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - restructure decision is made
  - v0.1 frozen tag receipt is finalized
  - documentation cutover completes
relaylm_not_authoritative_for:
  - current documentation placement rules
  - current runtime behavior
  - implementation phase status
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM ドキュメント情報アーキテクチャ hard cutover 提案

作成日: 2026-07-11

本ドキュメントは提案であり、採択されるまで現行の配置規則([DOCUMENTATION_MODEL.md](../DOCUMENTATION_MODEL.md))を変更しない。

## 0. 結論

RelayLM は単独メンテナ、pre-v0.1、主要読者が本人と AI エージェントであり、旧 docs path や旧 metadata enum を公開互換 API として維持する合理性が小さい。したがって、ドキュメント再構成は互換移行ではなく **hard cutover** とする。

採用する原則は次のとおり。

1. **文書の第一軸を権威・役割に統一する。**
2. **規範文書と非規範的 evidence を path で分離する。**
3. **新体系では全 active 文書へ 1 文書 1 権威を適用する。**
4. **旧 path、redirect stub、旧 enum、legacy exception、hybrid 例外を残さない。**
5. **意味のある意思決定・検証証跡だけを `evidence/` に残し、価値のない snapshot は Git history に委ねる。**
6. **exact contract の規範文言は逐語移送し、旧 blob との照合 receipt を残す。**
7. **cutover は v0.1 frozen tag receipt 確定直後に開始する。**

残す移行安全装置は次の 3 つだけとする。

- ADR の一度限り canonicalization
- placement tie-breaker
- contract の逐語移送・文字列照合

## 1. 適用条件

この hard cutover 方針は、次の repository 条件を前提とする。

- 単独メンテナである。
- v0.1 未満であり、docs path を安定 API として公開していない。
- 主な consumer が repository owner と AI coding agent である。
- root `README.md`、`README_ja.md`、`docs/README.md`、`docs/PROJECT_STATUS.md` の主要入口は維持する。
- README 画像等の `docs/assets/` は安定した補助資産 path として維持する。
- 過去の path を確認する必要がある場合は Git history を利用できる。

これらの条件が変わった後は、将来の path 変更に別の互換方針を採用してよい。本提案は今回の一度限りの再基礎化を対象とする。

## 2. 再現可能な現状基準

定量基準は PR #549 の base commit `fe8f4652390b6a4c3f0c1a81e6051f09e8cb4ae5` とする。

- `docs/` 配下 Markdown: **319 ファイル**
- 本提案追加後: **320 ファイル**
- front matter 無し: **151 ファイル**
  - `docs/architecture/`: 46
  - `docs/mvp/`: 61
  - その他: 44
- `relaylm_status` 主な分布:
  - `current`: 103
  - `historical_after_merge`: 45
  - `target`: 17

この inventory は cutover planning の基準であり current runtime authority ではない。実施 PR では commit 固定の machine-readable inventory を再生成する。

## 3. 現状の問題

### P1: authority が path から判別できない

`docs/architecture/` に恒久設計、target、exact contract、handoff、audit、evaluation、roadmap、vision、compatibility stub が同居している。

### P2: exact contract の canonical home が二重である

`docs/contracts/` と architecture 内 contract の両方が許容され、AI が正確な境界を探索する場所が一意でない。

### P3: current / target / historical の検索空間が混在する

同一語彙を持つ active 文書と過去証跡が近接し、部分取得時に現役権威が希釈される。

### P4: semantic audit が個別 path に依存する

現在の audit は多数の required path を列挙している。単に新 path へ定数を差し替えるだけでは hard-code debt が再発する。

### P5: 互換機構そのものが長期負債になる

redirect stub、legacy manifest、旧 enum 併存、hybrid 例外を導入すると、新体系の CI と AI reading rule が恒久的に複雑になる。

## 4. 最終構成

```text
docs/
├── README.md
├── PROJECT_STATUS.md
├── DOCUMENTATION_MODEL.md
├── assets/                        # README image 等の非 Markdown 補助資産。stable path
├── proposals/                     # 未決定 proposal のみ
├── guides/                        # task-oriented how-to / tutorial
├── reference/                     # config / CLI / API / current-target interpretation
├── strategy/                      # 非拘束の長期方向・product principles
├── planning/                      # execution plan / roadmap / migration sequencing
├── architecture/                  # 恒久的な構造・責務・ownership
├── contracts/                     # exact schema / gate / API / invariant
├── adr/                           # append-only decision log
├── operations/                    # runbook / smoke / tool operation
├── evaluation/                    # rubric / method / scenario / current synthesis
├── release/                       # current release criteria / readiness
└── evidence/                      # 非規範的証跡
    ├── implementation/
    ├── waves/
    ├── evaluations/
    ├── releases/
    ├── proposals/
    └── migrations/
```

`docs/assets/` は document role directory ではない。Markdown front matter / document type invariant の対象外とし、参照切れと未使用 asset の検証対象には含める。

次は最終構成に含めない。

- `docs/mvp/`
- `docs/relaysoul/`
- top-level `docs/smoke/`
- top-level `docs/tools/`
- `evidence/legacy/`
- `evidence/milestones/`
- redirect stub collection
- superseded architecture / contract の専用保存 tree

## 5. 保存するものと削除するもの

### 5.1 repository に残す evidence

- completion report
- wave convergence audit
- dated evaluation result
- release receipt
- validation receipt
- accepted / rejected / withdrawn proposal
- cutover path-map / verification receipt
- 後続 ADR から説明上必要な重大な旧 decision record

### 5.2 Git history のみに残すもの

- MVP-0〜48 など、現在の意思決定・検証に使われない milestone snapshot
- 重複した handoff summary
- 役割を失った progress memo
- active authority を複製している旧 architecture / contract
- 古い README の証跡一覧
- 一時的な compatibility note

`docs/mvp/` の snapshot 群を含む約 60 ファイルは、inventory で個別確認したうえで削除候補として明示分類する。暗黙に消さず、frozen migration receipt に `deleted_git_history_only` として記録する。

## 6. 配置 tie-breaker

### 6.1 planning / reference / strategy / architecture / contracts

次の順で判定する。

1. 時期、依存順、open gate、実装順、migration sequence を規定する → `planning/`
2. current / target / compatibility の読み分けを参照資料として説明する → `reference/`
3. 非拘束の将来像、可能性、post-release direction を示す → `strategy/`
4. 時期に依存しない責務、構造、ownership、design principle を規定する → `architecture/`
5. exact schema、gate、artifact、API、must / must-not invariant を規定する → `contracts/`

`current_target_migration_guide.md` は、実行順ではなく current / target / compatibility の解釈が主である限り `reference/` とする。

`analyzer_candidate_governance.md` のような hybrid は、新体系では主権威ごとに分割する。

### 6.2 guides / reference

- 前提、手順、期待結果、troubleshooting flow → `guides/`
- field、option、command、schema、default、constraint → `reference/`
- guide から reference をリンクし、仕様表を複製しない。

### 6.3 最終判定

判断が残る場合は次の順で決める。

1. exact invariant の有無
2. 読者の行動を直接規定するか
3. 時期・順序に依存するか
4. current implementation の解釈に使われるか
5. 各部分が独立して更新されるか

複数の主権威が残る文書は分割する。

## 7. 1 文書 1 権威

hard cutover 後は、既存文書を含めて次の兼務を認めない。

- architecture + exact contract
- implementation handoff + current contract
- evaluation method + dated result
- release readiness + frozen receipt
- proposal + accepted decision
- strategic vision + committed execution plan

非規範の背景説明は必要最小限にし、独立 evidence がある場合は canonical link のみにする。

## 8. Exact contract の逐語移送

contract 再構築は本 cutover で最も意味リスクが高いため、次を必須とする。

### 8.1 規範セクションの定義

次を規範セクションとして扱う。

- must / must not / required / forbidden を含む境界
- field / schema / enum / gate / status / transition の定義
- artifact path / exact key / exact value
- safety invariant
- semantic audit が anchor check している文字列
- test / workflow が literal reference している contract 文言

### 8.2 移送規則

1. 規範セクションは旧 blob から**逐語移送**する。
2. whitespace 正規化以外の paraphrase を禁止する。
3. 書き直してよいのは非規範の背景、実装経緯、重複説明のみとする。
4. 規範文言を変更する必要がある場合は docs cutover ではなく、別の contract change PR として扱う。
5. 旧文書に current と失効 boundary が混在する場合は、current authority と code / test を照合し、採用根拠を receipt に記録する。

### 8.3 検証

migration script は旧 blob と新 contract から規範 block を抽出し、正規化後の文字列または digest を比較する。

receipt には少なくとも次を残す。

```yaml
old_path: docs/architecture/example_contract.md
old_blob_sha: <sha>
new_path: docs/contracts/example.md
disposition: rebuilt_verbatim
normative_block_count: 4
normative_digest_before: <sha256>
normative_digest_after: <sha256>
verification: exact_match
```

既存 semantic anchor check は cutover 中も維持し、新 directory invariant へ置き換えるのは最終 enforcement PR とする。

## 9. Metadata の一括正規化

### 9.1 旧 enum を残さない

次を cutover 完了時に全面禁止する。

- `historical_after_merge`
- 一時的な旧 document type
- metadata 無しの active / evidence 文書
- legacy profile / exception list

全 evidence は次の新形式へ正規化する。

```yaml
relaylm_status: historical
relaylm_evidence_status: merged
relaylm_source_pr: 123
relaylm_source_commit: <sha>
relaylm_recorded_on: 2026-07-11
```

### 9.2 provenance の自動生成

front matter 無し文書を手作業で補完しない。cutover script が Git history から次を生成する。

- first-introduced commit
- source PR（merge commit / GitHub association から取得可能な場合）
- recorded-on
- original blob SHA
- destination
- disposition

source PR を一意に取得できない場合は `relaylm_source_pr: null` とし、推測値を入れない。commit SHA と recorded-on は必須とする。

これにより legacy manifest による新旧判定自体を不要にする。

## 10. ADR の一度限り canonicalization

- 新規 ADR は `NNNN-short-title.md` とする。
- 既存非番号 ADR は cutover 中に一度だけ deterministic に番号化する。
- 番号は `relaylm_decided_on`、作成 commit 順、旧 path 順で割り当てる。
- redirect stub は作らない。
- cutover receipt に old path、old blob SHA、new path を残す。
- cutover 完了後、ADR canonical path は不変とする。

ADR は二軸状態を持つ。

```yaml
relaylm_doc_type: adr
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-11
relaylm_supersedes: []
relaylm_superseded_by: null
```

`accepted` は implemented を意味しない。current implementation は `PROJECT_STATUS.md` と exact contract が示す。

## 11. Proposal lifecycle

```text
proposals/<name>.md
  ├── accepted -> ADR + normative docs + evidence/proposals/
  ├── rejected -> decision link + evidence/proposals/
  └── withdrawn -> reason + evidence/proposals/
```

本提案は現行モデルに `proposal` 型がないため、この PR では `relaylm_doc_type: strategic_vision` を pre-adoption compatibility type として明示的に例外使用し、同時に `relaylm_proposal_status: under_review` を持つ。これにより現行 enum を壊さず、front matter consumer は本ファイルを未決定 proposal と判定できる。

採択 PR で `proposal` 型を定義し、本ファイルを最初の lifecycle conformance case として次へ移す。

```yaml
relaylm_doc_type: proposal
relaylm_status: historical
relaylm_proposal_status: accepted
relaylm_decision_source: ../../adr/NNNN-documentation-information-architecture.md
relaylm_evidence_status: frozen
```

## 12. Cutover の実施時期

hard cutover は、**v0.1 final main-HEAD validation と frozen tag receipt が確定した直後**に開始する。

理由:

- v0.1 readiness assessment が参照する path を validation 前後で混在させない。
- frozen tag receipt に旧 documentation structure の検証境界を固定できる。
- cutover 後の main は次リリースの新構造として明確に開始できる。

v0.1 validation 中は本提案の採択準備、inventory、dry-run script の作成までは許すが、canonical docs path の移動・削除は行わない。

## 13. Cutover sequence

複数 PR を使う場合、repository 全体では一時的に新旧構造が混在する。ただし、その期間にも互換機構を追加しない。

- redirect stub を作らない。
- 旧 enum を新規文書で許容しない。
- legacy manifest / exception list を作らない。
- 最終 directory invariant は最終 enforcement PR で有効化する。
- 各領域 PR は自分が担当する領域を完結させ、旧 path と新 path を同一領域で二重保持しない。

順序は固定する。

### Cutover 1: evidence 移動・削除分類

- completion report、audit、evaluation result、release receipt を `evidence/` へ移動
- Git history のみに残す snapshot を削除
- provenance metadata を自動生成
- frozen path-map receipt を開始

意味リスクが最小のため最初に行う。

### Cutover 2: active 文書の再分類

- planning / reference / strategy / architecture / guides / operations / evaluation / release へ移動
- hybrid active 文書を role ごとに分割
- root / collection index を router 化

### Cutover 3: contract 統合・再構築

- architecture 内 exact contract を `contracts/` へ集約
- 規範 block を逐語移送
- digest / anchor / test 照合
- verification receipt を完成

意味リスクが最大のため、先行 inventory と新 directory が安定した後に行う。

### Cutover 4: cleanup と全面 enforcement

- 旧 directory を削除
- 旧 enum を禁止
- metadata coverage 100% を要求
- repository-wide old path literal reference を 0 にする
- directory invariant CI を有効化
- `docs/assets/` を唯一の document-role 外 top-level support directory として allowlist する
- frozen migration receipt を確定

## 14. Frozen migration receipt

`evidence/migrations/` には、この cutover を説明する 1 つの frozen receipt を残す。

各旧文書について次を記録する。

```yaml
- old_path: docs/mvp/wave7/example.md
  old_blob_sha: <sha>
  disposition: moved | deleted_git_history_only | split | rebuilt_verbatim
  new_paths:
    - docs/evidence/waves/wave7/example.md
  source_commit: <sha>
  source_pr: 123
  verification: metadata_normalized | link_checked | exact_match | not_applicable
```

必須区分:

- `moved`: 内容を実質変更せず移動
- `deleted_git_history_only`: repository から削除し Git history のみで保持
- `split`: role ごとに複数文書へ分割
- `rebuilt_verbatim`: exact contract の規範 block を逐語移送して再構築

contract の場合は normative digest before / after と anchor verification を追加する。

この receipt は旧 path 互換を提供しない。git blame / rename 追跡の喪失を補償する provenance record としてのみ使う。

## 15. Semantic audit

cutover 完了後の audit は directory invariant 中心とする。

- 全 Markdown に front matter がある。
- path と `relaylm_doc_type` が一致する。
- exact contract は `contracts/` にのみ存在する。
- architecture に handoff、audit、dated result、roadmap、vision がない。
- proposals に accepted / rejected / withdrawn proposal がない。
- evidence は `relaylm_status: historical` を持つ。
- `historical_after_merge` を拒否する。
- 旧 top-level directory を拒否する。
- `docs/assets/` は非 Markdown support directory として明示 allowlist し、document type invariant を適用しない。
- repository 内の旧 docs path literal reference を拒否する。
- ADR は decision status を持つ。
- contract anchor と normative digest verification が成功している。

個別安全境界 anchor は、新 invariant が同等以上の保証を持つことを確認するまで削除しない。

## 16. 完了条件

### 構造

- final tree が §4 と一致する。
- `docs/mvp/`、`docs/relaysoul/`、top-level `docs/smoke/`、`docs/tools/` が存在しない。
- `evidence/legacy/`、`evidence/milestones/`、redirect stub が存在しない。
- `docs/assets/` の既存 README asset link が維持される。

### 権威

- exact contract の canonical home は `contracts/` のみ。
- active 文書は 1 文書 1 権威。
- `PROJECT_STATUS.md` が repository-wide current implementation の唯一の authority。
- accepted ADR と implemented behavior が分離されている。

### Metadata

- active / evidence Markdown の front matter coverage が 100%。
- `historical_after_merge` が 0 件。
- legacy exception / manifest が存在しない。

### 検証

- docs link check が green。
- semantic audit が green。
- documentation boundary smoke が green。
- README image asset link が green。
- old docs path literal reference が 0。
- contract normative digest の before / after が一致する。
- frozen migration receipt が全旧文書の disposition を説明する。

## 17. 採択後の実装単位

### Preparation PR（v0.1 receipt 前でも可）

- documentation information architecture ADR
- `DOCUMENTATION_MODEL.md` の新モデル草案
- placement tie-breaker
- inventory / provenance / normative-block extraction script
- cutover dry-run artifact
- 本 proposal の lifecycle 定義

canonical path はまだ変更しない。

### Cutover PR 群（v0.1 frozen tag receipt 後）

1. evidence migration and snapshot deletion
2. active document reclassification
3. contract verbatim reconstruction and verification
4. old tree removal and full CI enforcement

本提案自身は Preparation PR または最初の cutover PR で正式な `proposal` 型へ切り替え、adopting ADR と結び付けたうえで `evidence/proposals/` へ移す。

## 18. 採択判断

この hard cutover は、旧 docs path の継続利用よりも次を優先する判断である。

- AI 検索時の権威分離
- directory invariant の単純性
- CI の長期保守性
- current / target / evidence の誤読防止
- pre-v0.1 のうちに情報アーキテクチャ負債を解消すること

結論として、RelayLM では「検索と運用のための互換性は捨てるが、意思決定と検証の証拠は残す」を正式方針とする。