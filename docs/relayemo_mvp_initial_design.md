# RelayEMO MVP Initial Design

## 目的
- text-only affect probe（推定のみ）を runtime diagnostics に追加する。
- assistant_emotion_state（表現状態）を turn 単位で更新する。
- scene-gated text marker を default off で preview/apply 可能にする。

## 非目的
- SOUL/MEM/TTS への書き込み。
- 外部 LLM API を使った感情推定。
- Voice affect / Irodori-TTS / feedback learning。

## SOUL contamination guard
- RelayEMO artifact は diagnostics/trace に限定する。
- `applied_to_soul=false`, `applied_to_mem=false`, `applied_to_tts=false` を明示する。
- `persisted_user_affect=false` を維持し、user_affect を保存しない。

## user_affect_estimate
- 入力文から lightweight heuristic で生成する推定値。
- 断定しないため `is_estimate=true` を常時付与する。
- confidence が低い場合は neutral/unknown 側へ倒す。

## assistant_emotion_state
- user_affect_estimate と scene 文脈から、表現用の内部状態を更新する。
- max_delta_per_turn / decay_per_turn / stability を持つ。
- classifier 無効/低信頼度時は decay_only を適用する。
- stateless MVP では initial request 時、confidence が十分な場合に user_affect_estimate から bootstrap する。
- 将来の session-state runtime では turn 蓄積状態に対して smoothing/decay を適用する。

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
