---
relaylm_doc_type: strategic_vision
relaylm_authority: documentation_restructure_proposal_only
relaylm_status: target
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - restructure decision is made
  - migration phase completes
relaylm_not_authoritative_for:
  - current documentation placement rules
  - current runtime behavior
  - implementation phase status
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM ドキュメント情報アーキテクチャ再設計提案

作成日: 2026-07-11

本ドキュメントは提案であり、採択されるまで現行の配置規則([DOCUMENTATION_MODEL.md](../DOCUMENTATION_MODEL.md))を変更しない。

## 0. 結論

RelayLM のドキュメント再構成は、単純な「読者別ディレクトリへの整理」や「古い文書の archive」ではなく、次の原則で設計し直す。

1. **第一軸は文書の権威・役割**とする。パスを見れば、その文書が guide、reference、strategy、plan、architecture、contract、decision、operation、evaluation、release、evidence のどれか分かるようにする。
2. **規範文書と非規範的証跡をパスで分離**する。実装記録、completion report、wave audit、評価実行結果、release receipt は、作成時点から `docs/evidence/` に置く。
3. **1 文書 1 権威**を原則とする。実装 handoff と現役 contract、設計説明と exact schema、評価方法と実行結果を同じ文書に兼務させない。
4. **ADR と proposal に独立したライフサイクルを持たせる**。ADR の採択と実装済み状態を混同せず、proposal を採択後も現役文書として残さない。
5. **索引はルーターに限定**し、証跡の巨大な重複リストを置かない。各 collection に 1 つだけ local index を持たせる。
6. **移行は段階的に行い、各 PR で link-check と documentation boundary smoke を green に保つ**。

現行モデルの front matter、権威の優先順位、`PROJECT_STATUS.md` の単一性、two-stage wave flow は維持する。ただし、ディレクトリ設計、ADR/proposal/evidence の状態モデル、索引規則は改める。

## 1. 再現可能な現状基準

本提案の定量基準は PR #549 の base commit `fe8f4652390b6a4c3f0c1a81e6051f09e8cb4ae5` とする。

- base commit の `docs/` 配下 Markdown: **319 ファイル**
- 本提案ファイルを含む PR head: **320 ファイル**
- base commit で front matter を持たないファイル: **151 ファイル**
  - `docs/architecture/`: 46
  - `docs/mvp/`: 61
  - その他: 44
- base commit の `relaylm_status` 主な分布:
  - `current`: 103
  - `historical_after_merge`: 43
  - `target`: 17
- PR head では本提案が `target` を 1 件追加するため、`target` は 18 となる。

初回調査では docs パスをハードコードするスクリプトと workflow が多数確認されている。ただし、移行規模の確定値として手作業の grep 件数を固定せず、Phase 0 で commit 固定の inventory を機械生成し、その出力を各移行 PR の基準にする。

## 2. 現状診断

### P1: `docs/architecture/` が複数の権威を兼務している

現在の `docs/architecture/` には、少なくとも次が同居している。

- 恒久的な architecture
- target architecture
- exact contract
- implementation handoff
- wave convergence audit
- evaluation record / consolidation
- execution plan / roadmap
- strategic vision
- compatibility stub

同じ RelayMEM、recall、gate、Primary、SOUL Lab などの語彙を持つ文書が、現在の設計、将来目標、実装時点の証跡という異なる権威で混在するため、AI の部分取得時に現役権威が希釈される。

### P2: contract の置き場が二重である

現行規則は exact contract の置き場として `docs/contracts/` と architecture 内の dedicated contract の両方を許している。このため、「正確な挙動境界を探す場所」が一意でない。

### P3: plan、strategy、architecture が分離されていない

`project_execution_plan.md` は実行順序、`post_v01_strategic_direction_vision.md` は非拘束の長期方向、`pipeline_responsibility_design.md` は恒久設計であり、権威が異なる。これらを architecture という 1 つの検索空間に置くべきではない。

### P4: guide と reference が混在・散在している

導入・設定・接続・troubleshooting・UI 利用方法・設定項目リファレンスが、`docs/` 直下、`docs/smoke/`、`docs/tools/`、`apps/soul-lab/README.md` に分散している。また、手順書と仕様リファレンスが区別されていない。

