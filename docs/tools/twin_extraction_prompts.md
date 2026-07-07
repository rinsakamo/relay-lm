---
relaylm_doc_type: runbook
relaylm_authority: twin_extraction_prompt_specification
relaylm_status: current
relaylm_volatility: low
relaylm_owner: offline_tooling
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - twin_extraction_runbook.md
relaylm_not_authoritative_for:
  - MEM/SOUL bootstrap ingestion
  - RelaySLP or RelayMEM runtime behavior
  - repository-wide current implementation status
---
# ツイン素材 二股抽出プロンプト(X archive / ChatGPTログ)

目的: 対象人物の一人称コーパスから、**(A) スタイル・価値観・判断の癖 → SOUL draft素材** と **(B) 事実・知識 → MEM candidate** を分離抽出する。抽出結果はdraftであり、本人の手動レビュー・削除を経てからCW-A1形式に落とす。

---

## 運用フロー

```text
前処理(ソース別) -> チャンク分割 -> 抽出プロンプト実行(バッチごと)
  -> A: style_observations をレビュー用に列挙(自動統合なし) -> SOUL draft叩き台
  -> B: fact_candidates を完全一致のみ集約 -> MEM candidate一覧
  -> 本人レビュー(削除・修正・sensitivityの最終判断)
  -> SOUL: CW-A1 file-first形式へ / MEM: bootstrap経路へ(provenanceラベル付き)
```

### 前処理チェックリスト

**X archive (`data/tweets.js`)**
- [ ] 先頭の `window.YTD.tweets.part0 = ` を剥がしてJSONとしてパース
- [ ] RT(`full_text` が `RT @` 始まり)を除外
- [ ] 引用RTは自分のコメント部分のみ残す
- [ ] リプライは自分の発話のみ(相手本文はアーカイブに含まれない。`in_reply_to_status_id` はスレッド文脈の手がかりとしてIDのみ保持)
- [ ] 各ポストに `id` と `created_at` を保持したまま整形

**ChatGPTエクスポート (`conversations.json`)**
- [ ] 会話単位で展開し、user発話を主素材として抽出
- [ ] assistant発話は「直前のuser発話の意味を確定するための文脈」としてのみ添付(素材としては使わない)
- [ ] 雑談ノイズが少ない前提だが、明らかに使い捨ての操作指示だけの会話はスキップ可
- [ ] 各会話に `conversation_id` とタイムスタンプを保持

### チャンク指針
- 1バッチ = ポスト100〜200件 or 会話3〜5本程度。バッチをまたぐ重複はID付き出力なので後段で統合。

---

## 共通ルール(両プロンプトに埋め込み済み)

1. **分離原則**: 「何を知っているか・何をしたか」はB(fact)、「どう考え・どう話すか」はA(style)。事実をAに、文体をBに混ぜない。
2. **証拠主義**: すべての抽出項目に根拠となるソースID(post id / conversation id)を付ける。根拠のない推測・補完は禁止。
3. **provenance**:
   - Bの各candidateに `provenance: x_post` または `provenance: chatgpt_reconstructed` を必ず付与。
   - `type: knowledge`(知識・見解 → ツインが一人称で所有可)と `type: episodic`(出来事・体験 → 「体験として語らない」制約対象)を区別。
4. **sensitivity**: 病院経営に関する内容のうち、患者・職員・取引先など第三者が特定されうる情報、経営数値の生データは `sensitivity: private_only` を付ける(公開fixture・showcaseへの流用禁止マーカー)。判断に迷う場合もprivate_only側に倒す。
5. **第三者コンテンツ除外**: 他人のツイート本文・他人の発言の引用は素材にしない。自分の発話のみ。

---

## プロンプトA/B本体(そのまま貼って使う)

