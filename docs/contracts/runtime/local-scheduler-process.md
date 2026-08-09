---
relaylm_doc_type: contract
relaylm_authority: current_local_scheduler_process_and_cli_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_scheduler
relaylm_update_trigger:
  - O3 local scheduler CLI arguments, defaults, or mutual exclusion change
  - config-load, settings-construction, signal-adapter, or O2 invocation behavior changes
  - O3 JSON output or exit-code mapping changes
  - always-on to O2 settings translation changes
  - local scheduler process becomes app-embedded or gains independent lower authority
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - O2 supervised service-loop result, settings, pacing, sleep, or policy-state semantics
  - O1E cancellation checkpoints or stale-recovery orchestration
  - O1D2 policy, O1D1 round, B3 queue, C2 worker, or I1-GC/I1-GD durable-finalization semantics
  - FastAPI startup, browser, or SOUL Lab authority
  - durable-memory E2 scenario semantics
  - scheduler gate defaults or lower mutation authority
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o3_always_on_local_scheduler.md
  - ../../architecture/o2_supervised_scheduler_service.md
relaylm_related_contracts:
  - supervised-scheduler-service.md
  - scheduler-operational-controls.md
  - scheduler-policy.md
  - scheduler-round.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o3_always_on_local_scheduler_smoke.py
  - ../../../scripts/relaylm_o2_supervised_scheduler_service_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - local RelayMEM scheduler operators
  - O3 CLI/process maintainers
  - O2 service and runtime operations maintainers
  - security, privacy, observability, and deployment reviewers
relaylm_authority_level: exact_contract
---
# Local Scheduler Process Contract

## Authority summary

This contract owns the exact current **O3 opt-in local process/CLI wrapper** implemented by:

```text
scripts/relaylm_o3_always_on_local_scheduler.py
```

O3 is a process surface above the separately owned O2 supervised scheduler service. It owns only:

```text
CLI parse
  -> bounded O2 settings construction
  -> RelayLM config load
  -> existing signal-cancellation adapter installation
  -> one O2 service invocation
  -> one content-free JSON projection print
  -> bounded process exit code
```

O3 does not own scheduler-round semantics, pacing policy, stale recovery, queue transitions, worker execution, memory formation, durable finalization, retrieval, browser behavior, or FastAPI startup.

The authority chain remains:

```text
O3 local process / CLI
  -> O2 supervised scheduler service
     -> O1E operational controls
        -> O1D2 scheduler policy
           -> O1D1 one-round scheduler
              -> separately owned replay / queue / worker / finalization boundaries
```

## Current implementation and source anchors

The exact process implementation is:

```text
scripts/relaylm_o3_always_on_local_scheduler.py
```

The current implementation handoff remains:

```text
docs/architecture/o3_always_on_local_scheduler.md
```

The O2 exact service contract is:

```text
docs/contracts/runtime/supervised-scheduler-service.md
```

This transaction does not retire or move the O3 handoff or implementation.

## Process nature

O3 is explicitly opt-in.

It does not:

- start on module import;
- start from FastAPI `create_app()`;
- register a browser or SOUL Lab background task;
- turn any scheduler or mutation gate on;
- spawn a second service or worker pool;
- directly inspect or mutate queue/memory state.

An operator starts O3 by invoking the script.

## Parser authority

The current parser is built by `_parser()` and has this description:

```text
Run the opt-in RelayMEM O3 always-on local scheduler wrapper.
```

The current CLI options are exactly:

```text
--config
--max-rounds
--always-on
--idle-sleep-ms
--stop-after-idle-rounds
--max-sleep-ms
```

O3 has no current CLI option for queue roots, job IDs, dispatch IDs, claim tokens, worker IDs, protected source, memory page paths, durable-finalization locators, or backend prompts.

## `--config`

`--config` supplies the path argument passed to the existing RelayLM:

```text
load_config(args.config)
```

O3 does not parse RelayLM configuration itself and does not redefine lower config fields.

The raw config path is not included in O3 public JSON output.

## Bounded-versus-always-on mutual exclusion