### P5: 実装証跡の索引が重複している

wave や slice の証跡リストが複数の README に重複し、収束 PR が複数索引を同期編集する。これは two-stage flow が避けようとしている共有ファイル競合を、索引側で再発させている。

### P6: `history/` という名前では作成時点の意味を正しく表せない

completion report は実装 PR の branch 上で作成され、merge 後に証跡となる。validation receipt や release receipt も「古いから保存する」のではなく、「規範ではなく証拠だから保存する」。したがって、トップレベルの分離軸は age を表す `history/` より、authority を表す `evidence/` の方が正確である。

### P7: ADR の採択状態と実装状態が混同され得る

現在の ADR は `relaylm_status: current` でありながら、本文では「Accepted as target architecture. Implementation remains pending.」とされている。ADR が採択済みであることと、挙動が current implementation であることは別の状態である。

### P8: semantic audit が個別パスへ強く依存している

現行の documentation audit は required metadata 対象や wave index、release readiness、operations docs のパスを個別に列挙している。移行時には単なるリンク修正だけでなく、ディレクトリ種別に基づく検証へ変更しなければ、新しい構造でも同じ hard-code debt が再発する。

## 3. 設計原則

### 3.1 パスが答えること

文書パスは、次の問いに答える。

> この文書は何のために存在し、どの種類の権威を持つか。

current / target / compatibility は front matter で表し、非規範的な実装・評価・release 証跡かどうかは `evidence/` への配置で表す。

### 3.2 1 文書 1 権威

次の組合せは原則として分割する。

- architecture + exact contract
- implementation handoff + current contract
- evaluation method + dated evaluation result
- release readiness assessment + frozen release receipt
- proposal + accepted decision
- strategic vision + committed execution plan

説明のために別種別へ言及する場合は、内容を複製せず canonical document へリンクする。

### 3.3 active document と evidence の扱い

- active directories の文書は full front matter を必須とする。
- `evidence/legacy/` はディレクトリ自体が非規範的であるため、未整備の既存 front matter を一括補完しなくてもよい。
- 新規または substantive に更新する evidence 文書には、最小限の provenance metadata を要求する。
- Git 履歴だけでは convergence audit、評価結果、release receipt、移行対応表を代替できないため、必要な証跡は repository に保持する。

### 3.4 索引はルーターであり台帳ではない

- `docs/README.md` は主要入口だけを示す。
- 各トップレベル directory の `README.md` は、その collection の canonical local index とする。
- wave 証跡は `evidence/waves/wave<N>/README.md` にだけ列挙する。
- `evidence/README.md` は category router とし、全証跡の巨大なリストを持たない。
- 同じ exhaustive list を複数の README に複製しない。

## 4. 提案する最終構成

