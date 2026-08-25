# RelayLM 1.0

[English](README.md) | **日本語**

> このファイルは利用者向けの日本語訳です。RelayLM `v1` の正本となる製品説明は [`README.md`](README.md) およびリンク先の current-authority docs です。内容に差異がある場合は、それらの英語正本を優先します。

RelayLM 1.0 は、ゼロから設計された永続キャラクター・ランタイムです。アーキテクチャとしては、交換可能な言語モデルの外側に置かれる、モデル非依存の **[Cognitive Proxy Runtime（認知プロキシ・ランタイム）](docs/architecture/core.md)** として動作します。

> **Identity + Now + LM**

モデルそのものがキャラクターなのではありません。RelayLM は、Identity、evidence、受理された現在の State、context authority、検証済みの状態変化をモデルの外側に保持します。

## 1つのランタイム、2つの見方

一般ユーザーにとって最も簡単な捉え方は、**対応するLMに、持続するキャラクターを与える**ことです。[`SOUL.md`](examples/starter/SOUL.md) が安定した Identity を与え、governed State と Continuity が受理された「今」を与えます。その下で動く provider model は交換できます。

ただし、RelayLM の Identity は人間らしい人格を模倣する必要はありません。同じ `SOUL.md` に、厳密な要約機、レビュアー、研究支援、構造化記録システムのような、意図的に機械的な cognitive role を記述することもできます。その意味で、**キャラクターは cognitive persona の一形態であって、RelayLM の限界ではありません。**

開発者や業務利用では、RelayLM は「どの安定した Identity / role と、どの governed context をモデルへ渡すか」を決め、さらにモデルから戻ってきた提案のうち、どの変化を RelayLM 側の authority に受け入れるかを決めるミドルウェアとして扱えます。

```text
application / user
      |
      v
   RelayLM
identity / role + governed context + State / Continuity
      |
      v
replaceable LM
```

小型のローカルモデルで気軽なキャラクター実験を始め、同じ RelayLM-owned Identity、role、accepted State を、あとからより大きな対応モデルへ渡すこともできます。持続したり「成長」したりする主体はモデルそのものではありません。安定した Identity と accepted State は RelayLM 側に保持され、bounded Continuity は RelayLM が所有する一時的な authority として扱われます。

> **Character is one cognitive persona. RelayLM is the cognitive proxy around the model.**  
> キャラクターは cognitive persona の一形態。RelayLM はモデルの外側にある cognitive proxy です。

## Product line