The parser creates one mutually exclusive argument group containing:

```text
--max-rounds
--always-on
```

They therefore cannot be selected together through normal argparse parsing.

## `--max-rounds`

The current option is:

```text
--max-rounds
  type = int
  default = 1
```

The default process invocation is therefore bounded to an O2 settings object with:

```text
max_rounds = 1
```

unless `--always-on` is selected.

The help boundary describes the value as an O2 round count and requires at least one round.

## O3 max-rounds precheck

When not in always-on mode, O3 performs this explicit pre-service check:

```text
type(args.max_rounds) is int
AND
args.max_rounds >= 1
```

If the check fails, O3 does not load config or invoke O2.

It builds an O2-shaped content-free projection using:

```text
make_relaymem_slp_supervised_scheduler_service_projection(
    status = invalid_config,
    reason_id = cli_max_rounds_invalid,
)
```

then prints the projection and exits using the normal O3 exit-code mapping.

## `--always-on`

`--always-on` is a boolean `store_true` flag.

Its exact current translation is:

```text
max_rounds = None
```

when constructing `RelayMEMSLPSupervisedSchedulerServiceSettings`.

Always-on therefore removes only the O2 max-round-count cap.

It does not remove or bypass:

- O2 cancellation;
- O2 idle stop limit;
- O2 lower disabled/invalid/unsafe/shutdown stops;
- O1E cancellation checks;
- O1D2 pacing semantics;
- lower queue, worker, durable-finalization, or mutation gates.

O3 does not implement its own while-loop. The recurring loop remains inside O2.

## Sleep-related CLI options

The current O3 parser exposes:

```text
--idle-sleep-ms
  type = int
  default = 1000

--stop-after-idle-rounds
  type = int
  default = 1

--max-sleep-ms
  type = int
  default = 60000
```

O3 passes those values to the exact O2 settings constructor.

O3 itself does not sleep and does not reinterpret O2 sleep bounds.

Invalid values are rejected by O2 settings construction and normalized by O3 to one bounded pre-service failure projection.

## Exact O2 settings construction

After max-round translation, O3 constructs:

```text
RelayMEMSLPSupervisedSchedulerServiceSettings(
    max_rounds = None if always_on else args.max_rounds,
    stop_after_idle_rounds = args.stop_after_idle_rounds,
    idle_sleep_ms = args.idle_sleep_ms,
    max_sleep_ms = args.max_sleep_ms,
    install_signal_handlers = false,
)
```

O3 deliberately sets:

```text
install_signal_handlers = false
```

because O3 owns process-level installation of the already-existing signal adapter around the O2 call.

The exact O2 numeric/type bounds remain owned by `supervised-scheduler-service.md`.

## Settings-construction failure

Any exception raised during O2 settings construction is caught by O3 and converted to:

```text
status = invalid_config
reason_id = cli_scheduler_settings_invalid
```

through the O2-shaped projection helper.

O3 then prints that projection as JSON and returns the O3 exit code for `invalid_config`.

The raw exception is not printed.

## RelayLM config loading

After valid O2 settings exist, O3 loads configuration with:

```text
load_config(args.config)
```

Any exception from config loading is caught and normalized to:

```text
status = invalid_config
reason_id = config_load_failed
```

through the same O2-shaped content-free projection helper.

O3 does not emit:

- the raw config body;
- the raw config path;
- parser internals;
- validation exception text;
- backend secrets or URLs beyond whatever bounded O2 projection fields already permit.

The config load must succeed before O2 is invoked.

## Signal-cancellation process boundary

For a valid settings/config pair, O3 constructs the existing:

```text
SchedulerSignalCancellationAdapter()
```

and installs it with:

```text
with adapter.installed():
```

The adapter currently maps SIGINT/SIGTERM into its existing `SchedulerCancellationToken` and restores prior handlers on exit.

O3 passes:

```text
cancellation = adapter.token
```

to O2.

O3 does not define a second cancellation token type, signal handler implementation, asynchronous interrupt mechanism, timer, or background watcher.

The exact signal-adapter mechanics remain owned by `scheduler-operational-controls.md`.

