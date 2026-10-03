"""Frozen #3018 campaign: proposal, durable reservation, canonical target.

No HTTP client is used. Strict closure is deliberately not relaxed here.
"""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
from typing import Any

from tools import physical_execution_queue as queue
from tools import relay_physical_env as physical_env
from tools import relay_physical_run as runner
from tools import wsl_cuda_exploration_authority as authority
from tools import wsl_cuda_exploration_ledger as ledger
from tools import wsl_nvidia_runtime_closure_rehearsal as shared
from tools import wsl_runtime_maps_diagnostic as diagnostic

MODULE = 'tools.wsl_cuda_exploration'


class CampaignError(RuntimeError):
    """Fail closed without refund or replay."""


def safe_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute() or str(path) != str(value) or '..' in path.parts:
        raise CampaignError('noncanonical campaign path')
    for item in (path, *path.parents):
        if item.is_symlink():
            raise CampaignError('symlink in campaign path')
    return path


def read(path: Path) -> dict[str, Any]:
    safe_path(path)
    return shared._read_json_object(path)


def write(path: Path, value: dict[str, Any], *, exclusive: bool = True) -> None:
    safe_path(path)
    shared._write_json(path, value, exclusive=exclusive)


def host_identity() -> dict[str, str]:
    gpu = subprocess.run(
        ['nvidia-smi', '--query-gpu=uuid,driver_version', '--format=csv,noheader'],
        capture_output=True, text=True, check=True, timeout=15,
    ).stdout.strip().splitlines()
    if len(gpu) != 1 or len(gpu[0].split(',')) != 2:
        raise CampaignError('exact single GPU identity unavailable')
    uuid, driver = [x.strip() for x in gpu[0].split(',')]
    toolkit = read(Path('/usr/local/cuda-12.8/version.json'))['cuda']['version']
    if not toolkit.startswith('12.8.'):
        raise CampaignError('CUDA toolkit drift')
    return dict(gpu_uuid=uuid, driver_version=driver, wsl_kernel=platform.release(),
                cuda_toolkit_version='12.8', cuda_toolkit_full_version=toolkit)


def port_clear(port: int = 1234) -> bool:
    # Passive observation only, including IPv6; no readiness connection.
    try:
        for table in ('tcp', 'tcp6'):
            for line in Path('/proc/net/' + table).read_text().splitlines()[1:]:
                fields = line.split()
                if int(fields[1].split(':')[1], 16) == port and fields[3] == '0A':
                    return False
        return True
    except (OSError, ValueError, IndexError):
        return False


def gpu_clear() -> bool:
    # Empty, successful NVML enumeration is necessary; unsupported is unknown.
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=15, check=False,
        )
        return result.returncode == 0 and not result.stdout.strip() and not result.stderr.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False


def audit_log(log: str) -> dict[str, int]:
    # llama.cpp logs all requests through log_server_r, including custom verbs.
    if re.search(r'log_server_r|\brequest:\s*\S+|\b(?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS|CONNECT|TRACE)\s+/', log):
        raise CampaignError('unexpected HTTP request in final server log')
    count = log.count(shared.MODEL_LOADED_MARKER)
    if count != 1:
        raise CampaignError('expected exactly one model load marker')
    return dict(model_load_markers=count, http_requests=0, generation=0, input_count=0, public_completion=0)


def paths(root: Path, trial_id: str) -> dict[str, Path]:
    if not re.fullmatch(r'exp-0[1-8]', trial_id):
        raise CampaignError('invalid trial identity')
    return {key: root / (trial_id + suffix) for key, suffix in {
        'descriptor': '-descriptor.json', 'receipt': '-receipt.json',
        'output': '-output', 'claim': '-started.json',
    }.items()}


def source_identity(repo: Path) -> dict[str, str]:
    return dict(root=str(repo), head=shared._git(repo, 'rev-parse', 'HEAD'),
                tree=shared._git(repo, 'rev-parse', 'HEAD^{tree}'))


def verify_source(repo: Path, expected: dict, grant: dict) -> None:
    shared._verify_repository(repo, expected)
    if shared._git(repo, 'remote', 'get-url', 'origin') != 'https://github.com/rinsakamo/relay-lm.git':
        raise CampaignError('canonical origin changed')
    runner._require_base_is_ancestor(repo, grant['approved_base_head'])
    changed = shared._git(repo, 'diff', '--name-only', grant['approved_base_head'], expected['head']).splitlines()
    if set(changed) - set(grant['allowed_change_paths']):
        raise CampaignError('source lineage changed outside the grant')


