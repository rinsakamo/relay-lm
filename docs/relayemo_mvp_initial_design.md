# RelayEMO MVP Initial Design

## 目的
- text-only affect probe（推定のみ）を runtime diagnostics に追加する。
- assistant_emotion_state（表現状態）を turn 単位で更新する。
- scene-gated text marker を default off で preview/apply 可能にする。

## 非目的
- SOUL/MEM/TTS への書き込み。
- 外部 LLM API を使った感情推定の apply。
- Voice affect / Irodori-TTS / feedback learning。

## SOUL contamination guard
- RelayEMO artifact は diagnostics/trace に限定する。
- `applied_to_soul=false`, `applied_to_mem=false`, `applied_to_tts=false` を明示する。
- `persisted_user_affect=false` を維持し、user_affect を保存しない。

## user_affect_estimate
- 入力文から lightweight heuristic で生成する推定値。
- 断定しないため `is_estimate=true` を常時付与する。
- confidence が低い場合は neutral/unknown 側へ倒す。
- 日本語 positive cue（例: 良い/いいね/最高/好き/楽しい/すごい/面白い/エモい）と全角 `！` を軽く拾う。
- LLM structured affect probe は dry-run candidate として diagnostics に並記し、初期は apply しない。
- fail-closed（parse失敗/validation失敗時は heuristic path 維持）を採用する。
- user emotion は断定せず推定として扱う。
- nested candidate fields (`user_affect_estimate_candidate`, `scene_state_candidate`) は object 必須で、non-object は fail-closed とする。
- VAD/intensity/confidence (`valence`, `arousal`, `dominance`, `intensity`, `confidence`) は required numeric fields とし、missing/non-numeric は fail-closed とする。
- numeric fields は finite number 必須で、NaN/Infinity/-Infinity は fail-closed とする。
- `scene_state_candidate.confidence` も required finite numeric field とし、missing/non-finite は fail-closed とする。

## LLM structured affect probe runtime dry-run
- runtime invocation は default off / dry-run only で開始する。
- `relayemo_affect_probe_mode=llm_structured_dry_run` かつ `relayemo_llm_affect_probe_enabled=true` かつ `relayemo_llm_affect_probe_dry_run=true` のときだけ候補生成を試みる。
- runtime candidate は diagnostics/trace にのみ出力し、active `user_affect_estimate`、`assistant_emotion_state`、text marker、session drift には適用しない。
- probe failure / timeout / invalid JSON / validation error は main response を止めず fail-closed とし、heuristic path を維持する。
- budget policy は `max_input_chars`, `timeout_ms`, `max_output_tokens`, `skip_when_busy`, `every_n_turns` で制御する。
- recursive RelayLM call を避けるため、runtime invocation 実装では dedicated backend/route 未設定時は skip するか、internal probe guard を必須にする。
- API key や token は diagnostics/trace/log に出さない。
- candidate apply gate、outcome observer、feedback loop、Irodori-TTS/voice affect 連携は future scope とする。

## assistant_emotion_state
- user_affect_estimate と scene 文脈から、表現用の内部状態を更新する。
- max_delta_per_turn / decay_per_turn / stability を持つ。
- classifier 無効/低信頼度時は decay_only を適用する。
- stateless MVP では initial request 時、confidence が十分な場合に user_affect_estimate から bootstrap する。
- 将来の session-state runtime では turn 蓄積状態に対して smoothing/decay を適用する。
- session-local emotion drift は process memory only で保持し、永続化しない。
- session-local reuse は session_id がある場合のみ有効化し、session_id がない場合は stateless/fail-safe とする。
- session key は resolved session_id を優先し、route-provided session_id も利用する。

## scene-gated text marker
- default false。
- apply mode: `diagnostics_only`, `preview`, `apply`。
- diagnostics 実行条件と marker 実行条件は分離し、`relayemo_enabled=true` で artifact を生成する。
- scene gate:
  - casual_chat / vtuber_roleplay / design_talk: allow 系
  - implementation_work: preview_only
  - review_work / formal_document / medical_or_safety: suppress
  - unknown: suppress or preview_only
- marker gate:
  - `assistant_emotion_state.intensity` と open/close threshold で gate 判定（hysteresis 対応可能な設定形）。
  - confidence 低値は suppress。
- marker map:
  - `light_positive_estimate -> ✨`
  - `playful_positive_estimate -> ♪`
  - `warm_positive_estimate -> ☺️`
  - neutral/uncertain/unknown は marker なし
- placement:
  - `postfix_replace_punctuation`。
  - 末尾が `。`, `！`, `!`, `.` の場合は marker 置換。
  - `？`, `?` は preserve/append。
  - 句読点なしは append。

## 今回やらないこと
- Irodori-TTS 連携
- voice affect
- feedback learning
- SOUL update
- LLM structured classifier candidate apply
- feedback loop learning
- candidate apply gate / outcome observer
