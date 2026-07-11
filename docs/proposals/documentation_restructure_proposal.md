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

1. **第一軸は文書の権威・役割**とする。パスを見れば、その文書が guide、reference、strategy、planning、architecture、contract、decision、operation、evaluation、release、evidence のどれか分かるようにする。
2. **規範文書と非規範的証跡をパスで分離**する。実装記録、completion report、wave audit、評価実行結果、release receipt は、作成時点から `docs/evidence/` に置く。
3. **1 文書 1 権威**を新規・実質更新文書の原則とする。ただし既存 hybrid 文書を移行のためだけに全面リライトしない。
4. **ADR と proposal に独立したライフサイクルを持たせる**。ADR の採択と実装済み状態を混同せず、proposal を採択後も現役文書として残さない。
5. **索引はルーターに限定**し、証跡の巨大な重複リストを置かない。各 collection に 1 つだけ local index を持たせる。
6. **移行は段階的に行い、各 PR で link-check と documentation boundary smoke を green に保つ**。

現行モデルの front matter、権威の優先順位、`PROJECT_STATUS.md` の単一性、two-stage wave flow は維持する。ただし、ディレクトリ設計、ADR/proposal/evidence の状態モデル、索引規則、semantic audit の検証方法は改める。

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
- 本提案追加後の `target`: 18

初回調査では docs パスをハードコードするスクリプトと workflow が多数確認されている。ただし、移行規模の確定値として手作業の grep 件数を固定せず、Phase 0 で commit 固定の inventory を機械生成し、その出力を各移行 PR の基準にする。

## 2. 現状診断

### P1: `docs/architecture/` が複数の権威を兼務している

現在の `docs/architecture/` には、恒久 architecture、target architecture、exact contract、implementation handoff、wave convergence audit、evaluation、execution plan、strategic vision、compatibility stub が同居している。

同じ RelayMEM、recall、gate、Primary、SOUL Lab などの語彙を持つ文書が、現在の設計、将来目標、実装時点の証跡という異なる権威で混在するため、AI の部分取得時に現役権威が希釈される。

### P2: contract の置き場が二重である

現行規則は exact contract の置き場として `docs/contracts/` と architecture 内の dedicated contract の両方を許している。このため、「正確な挙動境界を探す場所」が一意でない。

### P3: planning、strategy、architecture が分離されていない

`project_execution_plan.md` は実行順序、strategic vision は非拘束の長期方向、`pipeline_responsibility_design.md` は恒久設計であり、権威が異なる。これらを architecture という 1 つの検索空間に置くべきではない。

### P4: guide と reference が混在・散在している

導入・設定・接続・troubleshooting・UI 利用方法・設定項目リファレンスが、`docs/` 直下、`docs/smoke/`、`docs/tools/`、`apps/soul-lab/README.md` に分散している。また、手順書と仕様リファレンスが区別されていない。

### P5: 実装証跡の索引が重複している

wave や slice の証跡リストが複数の README に重複し、収束 PR が複数索引を同期編集する。これは two-stage flow が避けようとしている共有ファイル競合を、索引側で再発させている。

### P6: `history/` では作成時点の意味を正しく表せない

completion report は source PR と同時に作られ、誕生時点から非規範的であるが「過去」ではない。validation receipt や release receipt も、古いからではなく規範ではないから分離する。したがって age を表す `history/` より authority を表す `evidence/` が正確である。

### P7: ADR の採択状態と実装状態が混同され得る

既存 ADR は `relaylm_status: current` でありながら、本文では「Accepted as target architecture. Implementation remains pending.」とされている。ADR が採択済みであることと、対象挙動が current implementation であることは別の状態である。

### P8: semantic audit が個別パスへ強く依存している

現行 audit は required metadata 対象、wave index、release readiness、operations docs のパスを個別に列挙している。移行時に定数を差し替えるだけでは、新構造でも同じ hard-code debt が再発する。

## 3. 設計原則

### 3.1 パスが答えること

