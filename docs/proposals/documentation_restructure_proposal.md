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

今回の再構成は単なる directory move ではない。次の 3 層を同時に正規化する。

1. **情報アーキテクチャ** — 文書の権威・役割・lifecycle
2. **文書モデル** — 構造・粒度・命名・自己完結性
3. **検証モデル** — code / contract / test / evidence の追跡可能性

採用する原則は次のとおり。

1. 文書の第一軸を権威・役割に統一する。
2. 規範文書と非規範的 evidence を path で分離する。
3. 全 active 文書へ 1 文書 1 権威を適用する。
4. 旧 path、redirect stub、旧 enum、legacy exception、hybrid 例外を残さない。
5. 意味のある意思決定・検証証跡だけを `evidence/` に残し、低価値 snapshot は Git history に委ねる。
6. exact contract の規範文言は逐語移送し、旧 blob との照合 receipt を残す。
7. architecture は既存文書の 1:1 移動ではなく、system / subsystem / concept の型へ synthesis する。
8. code から導出可能な reference は生成または自動照合し、手書き複製を canonical にしない。
9. cutover は v0.1 frozen tag receipt 確定直後に開始する。

残す移行安全装置は次の 3 つだけとする。

- ADR の一度限り canonicalization
- placement / granularity tie-breaker
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

### P4: architecture 文書の構造と粒度が不統一である

同じ `stable_architecture` に、system-wide pipeline、subsystem 横断 boundary、単一概念 note が混在する。別の文書では contract、implementation evidence、config reference、次 phase planning が 1 ファイルに併存する。

### P5: milestone ID が恒久概念名として残っている

`ACG-4`、`O1D2`、`I1GE` 等の slice ID は実装 evidence には有用だが、恒久 architecture / contract の canonical name としては不安定である。

### P6: code と docs の重複 authority がある

config field、enum、API signature、artifact path を手書き docs が複製すると、実装変更時に静かな drift が起こる。

### P7: 用語・例示・言語の統治が弱い

canonical glossary がなく、同じ語が複数文書で再定義される。例示と規範、英語 canonical と日本語説明の境界も一意でない。

### P8: semantic audit が個別 path に依存する

現在の audit は多数の required path を列挙している。単に新 path へ定数を差し替えるだけでは hard-code debt が再発する。

### P9: 互換機構そのものが長期負債になる

redirect stub、legacy manifest、旧 enum 併存、hybrid 例外を導入すると、新体系の CI と AI reading rule が恒久的に複雑になる。

## 4. 最終構成