- `v1` が RelayLM 1.0 の現行 product line です。
- RelayLM 0.x は歴史的資料・参照実装として保存されています。
- 1.0 は、0.x の runtime / module 構造を既定では継承しません。
- Issue [#1257](https://github.com/rinsakamo/relay-lm/issues/1257) と [#1258](https://github.com/rinsakamo/relay-lm/issues/1258) の design evidence は意図的に引き継いでいます。

## Core 1.0 turn

現在の通常リリース／参照アーキテクチャは [two-pass](docs/contracts/cognition-pass-execution.md) で、同じロード済み online model を順番に再利用します。

```text
SOUL.md + Events + State
          |
          v
    Context Compiler
          |
          v
   CognitiveInput
      /       \
     v         v
 Pass 1       Pass 2
conversation  semantic extraction
     |         |
     v         v
 response   State / Continuity proposals
               |
               v
        deterministic validation
               |
               v
        State / Continuity authority
```

Pass 1 がユーザーに見える会話応答を担当します。Pass 2 は、governed turn と、それより authority の低い Pass 1 response から即時に semantic extraction を行います。proposal の parsing、validation、lifecycle、persistence、canonical authority を所有するのはモデルではなく RelayLM です。

Pass 2 が失敗または拒否されても、正しく生成された Pass 1 response は有効なままです。永続キャラクター・ランタイムとして正しく動作している RelayLM は、生の transcript history を真実としてリプレイしなくても停止・再起動できます。

## 現在の v1 artifact をビルドして実行する

現時点では public publication channel の存在を前提にしません。クリーンな `v1` source checkout から現在の配布 artifact をビルドし、wheel を editable ではない形でインストールします。

```bash
python -m pip install build
python -m build --wheel --sdist
python -m venv .relaylm-runtime
.relaylm-runtime/bin/python -m pip install dist/relaylm-*.whl
```

Character Package はインストール済み Python package の外側に置き、その filesystem path を runtime に指定します。

```bash
export RELAYLM_CHARACTER_DIR=/absolute/path/to/character
export RELAYLM_PROVIDER_BASE_URL=http://127.0.0.1:1234/v1
export RELAYLM_PROVIDER_MODEL='<provider-model-id>'

.relaylm-runtime/bin/relaylm doctor
.relaylm-runtime/bin/relaylm serve
```

calibrated profile を選択していない場合、Core 1.0 cognition topology の既定値は `two_pass` です。この topology default が reasoning、decoding、output budget、context window の値を勝手に設定することはありません。明示的な pass control は runtime YAML から渡せます。calibrated profile の authority は引き続き [#1388](https://github.com/rinsakamo/relay-lm/issues/1388) です。

同等の machine / runtime 設定は、`--config PATH` または `RELAYLM_CONFIG` で選択した versioned runtime YAML からも指定できます。schema / precedence は [`runtime-configuration.md`](docs/contracts/runtime-configuration.md)、`doctor` / `serve` の動作は [`runtime-operator.md`](docs/contracts/runtime-operator.md) を参照してください。

provider authentication が必要な場合は `RELAYLM_PROVIDER_API_KEY` を使用します。server は既定で `127.0.0.1:8090` に bind し、`RELAYLM_HOST` と `RELAYLM_PORT` で上書きできます。[`examples/starter`](examples/starter/) は source checkout 向けの example であり、installed artifact の runtime dependency ではありません。

[OpenAI互換の client endpoint](docs/contracts/openai-api.md) は次のとおりです。

```text
POST /v1/chat/completions
```

buffered request と streaming request は、同じ選択済み cognition topology を使用します。two-pass streaming では、安全に decode された Pass 1 text を Pass 2 完了前に配信できますが、State / Continuity の mutation には有効かつ current な Pass 2 result が必要です。client-supplied history は RelayLM の memory や Identity authority として扱われません。

## Native evaluation

決定論的な RelayLM-native evaluation foundation は、installed artifact から次のように実行できます。

```bash
.relaylm-runtime/bin/relaylm-eval
```

RelayLM boundary ごとの machine-readable な invariant check を出力し、意図的に weighted composite score は持ちません。[`evaluation.md`](docs/reference/evaluation.md) と [#1247](https://github.com/rinsakamo/relay-lm/issues/1247) を参照してください。

実モデルを使う Stage R quality / evidence は、この deterministic native suite とは別のプロセスです。

## Development workflow

現在の `v1` development workflow は [`development-workflow.md`](docs/reference/development-workflow.md) に定義されています。

semantic change の基本順序は次のとおりです。

> **Meaning → Example → Test → Code → Docs/Authority → Audit**

semantic behavior change は test-first で進めます。behavior-preserving change と docs-only transaction は、それより軽量な手順を使います。1 transaction は1つの bounded responsibility を持ち、current-authority docs は deferred behavior を現在実装済みであるかのように記述してはいけません。merge は exact-head で行います。各 transaction は自身の semantic owner の authority を直接収束させ、global view は必要時に導出し、手作業では維持しません。

repository 利用上の規約は [`repository-practices.md`](docs/reference/repository-practices.md) にあります。長期的に残す architecture decision は意図的に [`docs/decisions/`](docs/decisions/) 配下へ絞り、[`.ai/authority/`](.ai/authority/) には semantic owner ごとの owner-local validated authority declaration を1つずつ置きます。

[`ARCHITECTURE.md`](ARCHITECTURE.md) は repository authority から生成される projection です。各 transaction で手作業同期するのではなく、version / release boundary で materialize されます。

詳細は [`core.md`](docs/architecture/core.md)、[`cognition-pass-execution.md`](docs/contracts/cognition-pass-execution.md)、[`openai-api.md`](docs/contracts/openai-api.md)、[`runtime-configuration.md`](docs/contracts/runtime-configuration.md)、[`release-distribution.md`](docs/contracts/release-distribution.md)、Issue [#1259](https://github.com/rinsakamo/relay-lm/issues/1259) を参照してください。