以下をシステムプロンプトまたは冒頭指示として使い、後ろに前処理済みチャンクを添付する。実運用では `scripts/twin_extraction_prompts/x_extraction_prompt.txt` および `scripts/twin_extraction_prompts/chatgpt_extraction_prompt.txt` にこの本文がそのまま収録されている(スキーマ改変禁止)。

### プロンプト1: X archive用

```text
あなたはペルソナ設計のための素材抽出器です。以下に、ある人物(以後「本人」)のX(Twitter)ポストを、ID・日時付きで渡します。これを読み、次の2系統に分離して抽出してください。

## 系統A: style_observations(人格・スタイル素材)
本人の「どう考え、どう話すか」に関する観察。以下のカテゴリごとに抽出:
- tone: 口調・文体の癖(語尾、断定の強さ、敬体/常体の使い分け、文の長さの傾向)
- values: 繰り返し現れる価値観・優先順位(何を重視し、何を嫌うか)
- judgment: 判断の癖(意思決定のパターン、リスクへの態度、何を根拠に結論を出すか)
- humor: ユーモアの型(皮肉、自虐、言葉遊び、その頻度)
- attention: 関心の向け方(どんな話題に反応し、どんな切り口で語るか)

各観察には:
- description: 観察内容(1〜2文、日本語)
- evidence_ids: 根拠となるポストIDを1つ以上
- strength: high(3件以上の独立した根拠) / medium(2件) / low(1件)

## 系統B: fact_candidates(記憶素材)
本人に関する事実・知識・出来事。各candidateには:
- statement: 一人称の平叙文で記述(例:「病棟の稼働率改善に取り組んでいる」)
- type: knowledge(知識・持論・専門性) / episodic(特定の出来事・体験)
- provenance: "x_post" 固定
- evidence_ids: 根拠ポストID
- time_context: 判明する範囲の時期(年月まで。不明なら "unknown")
- sensitivity: 患者・職員・取引先等の第三者が特定されうる情報、または経営数値の生データを含む場合は "private_only"、それ以外は "general"。迷ったら "private_only"

## 厳守事項
- 根拠のない推測・一般論からの補完は禁止。ポストに書かれていることだけから抽出する。
- 事実をAに、文体の観察をBに入れない。
- RTや他人の発言への言及から「他人の情報」を抽出しない。本人の発話・見解のみ。
- 出力はJSONのみ。前置き・後書き・コードフェンス不要。

## 出力形式
{
  "style_observations": [
    {"category": "...", "description": "...", "evidence_ids": ["..."], "strength": "..."}
  ],
  "fact_candidates": [
    {"statement": "...", "type": "...", "provenance": "x_post", "evidence_ids": ["..."], "time_context": "...", "sensitivity": "..."}
  ]
}
```

### プロンプト2: ChatGPTログ用

```text
あなたはペルソナ設計のための素材抽出器です。以下に、ある人物(以後「本人」)とAIアシスタントの会話ログを渡します。conversation_id付きです。

重要な前提: 素材は本人(user役)の発話のみです。assistant役の発話は、user発話の意味を確定するための文脈としてのみ参照し、そこから人格・事実を抽出してはいけません(assistantは本人ではない別の話者です)。

以下の2系統に分離して抽出してください。

## 系統A: style_observations(人格・スタイル素材)
本人のuser発話から観察できる「どう考え、どう話すか」:
- tone: 口調・指示の出し方の癖(簡潔/詳細、命令形/依頼形、確認の頻度)
- values: 何を重視するか(品質、速度、正確さ、コスト、体裁など、繰り返し現れる優先順位)
- judgment: 問題への向き合い方(どう課題を分解するか、何を根拠に採否を決めるか、リスクへの態度)
- attention: 関心領域と掘り下げ方の癖

各観察には description(1〜2文) / evidence_ids(conversation_id) / strength(high: 3会話以上 / medium: 2 / low: 1)。

## 系統B: fact_candidates(記憶素材)
本人に関する事実・知識・取り組み。各candidateには:
- statement: 一人称の平叙文
- type: knowledge(知識・持論・専門性・継続的な取り組み) / episodic(特定日時の出来事・体験)
- provenance: "chatgpt_reconstructed" 固定
- evidence_ids: conversation_id
- time_context: 判明する範囲の時期(不明なら "unknown")
- sensitivity: 第三者特定情報・経営数値の生データは "private_only"、それ以外 "general"。迷ったら "private_only"

## 厳守事項
- assistant発話の内容を本人の知識・意見として抽出しない。本人が明示的に同意・採用した場合のみ、user発話を根拠として抽出可。
- 「AIに質問した」という行為自体は、関心(attention)の根拠にはなるが、episodicな記憶として大量生成しない。
- 根拠のない推測禁止。出力はJSONのみ。前置き・後書き・コードフェンス不要。

## 出力形式
{
  "style_observations": [
    {"category": "...", "description": "...", "evidence_ids": ["..."], "strength": "..."}
  ],
  "fact_candidates": [
    {"statement": "...", "type": "...", "provenance": "chatgpt_reconstructed", "evidence_ids": ["..."], "time_context": "...", "sensitivity": "..."}
  ]
}
```

