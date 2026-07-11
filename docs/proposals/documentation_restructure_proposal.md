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
# RelayLM ドキュメント再構成提案(ゼロベース)

作成日: 2026-07-11

本ドキュメントは提案であり、採択されるまで現行の配置規則([DOCUMENTATION_MODEL.md](../DOCUMENTATION_MODEL.md))を変更しない。

## 1. 現状の定量サマリ

- `docs/` 配下の Markdown: **313 ファイル / 約 50,000 行 / 2.9 MB**
- `docs/architecture/`: **163 ファイル**。うち恒久的な設計・方針文書は約 25〜30。残り約 130 は完了済みスライスの handoff、wave 収束監査、評価記録、互換スタブ
- `docs/mvp/`: **88 ファイル**。MVP-0〜48 の歴史的サマリ + wave3〜8 completion report + release readiness
- front matter を持たないファイル: **151 / 313**(mvp 58、architecture 38、contracts 13、smoke 12、relaysoul 11、他)
- `relaylm_status` の分布: current 104 / historical_after_merge 45 / target 17 / その他 7
- wave 実装証跡の索引が **3 箇所に重複**(`docs/README.md`、`docs/architecture/README.md`、`docs/mvp/README.md`)
- docs パスをハードコードするもの: **スクリプト 24 本(延べ 94 パス参照)+ GitHub workflow 18 本** → 再構成の移行コストを規定する最大の制約

## 2. 現行モデルの強み(維持するもの)

現行の AI-first ドキュメントモデルは以下の点で優れており、再構成後もそのまま維持する。

1. **単一の現状権威** — `docs/PROJECT_STATUS.md` が唯一の current status authority
2. **権威の優先順位が明文化** — Status → Execution Plan → Pipeline Responsibility → 個別 contract → Migration Guide
3. **YAML front matter による自己記述** — 部分取得されても文書単体で権威範囲・状態・更新責任が分かる
4. **two-stage parallel wave flow** — 並列実装 PR と収束 PR の責務分離

問題は内容モデルではなく、**ライフサイクルと読者がディレクトリ構造に反映されていない**ことにある。

## 3. 課題

### P1: `docs/architecture/` が「何でも置き場」になっている

163 ファイル中、現役の設計権威は 2 割弱。`phase6c1_*`、`phase_i4*`、`e1r*`、`o1*`、`soul_lab_ui_a*` など完了済みスライスの実装記録が同じ語彙(RelayMEM、Primary、recall、gate…)で大量に同居しており、AI の部分取得時に**現行権威が歴史的記録に希釈される**。これは「部分取得されても正しく読める」という本モデルの根幹目標と直接衝突する。ディレクトリ名 `architecture` はもはや内容を表していない。

### P2: 索引の重複が収束 PR の負担とコンフリクト表面積を生む

wave 証跡リストが 3 つの索引に重複掲載され、収束 PR は毎回 3〜4 ファイルの索引を同期編集する。two-stage flow が「共有文書の同時編集を避ける」ために設計されているのに、索引側の構造がそれを打ち消している。

### P3: contract の置き場が二重

配置規則自体が「exact schemas and contracts → `docs/contracts/` **or** dedicated architecture contract docs」と二択を許しており、実際に `docs/contracts/` に 15 本、`docs/architecture/*_contract.md` に十数本が分裂している。「正確な挙動境界を探すならここ」という単一の場所がない。

### P4: 人間ユーザー向け文書が散在

導入・設定・接続・トラブルシュートという最初の読者体験に必要な文書が、`docs/` 直下(`openwebui_lmstudio_mvp.md`、`config_schema.md`)、`docs/smoke/`(troubleshooting、チェックリスト)、`apps/soul-lab/README.md` に分散している。「ユーザー向け」「開発者向け」「運用/検証向け」の読者軸がディレクトリに存在しない。

### P5: 分類軸の不統一

- `docs/relaysoul/` だけがコンポーネント別ディレクトリで、他コンポーネント(RelayMEM、RelaySCN…)の設計は `docs/architecture/` にある
- 評価記録が `docs/evaluation/`、`docs/smoke/`、`docs/architecture/e1_*` の 3 箇所に分散
- front matter 無しの 151 ファイルは規約上「SHOULD」の範囲内だが、ディレクトリがライフサイクルを表さないため、front matter が無い歴史的文書は状態の手掛かりがゼロになる

## 4. 提案する構成

第一軸を **読者**、第二軸を **ライフサイクル(current / history)** とする。

