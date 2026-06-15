# RelayLM

<p align="center">
  <strong>ローカルLLMのための、記憶・人格指向 OpenAI互換会話プロキシ</strong>
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-blue">
  <img alt="OpenAI互換" src="https://img.shields.io/badge/API-OpenAI--compatible-6f42c1">
  <img alt="開発状況: active development" src="https://img.shields.io/badge/status-active%20development-orange">
  <a href="./LICENSE"><img alt="ライセンス: Apache-2.0" src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"></a>
</p>

<p align="center">
  <a href="./README.md">English README</a> ・
  <a href="./docs/PROJECT_STATUS.md">現在の実装状況</a> ・
  <a href="./docs/README.md">ドキュメント</a> ・
  <a href="./LICENSE">ライセンス</a>
</p>

> [!WARNING]
> RelayLMはMVPを開発中です。現在のPhase、実装済み境界、ゲート付き・デフォルト無効の挙動、直近の実装予定は [Project Status](docs/PROJECT_STATUS.md) を参照してください。

## 🌉 RelayLMとは？

RelayLMは、ローカルLLMアプリ、AIコンパニオン、AI VTuber、エージェント、ローカル推論ランタイム向けの、人格に特化した会話プロキシです。

OpenAI互換のフロントエンドとバックエンドの間に配置します。

```text
フロントエンド
  -> RelayLM /v1/chat/completions
  -> OpenAI互換 LLMバックエンド
```

RelayLM自体は**言語モデルではなく**、**メモリデータベースでもありません**。人格、承認済み記憶、RAG、直近の会話、シーン状態、退避コンテキストを、トークン予算内で人格を安定させ、KVキャッシュを再利用しやすい実効コンテキストへ組み立てることを目的としています。

> フロントエンド側で長いコンテキストを管理しなくても、AI VTuberやAIコンパニオンが「よく覚えている」と感じられる会話を目指します。

## ✨ RelayLMの特徴

- 🔌 **URL差し替えで統合** — OpenAI互換の `/v1/chat/completions` エンドポイントに接続します。
- 🧠 **人格を優先したコンテキスト** — 動的な記憶や検索結果より上位に、人格と出力方針を保ちます。
- 🧩 **責務を分けたパイプライン** — シーン、感情、意図、検索、コンテキスト、出力観察、実行制御、遅延永続化を分離します。
- ⚡ **KV再利用を意識した配置** — prefix/KVキャッシュを再利用しやすい安定した順序を重視します。
- 🛡️ **安全側のデフォルト** — リクエスト書き換えや永続化を、互換性・ポリシー・applyゲートの後ろで導入します。
- 💻 **ローカルファースト** — ストレージを原則ローカルに置き、バックエンドURLを設定で明示し、隠れた外部テレメトリを持ちません。

> [!NOTE]
> RelayLMはローカルファーストですが、ホスト型・リモート型バックエンドを設定した場合、選択されたコンパイル済みコンテキストはリクエストの一部としてそのバックエンドへ送信されます。

## 🛠️ 作れるもの

- 人格と会話文脈を安定させたローカルAIコンパニオン
- OpenWebUIから使う、記憶付きローカル作業アシスタント
- Open-LLM-VTuberとローカルLLMの間で文脈を管理するAI VTuber構成

## 🧭 利用経路

### 標準MVP構成

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

### AI VTuber向け任意構成

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI互換バックエンド
```

RelayLMが担当するのは会話プロキシ、コンテキスト境界、ランタイム境界です。フロントエンドUI、ASR、TTS、アバター実行環境は担当しません。

## 📍 開発状況

現在のPhase、実装済み境界、dry-run・read-only・default-offの挙動、直近の実装予定は [Project Status](docs/PROJECT_STATUS.md) を参照してください。

`docs/PROJECT_STATUS.md` を現在地の正本とし、このREADMEではPhase番号や短期間で変わる実装状況を重複管理しません。

## ✅ 動作要件

| 項目 | 要件 |
|---|---|
| Python | 3.10以上 |
| バックエンド | OpenAI互換Chat Completions対応 |
| 標準構成 | OpenWebUI + RelayLM + LM Studio |
| OpenWebUI | OpenAI互換接続を使い、Responses APIを無効化 |
| RelayLM API | `/healthz`, `/v1/models`, `/v1/chat/completions` |

## 🚀 クイックスタート

### 1. クローンしてインストール

```bash
git clone https://github.com/rinsakamo/relay-lm.git
cd relay-lm

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

<details>
<summary>Windows PowerShellで仮想環境を有効にする場合</summary>

```powershell
.venv\Scripts\Activate.ps1
```

</details>

editable install時にビルド依存パッケージへアクセスできない環境では、現在の環境にあるビルドツールを使います。

```bash
pip install -e . --no-build-isolation
```

### 2. 設定ファイルを作成

標準のOpenWebUI + LM Studio構成では、次のcopy-ready設定を使います。

```bash
cp examples/config/openwebui_lmstudio.yaml config.yaml
```

汎用的な設定から始める場合は、代わりに次を使います。