def verify_frozen(freeze: dict, grant: dict, repo: Path, source: dict) -> None:
    if freeze['campaign_id'] != ledger.CAMPAIGN_ID or freeze['repository']['head'] != grant['approved_base_head']:
        raise CampaignError('wrong campaign/base freeze')
    if freeze['repository']['root'] != str(repo):
        raise CampaignError('frozen checkout path changed')
    verify_source(repo, source, grant)
    identity = physical_env.verify_environment(repo_root=repo)
    expected_python = dict(python_executable=identity.python_executable,
                           python_policy_sha256=identity.policy_sha256,
                           python_fingerprint=identity.distribution_fingerprint)
    if any(grant[k] != v for k, v in expected_python.items()) or freeze['python'] != expected_python:
        raise CampaignError('persistent Python identity changed')
    if str(Path(sys.executable).absolute()) != identity.python_executable:
        raise CampaignError('campaign must use the persistent physical Python')
    host = host_identity()
    if host != freeze['host'] or any(host[k] != grant[k] for k in host if k in grant):
        raise CampaignError('hardware/runtime identity changed')
    manifest = freeze['manifest']
    for name, path_key, hash_key in [('server', 'server_binary', 'server_sha256'), ('model', 'model_path', 'model_sha256')]:
        record = manifest[name]
        if record['path'] != grant[path_key] or record['sha256'] != grant[hash_key]:
            raise CampaignError('model/binary grant mismatch')
    live = shared.collect_candidate_manifest(candidate_binary=Path(grant['server_binary']), model_path=Path(grant['model_path']))
    if live != manifest:
        raise CampaignError('frozen static runtime closure changed')
    shared._validate_frozen_server_environment(freeze['environment'], manifest)
    if freeze['timeouts'] != {k: grant[k] for k in ('startup_timeout_seconds', 'cleanup_timeout_seconds')}:
        raise CampaignError('trial timeouts changed')
    if not port_clear() or not gpu_clear():
        raise CampaignError('baseline port/GPU quiescence unavailable')


def load_authorized(freeze_path: Path, comment_id: int, grant_hash: str) -> tuple[dict, dict]:
    grant, digest = authority.verify_owner_execution_grant(comment_id)
    if digest != grant_hash:
        raise CampaignError('owner grant SHA256 changed')
    if shared._sha256_file(safe_path(freeze_path)) != grant['frozen_campaign_sha256']:
        raise CampaignError('campaign freeze SHA256 changed')
    if freeze_path != safe_path(grant['evidence_root']) / 'freeze.json':
        raise CampaignError('wrong canonical freeze path')
    return read(freeze_path), grant


def child_args(descriptor: Path) -> list[str]:
    return ['--target', '--descriptor', str(descriptor)]