```text
docs/
├── README.md                     # 薄いルーター。各領域へのポインタのみ。証跡リストの重複掲載を禁止
├── PROJECT_STATUS.md             # 現状唯一の権威(役割不変)
├── DOCUMENTATION_MODEL.md        # メタデータ/権威モデル(配置規則を本提案に合わせて改訂)
│
├── guides/                       # 【ユーザー向け】インストール、設定、接続、UI、トラブルシュート
│   ├── openwebui_lmstudio.md     #   ← docs/openwebui_lmstudio_mvp.md
│   ├── config_schema.md          #   ← docs/config_schema.md
│   ├── character_workspace_ui.md #   ← apps/soul-lab/README.md の利用者向け部分
│   └── troubleshooting.md        #   ← docs/smoke/openwebui_lmstudio_troubleshooting.md
│
├── architecture/                 # 【開発者向け・現役のみ】恒久設計 約25〜30本に縮小
│   ├── README.md
│   ├── project_execution_plan.md
│   ├── current_target_migration_guide.md
│   ├── pipeline_responsibility_design.md
│   ├── file_first_character_workspace_design.md
│   ├── memory_lifecycle_design.md / relayrel_relationship_design.md / ほか *_design.md
│   ├── relaysoul_design.md ほか   #   ← docs/relaysoul/ のうち現役設計を統合
│   └── vision/                   #   post_v01_strategic_direction_vision.md など
│
├── contracts/                    # 【開発者向け・現役のみ】exact contract の唯一の置き場
│   │                             #   ← docs/contracts/ 全部
│   │                             #   ← docs/architecture/*_contract.md のうち現役のもの
│   │                             #   ← ACG-1 等「現役の exact boundary」を担う slice 文書
│   └── README.md
│
├── operations/                   # 【運用者向け】runbook、smoke、オフラインツーリング
│   ├── smoke/                    #   ← docs/smoke/
│   ├── tools/                    #   ← docs/tools/
│   └── scripts_inventory.md
│
├── evaluation/                   # 現役の評価統合とテンプレート(役割はほぼ現状通り)
│   ├── e1_evaluation_consolidation.md   # ← architecture/ から移動
│   └── templates/
│
├── adr/                          # 意思決定記録(現状通り)
│
├── release/                      # リリース判定
│   └── v0.1_release_readiness.md #   ← docs/mvp/ から移動
│
└── history/                      # 【追記専用の証跡】索引は history/README.md の1箇所のみ
    ├── README.md                 #   wave 索引の唯一の置き場(P2 の解消)
    ├── handoffs/                 #   ← architecture/ の historical_after_merge な slice handoff 約120本
    ├── waves/wave3 .. wave8/     #   ← docs/mvp/wave*/ の completion report
    ├── audits/                   #   ← wave*_cross_slice_convergence_audit.md、*受領証
    ├── milestones/               #   ← docs/mvp/mvp0〜48 サマリ
    └── archive/                  #   ← docs/architecture/archive/(廃止済み設計)
```

`docs/mvp/` と `docs/relaysoul/` はディレクトリとして解消する(中身はライフサイクル・種別に従って移動)。

### 4.1 配置を決める運用ルール(ここが本提案の核)

| 文書の性質 | 置き場 |
|---|---|
| 現在強制されている正確な挙動境界(schema、gate、API) | `contracts/` |
| 恒久的な責務・設計・方針 | `architecture/` |
| 「ある PR が何をしたか」の記録(handoff、completion report) | **最初から** `history/` に作成 |
| 現役 contract が置き換えられた | `git mv` で `history/archive/` へ + 必要なら redirect stub |
| 手順・検証・ツーリング操作 | `operations/` |
| ユーザーが読む導入・設定・利用ガイド | `guides/` |

重要な変更点は「**slice 実装記録は生まれた時から history に置く**」こと。現行モデルでは handoff が `architecture/` に生まれ、マージ後に `historical_after_merge` へ**メタデータだけ**変わる。ライフサイクル遷移をメタデータでなくディレクトリで表すことで:

- 現役ディレクトリの希釈(P1)が構造的に再発しなくなる
- `history/` はディレクトリ単位で「歴史的証跡」と宣言できるため、per-file front matter は任意にでき、151 ファイル問題の大半が解消する
- ただし「まだ現役の exact boundary を担う slice 文書」(例: ACG-1 contract、O1E operational controls)は handoff ではなく contract として `contracts/` に置く。1 つの文書に「実装記録」と「現役境界」を兼務させない

### 4.2 two-stage wave flow への写像

フロー自体は不変。パスだけが変わる:

- 実装 PR: `history/waves/wave<N>/<slice>_completion_report.md` を 1 本作成 + 現役境界があれば `contracts/` に slice contract を作成
- 収束 PR: `PROJECT_STATUS.md`、`architecture/project_execution_plan.md`、**`history/README.md`(索引はここだけ)** を更新
- `docs/README.md` と `architecture/README.md` から wave 証跡セクションを削除(P2 の解消)