```text
docs/
├── README.md
├── PROJECT_STATUS.md
├── DOCUMENTATION_MODEL.md
├── assets/                        # README image 等の非 Markdown 補助資産
├── templates/                     # 文書型テンプレート。非権威
├── proposals/                     # 未決定 proposal のみ
├── guides/                        # task-oriented how-to / tutorial
├── reference/                     # config / CLI / API / glossary / interpretation
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

`docs/assets/` と `docs/templates/` は document role directory ではない。

- `assets/`: front matter / document type invariant の対象外。参照切れ・未使用 asset を検証する。
- `templates/`: template 自体は権威を持たない。生成された文書側が authority と lifecycle を持つ。

最終構成に含めないもの:

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
- release / validation receipt
- accepted / rejected / withdrawn proposal
- cutover path-map / verification receipt
- 後続 ADR から説明上必要な重大な旧 decision record

### 5.2 Git history のみに残すもの

- MVP-0〜48 等、現在の意思決定・検証に使われない milestone snapshot
- 重複 handoff summary
- 役割を失った progress memo
- active authority を複製する旧 architecture / contract
- 古い README の証跡一覧
- 一時的 compatibility note

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
- generated reference + hand-written duplicate authority

非規範の背景説明は必要最小限にし、独立 authority がある場合は canonical link のみにする。

## 8. Architecture document model

architecture は単一テンプレートへ平板化せず、粒度の異なる 3 型へ統一する。

### 8.1 System architecture

対象:

- RelayLM 全体
- primary runtime pipeline
- character workspace 全体
- memory system 全体

必須 section:

```text
Purpose
System context
Responsibility map
Canonical data/control flow
Ownership boundaries
System-wide invariants
Failure and privacy boundaries
Extension points
Related subsystem architecture
Related contracts
Non-goals
```

個別関数 signature、全 config field、PR 番号、完了状況は含めない。

### 8.2 Subsystem / component architecture

対象:

- RelayMEM
- RelayCTX
- RelaySCN
- scheduler
- source compiler 等、独立して変更される単位

必須 section:

```text
Purpose
Scope
Inputs and outputs
Owned responsibilities
Explicit non-responsibilities
Internal components
State/lifecycle model
Data/control flow
Failure and recovery boundary
Privacy/security boundary
Stable invariants
Related contracts
```

実装成果物一覧や次 phase handoff は evidence / planning へ分離する。

### 8.3 Concept / policy design

対象:

- pinned memory
- scene-aware memory scope
- relationship target
- candidate governance 等、component 横断の一概念

必須 section:

```text
Problem
Definition
Scope
Semantic model
Invariants
Interaction with components
Trade-offs
Non-goals
Related architecture and contracts
```

concept note は短くてよいが、特定 milestone の完了報告を兼ねない。

### 8.4 粒度判定

次のいずれかに該当すれば別文書へ分割する。

- owner が異なる
- update trigger が異なる
- 一方だけ独立して置き換えられる
- exact contract と rationale が混在する
- current implementation と target architecture が混在する
- milestone ID を除くと成立しない部分と、恒久概念として成立する部分が混在する
- 各部分が独立 consumer / verification を持つ

文書の行数だけでは分割しない。ただし 1 文書に複数の primary responsibility map、複数 lifecycle、または多数の独立 H2 がある場合は synthesis review の警告対象とする。

### 8.5 命名と内部構造

恒久文書は安定した概念名を使う。

```text
architecture/reference-intent-analysis.md
contracts/reference-intent-candidate.md
evidence/implementation/acg4-reference-intent-analyzer.md
```

slice ID は evidence / planning にのみ残す。

`architecture/` 内では第二軸として domain を使用できる。

```text
architecture/
├── README.md
├── system-overview.md
├── pipeline-responsibilities.md
├── runtime/
├── memory/
├── character-workspace/
├── relationship/
└── scene/
```

domain directory は repository 全体の第一軸ではなく、architecture collection 内の navigation 軸である。

### 8.6 Architecture synthesis

既存 architecture を 1:1 で新 path へ移さない。各旧文書を次のいずれかへ分類する。

- `moved`: 構造・粒度とも新モデルに適合
- `split`: 複数 authority / 粒度へ分割
- `synthesized`: 複数旧文書から新 canonical architecture を構成
- `absorbed`: 既存 canonical 文書へ統合
- `rebuilt_verbatim`: contract 規範 block を逐語移送
- `deleted_git_history_only`: active value がなく削除

synthesis では exact contract の文言を paraphrase しない。architecture rationale の再記述は許可するが、採用元を migration receipt に残す。

## 9. Cross-cutting documentation model

### 9.1 Canonical vocabulary

`reference/glossary.md` を RelayLM 用語の canonical home とする。

- component 名、artifact 名、state、scope、authority 用語を定義する。
- 各文書は glossary を参照し、同じ用語を独自再定義しない。
- 文書固有の狭い定義は、その文書内で glossary との差分を明記する。
- 廃止語・旧称は active 本文へ併記せず migration receipt または glossary の旧称表へ限定する。

### 9.2 File naming

- lowercase kebab-case を基本とする。
- 恒久 active 文書の filename に phase / wave / PR / date を入れない。
- date / milestone ID は evidence で許可する。
- `design`, `architecture`, `contract`, `guide`, `runbook`, `report` を内容と矛盾して付けない。
- `README.md` は collection router に限定する。

### 9.3 Document opening contract

AI が部分取得しても誤読しないよう、active 文書の冒頭に次を置く。

```text
Title
Authority summary
Status: current | target
Purpose
Scope
Non-goals
Canonical related authorities
```

タイトル直後の短い authority summary は、「この文書が何について authoritative で、何について authoritative でないか」を自然文で示す。

### 9.4 Stable headings and chunking

- 1 ファイル 1 H1
- H2 は意味のある retrieval boundary にする。
- `Overview`, `Details`, `Misc` のような曖昧 heading を避ける。
- 「上記」「以下の通り」だけに依存せず、section 単体で主語と対象を識別できるようにする。
- 巨大文書は行数ではなく authority / owner / update trigger / lifecycle の分離可能性で split する。
- table や code block の前後に、それが規範か例示かを明記する。

### 9.5 Duplication policy

- exact field、enum、default、status、path、gate を複数 active 文書へコピーしない。
- architecture は contract の意味と関係を説明し、exact 値は canonical contract へリンクする。
- guide は reference をリンクし、option table を複製しない。
- status summary は `PROJECT_STATUS.md` をリンクし、各文書に進捗表を持たない。
- unavoidable な短い引用は source link と「non-authoritative excerpt」を明記する。

### 9.6 Generated and source-derived documentation

次は code / schema から生成または自動照合する。

- config field / default / bounds
- public enum
- CLI option
- schema field
- workflow / smoke inventory
- public API signature
- artifact path inventory

source of truth は code、schema、または exact contract のいずれか一つに固定する。

生成物には次を付ける。

```yaml
relaylm_generated: true
relaylm_generated_from:
  - relaylm/config.py
