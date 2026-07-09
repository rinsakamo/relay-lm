---
relaylm_doc_type: runbook
relaylm_authority: mobile_dogfood_observation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - runtime behavior
  - MEM/SOUL mutation authority
  - Cloudflare configuration
  - production benchmark claims
  - public release readiness
  - content-bearing local artifacts
---
# Mobile Dogfood Observation Runbook

## 適用範囲

このランブックは、[P0 Mobile Dogfood Entry](../tools/mobile_dogfood_entry.md) で確立した single-owner モバイル到達構成を前提に、運用者本人が日常的にReLMと会話する中で会話品質・応答速度・MEM挙動・記憶の気持ち悪さ/自然さを継続観測するための手順と記録テンプレートを扱う。

このランブックはRelayLM runtimeの挙動、Cloudflare設定の自動化、MEM/SOUL/REL mutation、P1/P2 importパイプラインのいずれも変更しない。観測運用の整備のみを目的とする。

## 目的

- 自分が毎日スマホからReLMと会話する。
- ReLMの記憶が自然に効くか確認する。
- 応答速度が日常利用に耐えるか確認する。
- P1/P2で育成した記憶が翌日以降の会話品質に効くか見る。
- 不快な記憶想起、拾いすぎ、拾わなすぎ、距離感のズレを記録する。

## 日常利用ループ

```text
朝:
  今日の予定、気分、やることを1-2往復
昼:
  作業中のメモ、違和感、思いつきを短文で投げる
夜:
  今日の振り返り、覚えておいてほしいこと、明日の整理
```

## 観測軸

### Conversation quality

- また話したくなるか
- 前提理解が自然か
- 口調/距離感が安定しているか
- 過去ログ由来の理解が効いたか
- キャラが過度に説明的/説教的/馴れ馴れしくないか

### Memory behavior

- 覚えてほしいことを拾ったか
- 拾いすぎて気持ち悪くないか
- 古い文脈を不要に持ち出していないか
- X由来/ChatGPT由来/日常会話由来が混線していないか
- private_only相当を不適切に出していないか

### Latency

- `retrieval_ms`
- `pipeline_overhead_ms`
- `backend_forward_ms`
- スマホ体感の待ち時間
- streamingの `time_to_first_token_ms` は現時点で常に `null` であり、スマホ体感速度の完全な指標ではないことに注意する

上記の `timing_summary` フィールドは [LAT-1 Latency Measurement](../architecture/lat1_latency_measurement.md) が定義するRelayRUN per-nodeタイミングの一部であり、`nodes_timed_count` / `nodes_untimed_count` も併せて参照できる。

streamingリクエストの「最初のchunkが届くまでの体感待ち時間」は `timing_summary.time_to_first_token_ms` ではなく、別トレースの [LAT-2 Mobile Perceived Latency](../architecture/lat2_mobile_perceived_latency.md) が定義する `stream_timing.time_to_first_chunk_ms` / `stream_drain_ms` / `stream_chunk_count` を参照する。LAT-2は測定のみで、trace有効時にのみ記録される。

### Mobile UX

- 短文入力で成立するか
- 入力し直しや誤字に耐えるか
- 外出先で触る気になるか
- Access再認証が面倒すぎないか

## 日次レビュー項目

- 今日よかった応答
- 今日不快だった応答
- 覚えていてよかった記憶
- 拾わなくてよかった記憶
- 忘れていた/拾えなかった重要記憶
- 応答が遅いと感じた場面
- 明日見るべき仮説

日次記録には [Mobile Dogfood Daily Note Template](templates/mobile_dogfood_daily_note_template.md) をlocalへコピーして使う。

## 週次レビュー項目

- 継続利用したいか
- MEM増加で遅くなっていないか
- P1/P2由来の記憶は価値があったか
- SOUL/REL/SCN/EMOを複雑化する価値が見えたか
- 削るべき記憶/候補/設定はあるか

週次記録には [Mobile Dogfood Weekly Review Template](templates/mobile_dogfood_weekly_review_template.md) をlocalへコピーして使う。

## local-only artifact policy

- content-bearing transcripts(実会話本文)はrepoにコミットしない。
- `local/dogfood/` や `local/value_smoke/` 相当のgitignore済みディレクトリを使う。
- 個人情報・家族情報・病院関係の第三者特定情報は公開fixtureにしない。
- public docs(このrepo)にはcontent-free summaryだけを書く。実会話ログ・評価本文・実測値の羅列はコミットしない。

## 非ゴール

- RelayLM runtime変更
- Cloudflare Tunnel設定の自動作成
- P1/P2 import bridge変更
- MEM/SOUL/REL適用
- latency改善
- `time_to_first_token_ms` 実装
- UI追加
- 家族テスター/multi-user
- 実会話ログや評価本文のコミット
- public benchmark主張

## 関連文書

このランブックは新しいruntime実装やMEM/SOUL挙動を追加しない。RelayLMランタイム自体の現在の実装境界は[Project Status](../PROJECT_STATUS.md)を参照すること。外部到達構成そのものは[P0 Mobile Dogfood Entry](../tools/mobile_dogfood_entry.md)を参照し、本書はその上に乗る観測運用のみを扱う。latency指標の定義は[LAT-1 Latency Measurement](../architecture/lat1_latency_measurement.md)を参照すること。
