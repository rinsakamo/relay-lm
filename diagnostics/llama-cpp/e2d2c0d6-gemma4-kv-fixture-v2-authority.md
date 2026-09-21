# Gemma 4 retained-prefix KV fixture v2 authority

Diagnostic only. This authority creates a new repository-owned synthetic request subject. It does not authorize measured KV generation.

## Status

`FIXTURE_V2_COMMITTED`

The fixture-v2 request subject is now durably repository-owned. No measured execution is authorized by this status.

## Why a new subject is required

The historical warm/target token arrays and L0/L1/LC raw request files are no longer recoverable from surviving local evidence.

Surviving repository material proves only historical identities and geometry:

```text
historical corpus SHA256 = 4ffd2967dc487d6c4fd4de94e66a017fdf452399105c08093ebbcf0ecfc13936
historical corpus bytes = 113853
historical warm token raw SHA256 = c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2
historical target token raw SHA256 = 549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e
historical warm length = 883
historical target length = 2927
historical LCP = 865
historical effective aligned reuse = 512
```

The raw bytes themselves are absent. The prior request reconciliation root, measured preflight binding, qualified pre-measured root, and bounded raw request artifacts are unavailable.

Therefore the historical request subject is:

`REQUEST_PROVENANCE_UNRECOVERABLE`

Do not regenerate, reconstruct, retokenize, or claim continuity with the historical request identity.

A new diagnostic can still test the retained-prefix KV mechanism, but it must use a distinct request identity and must not compare prompt-specific numerical values as if they belonged to the historical g1/g2 subject.

## New synthetic fixture geometry

Fixture v2 intentionally preserves only the physical geometry relevant to the aligned-reuse discriminator:

```text
warm length = 883
target length = 2927
LCP = 865
n_batch = 512
n_ubatch = 512
effective aligned reuse = floor(865 / 512) * 512 = 512
```

This preserves the same four-point KV observation structure:

- warm P512;
- retained R512 after reuse=512;
- fresh warm reproducibility P512;
- cold target P512.

It does not preserve historical prompt semantics or historical logits.

## Repository-owned fixture tooling

Use only:

```text
e2d2c0d6-gemma4-kv-fixture-v2-corpus.py
e2d2c0d6-gemma4-kv-fixture-v2-materialize.py
e2d2c0d6-gemma4-kv-fixture-v2-admission.py
e2d2c0d6-gemma4-kv-fixture-v2-selftest.py
e2d2c0d6-gemma4-kv-fixture-v2-tokenize-run.py
e2d2c0d6-gemma4-kv-fixture-v2-tokenize-run-selftest.py
```

The source-corpus generator emits:

- a deterministic synthetic UTF-8 corpus;
- the exact canonical `POST /tokenize` request body.

The tokenizer request is fixed to:

```json
{
  "add_special": false,
  "parse_special": false,
  "with_pieces": false
}
```

with `content` equal byte-for-text to the generated corpus.

The exact llama.cpp source revision documents `POST /tokenize` with:

- required `content`;
- `add_special=false`;
- `parse_special=false`;
- `with_pieces=false`;
- response object field `tokens` containing integer token IDs.

## Materialization rule

The tokenizer response supplies only a pool of valid model token IDs.

The materializer constructs:

```text
warm = pool[0:883]

common = pool[0:865]

target suffix length = 2062
target suffix source offset =
  first offset >= 883 for which pool[offset] != pool[865]
  and enough tokens remain

target = common + selected 2062-token suffix
```

It must prove:

```text
len(warm) = 883
len(target) = 2927
LCP(warm, target) = 865
```

The materializer then creates canonical JSON:

```text
warm.tokens.json
target.tokens.json

L0.request.json
  prompt = warm
  cache_prompt = true

L1.request.json
  prompt = target
  cache_prompt = true

LC.request.json
  prompt = target
  cache_prompt = false
```

All three requests use exactly:

```text
n_predict = 1
temperature = 0
stream = false
n_probs = 20
```

L1 and LC must differ only by `cache_prompt`.