relaylm_generator: scripts/...
```

生成物を手編集しない。生成不能な解説は別の hand-written guide / architecture に置く。

### 9.7 Code / contract / test traceability

current contract と重要 architecture は、機械可読な関連を持つ。

```yaml
relaylm_code_sources:
  - relaylm/...
relaylm_verified_by:
  - scripts/...
  - .github/workflows/...
relaylm_related_contracts:
  - ../contracts/...
```

- code source が変更された PR では関連 docs / verification の更新要否を CI が表示する。
- `verified_by` は「この文書全体が正しい」と保証せず、検証される boundary を本文または test 名で特定する。
- test のない rationale 文書へ偽の verification を付けない。

### 9.8 Diagrams

- normative flow diagram は Mermaid 等の text source を repository に保持する。
- PNG / WebP は presentation asset であり、diagram source の代替 authority にしない。
- diagram は本文と同じ component 名・state 名を使う。
- image のみで invariant を表現せず、本文または contract にも記述する。
- accessibility 用の短い text summary を付ける。

### 9.9 Examples and fixtures

- example は原則 non-authoritative。
- valid / invalid / edge case を区別する。
- conformance fixture として authority を持つ場合は、`relaylm_example_role: conformance_fixture` を明示し test から参照する。
- raw user text、memory、protected source、credential、private path を例示へ入れない。
- example config を canonical default table として扱わない。

### 9.10 Language and localization

- 1 文書につき canonical language は一つとする。
- full translation copy を別 authority として並立させない。
- root README の英日 pair は例外として維持し、リンク・主要主張の同期を検証する。
- code / API / field / internal identifier は英語に固定する。
- 日本語 summary を追加する場合は non-authoritative summary と明記し、canonical 本文へリンクする。
- 同一文書内で説明言語を頻繁に切り替えない。

### 9.11 Ownership and freshness

current / target active 文書は次を必須とする。

- owner
- update trigger
- authoritative scope
- non-authoritative scope
- related authority
- current status source

calendar-based `last reviewed` のみで freshness を判定しない。code、contract、decision、release gate の変更 trigger により stale candidate を検出する。

owner 不在、trigger 不在、incoming link 不在の active 文書は orphan warning とする。

### 9.12 Navigation and discoverability

- `docs/README.md` は role-based entry router。
- collection `README.md` は collection-local router。
- global exhaustive ledger は作らない。
- active 文書は最低 1 つの router または canonical parent から到達可能にする。
- evidence index は collection-local かつ summary 中心とし、active authority と混在させない。
- orphan link、duplicate title、duplicate authority key を CI で検出する。

### 9.13 Security and privacy

- docs / examples / evidence へ content-bearing runtime data を保存しない。
- private path、token、claim、credential、user identity、protected source、memory body は sanitize する。
- security boundary は architecture に意味を、contract に exact prohibition を置く。
- public diagnostic の content-free invariant は docs generation / example にも適用する。

### 9.14 Versioning

- main 上の active docs は main の current / target authority。
- release 時点の docs は tag / release receipt で固定する。
- repository 内に v0.1 / v0.2 の active docs copy tree を並立させない。
- version 差分説明は release notes または migration guide に置く。

## 10. Exact contract の逐語移送

contract 再構築は本 cutover で最も意味リスクが高いため、次を必須とする。

### 10.1 規範セクション

次を規範 block として扱う。

- must / must not / required / forbidden を含む境界
- field / schema / enum / gate / status / transition
- artifact path / exact key / exact value
- safety invariant
- semantic audit が anchor check する文字列
- test / workflow が literal reference する contract 文言

### 10.2 移送規則

1. 規範 block は旧 blob から逐語移送する。
2. whitespace 正規化以外の paraphrase を禁止する。
3. 書き直してよいのは非規範の背景、実装経緯、重複説明のみ。
4. 規範文言変更は docs cutover ではなく別 contract change PR にする。
5. current と失効 boundary が混在する場合は code / test と照合し、採用根拠を receipt に記録する。

### 10.3 検証

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

## 11. Metadata の一括正規化

### 11.1 旧 enum を残さない

cutover 完了時に次を全面禁止する。

- `historical_after_merge`
- 一時的な旧 document type
- metadata 無しの active / evidence 文書
- legacy profile / exception list

全 evidence は新形式へ正規化する。

```yaml
relaylm_status: historical
relaylm_evidence_status: merged
relaylm_source_pr: 123
relaylm_source_commit: <sha>
relaylm_recorded_on: 2026-07-11
```

### 11.2 provenance の自動生成

cutover script が Git history から次を生成する。

- first-introduced commit
- source PR（取得可能な場合）
- recorded-on
- original blob SHA
- destination
- disposition

source PR を一意に取得できない場合は `null` とし、推測値を入れない。commit SHA と recorded-on は必須とする。

## 12. ADR と proposal lifecycle

### 12.1 ADR canonicalization

- 新規 ADR は `NNNN-short-title.md`。
- 既存 ADR は cutover 中に一度だけ deterministic に番号化する。
- 番号は `relaylm_decided_on`、作成 commit 順、旧 path 順で割り当てる。
- redirect stub は作らない。
- receipt に old path、old blob SHA、new path を残す。
- cutover 後の ADR canonical path は不変。

ADR は implementation status と decision status を分離する。

```yaml
relaylm_doc_type: adr
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-11
relaylm_supersedes: []
relaylm_superseded_by: null
```

`accepted` は implemented を意味しない。

### 12.2 Proposal lifecycle

```text
proposals/<name>.md
  ├── accepted -> ADR + normative docs + evidence/proposals/
  ├── rejected -> decision link + evidence/proposals/
  └── withdrawn -> reason + evidence/proposals/