def verify_receipt(descriptor: dict, descriptor_path: Path, trial: dict, *, running: bool) -> dict:
    receipt = read(Path(trial['receipt_path']))
    command = [descriptor['python_executable'], '-m', MODULE, *child_args(descriptor_path)]
    expected = dict(schema_version=2, receipt_path=trial['receipt_path'],
                    target_label=authority.TARGET, resource_key=authority.RESOURCE,
                    cwd=descriptor['repository']['root'], command_argv_sha256=runner._argv_sha256(command),
                    command_executable=Path(command[0]).name)
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise CampaignError('queue receipt does not bind reservation/descriptor/argv')
    if not re.fullmatch('[0-9a-f]{32}', str(receipt.get('request_id', ''))):
        raise CampaignError('queue request identity invalid')
    if running:
        if receipt.get('state') != 'RUNNING' or receipt.get('lease_state') != 'ACQUIRED':
            raise CampaignError('queue lease not running')
        # A saved/forged JSON receipt alone cannot enter the physical target.
        pid, fd = receipt.get('controller_pid'), receipt.get('queue_lock_fd')
        if type(pid) is not int or pid != os.getppid() or type(fd) is not int or fd < 3:
            raise CampaignError('target was not invoked by its queue controller')
        lock = queue.DEFAULT_LOCK_ROOT / queue._safe_resource_id(authority.RESOURCE)
        if receipt.get('lock_path') != str(lock):
            raise CampaignError('noncanonical resource lease path')
        actual = os.fstat(fd)
        if (actual.st_dev, actual.st_ino) != (lock.stat().st_dev, lock.stat().st_ino):
            raise CampaignError('inherited queue lock identity changed')
        parent_argv = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
        if parent_argv[1:3] != [b'-m', b'tools.relay_physical_run']:
            raise CampaignError('canonical public runner parent required')
        with lock.open('rb') as independent:
            try:
                fcntl.flock(independent, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                fcntl.flock(independent, fcntl.LOCK_UN)
                raise CampaignError('queue lock is not held')
    elif receipt.get('state') != 'CHILD_EXITED' or receipt.get('lease_state') != 'RELEASED':
        raise CampaignError('queue terminal/release unconfirmed')
    return receipt


def verify_reservation(descriptor: dict, descriptor_path: Path, grant: dict) -> dict:
    root = safe_path(grant['evidence_root'])
    expected = paths(root, descriptor['trial_id'])
    if descriptor_path != expected['descriptor']:
        raise CampaignError('wrong trial descriptor path')
    state = ledger.inspect_ledger(root / 'ledger.json')
    if state['execution_comment_id'] != descriptor['comment_id'] or state['execution_grant_sha256'] != descriptor['grant_sha256']:
        raise CampaignError('ledger owner grant mismatch')
    if not state['trials']:
        raise CampaignError('no reserved trial')
    trial = state['trials'][-1]
    required = dict(status='RESERVED', trial_id=descriptor['trial_id'],
                    trial_descriptor_sha256=shared._sha256_file(descriptor_path),
                    frozen_checkout=descriptor['repository']['root'],
                    receipt_path=str(expected['receipt']), output_root=str(expected['output']))
    if any(trial.get(k) != v for k, v in required.items()):
        raise CampaignError('reservation does not bind this trial')
    return trial


def capture_maps(process: subprocess.Popen, root: Path, name: str) -> dict:
    before = shared.qualification._process_start_ticks(process.pid)
    raw = Path(f'/proc/{process.pid}/maps').read_text()
    after = shared.qualification._process_start_ticks(process.pid)
    if before != after or process.poll() is not None or not raw:
        raise CampaignError('maps process identity changed')
    snapshot = dict(content=raw, complete_snapshot=True, line_count=len(raw.splitlines()),
                    sha256=shared._sha256_bytes(raw.encode()), pid=process.pid,
                    process_start_ticks=before, captured_monotonic_ns=time.monotonic_ns())
    write(root / (name + '.json'), snapshot)
    return snapshot


def collect_postload(process: subprocess.Popen, root: Path, manifest: dict) -> tuple[list[dict], list[dict]]:
    # Save both complete snapshots before diagnostics or strict acceptance.
    first = capture_maps(process, root, 'maps-first')
    time.sleep(0.25)
    second = capture_maps(process, root, 'maps-second')
    results = []
    for name, snapshot in [('first', first), ('second', second)]:
        result = diagnostic.diagnose(snapshot, manifest)
        write(root / ('diagnostic-' + name + '.json'), result)
        results.append(result)
    return [first, second], results


def strict_maps(process: subprocess.Popen, manifest: dict, snapshots: list[dict], diagnoses: list[dict]) -> list[dict]:
    if snapshots[0]['process_start_ticks'] != snapshots[1]['process_start_ticks'] or snapshots[0]['content'] != snapshots[1]['content']:
        raise CampaignError('complete maps identity drift')
    if any(row['diagnostic'] not in ('ANONYMOUS_OR_PSEUDO', 'SEALED_MODEL_MAP_IDENTITY_MATCH', 'SEALED_MAP_IDENTITY_MATCH')
           for result in diagnoses for row in result['rows']):
        raise CampaignError('unknown/malformed/mismatched maps; diagnostics preserved')
    attestations = []
    for snapshot in snapshots:
        attestations.append(shared.qualification._verify_loaded_library_closure(
            process=process, binary=Path(manifest['server']['path']), manifest=manifest,
            require_cuda=True, previous_attestation=attestations[-1] if attestations else None,
            map_text=snapshot['content']))
    return attestations


def cleanup(process: subprocess.Popen | None, timeout: int) -> dict:
    result: dict[str, Any] = dict(process_terminated=process is None, group_absent=process is None)
    try:
        if process is not None:
            if not shared._owned_session_group_quiescent(process.pid):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=timeout / 2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=timeout / 2)
            result.update(process_terminated=process.poll() is not None,
                          group_absent=shared._owned_session_group_quiescent(process.pid))
    except (OSError, subprocess.TimeoutExpired) as exc:
        result['error'] = str(exc)
    result.update(gpu_released=gpu_clear(), port_released=port_clear())
    result['verified'] = all(result.get(k) is True for k in ('process_terminated', 'group_absent', 'gpu_released', 'port_released'))
    return result