L0R remains defined as sending the exact raw bytes of `L0.request.json` on the fresh WR2 server.

## Provenance bundle

The fixture directory must contain all of:

```text
source-corpus.txt
tokenizer-request.json
tokenizer-response.json
warm.tokens.json
target.tokens.json
L0.request.json
L1.request.json
LC.request.json
manifest.json
```

The manifest binds SHA256 and byte counts for every non-manifest file plus:

- tokenizer response token-pool length;
- exact target-suffix source offset;
- warm/target/LCP geometry;
- tokenizer endpoint/options;
- exact L0R rule.

The admission checker must pass:

`LOGICAL_PREFIX_FIXTURE_V2_ADMISSION_PASS`

before any fixture may be committed.

## Static gate

Before physical tokenization:

1. Python-compile all four fixture-v2 helpers.
2. Run:

`e2d2c0d6-gemma4-kv-fixture-v2-selftest.py`

Required terminal:

`LOGICAL_PREFIX_FIXTURE_V2_SELFTEST_PASS`

The self-test uses a synthetic integer token pool only. It performs no model/server/GPU call.

## Tokenize-run static endpoint self-test correction

The first fixture-v2 preparation transaction stopped at the tokenize-run static self-test before build, guard acquisition, server startup, tokenization, materialization, admission, repository commit, or push.

Observed static terminal:

`LOGICAL_PREFIX_FIXTURE_V2_TOKENIZE_RUN_SELFTEST_FAIL`

Failed checks:

```text
health_endpoint_present
tokenize_endpoint_present
```

The tokenize runner itself was not invoked. Its Git blob remained:

`ea690526ce281eaf839ce1a64c1008db5577e0c3`

Fresh source inspection confirmed that the runner already calls exactly:

```text
http_get(f"http://127.0.0.1:{args.port}/health", ...)
http_post_raw(f"http://127.0.0.1:{args.port}/tokenize", ...)
```

The prior self-test incorrectly searched the source text for standalone literals `"/health"` and `"/tokenize"`. Those literals do not occur because the endpoints are embedded in f-strings.

Diagnostic-only self-test repair:

```text
82dd76ef8cdd3c6d704143f2c494e148de3e4001
  Fix tokenize runner endpoint self-test
```

The corrected self-test parses the runner AST, extracts endpoint templates from `http_get` and `http_post_raw` call sites, and requires the exact set:

```text
http_get      -> http://127.0.0.1:{}/health
http_post_raw -> http://127.0.0.1:{}/tokenize
```

It also requires that these are the only HTTP endpoint call templates and separately rejects completion/chat-completion endpoint templates.

The failed transaction accounting was:

```text
build attempts = 0
guard acquisitions = 0
idle observations = 0
server lifetimes = 0/0
/tokenize requests = 0
generation requests = 0
materializer invocations = 0
admission invocations = 0
repository commits = 0
pushes = 0
v1 mutations = 0
scientific campaign interactions = 0
```

Therefore fixture v2 remains unmaterialized and unconsumed. A new fixture-v2 preparation transaction may begin from fresh repository authority. No measured execution authority is created by this correction.

## Tokenization physical boundary

The only permitted model interaction in the fixture-preparation transaction is one `POST /tokenize` call.

No completion/chat/generation endpoint may be called.

Use:

```text
llama.cpp source = e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d
model SHA256 = c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed
parallel = 1
context = 8192
n_batch = 512
n_ubatch = 512
gpu layers = 999
context shift = disabled
flash attention = ON
```

A fresh disposable build may use the current repaired diagnostic patch set. Tokenization semantics are model/vocabulary material; nevertheless exact source/patch/server/model identity must be recorded.

The only authorized tokenization child entrypoint is:

`e2d2c0d6-gemma4-kv-fixture-v2-tokenize-run.py`

Its static contract must first pass:

`LOGICAL_PREFIX_FIXTURE_V2_TOKENIZE_RUN_SELFTEST_PASS`