```text
docs/
├── README.md                      # 薄い入口。読者別 start route のみ
├── PROJECT_STATUS.md              # 現在実装済み境界の唯一の repository-wide authority
├── DOCUMENTATION_MODEL.md         # 文書種別、metadata、配置、AI reading rules
│
├── proposals/                     # 未決定の変更提案。採択後は残さない
│   └── README.md
│
├── guides/                        # task-oriented: 導入、接続、設定、操作、troubleshooting
│   └── README.md
│
├── reference/                     # supported config / CLI / user-facing API の参照資料
│   └── README.md                  # internal exact contract を複製せずリンクする
│
├── strategy/                      # 非拘束の長期方向、product principles、post-release vision
│   └── README.md
│
├── planning/                      # execution plan、roadmap、migration sequencing
│   ├── README.md
│   ├── project_execution_plan.md
│   └── current_target_migration_guide.md
│
├── architecture/                  # current / accepted-target の恒久設計のみ
│   ├── README.md
│   ├── pipeline_responsibility_design.md
│   ├── file_first_character_workspace_design.md
│   └── <durable-design>.md
│
├── contracts/                     # exact schema / gate / artifact / API / invariant の唯一の置き場
│   ├── README.md
│   └── <exact-contract>.md
│
├── adr/                           # append-only decision log。accepted / superseded を同じ系列で保持
│   ├── README.md
│   └── NNNN-<decision>.md
│
├── operations/                    # operator runbook、smoke procedure、tooling operation
│   ├── README.md
│   ├── smoke/
│   └── tools/
│
├── evaluation/                    # rubric、scenario、harness contract、current evidence synthesis
│   ├── README.md
│   ├── methods/
│   ├── scenarios/
│   └── templates/
│
├── release/                       # 現在進行中の release criteria / readiness assessment
│   └── README.md
│
└── evidence/                      # 非規範的・追記中心の証跡
    ├── README.md                  # category router のみ
    ├── implementation/            # wave 外の slice handoff / completion record
    ├── waves/
    │   └── wave<N>/
    │       ├── README.md          # 当該 wave の唯一の証跡索引
    │       ├── <slice>_completion_report.md
    │       └── convergence_audit.md
    ├── evaluations/               # 日付・model・commit 固定の実行結果
    ├── releases/                  # frozen release receipt / 過去 readiness assessment
    ├── proposals/                 # accepted / rejected / withdrawn proposal
    ├── migrations/                # path map、移行 receipt、compatibility stub 台帳
    ├── milestones/                # 旧 MVP snapshot など
    ├── superseded/
    │   ├── architecture/
    │   └── contracts/
    └── legacy/                    # 既存体系から分類不能な文書。新規作成先にはしない
```

`docs/mvp/`、`docs/relaysoul/`、`docs/smoke/`、`docs/tools/` は最終的にトップレベル directory として解消する。コンポーネント固有であることは配置軸にせず、文書の役割で配置する。

## 5. 配置ルール

| 文書の役割 | canonical home | 補足 |
|---|---|---|
| repository-wide current implementation status | `PROJECT_STATUS.md` | 現状、open gate、active caveat、次候補だけを持つ |
| 未決定の構造変更・大規模提案 | `proposals/` | 採択・却下後は `evidence/proposals/` へ移す |
| 利用者が目的を達成する手順 | `guides/` | how-to / tutorial |
| 設定項目、CLI、外部利用面の参照 | `reference/` | exact internal contract のコピーを作らない |
| 非拘束の長期方向・原則 | `strategy/` | current status や execution authorization ではない |
| 実行順序、roadmap、migration plan | `planning/` | architecture と分離する |
| 恒久的な責務・構造・ownership | `architecture/` | handoff、audit、dated result を置かない |
| exact schema、gate、API、artifact、invariant | `contracts/` | 唯一の置き場 |
| 設計判断と rationale | `adr/` | runtime status authority ではない |
| runbook、smoke、tool operation | `operations/` | 実行結果は evidence へ |
| 評価方法、rubric、scenario、current synthesis | `evaluation/` | 日付付き run result は evidence へ |
| 現在の release criteria / readiness | `release/` | 完了 receipt は evidence へ |
| PR / wave / validation / migration の証跡 | `evidence/` | 作成時点から非規範的 |

配置に迷う hybrid document は「最も近い directory へ置く」のではなく、権威ごとに分割する。

## 6. ADR のゼロベース運用

### 6.1 ADR を `adr/` に残す理由

ADR は current architecture のコピーではなく、意思決定の append-only log である。superseded ADR も supersession chain の一部なので、単純に `evidence/` へ移動しない。`adr/` というパス自体が「現在挙動ではなく decision rationale」であることを示す。

### 6.2 命名と不変性

- 新規 ADR は `NNNN-short-title.md` とする。
- Accepted ADR の decision 本文は、誤字、リンク、metadata、supersession pointer を除き原則として書き換えない。
- 方針変更は既存 ADR の全面改稿ではなく、新 ADR で supersede する。
- ADR index は `adr/README.md` の 1 箇所とし、proposed / accepted / superseded / rejected を区別する。

### 6.3 状態を二軸に分ける

ADR には既存の `relaylm_status` に加え、次の type-specific metadata を導入する。

```yaml
relaylm_doc_type: adr
relaylm_status: target              # current / target / historical
relaylm_decision_status: accepted   # proposed / accepted / superseded / rejected
relaylm_decided_on: 2026-07-11
relaylm_supersedes: []
relaylm_superseded_by: null
```