文書パスは、次の問いに答える。

> この文書は何のために存在し、どの種類の権威を持つか。

current / target / compatibility は front matter で表し、非規範的な実装・評価・release 証跡かどうかは `evidence/` への配置で表す。

### 3.2 1 文書 1 権威と既存文書の移行例外

新規文書と、今後も実質更新される文書では、次の兼務を原則として認めない。

- architecture + exact contract
- implementation handoff + current contract
- evaluation method + dated evaluation result
- release readiness assessment + frozen release receipt
- proposal + accepted decision
- strategic vision + committed execution plan

ただし、この原則を既存文書へ機械的に遡及させない。既存の `architecture/*_contract.md` などで、exact contract が明らかな主権威であり、handoff 文脈が補足として同居するだけの低変更文書は、次の条件で**丸ごと `contracts/` へ移動してよい**。

1. front matter で exact contract を主権威として宣言する。
2. 実装経緯・PR 文脈は非規範的な背景であると本文または metadata に明記する。
3. exact boundary と背景記録が矛盾しない。
4. 今後、背景部分を独立して更新する予定がない。

既存 hybrid 文書を分割するのは、次のいずれかに該当する場合に限る。

- 今後も contract と実装記録の双方が実質更新される。
- 非 contract 部分が別の consumer から独立に参照される。
- 混在により AI 部分取得で current boundary を誤読する具体的リスクがある。
- 文書内に現在有効な boundary と失効した boundary が混在する。

これにより、1 文書 1 権威を将来の構造原則として維持しつつ、Phase 3 を既存文書の全面リライトにしない。

### 3.3 active document と evidence

- active directories の文書は full front matter を必須とする。
- `evidence/legacy/` はディレクトリ自体が非規範的であるため、未整備の既存 front matter を一括補完しなくてもよい。
- 新規または実質更新する evidence 文書には provenance metadata を要求する。
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
├── README.md
├── PROJECT_STATUS.md
├── DOCUMENTATION_MODEL.md
├── proposals/                     # 未決定の提案のみ
├── guides/                        # task-oriented how-to / tutorial
├── reference/                     # config / CLI / API / migration interpretation
├── strategy/                      # 非拘束の長期方向・product principles
├── planning/                      # execution plan / roadmap / migration sequencing
├── architecture/                  # 恒久的な構造・責務・ownership
├── contracts/                     # exact schema / gate / API / invariant の唯一の置き場
├── adr/                           # append-only decision log
├── operations/                    # runbook / smoke / tooling operation
├── evaluation/                    # rubric / scenario / method / current synthesis
├── release/                       # current release criteria / readiness
└── evidence/                      # 非規範的証跡
    ├── README.md
    ├── implementation/
    ├── waves/wave<N>/
    ├── evaluations/
    ├── releases/
    ├── proposals/
    ├── migrations/
    ├── milestones/
    ├── superseded/
    └── legacy/