```bash
cp config.example.yaml config.yaml
```

`config.yaml` でバックエンドURL、バックエンドモデル、RelayLMのルートを設定します。標準例ではLM Studioを `http://127.0.0.1:1234/v1`、RelayLMを `http://127.0.0.1:8090/v1` としています。詳細は [設定スキーマ](docs/config_schema.md) と [OpenWebUI + LM Studioガイド](docs/openwebui_lmstudio_mvp.md) を参照してください。

### 3. RelayLMを起動

```bash
relaylm --config config.yaml
```

モジュールから起動する場合:

```bash
python -m relaylm.app --config config.yaml
```

Uvicornから起動する場合:

```bash
RELAYLM_CONFIG=config.yaml \
  uvicorn relaylm.app:create_app --factory --host 127.0.0.1 --port 8090
```

### 4. フロントエンドの接続先を変更

OpenWebUI、Open-LLM-VTuber、または別のOpenAI互換フロントエンドで、base URLを次に設定します。

```text
http://127.0.0.1:8090/v1
```

### 5. 動作を確認

バックエンドモデルをロードした状態で、health、route、非ストリーム応答を確認します。

```bash
curl http://127.0.0.1:8090/healthz
curl http://127.0.0.1:8090/v1/models
curl http://127.0.0.1:8090/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"relaylm-work-assistant","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

## 🧰 トラブルシューティング

接続できない場合は [OpenWebUI + RelayLM + LM Studioトラブルシューティング](docs/smoke/openwebui_lmstudio_troubleshooting.md) を参照してください。

## 🏗️ アーキテクチャ

正規のランタイム順序は次のとおりです。

```text
User input
  -> RelayRUN request shell
  -> PipelineContext
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM / backend forward
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> RelayRUN final artifact / trace / checkpoint summary
  -> User output

Out-of-band after-turn path:
  governed evidence
  -> RelaySLP
  -> MEM update candidates / SOUL proposals
  -> persistence and approval gates
```

これは責務上の正規順序であり、すべての段階が現在有効という意味ではありません。実装状況は [Project Status](docs/PROJECT_STATUS.md) を参照してください。

| Relayコンポーネント | 責務 |
|---|---|
| 🌬️ **RelaySCN** | シーン分類とシーン・永続化ポリシー |
| 🙂 **RelayEMO** | 感情推定とシーン制御された表現 |
| 🚦 **RelayINT** | 入力側の意図、曖昧性、確認、続行・停止ゲート |
| 🧠 **RelayMEM** | 通常応答経路での読み取り専用記憶検索 |
| 📦 **RelayCTX** | Repackによるバックエンド入力構築と、Unpackによる表示文・内部候補の分離 |
| 🔎 **RelayREF** | 軽量な出力側観察と診断 |
| 🎛️ **RelayRUN** | 実行制御、fallback/recovery、checkpoint、trace、node state |
| 🌙 **RelaySLP** | 通常応答経路外でのMEM・SOULコンパイル |

横断・transport境界:

- `PipelineContext`: リクエスト単位の調整、payload replacement履歴、runtime-private state、node result、diagnostics handoff
- Runtime Compile Gate: リクエスト単位のapply・互換性decision phase。独立した `RelayPLC` コンポーネントではない
- OpenAI-compatible adapter: frontend/backend protocol境界。semantic pipeline stageではない

重要なタイミング規則は次のとおりです。

```text
RelayINT = before action
RelayREF = after response
```

責務と順序の正式な定義は [Pipeline Responsibility Design](docs/architecture/pipeline_responsibility_design.md) を参照してください。

## 📚 ドキュメント

- 📍 [現在のプロジェクト状況](docs/PROJECT_STATUS.md)
- 🗺️ [ドキュメント一覧](docs/README.md)
- 🏗️ [アーキテクチャ文書](docs/architecture/README.md)
- 🧭 [パイプライン実装計画](docs/architecture/pipeline_implementation_plan.md)
- 🚀 [OpenWebUI + LM Studio MVPガイド](docs/openwebui_lmstudio_mvp.md)
- ⚙️ [設定スキーマ](docs/config_schema.md)
- 📜 [契約文書](docs/contracts/README.md)
- 🧪 [Smoke testと検証](docs/smoke/README.md)
- 🧬 [RelaySOUL設計とゲート](docs/relaysoul/README.md)
- 🗃️ [MVP概要とマイルストーン履歴](docs/mvp/README.md)

## 🔗 RelayKVとの関係

[RelayKV](https://github.com/rinsakamo/relay-kv) は、隣接するランタイム・KVキャッシュ研究リポジトリです。RelayLMは、その1層上で会話とコンテキストを扱うプロキシです。

RelayLMは、RelayKVのworking-set選択、anchor/recent/retrieved分離、Persona Anchor KV、cache-aware layoutといった設計知見を活用しますが、初期製品では推論エンジンのKVキャッシュを直接変更しません。

## 📄 ライセンス

RelayLMは [Apache License 2.0](LICENSE) のもとで公開されています。