- `relaylm_decision_status` は意思決定の状態を表す。
- `relaylm_status` はその決定が対象とする挙動の current / target / historical を表す。
- `accepted` は実装済みを意味しない。
- 実装済み境界は `PROJECT_STATUS.md` と exact contract が示す。

現在の `character_conditioned_belief_model.md` は本文上「accepted target / implementation pending」であるため、移行時に `relaylm_status: target` と `relaylm_decision_status: accepted` へ正規化する。

### 6.4 ADR の遷移

```text
proposed
  ├── accepted  ──(new ADR supersedes)──> superseded
  ├── rejected
  └── withdrawn
```

rejected / withdrawn を採用する場合は、`relaylm_decision_status` の許容値と DOCUMENTATION_MODEL を同時に更新する。ADR が accepted になっても、その ADR 自体を contract や current implementation receipt として扱わない。

## 7. proposal のライフサイクル

proposal は decision より前の検討物であり、採択後の権威を持たない。

```text
proposals/<name>.md
  ├── accepted -> 新規 ADR + normative docs 更新 + evidence/proposals/ へ移動
  ├── rejected -> decision link を付けて evidence/proposals/ へ移動
  └── withdrawn -> 理由を付けて evidence/proposals/ へ移動
```

proposal 用に次の metadata を追加する。

```yaml
relaylm_doc_type: proposal
relaylm_status: target
relaylm_proposal_status: under_review  # draft / under_review / accepted / rejected / withdrawn
relaylm_decision_source: null
```

本提案を採択する場合も、このファイルを配置規則の永久 authority に昇格させず、documentation architecture ADR と `DOCUMENTATION_MODEL.md` に決定内容を移し、本提案は `evidence/proposals/` へ移す。

## 8. evidence の運用

### 8.1 `history/` ではなく `evidence/` とする理由

- completion report は source PR と同時に作られるため、誕生時点では「過去」ではない。
- validation receipt は現在の gate 判定に参照されても、runtime authority ではない。
- release receipt は長期間参照されるが、current release plan ではない。
- 重要なのは文書の年齢ではなく、**規範か証拠か**である。

### 8.2 evidence metadata

新規 evidence には type に応じて次を要求する。

```yaml
relaylm_status: historical
relaylm_evidence_status: merged      # draft / merged / validated / invalidated / frozen
relaylm_source_pr: 549
relaylm_source_commit: <sha>
relaylm_recorded_on: 2026-07-11
```

既存の `historical_after_merge` は移行互換値として当面許容し、新規文書では `historical` + `relaylm_evidence_status` を優先する。これにより lifecycle と merge event を 1 つの enum に混在させない。

### 8.3 evidence index

- wave ごとに local `README.md` を作り、slice report と convergence audit をそこだけに列挙する。
- wave close 後は、その directory を link fix と provenance correction 以外で変更しない。
- `evidence/README.md` は waves、evaluations、releases などへのリンクだけを持つ。
- 全 evidence を 1 つの中央 README に列挙しない。中央台帳は新たな競合点になるためである。

## 9. two-stage wave flow への写像

フローは維持するが、文書の責務を明確にする。

### Stage 1: implementation PR

implementation PR が所有する文書は次だけとする。

- production code と直接結合する test / workflow
- runtime field と原子的に出荷すべき exact contract
- `evidence/waves/wave<N>/<slice>_completion_report.md`
- wave 外であれば `evidence/implementation/<area>/<slice>_completion_report.md`

implementation handoff を architecture に作らない。恒久設計が変わる場合は architecture、exact boundary が変わる場合は contract、PR が何をしたかは evidence として別ファイルにする。

### Stage 2: convergence PR

convergence PR は次を行う。

1. merged code、completion report、exact contract を照合する。
2. `PROJECT_STATUS.md`、`planning/project_execution_plan.md`、影響する architecture / contract を更新する。
3. `evidence/waves/wave<N>/convergence_audit.md` を追加する。
4. 当該 wave の `README.md` を完成させる。
5. root README や architecture README に wave 証跡一覧を複製しない。
6. convergence merge まで次 wave / release gate を開かない。