```

`docs/mvp/`、`docs/relaysoul/`、`docs/smoke/`、`docs/tools/` は最終的にトップレベル directory として解消する。コンポーネント名を配置の第一軸にしない。

## 5. 配置ルールと tie-breaker

| 文書の役割 | canonical home |
|---|---|
| repository-wide current implementation status | `PROJECT_STATUS.md` |
| 未決定の構造変更・大規模提案 | `proposals/` |
| 利用者が目的を達成する手順 | `guides/` |
| 設定項目、CLI、外部利用面、current/target 解釈の参照 | `reference/` |
| 非拘束の長期方向・原則 | `strategy/` |
| 実行順序、roadmap、migration sequencing | `planning/` |
| 恒久的な責務・構造・ownership | `architecture/` |
| exact schema、gate、API、artifact、invariant | `contracts/` |
| 設計判断と rationale | `adr/` |
| runbook、smoke、tool operation | `operations/` |
| 評価方法、rubric、scenario、current synthesis | `evaluation/` |
| current release criteria / readiness | `release/` |
| PR / wave / validation / migration の証跡 | `evidence/` |

分類に迷う場合は、次の順で判定する。

### 5.1 planning / strategy / architecture / reference

1. **時期、依存順、open gate、実装順序、移行手順を規定する**なら `planning/`。
2. 順序を規定せず、**現在と target / compatibility の読み分け方を参照資料として説明する**なら `reference/`。
3. 非拘束の将来像、可能性、post-release の方向を示すなら `strategy/`。
4. 時期に依存しない責務、構造、ownership、設計原則を規定するなら `architecture/`。
5. exact schema、gate、API、must/must-not invariant を規定するなら `contracts/`。

したがって、現行 `current_target_migration_guide.md` は、実行順序ではなく current / target / compatibility の解釈権威が主である限り `reference/` が第一候補となる。

`analyzer_candidate_governance.md` のように roadmap と policy synthesis を両方持つ文書は、次で扱う。

- roadmap 部分が実行順序を規定するなら `planning/` へ分離する。
- durable policy 部分は `architecture/` に置く。
- 片方が短い補足にすぎず今後独立更新されない場合は、主権威側へ丸ごと置き、補足が非権威であることを明記する。

### 5.2 guides / reference

- 実行順の手順、前提、期待結果、troubleshooting の流れを示すなら `guides/`。
- field、option、command、schema、default、制約を列挙するなら `reference/`。
- 両方必要なら guide から reference をリンクし、仕様表を複製しない。
- 既存の低変更 hybrid 文書は主目的で配置し、実質更新時に分割する。

### 5.3 最終 tie-breaker

それでも判断できない文書は、次の優先順位で決める。

1. exact invariant の有無
2. 読者が取る行動を直接規定するか
3. 時期・順序に依存するか
4. current implementation の解釈に使われるか
5. 今後どの部分が独立して更新されるか

複数の主権威が残る場合のみ分割する。

## 6. ADR のゼロベース運用

### 6.1 ADR を `adr/` に残す理由

ADR は current architecture のコピーではなく、意思決定の append-only log である。superseded ADR も supersession chain の一部なので `evidence/` へ移動しない。`adr/` というパス自体が decision rationale であり runtime authority ではないことを示す。

### 6.2 二軸状態

```yaml
relaylm_doc_type: adr
relaylm_status: target              # current / target / historical
relaylm_decision_status: accepted   # proposed / accepted / superseded / rejected / withdrawn
relaylm_decided_on: 2026-07-11
relaylm_supersedes: []
relaylm_superseded_by: null
```

- `relaylm_decision_status` は意思決定の状態を表す。
- `relaylm_status` は、その決定が対象とする挙動が current / target / historical のどれかを表す。
- `accepted` は実装済みを意味しない。
- 実装済み境界は `PROJECT_STATUS.md` と exact contract が示す。

現在の `character_conditioned_belief_model.md` は「accepted target / implementation pending」であるため、`relaylm_status: target` と `relaylm_decision_status: accepted` へ正規化する。

### 6.3 命名と一度限りの canonicalization

- 新規 ADR は `NNNN-short-title.md` とする。
- 既存の非番号 ADR を番号付きへ統一する場合、**Phase 0 の一度だけ** deterministic にリネームする。
- 番号は `relaylm_decided_on`、既存作成順、旧パスの順で安定的に割り当てる。
- 同一 PR で old path -> new path map を `evidence/migrations/` に保存する。
- 外部参照が疑われる旧 ADR path にだけ期限付き redirect stub を置く。
- Phase 0 完了後、ADR の canonical path は不変とし、以後はリネームしない。
- 方針変更は既存 ADR の全面改稿ではなく、新 ADR で supersede する。

これにより、番号体系の導入と supersession chain の安定パスを両立する。

## 7. proposal のライフサイクル

```text
proposals/<name>.md
  ├── accepted -> ADR + normative docs + evidence/proposals/ へ移動
  ├── rejected -> decision link 付きで evidence/proposals/ へ移動
  └── withdrawn -> 理由付きで evidence/proposals/ へ移動