```

本提案は現行モデルに `proposal` 型がないため、この PR では `strategic_vision` を pre-adoption compatibility type として明示例外使用し、`relaylm_proposal_status: under_review` を持つ。

採択 PR で `proposal` 型を定義し、本ファイルを最初の lifecycle conformance case として移動する。

```yaml
relaylm_doc_type: proposal
relaylm_status: historical
relaylm_proposal_status: accepted
relaylm_decision_source: ../../adr/NNNN-documentation-information-architecture.md
relaylm_evidence_status: frozen
```

## 13. Cutover の実施時期

hard cutover は、**v0.1 final main-HEAD validation と frozen tag receipt が確定した直後**に開始する。

v0.1 validation 中は採択準備、inventory、template、dry-run script、synthesis plan の作成まで許すが、canonical docs path の移動・削除は行わない。

## 14. Cutover sequence

複数 PR を使う場合、repository 全体では一時的に新旧構造が混在する。ただし互換機構を追加しない。

- redirect stub を作らない。
- 旧 enum を新規文書で許容しない。
- legacy manifest / exception list を作らない。
- 最終 directory invariant は最終 enforcement PR で有効化する。
- 各領域 PR は担当領域を完結させ、同一 authority を旧 path と新 path へ二重保持しない。

### Cutover 1: evidence 移動・削除分類

- completion report、audit、evaluation result、release receipt を `evidence/` へ移動
- Git history のみに残す snapshot を削除
- provenance metadata を自動生成
- frozen migration receipt を開始

### Cutover 2A: architecture inventory

各旧 architecture / design / handoff を次で棚卸しする。

- actual authority
- system / subsystem / concept 粒度
- current / target
- contract block の有無
- implementation evidence の有無
- owner / update trigger
- proposed disposition
- canonical destination

### Cutover 2B: target architecture graph

新しい canonical architecture の一覧と依存 graph を先に確定する。

- system architecture
- subsystem architecture
- concept / policy design
- related contract
- parent / child relation
- incoming router

ファイルを先に移してから構造を考えない。

### Cutover 2C: architecture synthesis

- moved / split / synthesized / absorbed / deleted を実行
- slice ID を evidence へ退避
- stable concept filename へ正規化
- architecture から exact contract、status、handoff、成果物一覧を分離
- source document / section mapping を receipt に記録

### Cutover 2D: その他 active 文書の再分類

- planning / reference / strategy / guides / operations / evaluation / release へ移動
- glossary、templates、router index を作成
- generated / hand-written authority を分離
- example / fixture role を明示

### Cutover 3: contract 統合・再構築

- architecture 内 exact contract を `contracts/` へ集約
- 規範 block を逐語移送
- digest / anchor / test 照合
- verification receipt を完成

### Cutover 4: cleanup と全面 enforcement

- 旧 directory を削除
- 旧 enum を禁止
- metadata coverage 100%
- old docs path literal reference 0
- duplicate authority / orphan active doc 0
- generated docs drift 0
- directory / document-shape invariant CI を有効化
- `docs/assets/` と `docs/templates/` を support directory として allowlist
- frozen migration receipt を確定

## 15. Frozen migration receipt

`evidence/migrations/` に、この cutover を説明する 1 つの frozen receipt を残す。

```yaml
- old_path: docs/architecture/acg4_reference_intent_analyzer.md
  old_blob_sha: <sha>
  disposition: synthesized | absorbed | split | moved | rebuilt_verbatim | deleted_git_history_only
  new_paths:
    - docs/architecture/reference-intent-analysis.md
    - docs/contracts/reference-intent-candidate.md
    - docs/evidence/implementation/acg4-reference-intent-analyzer.md
  source_commit: <sha>
  source_pr: 123
  source_sections:
    - old_heading: Implemented boundary
      new_path: docs/contracts/reference-intent-candidate.md
  verification: exact_match | structure_reviewed | metadata_normalized | not_applicable