## 10. front matter と CI の方針

### 10.1 full metadata を必須にする範囲

次の active directories は全 Markdown で full metadata を必須にする。

```text
proposals/
strategy/
planning/
architecture/
contracts/
adr/
operations/
evaluation/
release/
```

`guides/` と `reference/` も新規・更新ファイルから必須にする。`evidence/legacy/` は path semantics で非規範性を保証し、151 ファイルへの一括 front matter 追加を migration prerequisite にしない。

### 10.2 directory policy による検証

semantic audit は、個別ファイルの列挙中心から次の directory invariant 中心へ移す。

- architecture に handoff / completion report / evaluation record / audit / strategic vision を置かない。
- contracts 以外に exact contract を新規作成しない。
- proposals に accepted / rejected proposal を残さない。
- evidence を current runtime authority として宣言しない。
- ADR は decision status を持つ。
- active directories は required metadata を持つ。
- prohibited top-level directory を無断追加しない。

個別の安全境界 anchor check は維持するが、documentation information architecture の検証を hard-coded path list だけに依存させない。

### 10.3 inventory の機械生成

Phase 0 で inventory script を追加し、commit ごとに少なくとも次を出力できるようにする。

- path
- document type
- status
- authority
- front matter 有無
- inbound Markdown links
- script / workflow からの literal path reference
- proposed destination
- ambiguity / manual-review flag

inventory は migration の入力であり current authority ではないため、CI artifact または `evidence/migrations/` の commit 固定 receipt として扱う。

## 11. 移行計画

### Phase 0: 決定と guardrail。ファイル移動なし

1. 本提案を採択する documentation architecture ADR を作成する。
2. `DOCUMENTATION_MODEL.md` に新しい document role、ADR/proposal/evidence metadata、配置規則を追加する。
3. commit 固定の docs inventory と path-reference inventory を生成する。
4. 新規 contract、completion report、proposal、strategic vision について新ルールを即時適用する。
5. semantic audit に「新たな配置違反を増やさない」検証を追加する。

### Phase 1: 新規負債を止め、索引を router 化

1. `proposals/`、`strategy/`、`planning/`、`reference/`、`operations/`、`evidence/` と各 README を作成する。
2. `docs/README.md` を start route のみに縮小する。
3. `docs/architecture/README.md` から wave / slice 証跡一覧を削除する。
4. 新規 wave report を `evidence/waves/` に置く。
5. 新規 exact contract は `contracts/` 以外に置けないよう CI で制約する。

### Phase 2: evidence の機械的移動

1. `docs/mvp/wave*/` の completion report を `evidence/waves/` へ移す。
2. wave convergence audit、validation receipt、dated evaluation result を対応する evidence collection へ移す。
3. `historical_after_merge` の implementation handoff を `evidence/implementation/` へ移す。
4. `docs/architecture/archive/` を `evidence/superseded/` または `evidence/legacy/` へ分類する。
5. 旧 MVP snapshot を `evidence/milestones/` へ移す。
6. 同一 PR 内で Markdown link、script、workflow、semantic audit の参照を更新する。
7. `evidence/migrations/` に old path -> new path map と検証 receipt を保存する。

移動判定は `relaylm_status` だけに依存せず、document type、命名、source PR、current index からの参照、script/workflow の inbound reference を合わせて行う。曖昧な hybrid document は Phase 2 で移動せず Phase 3 で分割する。

### Phase 3: active knowledge の再分類と分割

1. `project_execution_plan.md` と migration guide を `planning/` へ移す。
2. strategic vision と product principle を `strategy/` へ移す。
3. `architecture/*_contract.md` を contract と implementation evidence に分割し、exact boundary を `contracts/` へ集約する。
4. `docs/relaysoul/` を役割別に architecture / contracts / strategy / evidence へ分解する。
5. user-facing how-to を `guides/`、設定・CLI リファレンスを `reference/` へ移す。
6. smoke / tools を `operations/` へ移し、実行結果を evidence に分離する。
7. evaluation method / current synthesis と dated result を分離する。
8. release readiness と frozen receipt を分離する。
9. ADR metadata を正規化し、既存 decision の target / current / superseded を監査する。