```

```yaml
relaylm_doc_type: proposal
relaylm_status: target
relaylm_proposal_status: under_review  # draft / under_review / accepted / rejected / withdrawn
relaylm_decision_source: null
```

採択後の proposal は配置規則の authority に昇格させない。正式な決定は ADR と `DOCUMENTATION_MODEL.md` に移し、proposal は evidence として保存する。

本提案を採択する PR では、ADR 作成と同じ commit または同じ PR 内で、このファイルを `evidence/proposals/` へ移す。Phase 0 は「ファイル移動ゼロ」ではなく、**bulk migration を行わず、採択に必要な atomic lifecycle move だけを許す**フェーズとする。

## 8. evidence の運用

### 8.1 metadata

新規 evidence には type に応じて次を要求する。

```yaml
relaylm_status: historical
relaylm_evidence_status: merged      # draft / merged / validated / invalidated / frozen
relaylm_source_pr: 549
relaylm_source_commit: <sha>
relaylm_recorded_on: 2026-07-11
```

既存の `historical_after_merge` は移行互換値として当面許容するが、新規文書では `historical` + `relaylm_evidence_status` を使う。

### 8.2 併存期間を fail-closed にする legacy manifest

作成日やファイル名だけでは新旧を安全に区別できないため、Phase 0 で commit 固定の manifest を生成する。

```yaml
baseline_commit: fe8f4652390b6a4c3f0c1a81e6051f09e8cb4ae5
legacy_documents:
  - source_path: docs/mvp/wave7/e1r5_completion_report.md
    source_blob_sha: <blob-sha>
    approved_destination: docs/evidence/waves/wave7/e1r5_completion_report.md
    metadata_profile: legacy_completion_report