## O2 invocation boundary

Inside the signal-adapter context, O3 invokes exactly:

```text
run_relaymem_slp_supervised_scheduler_service(
    config = config,
    settings = settings,
    cancellation = adapter.token,
)
```

O3 does not pass a custom O1E runner, sleeper, registry, or `now` value in the current process implementation.

All repeated scheduling, sleeps, policy-state carry-forward, idle handling, and lower-state handling remain O2 authority.

## Successful O2 return handling

After O2 returns, O3 obtains only:

```text
projection = result.projection()
```

It does not inspect lower private results because the O2 result retains none.

The projection is printed once and its `status` controls the exit code.

## JSON-only output helper

`_print_projection(projection)` currently executes:

```text
json.dumps(
    dict(projection),
    ensure_ascii = false,
    sort_keys = true,
)
```

and prints exactly that serialized object followed by normal print newline behavior.

O3 does not wrap the projection in prose, labels, markdown, log prefixes, or a second JSON object.

The focused CLI smoke requires stdout to begin with `{` and end with `}` and requires stderr to be empty for its tested cases.

## O2-shaped pre-service failures

O3 does not define a second result schema for config/settings/precheck failures.

Instead it calls:

```text
make_relaymem_slp_supervised_scheduler_service_projection(...)
```

so pre-service failures retain the existing O2 public projection shape.

Current O3-specific bounded reason IDs used this way are:

```text
cli_max_rounds_invalid
cli_scheduler_settings_invalid
config_load_failed
```

The reason IDs do not include raw values, paths, exceptions, config bodies, queue identities, or memory content.

## Normal-status set

The current O3 `_NORMAL_STATUSES` set is exactly:

```text
disabled
completed
idle
cancelled
shutdown_requested
```

These statuses map to successful process exit code `0`.

A normal exit code does not assert that any queue or memory mutation occurred. For example, default-off config normally produces O2/O3 `disabled` and exit code zero.

## Exit-code mapping

The current `_exit_code(status)` mapping is exactly:

```text
disabled            -> 0
completed           -> 0
idle                -> 0
cancelled           -> 0
shutdown_requested  -> 0

invalid_config      -> 2
invalid_input       -> 2

unsafe_state        -> 3

anything else       -> 4
```

The fallback `4` therefore covers current `unexpected_failure` and any unrecognized status object.

O3 does not reuse process exit codes as lower queue, worker, memory, or durable-finalization statuses.

## Default invocation behavior

With a valid default RelayLM config and no explicit scheduling enablement, the focused O3 smoke verifies:

```text
python .../relaylm_o3_always_on_local_scheduler.py --config <config>
```

returns:

```text
exit code = 0
projection.status = disabled
projection.rounds_attempted = 1
```

The same behavior is verified with explicit:

```text
--max-rounds 1
```

This demonstrates that O3 is opt-in and does not silently enable lower scheduling gates.

## Always-on invocation under default-off gates

The focused smoke also runs:

```text
--always-on
```

against default-off scheduler configuration.

The process returns normally because lower O1E/O2 reports disabled:

```text
exit code = 0
projection.status = disabled
projection.last_operational_status = disabled
```

`--always-on` therefore does not force lower operational gates open.

## Invalid lower configuration behavior

The focused smoke provides a RelayLM configuration with an invalid operational gate triple.

O3 invokes O2 only after configuration loading succeeds; lower validation then produces a bounded invalid configuration result.

The smoke requires:

```text
exit code != 0
projection.status = invalid_config
projection.last_operational_status = not_invoked
```

No raw config or lower private identity is emitted.

## Public privacy boundary

O3 prints only the O2 public projection or the O2-shaped pre-service projection.

Current smoke evidence forbids public occurrence of tokens representing:

```text
job_id
dispatch_idempotency_key
lease_token
claim_owner
protected_source_body
memory_content
O3_PRIVATE_CANARY_68c872
```

The architecture boundary additionally excludes queue paths and raw config paths.

O3 does not inspect those values in normal operation, so it has no reason to project them.

## Stderr boundary