### Phase 4: compatibility cleanup と enforcement

1. 旧トップレベル directory を解消する。
2. compatibility stub の期限と削除条件を確認し、不要な stub を削除する。
3. active directories の front matter coverage を 100％にする。
4. directory invariant を CI で必須化する。
5. repository-wide hard-coded old docs path が 0 であることを確認する。

## 12. compatibility stub の規則

全移動元に redirect stub を置くと、古い検索空間と重複文書を恒久化するため、stub は例外とする。

stub を置けるのは次だけとする。

- repository root README や外部利用者から参照される入口
- automation が段階移行を必要とする path
- current authority の既知の旧 canonical path

各 stub は次を持つ。

- canonical destination
- created-on
- removal condition または removal-after release
- `redirect_stub` type
- current status や contract 本文を複製しない

## 13. 完了条件

### 構造

- `architecture/` に implementation handoff、completion report、wave audit、dated evaluation result、strategic vision、execution plan がない。
- exact contract の canonical home が `contracts/` のみである。
- `planning/`、`strategy/`、`guides/`、`reference/`、`operations/` の責務が重複しない。
- `docs/mvp/`、`docs/relaysoul/`、トップレベルの `docs/smoke/`、`docs/tools/` が解消されている。
- `evidence/legacy/` が新規文書の作成先として使われていない。

### 権威

- `PROJECT_STATUS.md` が現在実装済み境界の唯一の repository-wide authority である。
- accepted ADR と implemented behavior が metadata 上で区別される。
- proposal は採択後に current authority として残らない。
- 1 文書が implementation evidence と exact contract を兼務していない。

### 索引

- root README は主要入口だけを持つ。
- exhaustive evidence list は collection ごとに 1 箇所だけである。
- wave 証跡は各 wave directory の README にのみ列挙される。
- convergence PR が複数の重複索引を同期編集しない。

### 検証

- active directories の front matter coverage が 100％である。
- docs link check、semantic audit、documentation boundary smoke が green である。
- old docs path の script / workflow literal reference が 0 である。
- directory と document type の不整合を CI が fail closed で検出する。

## 14. 検討した代替案と却下理由

### A. 読者別だけで分類する

同じ開発者が plan、architecture、contract、ADR、evaluation を読むため、reader だけでは権威を区別できない。README の導線には読者軸を使うが、物理配置の第一軸には採用しない。

### B. `history/` に全証跡を集約する

作成時点から非規範的な completion report や現在参照される receipt を「過去」と呼ぶのは不正確である。age ではなく authority を示す `evidence/` を採用する。

### C. history / evidence の中央 README に全記録を列挙する

単一の巨大 index は、更新競合とレビュー負担を別の場所へ移すだけである。category router + collection-local index を採用する。

### D. front matter の一括整備だけで済ませる

同語彙の current / target / historical 文書が同じ検索空間に残り、path signal と索引重複が改善しないため却下する。

### E. コンポーネント別 directory を全体へ拡張する

wave、pipeline、evaluation、release、cross-component contract は複数コンポーネントを跨ぐ。`relaysoul/` で生じた分類軸の不統一を拡大するため却下する。

### F. superseded ADR を evidence へ移す

ADR は decision chain 全体が価値であり、superseded record も後継 ADR から安定して参照できる必要がある。ADR 自体が runtime authority ではないことを metadata と reading rule で保証する。

### G. 一括リネームする

多数の Markdown link、script、workflow、semantic audit が現行 path に依存している。レビュー可能性と green state を保てないため、段階移行を採用する。

## 15. 採択時の最初の実装単位

本提案の採択後、最初の PR はファイル移動ではなく次だけを行う。

1. documentation information architecture ADR の追加
2. `DOCUMENTATION_MODEL.md` の新ルール追加
3. docs inventory script と commit 固定 baseline receipt の追加
4. 新規配置違反を防ぐ semantic audit
5. proposal / ADR / evidence の lifecycle metadata 定義

これにより、既存構造を壊さず新規負債を止めた後、機械的に安全な移行を開始できる。