```

semantic audit は次を fail-closed で検証する。

1. `evidence/` 配下の文書が manifest に無ければ、新 metadata profile を必須とする。
2. `historical_after_merge` や front matter 無しを許せるのは、frozen baseline manifest に source blob が存在し、approved destination と一致する既存文書だけとする。
3. manifest への追加は、baseline commit に存在する source path / blob から生成されたものだけを許す。新規ファイルを同じ PR で legacy 登録して回避することを禁止する。
4. legacy 文書を新 metadata へ変換したら manifest entry を削除し、再登録を禁止する。
5. `evidence/legacy/` の front matter 例外も manifest 登録済み文書だけに限定する。
6. manifest 自体の変更は migration 専用 PR とし、inventory script の再現可能な出力と照合する。

新規か既存かの判定を日付や git 追加日の推測に依存させず、frozen baseline の source path / blob によって決める。

### 8.3 evidence index

- wave ごとに local `README.md` を作り、slice report と convergence audit をそこだけに列挙する。
- wave close 後は link fix と provenance correction 以外で変更しない。
- `evidence/README.md` は category router のみとする。
- 全 evidence を 1 つの中央 README に列挙しない。

## 9. two-stage wave flow

### Stage 1: implementation PR

- production code と直接結合する test / workflow
- runtime field と原子的に出荷すべき exact contract
- `evidence/waves/wave<N>/<slice>_completion_report.md`
- wave 外なら `evidence/implementation/<area>/<slice>_completion_report.md`

implementation handoff を architecture に作らない。恒久設計が変わる場合は architecture、exact boundary が変わる場合は contract、PR が何をしたかは evidence として分ける。

### Stage 2: convergence PR

1. merged code、completion report、exact contract を照合する。
2. `PROJECT_STATUS.md`、`planning/project_execution_plan.md`、影響する architecture / contract / reference を更新する。
3. `evidence/waves/wave<N>/convergence_audit.md` を追加する。
4. 当該 wave の `README.md` を完成させる。
5. root README や architecture README に wave 証跡一覧を複製しない。
6. convergence merge まで次 wave / release gate を開かない。

## 10. front matter、inventory、CI

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

`guides/` と `reference/` も新規・更新ファイルから必須にする。legacy 例外は frozen manifest で管理する。

### 10.2 directory invariant

semantic audit は、個別パス列挙中心から次の directory invariant 中心へ移す。

- architecture に handoff / completion report / audit / strategic vision / execution plan を置かない。
- contracts 以外に新規 exact contract を作成しない。
- proposals に accepted / rejected / withdrawn proposal を残さない。
- evidence を current runtime authority として宣言しない。
- ADR は decision status を持つ。
- active directories は required metadata を持つ。
- 新規 evidence は新 metadata profile を持つ。
- legacy metadata 例外は frozen manifest と一致する。
- prohibited top-level directory を無断追加しない。

個別の安全境界 anchor check は維持するが、information architecture の検証を hard-coded path list だけに依存させない。

### 10.3 inventory

Phase 0 で inventory script を追加し、少なくとも次を出力する。

- path / blob SHA
- document type / status / authority
- front matter 有無
- inbound Markdown links
- script / workflow からの literal path reference
- proposed destination
- legacy metadata profile
- ambiguity / manual-review flag

inventory は current authority ではなく、CI artifact または `evidence/migrations/` の commit 固定 receipt として扱う。

## 11. 移行計画

### Phase 0: 決定、guardrail、atomic lifecycle move。bulk migration なし

1. 本提案を採択する documentation architecture ADR を作成する。
2. `DOCUMENTATION_MODEL.md` に document role、tie-breaker、hybrid migration exception、ADR/proposal/evidence metadata を追加する。
3. `evidence/proposals/` を作成し、本提案を ADR 採択と同じ PR で移動する。
4. 既存 ADR を番号付きへ統一する場合は、この Phase で一度だけ canonicalize し、path map を保存する。
5. commit 固定 inventory と legacy metadata manifest を生成する。
6. 新規 contract、completion report、proposal、strategic vision に新ルールを即時適用する。
7. semantic audit に「新たな配置違反を増やさない」guardrail を追加する。

Phase 0 で許す移動は proposal の lifecycle retirement、ADR の一度限りの canonicalization、そのための最小 directory / index 作成だけとする。既存 docs 群の bulk migration は行わない。

### Phase 1: 新規負債を止め、索引を router 化

1. `strategy/`、`planning/`、`reference/`、`operations/`、`evidence/` と各 README を整備する。
2. `docs/README.md` を start route のみに縮小する。
3. `docs/architecture/README.md` から wave / slice 証跡一覧を削除する。
4. 新規 wave report を `evidence/waves/` に置く。
5. 新規 exact contract は `contracts/` 以外に置けないよう CI で制約する。

### Phase 2: evidence の機械的移動

1. `docs/mvp/wave*/` の completion report を `evidence/waves/` へ移す。
2. convergence audit、validation receipt、dated evaluation result を対応する evidence collection へ移す。
3. `historical_after_merge` の implementation handoff を `evidence/implementation/` へ移す。
4. `docs/architecture/archive/` を `evidence/superseded/` または `evidence/legacy/` へ分類する。
5. 旧 MVP snapshot を `evidence/milestones/` へ移す。
6. Markdown link、script、workflow、semantic audit の参照を同一 PR 内で更新する。
7. old path -> new path map と検証 receipt を保存する。

移動判定は `relaylm_status` だけに依存せず、document type、命名、source PR、inbound link、script/workflow 参照、legacy manifest を合わせて行う。

### Phase 3: active knowledge の再分類

1. execution plan / roadmap を `planning/` へ移す。
2. current / target / compatibility の解釈資料を `reference/` へ移す。
3. strategic vision と product principle を `strategy/` へ移す。
4. architecture 内の active contract を `contracts/` へ集約する。
5. 既存 hybrid contract は §3.2 の条件を満たせば丸ごと移動し、分割を必須にしない。
6. 分割は今後も双方が更新される hybrid、具体的な誤読リスクがある hybrid に限定する。
7. `docs/relaysoul/` を役割別に architecture / contracts / strategy / evidence へ整理する。
8. how-to を `guides/`、仕様列挙を `reference/` へ整理する。
9. smoke / tools を `operations/` へ移し、実行結果を evidence に分離する。
10. evaluation method / current synthesis と dated result を分離する。
11. release readiness と frozen receipt を分離する。
12. ADR metadata を二軸状態へ正規化する。Phase 0 後の ADR path は変更しない。

### Phase 4: compatibility cleanup と enforcement

1. 旧トップレベル directory を解消する。
2. compatibility stub の期限と削除条件を確認する。
3. active directories の front matter coverage を 100％にする。
4. directory invariant を CI で必須化する。
5. repository-wide hard-coded old docs path が 0 であることを確認する。
6. legacy metadata manifest を段階的に空へ近づける。

## 12. compatibility stub

全移動元に redirect stub を置くと、古い検索空間と重複文書を恒久化するため、stub は例外とする。

stub を置けるのは次だけとする。

- repository root README や外部利用者から参照される入口
- automation が段階移行を必要とする path
- current authority または ADR の既知の旧 canonical path

各 stub は canonical destination、created-on、removal condition、`redirect_stub` type を持ち、本文を複製しない。

## 13. 完了条件

### 構造

- `architecture/` に implementation handoff、completion report、wave audit、dated evaluation result、strategic vision、execution plan がない。
- exact contract の canonical home が `contracts/` のみである。
- `planning/`、`strategy/`、`guides/`、`reference/`、`operations/` の tie-breaker が `DOCUMENTATION_MODEL.md` に実装されている。
- `docs/mvp/`、`docs/relaysoul/`、トップレベルの `docs/smoke/`、`docs/tools/` が解消されている。
- `evidence/legacy/` が新規文書の作成先として使われていない。

### 権威

- `PROJECT_STATUS.md` が現在実装済み境界の唯一の repository-wide authority である。
- accepted ADR と implemented behavior が metadata 上で区別される。
- proposal は採択 PR 内で evidence へ退役する。
- 新規・実質更新文書は 1 文書 1 権威を満たす。
- 既存 hybrid の例外は明示条件と front matter で管理される。

### 検証

- active directories の front matter coverage が 100％である。
- docs link check、semantic audit、documentation boundary smoke が green である。
- directory と document type の不整合を CI が fail closed で検出する。
- 新規 evidence が legacy metadata を偽装できない。
- ADR canonical path が Phase 0 後に変更されていない。

## 14. 検討した代替案と却下理由

- **読者別だけで分類**: reader だけでは plan、architecture、contract、ADR の権威を区別できない。
- **`history/` に集約**: completion report は作成時点から非規範的だが過去ではない。
- **中央 README に全 evidence を列挙**: 新しい競合点になる。
- **front matter の一括整備だけ**: path signal と索引重複が改善しない。
- **コンポーネント別 directory**: cross-component 文書の置き場が曖昧になる。
- **superseded ADR を evidence へ移す**: supersession chain の安定パスを失う。
- **既存 hybrid をすべて分割**: Phase 3 が全面リライトになり、移行リスクが効果を上回る。
- **一括リネーム**: 多数の link、script、workflow を 1 PR で変更できない。

## 15. 採択時の最初の実装単位

採択 PR は、既存 docs の bulk migration を行わず、次だけを行う。

1. documentation information architecture ADR の追加
2. `DOCUMENTATION_MODEL.md` への tie-breaker、hybrid exception、lifecycle metadata の追加
3. 本 proposal の `evidence/proposals/` への atomic move
4. 必要な場合に限る既存 ADR の一度限りの canonicalization
5. docs inventory script、frozen baseline、legacy metadata manifest の追加
6. 新規配置違反と metadata 逃れを防ぐ semantic audit

これにより、既存構造を壊さず、新規負債と分類の再曖昧化を止めた後、機械的に安全な移行を開始できる。