### 4.3 PROJECT_STATUS.md のスリム化(任意・小)

「Offline tooling addenda」節は変更ログ化しつつある。現行能力の一覧としては保持しつつ、追記が続くなら「現行能力インベントリ」節に整理して各 addendum は 1〜2 行 + リンクに圧縮することを推奨する。役割・権威は変えない。

## 5. 移行計画(3 フェーズ、各 PR で docs-link-check / boundary-smoke green を維持)

ハードコードされた docs パス(スクリプト 24 本・延べ 94 参照、workflow 18 本)があるため、一括リネームは行わない。

### Phase 0 — ファイル移動なし(低リスク・即効)

1. `docs/README.md` / `docs/architecture/README.md` から wave 証跡リストの重複を除去し、`docs/mvp/README.md`(将来の `history/README.md`)への 1 リンクに置換
2. `DOCUMENTATION_MODEL.md` の配置規則を本提案の表(4.1)に改訂し、「新規文書は新ルールで配置」を宣言(既存文書は動かさない)
3. contract 二択規則を「新規 contract は `docs/contracts/` のみ」に一本化

### Phase 1 — history/ の新設と機械的移動

1. `docs/history/` を作成し、まず `docs/mvp/` 全体(release readiness を除く)と `docs/architecture/archive/` を `git mv`
2. `relaylm_status: historical_after_merge` の architecture 文書(45 本 + front matter 無しの完了 handoff)を `history/handoffs/` へ移動
3. 同一 PR 内で: `scripts/relaylm_docs_link_check.py` を回して全リンク修正、`relaylm_documentation_current_boundary_smoke.py`・`relaylm_docs_semantic_audit.py`・completion-report 系 workflow のパス定数を更新
4. 外部から参照されやすい少数の旧パス(README 等からリンクされていたもの)にのみ `redirect_stub` を置く(全ファイルには置かない)

移動判定は `relaylm_status` による機械的判定を基本とし、境界が曖昧な文書(handoff だが現役境界を兼ねるもの)は Phase 1 では動かさず Phase 2 で個別判断する。

### Phase 2 — 現役側の整理

1. `docs/architecture/*_contract.md` のうち現役のものを `contracts/` へ統合
2. `docs/relaysoul/` を解体: 現役設計 → `architecture/`、gate contract → `contracts/`、完了記録 → `history/`
3. `guides/` と `operations/` を新設し、ユーザー向け・運用者向け文書を移動。`README.md`(リポジトリルート)のリンクを更新
4. `evaluation/` へ e1 評価統合を移動

### 完了条件

- `docs/architecture/` が約 25〜30 ファイル(全て current または target)
- wave 証跡索引が `history/README.md` の 1 箇所
- 全 workflow green、`relaylm_docs_link_check.py` クリーン

## 6. 期待効果

| 指標 | 現状 | 再構成後 |
|---|---|---|
| `docs/architecture/` のファイル数 | 163 | 約 25〜30(全て現役) |
| wave 証跡索引の掲載箇所 | 3 | 1 |
| 収束 PR が編集する索引ファイル | 3〜4 | 1 |
| exact contract の置き場 | 2 系統 | 1 系統 |
| front matter 必須管理対象 | 313(うち 151 未整備) | 現役側のみ約 80〜90(history は任意) |
| ユーザー向け導線 | 散在 | `guides/` に集約 |

最大の効果は AI 部分取得の精度で、「現行の権威文書」と「同じ語彙を持つ歴史的記録」がパス空間で分離されるため、`docs/architecture/` や `docs/contracts/` に限定した検索がそのまま「現役のみ」を意味するようになる。

## 7. 検討した代替案と却下理由

- **A. 一括リネーム(big-bang)** — スクリプト・workflow の 94 パス参照を 1 PR で更新するのはレビュー不能でリスクが高い。却下、段階移行を採用
- **B. 現状維持 + front matter 整備のみ** — 151 ファイルへの front matter 追加だけでは、部分取得時のパスシグナル(ディレクトリ = ライフサイクル)が得られず P1/P2 が残る。却下
- **C. コンポーネント別構成(`docs/relaymem/`、`docs/relayscn/` …)** — slice(wave、E1-R、ACG)は複数コンポーネントを跨ぐため置き場が毎回曖昧になり、`relaysoul/` で既に起きた不整合を全コンポーネントに拡大する。却下
- **D. history を Git 履歴に任せて削除** — completion report と audit は two-stage flow の監査証跡であり、収束 PR・release gate が参照する現役プロセスの一部。削除は却下、追記専用ディレクトリとして保持