In current focused success/invalid-config smoke cases, stderr is required to remain empty.

O3 catches settings/config-load failures that it owns and emits their bounded result on stdout rather than a traceback.

Argument-parser failures remain argparse process behavior and are not redefined as O2-shaped runtime projections by this contract.

## Argparse failure boundary

Parser-level errors such as mutually exclusive options or malformed integer syntax are handled by Python `argparse` before `main` reaches the bounded pre-service projection logic.

This exact contract does not claim that every command-line syntax error yields O2 JSON. The JSON-only runtime projection rule applies after successful argument parsing enters O3 `main`.

## No direct lower authority

O3 never directly calls:

- queue-root open/read/write helpers;
- B3 queue transition functions;
- replay-lane discovery or replay finalization;
- C2 worker execution;
- Subjective MEM writer or reader;
- durable-finalization store mutation;
- O1D1 lane delegates;
- O1D2 policy application functions.

Its only scheduling execution call is O2.

## App/browser boundary

O3 remains a local process wrapper.

It is not started by:

- FastAPI `create_app()`;
- request handling;
- SOUL Lab UI;
- browser JavaScript;
- character workspace compilation;
- ordinary conversation path startup.

This separation prevents local process lifecycle from becoming browser or request-path authority.

## Durable-memory E2 boundary

O3 may be used operationally to drain eligible lower work before a later durable-memory evaluation.

O3 does not own:

- E2 scenario setup;
- memory formation correctness;
- fresh-session recall correctness;
- memory-value scoring;
- evaluation pass/fail authority.

Those remain separate evaluation/runtime responsibilities.

## Failure closure

The exact current O3 process rules close failures as follows:

1. invalid bounded `--max-rounds` after parsing becomes O2-shaped `invalid_config` and exit `2`;
2. O2 settings construction exception becomes `cli_scheduler_settings_invalid`, with no traceback projection;
3. config-load exception becomes `config_load_failed`, with no raw path/config/exception in JSON;
4. lower O2 `invalid_config` or `invalid_input` exits `2`;
5. lower O2 `unsafe_state` exits `3`;
6. lower unexpected/unrecognized status exits `4`;
7. lower normal disabled/completed/idle/cancel/shutdown exits `0`;
8. O3 never bypasses lower gates in response to an error;
9. `--always-on` removes only max-round count and cannot open lower scheduler/mutation gates;
10. process cancellation uses the existing O1E signal token rather than a new mutation/cancellation authority.

## Current focused evidence

The exact O3 process contract is guarded by:

```text
scripts/relaylm_o3_always_on_local_scheduler_smoke.py
scripts/relaylm_o2_supervised_scheduler_service_smoke.py
```

The O3 subprocess smoke validates:

- default bounded invocation;
- explicit `--max-rounds 1`;
- `--always-on` translation;
- default-off lower scheduler behavior;
- invalid lower operational configuration;
- JSON stdout shape;
- empty stderr for tested runtime cases;
- bounded exit-code behavior;
- absence of private canaries and queue/claim/memory identity tokens.

## Relationship to O2

O2 owns the supervised scheduler service loop, settings validation, round counters, sleeps, pacing handling, cancellation checks, signal combination when requested by its API, and O2 result/projection schema.

O3 owns only the local process/CLI surface that constructs one O2 settings object, installs the existing process signal adapter, invokes O2, prints its projection, and maps the final public status to a process exit code.

O3 must not become an alternate scheduler implementation.

## Relationship to permanent runtime architecture

`docs/architecture/runtime/scheduler.md` owns the durable target separation of runtime scheduling responsibilities.

This contract owns the current local process/CLI behavior only. The historical O3 slice label is provenance and does not create a permanent architecture namespace.

## Source-retirement boundary

This transaction does not retire:

```text
docs/architecture/o3_always_on_local_scheduler.md
scripts/relaylm_o3_always_on_local_scheduler.py
scripts/relaylm_o3_always_on_local_scheduler_smoke.py
```

It also does not retire O1A-O2 sources or evidence. Source retirement requires a separate bounded transaction with exact provenance, consumer repair, and migration disposition.