The tokenize-only runner is fixed to the target runtime, validates the model SHA256, generates the repository-owned corpus/request, starts one server, polls only `/health`, sends exactly one `POST /tokenize`, saves raw response bytes, records `generation_requests=0`, and terminates that server. It contains no completion/chat-completion endpoint.

The server must be started only as the child of the canonical diagnostic local-GPU resource guard:

```text
resource key = llama-cpp:local-gpu
lock = /tmp/relaylm/physical/locks/a820834e5681ba28.lock
```

Require exactly two external-idle observations five seconds apart before the child starts.

The guard child must be exactly the tokenize-only runner above. Do not reproduce its server lifecycle manually with curl/bash when the repository-owned runner is available.

It must send zero generation requests.

## Repository durability boundary

A successfully admitted fixture is not considered durable until its complete provenance bundle is committed to:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2/`

on the diagnostic branch.

The fixture-preparation transaction may create exactly one repository commit containing only that fixture directory.

Before pushing:

- reacquire the remote diagnostic branch HEAD;
- require it to equal the execution base expected by the isolated checkout;
- do not rebase or merge on drift;
- if remote drift exists, preserve the local fixture commit and stop without pushing.

No v1 mutation is permitted.

Once pushed, stop. Do not run pre-measured KV qualification and do not create a measured authority in the same transaction.

## Terminal classes

### `LOGICAL_PREFIX_FIXTURE_V2_COMMITTED`

All static checks passed, exactly one tokenization request succeeded, fixture admission passed, and the exact bundle was committed/pushed to the diagnostic branch without remote drift.

### `LOGICAL_PREFIX_FIXTURE_V2_MATERIALIZED_NOT_COMMITTED`

Fixture materialization/admission succeeded but repository durability was not established.

### `LOGICAL_PREFIX_FIXTURE_V2_NOT_MATERIALIZED`

Any pre-tokenization or tokenization/materialization/admission requirement failed.

No automatic retry, replay, reseed, alternative corpus, fallback tokenizer, or request reconstruction is authorized in the same transaction.

## Counters

Report exactly:

```text
fixture self-test invocations
build attempts
guard acquisitions
idle observations
server lifetime attempts/completions
/tokenize requests
generation requests
fixture materializer invocations
fixture admission invocations
repository commits
push attempts
v1 mutations
scientific campaign interactions
```

## Committed fixture authority

Fixture commit:

`58d3c1e9b8cf973648be1aeb8a8b12429a69d088`

Commit tree:

`8c6b356a7b73931cc0a71834c784935cf82bc256`

Fixture subtree:

`455d94850515c70995addc6c1c446ba738a01474`

Repository path:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2/`

The committed directory contains exactly nine authority files and no runtime/admission logs.

Fresh remote read-back from the diagnostic branch confirms:

```text
subject = logical-prefix-kv-fixture-v2
format_version = 1
warm_len = 883
target_len = 2927
LCP = 865
target_suffix_source_offset = 883
target_suffix_len = 2062
token_pool_len = 90140
tokenizer endpoint = /tokenize
add_special = false
parse_special = false
with_pieces = false
```

Fresh semantic read-back also confirms:

```text
L0 prompt == warm fixture
L1 prompt == target fixture
LC prompt == target fixture

L0 cache_prompt = true
L1 cache_prompt = true
LC cache_prompt = false

n_predict = 1 for L0/L1/LC
temperature = 0 for L0/L1/LC
stream = false for L0/L1/LC
n_probs = 20 for L0/L1/LC

L1 and LC differ only by cache_prompt
```

Committed SHA256 identities:

```text
source-corpus.txt =
8f5e83bc034a7678ecce6ddc25dc5507ed726b849f9ecfaa19865b9ba885459a

tokenizer-request.json =
cd55b727276462f2725e1a13b0f217bb35f0e7a097504f082473200fa2bdb66e

tokenizer-response.json =
e46ec4970db8dfeca4f7f0a7133da4c5eba75c20815dfbdcf446912310ebe4ac

warm.tokens.json =
cc42e325d85ed559835225b53152446bc405b2d166c10a3e16b07c7859bf7f27

target.tokens.json =
8c05cf7a6d11d684be091c49a9f9d76201274e1efad31c9b19234cb4ec985730

L0.request.json =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d

L1.request.json =
b7e482874b1a3c8b80136e2d2e8a76594c318230f5f8bae4171d2f0efff465eb

LC.request.json =
63afb2a44ea12f14377ba52348616a0bd8ac3ebdd65d81d1a3ede1c4c2c64043

manifest.json =
d08e6aa1c4a9c263f5b3e0d1911f3117335f4dfdc267d9a2d5ea187401c92e3d
```

Committed Git blob identities:

```text
source-corpus.txt =
7ad9ae44ee56f7338cdc8594ed5872e9d1773001

tokenizer-request.json =
7bf97501c02a813c3ae8b608c1e8f82c869918dd

tokenizer-response.json =
247a2a285877b217f2f6132f3e7edf5629b1658f

warm.tokens.json =
c83fffa75bf006804131eb9dd9ad84dfa9f46d1b

target.tokens.json =
f127cf2bec7f217f27a5c04cb059ddb9ccd039bd

L0.request.json =
a4d7d31b268cb173a93ff32c87184dc9a16998e4

L1.request.json =
07dfdc83366dd5ba57e0c9af5571493dbe9ed6ca

LC.request.json =
5534a9dcb9da289b0448a139b77dcf94287fdfd7

manifest.json =
ece1a792d3ec60e594131c52d5f0f4900298db04
```

L0R is now durably defined as the exact raw bytes of the committed `L0.request.json` on a fresh WR2 server.

The fixture-generation transaction was generation-free and measured-L0-free:

```text
build attempts = 1
guard acquisitions = 1
idle observations = 2
server lifetimes = 1/1
/tokenize requests = 1
generation requests = 0
materializer invocations = 1
admission invocations = 1
repository commits = 1
pushes = 1
v1 mutations = 0
scientific campaign interactions = 0
campaign queue/spend mutation = false
measured qualification/L0 = 0
```

The tokenizer build/server SHA `64f73785c3d70203826a8da6a54fbd277b01b542dd343b005ad3a07f9eaaddb0` belongs only to fixture materialization. It is not measured-apparatus authority and must not be promoted or reused as such.

## Current measured execution route

The fresh repaired pre-measured apparatus qualification has completed successfully and a distinct fixture-v2 measured authority now exists.

Current measured authority:

`e2d2c0d6-gemma4-kv-fixture-v2-measured-authority.md`

Required status:

`QUALIFIED_FOR_ONE_FIXTURE_V2_MEASURED_ATTEMPT`

Authority generation:

`logical-prefix-kv-fixture-v2-measured-authority-20260922-f6b67141`

Attempt identity:

`logical-prefix-kv-fixture-v2-20260922-f6b67141`

Bound fresh physical apparatus:

```text
pre-measured root =
/tmp/relaylm-kv-v2-premeasured.kq8VQ5/output

llama-server SHA256 =
f6b671417ac9b6c7b4e00da95980caf828b8d63133ca61fdad60153b67a39e22

libllama-server-impl.so SHA256 =
7456ded50dca4f6ad5f53dd9e178d16954e2c9134ee912c5ea8ed3760db3735a

libllama.so SHA256 =
178b81207d10e053490627e2755a61069ae912053cf0abcffa258989bac0528e

startup canonical argv SHA256 =
5d9d486e67aa19e1b26ff00c33f50c30b57a41788c212bcccc2ab0bf4f992706

base KV = 8192
SWA KV = 1536
```

The only authorized measured entrypoint is:

`e2d2c0d6-gemma4-kv-fixture-v2-execute-once.py`

This fixture authority does not itself authorize direct execution. The measured-attempt authority above is the execution authority.

The historical request subject remains `REQUEST_PROVENANCE_UNRECOVERABLE`, and the historical consumed measured authority remains terminal.

No other pre-measured qualification, request regeneration, historical runner invocation, or alternate measured path is authorized before this measured authority is resolved.

