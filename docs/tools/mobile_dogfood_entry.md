---
relaylm_doc_type: runbook
relaylm_authority: p0_mobile_dogfood_entry
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: operations
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - Cloudflare product documentation
  - production multi-user access control
  - RelayLM runtime behavior
  - MEM/SOUL mutation authority
  - public deployment security guarantee
---
# P0 Mobile Dogfood Entry

## 適用範囲

このランブックは、運用者本人がスマートフォンから日常的にRelayLM/ReLMと会話し、会話品質・応答速度・MEM挙動をドッグフードするための、Cloudflare Tunnel + Cloudflare Access前提の安全な外部到達構成を扱う。実際のCloudflare秘密情報・実ドメイン・認証情報・トンネルID・credentialファイルはこのリポジトリに含めない。すべての値はサンプル/placeholderである。

このランブックはCloudflare製品自体の仕様書ではない。Cloudflare Tunnel/Accessの詳細な設定手順はCloudflare公式ドキュメントを参照し、本書はRelayLM側の到達境界と安全確認手順のみを記録する。

## 目的

- 自分が毎日スマホでReLMと会話し、会話品質・応答速度・MEM挙動をドッグフードする。
- 外部からの到達をchat-only UIのみに限定し、それ以外のRelayLM内部surfaceを一切公開しない。

## single-owner boundary

このドッグフード運用は single-owner 前提であり、以下は今回の範囲に含めない:

- 家族テスターなし
- multi-actorなし
- actor識別なし
- family namespaceなし
- memory_mode分岐なし

複数人利用やactor識別が必要になった場合は、本書とは別の設計・PRで扱う。

## 推奨構成図

```text
smartphone browser
  -> Cloudflare Access
  -> Cloudflare Tunnel
  -> chat-only UI
  -> RelayLM
  -> local backend / LM Studio
```

Cloudflare Tunnelはローカル側(家庭/ローカルネットワーク)からCloudflareへ出ていく方式で使用する。家庭側ルーターやファイアウォールでのポート開放は前提にしない。

## 公開してよいもの / 公開禁止

### 公開してよいもの

- chat-only UI のみ

### 公開禁止

- RelayLM `/v1` OpenAI互換API
- LM Studio (`/v1` または既定ポート `:1234`)
- RelayLM admin
- SOUL Lab
- Memory Inspector
- その他の内部debug surface、admin/debug endpoints
- local file browser
- raw runtime artifacts

Cloudflare Tunnelのルーティング設定は、chat-only UIが listen するポートのみをpublic hostnameに紐づけ、他のRelayLM/LM Studioポートは同じTunnel設定からpublicに晒さないこと。

## Cloudflare Access方針

- allowlistは自分のメールアドレスのみ(1件)とする。
- OTP / identity providerの選択は運用者に委ねる(本書はどちらを使うべきかを指定しない)。
- Access自体を無効化する場合は、Access側だけでなくTunnel側も同時に止める。Access無効化のままTunnelだけ生かした状態を放置しない。

## セットアップ順序

1. Cloudflare Access applicationを先に作成し、対象hostnameに自分のメールアドレス1件だけを許可するAllow policyを設定する。
2. Access applicationが有効であることを確認してから、Tunnelのpublic hostname / published application routeを作成する。
3. Tunnel route作成後、`cloudflared`側でAccess token validation / Protect with Accessが有効になっていること、またはorigin側でAccess tokenを検証していることを確認する。
4. Access applicationなし、またはtoken validationなしの状態でpublic hostnameを残さない。

## Tunnel設定のplaceholder例

以下はサンプル値であり、実際の値をコミットしないこと。

```yaml
# cloudflared config.yml (placeholder example, do not commit real values)
tunnel: <tunnel-id-placeholder>
credentials-file: /path/to/placeholder-credentials.json

ingress:
  - hostname: chat.example.com
    service: http://127.0.0.1:<chat-ui-port>
  - service: http_status:404
```

- hostnameは `chat.example.com` のようなplaceholderを使う。実ドメインは書かない。
- serviceは `http://127.0.0.1:<chat-ui-port>` のようにchat-only UIのローカルポートのみを指す。
- credentials-fileはplaceholderパスとする。実credentialファイルの内容やパスは記載・コミットしない。
- 実tunnel IDは書かない。

## ローカル停止手順

外部到達を止める、または縮退させたいときは以下の順で行う:

1. `cloudflared` serviceを停止する(ローカルのcloudflaredプロセス/サービスを止める)。
2. Tunnel側のroute/public hostname設定を無効化する。
3. Cloudflare Access側のapplicationをdisableする。
4. 該当hostnameのDNSレコード(public hostname)を削除または無効化する。

Access appだけを止めてTunnel routeを残す、または逆の状態を放置しないこと。両方合わせて止まっていることを確認する。

## 日常利用チェックリスト

- 朝/昼/夜など、日常の中で短く使う。
- 前日までの記憶が自然に会話に効いているか確認する。
- 記憶の想起が「拾いすぎ」「拾わなすぎ」「不快な想起」になっていないか確認する。
- 応答待ち時間が日常利用として許容できる範囲か確認する。
- スマホでの短文入力・雑な入力に応答が耐えられるか確認する。

## 安全確認チェックリスト

- Tunnel route / public hostnameを作る前にCloudflare Access applicationが有効化済みであることを確認する。
- Access token validation / Protect with Access、またはorigin側token validationが有効であることを確認する。
- Cloudflare Access認証を経由せずにchat-only UIへ到達できないことを確認する。
- 自分以外のメールアドレスではAccess認証を通過できないことを確認する。
- `/v1` (RelayLM OpenAI互換API) へ外部から直接到達できないことを確認する。
- LM Studio (`:1234` など) へ外部から直接到達できないことを確認する。
- SOUL Lab / Memory Inspector / admin / debug endpointsへ外部から到達できないことを確認する。
- 実データ・秘密情報(実ドメイン、実メール、実Tunnel ID、credentialファイルの中身など)をrepoに書いていないことを確認する。

## 非ゴール

- ユーザー管理(複数アカウント、権限分離など)
- 家族テスターの受け入れ
- public SaaS化
- Cloudflare設定の自動作成・自動化
- Cloudflare API連携
- RelayLM runtimeの挙動変更
- MEM/SOUL挙動の変更
- 認証情報・秘密情報の管理方式の設計
- TTS/Avatar/ASR対応

## 関連文書

このランブックは新しいruntime実装やMEM/SOUL挙動を追加しない。RelayLMランタイム自体の現在の実装境界は[Project Status](../PROJECT_STATUS.md)を参照すること。P1 Twin Extraction offline tooling とは独立しており、本書はそのofflineツールの動作を変更しない。日常利用における会話品質・MEM挙動・応答速度の継続観測手順と記録テンプレートは[Mobile Dogfood Observation Runbook](../evaluation/mobile_dogfood_observation_runbook.md)を参照すること。