```

必須区分:

- `moved`
- `split`
- `synthesized`
- `absorbed`
- `rebuilt_verbatim`
- `deleted_git_history_only`

contract は normative digest before / after と anchor verification を追加する。receipt は旧 path 互換を提供せず、provenance と synthesis trace のみを提供する。

## 16. Semantic audit

cutover 完了後の audit は directory invariant と document-shape invariant を中心とする。

### 16.1 Placement and lifecycle

- 全 active / evidence Markdown に front matter
- path と document type が一致
- exact contract は `contracts/` のみ
- architecture に handoff、dated result、roadmap、completion evidence がない
- proposals に accepted / rejected / withdrawn proposal がない
- evidence は `historical`
- `historical_after_merge` を拒否
- old top-level directory を拒否

### 16.2 Shape and granularity

- architecture subtype が system / subsystem / concept のいずれか
- subtype ごとの必須 section がある
- active filename に phase / wave / PR / date を含めない
- duplicate title / duplicate authority key を拒否
- one-document/one-authority violation を検出
- system / subsystem / concept の parent relation が有効
- slice ID を含む active architecture を warning または fail

### 16.3 Traceability and drift

- code-derived reference が generator output と一致
- contract anchor / normative digest が一致
- `relaylm_code_sources` と `relaylm_verified_by` の path が存在
- stale trigger candidate を報告
- router から到達不能な active doc を拒否
- old docs path literal reference 0
- README asset link green
- bilingual root README の主要 link / section parity を検証

### 16.4 AI readability and safety

- active 文書に authority summary / purpose / scope / non-goals
- 1 H1
- ambiguous generic heading を warning
- example の authoritative role が明示
- content-bearing private data pattern を拒否
- diagram source / text summary の存在を検証

個別安全境界 anchor は、新 invariant が同等以上の保証を持つまで削除しない。

## 17. 完了条件

### 構造

- final tree が §4 と一致
- `docs/mvp/`、`docs/relaysoul/`、top-level `docs/smoke/`、`docs/tools/` が存在しない
- legacy / milestones / redirect stub が存在しない
- assets と templates の support boundary が明示される

### 権威

- exact contract の canonical home は `contracts/` のみ
- active 文書は 1 文書 1 権威
- `PROJECT_STATUS.md` が repository-wide current implementation authority
- accepted ADR と implemented behavior が分離
- generated reference の source authority が一意

### Architecture quality

- canonical architecture graph が存在
- architecture は system / subsystem / concept の型に適合
- milestone-ID active architecture が 0
- architecture / contract / evidence / planning の混載が 0
- synthesis source mapping が receipt に残る

### Metadata and verification

- front matter coverage 100%
- `historical_after_merge` 0
- legacy exception / manifest 0
- duplicate authority key 0
- orphan active doc 0
- generated docs drift 0
- contract normative digest 一致
- frozen receipt が全旧文書の disposition を説明

## 18. 採択後の実装単位

### Preparation PR（v0.1 receipt 前でも可）

- documentation information architecture ADR
- `DOCUMENTATION_MODEL.md` 新モデル草案
- document templates
- canonical glossary draft
- architecture inventory / target graph
- placement / granularity tie-breaker
- provenance / generator / normative-block extraction script
- cutover dry-run artifact
- 本 proposal の lifecycle 定義

canonical path はまだ変更しない。

### Cutover PR 群（v0.1 frozen tag receipt 後）

1. evidence migration and snapshot deletion
2. architecture inventory finalization and synthesis
3. other active document reclassification
4. contract verbatim reconstruction and verification
5. old tree removal and full CI enforcement

本提案自身は Preparation PR または最初の cutover PR で正式な `proposal` 型へ切り替え、adopting ADR と結び付けて `evidence/proposals/` へ移す。

## 19. 採択判断

この hard cutover は、旧 docs path の継続利用よりも次を優先する。

- AI 検索時の権威分離
- 設計文書の構造・粒度の一貫性
- code / contract / test / evidence の追跡可能性
- generated reference の drift 防止
- canonical vocabulary と stable naming
- CI の長期保守性
- current / target / evidence の誤読防止
- pre-v0.1 のうちに情報アーキテクチャ負債を解消すること

結論として、RelayLM では「検索と運用のための互換性は捨てるが、意思決定と検証の証拠は残す」に加え、「配置だけでなく文書の型・粒度・生成元・検証関係まで正規化する」を正式方針とする。