def target(descriptor_path: Path) -> int:
    descriptor = read(descriptor_path)
    freeze, grant = load_authorized(Path(descriptor['freeze']), descriptor['comment_id'], descriptor['grant_sha256'])
    if descriptor['python_executable'] != grant['python_executable'] or descriptor['campaign_id'] != ledger.CAMPAIGN_ID:
        raise CampaignError('descriptor Python/campaign mismatch')
    trial = verify_reservation(descriptor, descriptor_path, grant)
    verify_receipt(descriptor, descriptor_path, trial, running=True)
    root = Path(trial['output_root'])
    # Durable once-only entry: controller restart/receipt replay cannot relaunch.
    write(paths(Path(grant['evidence_root']), trial['trial_id'])['claim'], dict(reservation_id=trial['reservation_id']))
    root.mkdir(mode=0o700, exist_ok=False)
    write(root / 'descriptor.json', descriptor)
    write(root / 'freeze.json', freeze)
    summary: dict[str, Any] = dict(status='BLOCKED', server_launches=0, model_load_attempts=0,
                                   zero_requests_verified=False, strict_closure_verified=False,
                                   scientific_attempt_consumed=False, reservation_id=trial['reservation_id'])
    process = None
    log_handle = None
    def interrupted(signum: int, frame: Any) -> None:
        raise CampaignError(f'interrupted by signal {signum}')
    old_handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        repo = Path(descriptor['repository']['root'])
        verify_frozen(freeze, grant, repo, descriptor['repository'])
        argv = freeze['argv'][trial['trial_id']]
        if argv != shared._expected_argv(freeze['manifest'], root):
            raise CampaignError('frozen argv changed')
        load_authorized(Path(descriptor['freeze']), descriptor['comment_id'], descriptor['grant_sha256'])
        log_handle = (root / 'console.log').open('xb')
        summary.update(server_launches=1, model_load_attempts=1)
        write(root / 'launch-intent.json', summary)
        process = subprocess.Popen(argv, cwd=str(Path(grant['server_binary']).parent), env=freeze['environment'],
                                   stdin=subprocess.DEVNULL, stdout=log_handle, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        write(root / 'owned-process.json', dict(pid=process.pid, pgid=process.pid,
                                               start_ticks=shared.qualification._process_start_ticks(process.pid)))
        try:
            capture_maps(process, root, 'maps-initial-observed')
            summary['initialization_observation'] = 'immediate-after-spawn; exact CUDA phase unknown'
        except Exception as exc:
            summary['initialization_observation'] = 'unavailable: ' + str(exc)
        shared._wait_for_model_loaded(root / 'llama-server.log', process, grant['startup_timeout_seconds'])
        snapshots, diagnoses = collect_postload(process, root, freeze['manifest'])
        # Fresh authority/host/process checks after preserving both maps.
        load_authorized(Path(descriptor['freeze']), descriptor['comment_id'], descriptor['grant_sha256'])
        verify_source(repo, descriptor['repository'], grant)
        if host_identity() != freeze['host']:
            raise CampaignError('hardware/runtime changed during trial')
        summary['process'] = shared._verify_server_process_identity(
            process, binary=Path(grant['server_binary']), binary_sha256=grant['server_sha256'],
            expected_argv=argv, expected_environment=freeze['environment'])
        summary['attestations'] = strict_maps(process, freeze['manifest'], snapshots, diagnoses)
        summary['strict_closure_verified'] = True
    except Exception as exc:
        summary['failure'] = f'{type(exc).__name__}: {exc}'
    finally:
        # A repeated interruption must not skip cleanup/evidence sealing.
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        summary['cleanup'] = cleanup(process, grant['cleanup_timeout_seconds'])
        if log_handle is not None:
            log_handle.flush()
            os.fsync(log_handle.fileno())
            log_handle.close()
        try:
            summary['counters'] = audit_log((root / 'llama-server.log').read_text())
            summary['zero_requests_verified'] = True
        except Exception as exc:
            summary['log_audit_error'] = str(exc)
        if summary['strict_closure_verified'] and summary['zero_requests_verified'] and summary['cleanup']['verified']:
            summary['status'] = 'PASSED'
        write(root / 'summary.json', summary)
        shared._seal_directory(root)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
    return 0 if summary['status'] == 'PASSED' else 2


def verify_history(state: dict) -> None:
    """Never trust terminal flags without re-reading their bound evidence."""
    for trial in state['trials']:
        if trial['status'] != 'BLOCKED' or trial.get('cleanup_verified') is not True:
            raise CampaignError('previous trial is incomplete, passed, or cleanup unknown')
        output = safe_path(trial['output_root'])
        receipt = safe_path(trial['receipt_path'])
        shared.verify_evidence_manifest(output)
        if (shared._sha256_file(output / 'evidence-manifest.json') != trial['evidence_manifest_sha256']
                or shared._sha256_file(receipt) != trial['queue_receipt_sha256']):
            raise CampaignError('previous evidence/receipt was tampered')
        summary = read(output / 'summary.json')
        if summary.get('zero_requests_verified') is not True or summary.get('cleanup', {}).get('verified') is not True:
            raise CampaignError('previous telemetry/cleanup prohibits continuation')


def launch(freeze_path: Path, comment_id: int, grant_hash: str) -> int:
    freeze, grant = load_authorized(freeze_path, comment_id, grant_hash)
    repo = Path(freeze['repository']['root'])
    source = source_identity(repo)
    verify_frozen(freeze, grant, repo, source)
    root = safe_path(grant['evidence_root'])
    ledger_path = root / 'ledger.json'
    if not ledger_path.exists():
        ledger.initialize_ledger(ledger_path, execution_comment_id=comment_id, execution_grant_sha256=grant_hash)
    state = ledger.inspect_ledger(ledger_path)
    verify_history(state)
    trial_id = f"exp-{len(state['trials']) + 1:02d}"
    trial_paths = paths(root, trial_id)
    descriptor = dict(campaign_id=ledger.CAMPAIGN_ID, trial_id=trial_id, freeze=str(freeze_path),
                      comment_id=comment_id, grant_sha256=grant_hash, repository=source,
                      python_executable=grant['python_executable'])
    write(trial_paths['descriptor'], descriptor)
    # Recheck immediately before committing the nonrefundable slot.
    load_authorized(freeze_path, comment_id, grant_hash)
    trial = ledger.reserve_trial(ledger_path, execution_comment_id=comment_id,
                                 execution_grant_sha256=grant_hash,
                                 trial_descriptor_sha256=shared._sha256_file(trial_paths['descriptor']),
                                 frozen_checkout=str(repo), receipt_path=trial_paths['receipt'],
                                 output_root=trial_paths['output'])
    command = [grant['python_executable'], '-m', 'tools.relay_physical_run', '--repo-root', str(repo),
               '--target', authority.TARGET, '--receipt', str(trial_paths['receipt']), '--',
               *child_args(trial_paths['descriptor'])]
    env = dict(os.environ, PYTHONPATH=physical_env._exact_pythonpath(repo), PYTHONNOUSERSITE='1')
    # Exactly one call; exceptions/missing evidence leave RESERVED and block successors.
    try:
        completed = subprocess.run(command, cwd=repo, env=env, check=False,
                                   timeout=grant['startup_timeout_seconds'] + grant['cleanup_timeout_seconds'] + 180)
    except BaseException as exc:
        write(root / (trial_id + '-controller-error.json'),
              dict(reservation_id=trial['reservation_id'], error=str(exc), cleanup_verified=False))
        raise
    shared.verify_evidence_manifest(trial_paths['output'])
    receipt = verify_receipt(descriptor, trial_paths['descriptor'], trial, running=False)
    summary = read(trial_paths['output'] / 'summary.json')
    if summary['reservation_id'] != trial['reservation_id']:
        raise CampaignError('terminal reservation mismatch')
    if summary['status'] == 'PASSED' and (completed.returncode != 0 or receipt['child_exit_code'] != 0):
        raise CampaignError('PASS conflicts with runner terminal')
    ledger.finalize_trial(ledger_path, reservation_id=trial['reservation_id'], status=summary['status'],
                          queue_receipt_sha256=shared._sha256_file(trial_paths['receipt']),
                          evidence_manifest_sha256=shared._sha256_file(trial_paths['output'] / 'evidence-manifest.json'),
                          cleanup_verified=summary['cleanup']['verified'],
                          zero_requests_verified=summary['zero_requests_verified'],
                          strict_closure_verified=summary['strict_closure_verified'])
    if summary['status'] == 'PASSED':
        write(root / 'success-freeze.json', dict(trial=trial, descriptor=descriptor, freeze=freeze,
                                               summary=summary, ledger_sha256=shared._sha256_file(ledger_path)))
    return completed.returncode


def prepare(repo: Path, root: Path) -> dict:
    """Read-only host qualification, then exclusive proposal files; no runner."""
    safe_path(root)
    source = source_identity(repo)
    shared._verify_repository(repo, source)
    if shared._git(repo, 'remote', 'get-url', 'origin') != 'https://github.com/rinsakamo/relay-lm.git':
        raise CampaignError('canonical origin required')
    identity = physical_env.verify_environment(repo_root=repo)
    python_identity = dict(python_executable=identity.python_executable,
                           python_policy_sha256=identity.policy_sha256,
                           python_fingerprint=identity.distribution_fingerprint)
    host = host_identity()
    manifest = shared.collect_candidate_manifest(candidate_binary=shared.EXPECTED_SERVER_BINARY,
                                                  model_path=shared.candidate_runtime.MODEL_PATH)
    if not port_clear() or not gpu_clear():
        raise CampaignError('baseline port/GPU quiescence unavailable')
    freeze = dict(campaign_id=ledger.CAMPAIGN_ID, repository=source, python=python_identity, host=host,
                  manifest=manifest, environment=shared._server_environment(manifest),
                  timeouts=dict(startup_timeout_seconds=600, cleanup_timeout_seconds=60),
                  argv={f'exp-{n:02d}': shared._expected_argv(manifest, paths(root, f'exp-{n:02d}')['output']) for n in range(1, 9)})
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    write(root / 'freeze.json', freeze)
    grant = dict(schema_version=1, kind=authority.MARKER, campaign_id=ledger.CAMPAIGN_ID,
                 proposal_sha256=ledger.PROPOSAL_SHA256, budget_comment_id=ledger.BUDGET_COMMENT_ID,
                 maximum_exploration_trials=8, contract_version=1, approved_base_head=source['head'],
                 frozen_campaign_sha256=shared._sha256_file(root / 'freeze.json'),
                 target_id=authority.TARGET, resource_key=authority.RESOURCE, evidence_root=str(root),
                 **python_identity, **{k: v for k, v in host.items() if k != 'cuda_toolkit_full_version'},
                 server_binary=manifest['server']['path'], server_sha256=manifest['server']['sha256'],
                 model_path=manifest['model']['path'], model_sha256=manifest['model']['sha256'], port=1234,
                 **freeze['timeouts'], allowed_change_paths=[
                     'tools/wsl_cuda_exploration.py', 'tools/cache_correctness_repair_runtime.py',
                     'tools/v1_cache_correctness_repair_qualification.py',
                     'tests/unit/test_wsl_cuda_exploration.py',
                     'tests/unit/test_v1_cache_correctness_repair_qualification.py',
                     'docs/reference/wsl-cuda-exploratory-campaign.md',
                     'docs/reference/wsl-cuda-driver-library-attestation.md'],
                 maximum_server_launches_per_trial=1, maximum_model_loads_per_trial=1, allowed_http_methods=[],
                 maximum_generation_requests=0, maximum_input_count_requests=0, maximum_public_completions=0)
    authority.validate_grant(grant)
    write(root / 'grant-proposal.json', dict(status='PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY', grant=grant,
                                            canonical_grant_sha256=authority.grant_sha256(grant)))
    return grant


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--launch', action='store_true')
    mode.add_argument('--target', action='store_true')
    parser.add_argument('--repo-root', type=Path)
    parser.add_argument('--evidence-root', type=Path)
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--descriptor', type=Path)
    parser.add_argument('--comment-id', type=int)
    parser.add_argument('--grant-sha256')
    args = parser.parse_args(argv)
    try:
        if args.prepare:
            prepare(args.repo_root, args.evidence_root)
            return 0
        if args.target:
            return target(args.descriptor)
        return launch(args.freeze, args.comment_id, args.grant_sha256)
    except Exception as exc:
        print(f'WSL CUDA campaign BLOCKED: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