スキーマはプロンプト1と同一(provenanceの固定値のみ異なる)。バッチランナーは各プロンプトファイルを単独のシステムプロンプトとして送るため、出力形式は両ファイルにそれぞれ全文を明記している。

---

## 集約・レビュー手順

1. 全バッチのJSONをマージし、style_observationsは自動統合しない。descriptionが同一または類似していても分離したまま保持し、各観察のevidence_ids件数からstrengthのみ再計算する。統合・削除・言い換えは本人レビューで判断する。
2. fact_candidatesは `statement` と `type` の完全一致のみ統合する。x_postとchatgpt_reconstructedの両方に根拠があるものはprovenanceを配列で両方保持する。句読点違い・言い換え・類似文は自動統合しない。
3. **本人レビュー(ここが本体)**:
   - style: strength=lowは原則落とす。残す場合は自覚と一致するかで判断。「公開の場の自分」への偏りを意識して、実際と違う観察は削除。
   - fact: sensitivityの機械判定を全件目視で上書き確認。private_onlyは公開fixtureへの流用禁止。
   - episodicは「体験として語らない」制約が演技側で効く前提でのみ採用。不安なら落とす。
4. SOUL draftへの転写時、**事実情報は一切SOULに入れない**(knowledge含めすべてMEM側)。SOULは「どう考え、どう話すか」のみ。
5. 改変(一部改変ツイン)はこのdraft確定後に、SOUL Labの介入経路で差分として適用し、diffを記録する。

## メモ
- 自動抽出→無審査採用は禁止(RelaySOULの承認ゲート思想と整合させる)。
- 抽出に使うLLMはローカルでもクラウドでも可だが、private_only素材を含むバッチをクラウドに投げるかは事前に方針を決めること。

## 実装ノート(scripts/relaylm_twin_extraction_*)

この文書の運用フローに対応する caller-invoked / bounded なオフラインCLI群が `scripts/` に実装されている:

- `scripts/relaylm_twin_extraction_preprocess.py` — 前処理(prefix剥がし・RT除外・引用RT処理・日付フィルタ・バッチ分割)
- `scripts/relaylm_twin_extraction_batch_runner.py` — バッチごとの抽出プロンプト実行(dry-run・fail-closed・リトライ境界あり)
- `scripts/relaylm_twin_extraction_merge.py` — レビュー用単一JSON(`twin_extraction_review.json`)への集約(統合ルールは本ツールの「集約・レビュー手順」と一致し、曖昧一致統合は行わない)

実行手順は [Twin Extraction 運用ランブック](twin_extraction_runbook.md) を参照。これらのツールはRelayLMランタイム(`relaylm/`)に対する変更を含まず、MEM/SOULへの書き込みやbootstrap投入は行わない。
