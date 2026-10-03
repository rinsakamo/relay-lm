"""Campaign admission and evidence boundaries; no GPU or HTTP."""

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from tools import wsl_cuda_exploration_authority as authority
from tools import wsl_cuda_exploration_ledger as ledger
from tools import wsl_nvidia_runtime_closure_rehearsal as shared
import pytest
from tools import wsl_cuda_exploration as campaign

@pytest.mark.parametrize('method', ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'CONNECT', 'TRACE', 'CUSTOM'])
def test_all_request_methods_rejected(method):
    with pytest.raises(campaign.CampaignError, match='HTTP'):
        campaign.audit_log('llama_server: model loaded\nsrv log_server_r: request: ' + method + ' /health 127.0.0.1 200\n')

def test_exactly_one_model_marker():
    for count in (0, 2):
        with pytest.raises(campaign.CampaignError, match='model load'):
            campaign.audit_log('llama_server: model loaded\n' * count)
    assert campaign.audit_log('llama_server: model loaded\n')['http_requests'] == 0



def test_missing_grant_never_initializes_or_reserves(tmp_path):
    with pytest.raises(authority.ExplorationGrantError):
        campaign.launch(tmp_path / 'freeze.json', ledger.BUDGET_COMMENT_ID, 'a' * 64)
    assert list(tmp_path.iterdir()) == []


def test_changed_grant_hash_never_reserves(tmp_path, monkeypatch):
    monkeypatch.setattr(authority, 'verify_owner_execution_grant', lambda _: ({}, 'a' * 64))
    with pytest.raises(campaign.CampaignError, match='grant SHA256'):
        campaign.launch(tmp_path / 'freeze.json', 6000000000, 'b' * 64)
    assert list(tmp_path.iterdir()) == []


def test_frozen_bytes_changed(tmp_path, monkeypatch):
    freeze = tmp_path / 'freeze.json'
    freeze.write_text('{}')
    monkeypatch.setattr(authority, 'verify_owner_execution_grant', lambda _: (
        {'frozen_campaign_sha256': 'a' * 64, 'evidence_root': str(tmp_path)}, 'b' * 64))
    with pytest.raises(campaign.CampaignError, match='freeze SHA256'):
        campaign.load_authorized(freeze, 6000000000, 'b' * 64)


def test_ancestor_symlink_rejected(tmp_path):
    actual = tmp_path / 'actual'
    actual.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(campaign.CampaignError, match='symlink'):
        campaign.safe_path(alias / 'child' / 'ledger.json')


def _manifest():
    record = {'path': '/server', 'identity': {'device': 1, 'inode': 2}, 'sha256': 'a' * 64}
    return {'server': record, 'model': dict(record, path='/model'),
            'build': {'shared_libraries': {}, 'wsl_cuda_driver_closure': {
                'shim': {'aliases': []}, 'accepted_mapped_objects': [], 'driver_package': {'root': '/usr/lib/wsl/drivers/pkg', 'runtime_objects': []}}}}


@pytest.mark.parametrize('raw', [
    '1000-2000 r-xp 00000000 00:01 2 /unknown.so\n',
    'malformed map line\n',
    '1000-2000 r-xp 00000000 00:02 2 /server\n',
])
def test_both_maps_preserved_before_unknown_malformed_identity_failure(tmp_path, monkeypatch, raw):
    def capture(process, root, name):
        result = dict(content=raw, complete_snapshot=True, line_count=1,
                      sha256=shared._sha256_bytes(raw.encode()), process_start_ticks=1)
        campaign.write(root / (name + '.json'), result)
        return result
    monkeypatch.setattr(campaign, 'capture_maps', capture)
    snapshots, diagnoses = campaign.collect_postload(None, tmp_path, _manifest())
    assert (tmp_path / 'maps-first.json').exists()
    assert (tmp_path / 'maps-second.json').exists()
    with pytest.raises(campaign.CampaignError, match='unknown/malformed/mismatched'):
        campaign.strict_maps(None, _manifest(), snapshots, diagnoses)
    assert len(list(tmp_path.glob('diagnostic-*.json'))) == 2


def test_maps_identity_drift_rejected():
    with pytest.raises(campaign.CampaignError, match='maps identity drift'):
        campaign.strict_maps(None, {}, [dict(process_start_ticks=1, content='a'), dict(process_start_ticks=2, content='a')], [])


def test_real_proc_snapshot(tmp_path):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
    try:
        result = campaign.capture_maps(child, tmp_path, 'initial')
        assert result['pid'] == child.pid
        assert result['line_count'] > 0
        assert result['sha256'] == shared._sha256_bytes(result['content'].encode())
    finally:
        child.terminate()
        child.wait(timeout=5)


@pytest.mark.parametrize(('gpu', 'port', 'group'), [(False, True, True), (True, False, True), (True, True, False)])
def test_unreleased_resources_never_verify_cleanup(monkeypatch, gpu, port, group):
    monkeypatch.setattr(campaign, 'gpu_clear', lambda: gpu)
    monkeypatch.setattr(campaign, 'port_clear', lambda: port)
    monkeypatch.setattr(shared, '_owned_session_group_quiescent', lambda _: group)
    monkeypatch.setattr(os, 'killpg', lambda *args: None)
    child = SimpleNamespace(pid=999999, poll=lambda: 0, wait=lambda **kw: 0)
    assert campaign.cleanup(child, 1)['verified'] is False


def test_interrupted_cleanup_unknown(monkeypatch):
    monkeypatch.setattr(campaign, 'gpu_clear', lambda: True)
    monkeypatch.setattr(campaign, 'port_clear', lambda: True)
    monkeypatch.setattr(shared, '_owned_session_group_quiescent', lambda _: False)
    def denied(*args):
        raise PermissionError('cannot terminate')
    monkeypatch.setattr(os, 'killpg', denied)
    child = SimpleNamespace(pid=999999, poll=lambda: None)
    assert campaign.cleanup(child, 1)['verified'] is False


def test_real_owned_process_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, 'gpu_clear', lambda: True)
    monkeypatch.setattr(campaign, 'port_clear', lambda: True)
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'], start_new_session=True)
    result = campaign.cleanup(child, 3)
    assert result['process_terminated'] and result['group_absent'] and result['verified']


def test_occupied_port_passive_inspection():
    import socket
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        assert campaign.port_clear(listener.getsockname()[1]) is False


def test_missing_and_tampered_evidence(tmp_path):
    campaign.write(tmp_path / 'summary.json', {'status': 'BLOCKED'})
    shared._seal_directory(tmp_path)
    shared.verify_evidence_manifest(tmp_path)
    (tmp_path / 'summary.json').write_text('tampered')
    with pytest.raises(shared.RehearsalError, match='read-back'):
        shared.verify_evidence_manifest(tmp_path)
    (tmp_path / 'summary.json').unlink()
    with pytest.raises(shared.RehearsalError, match='read-back'):
        shared.verify_evidence_manifest(tmp_path)


def _launch_fixture(tmp_path, monkeypatch):
    grant = {'evidence_root': str(tmp_path), 'python_executable': sys.executable,
             'startup_timeout_seconds': 1, 'cleanup_timeout_seconds': 1}
    freeze = {'repository': {'root': str(tmp_path)}}
    monkeypatch.setattr(campaign, 'load_authorized', lambda *a: (freeze, grant))
    monkeypatch.setattr(campaign, 'source_identity', lambda p: {'root': str(p), 'head': 'a' * 40, 'tree': 'b' * 40})
    monkeypatch.setattr(campaign, 'verify_frozen', lambda *a: None)
    return grant, freeze


def test_prelaunch_failure_is_spent_and_restart_blocked(tmp_path, monkeypatch):
    _launch_fixture(tmp_path, monkeypatch)
    calls = []
    def fail(command, **kwargs):
        state = ledger.inspect_ledger(tmp_path / 'ledger.json')
        assert state['trials'][0]['status'] == 'RESERVED'
        calls.append(command)
        raise OSError('cannot spawn runner')
    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(OSError, match='cannot spawn'):
        campaign.launch(tmp_path / 'freeze.json', 6000000000, 'a' * 64)
    assert len(calls) == 1 and 'tools.relay_physical_run' in calls[0]
    with pytest.raises(campaign.CampaignError, match='previous trial'):
        campaign.launch(tmp_path / 'freeze.json', 6000000000, 'a' * 64)
    assert len(calls) == 1
    assert len(ledger.inspect_ledger(tmp_path / 'ledger.json')['trials']) == 1


def test_source_drift_before_reservation(tmp_path, monkeypatch):
    _launch_fixture(tmp_path, monkeypatch)
    def drift(*args):
        raise campaign.CampaignError('source drift')
    monkeypatch.setattr(campaign, 'verify_frozen', drift)
    with pytest.raises(campaign.CampaignError, match='source drift'):
        campaign.launch(tmp_path / 'freeze.json', 6000000000, 'a' * 64)
    assert not (tmp_path / 'ledger.json').exists()


def _receipt(tmp_path):
    descriptor_path = tmp_path / 'exp-01-descriptor.json'
    descriptor = {'python_executable': sys.executable, 'repository': {'root': str(tmp_path)}}
    trial = {'receipt_path': str(tmp_path / 'receipt.json')}
    receipt = dict(schema_version=2, receipt_path=trial['receipt_path'], target_label=authority.TARGET,
                   resource_key=authority.RESOURCE, cwd=str(tmp_path),
                   command_executable=Path(sys.executable).name,
                   command_argv_sha256=campaign.runner._argv_sha256([sys.executable, '-m', campaign.MODULE, *campaign.child_args(descriptor_path)]),
                   request_id='a' * 32, state='RUNNING', lease_state='ACQUIRED')
    return descriptor_path, descriptor, trial, receipt


@pytest.mark.parametrize('field', ['cwd', 'target_label', 'resource_key', 'receipt_path', 'command_argv_sha256', 'request_id', 'schema_version'])
def test_queue_receipt_tampering(tmp_path, field):
    path, descriptor, trial, receipt = _receipt(tmp_path)
    receipt[field] = 'wrong'
    campaign.write(Path(trial['receipt_path']), receipt)
    with pytest.raises(campaign.CampaignError):
        campaign.verify_receipt(descriptor, path, trial, running=True)


def test_direct_target_with_forged_receipt_no_inherited_capability(tmp_path):
    path, descriptor, trial, receipt = _receipt(tmp_path)
    campaign.write(Path(trial['receipt_path']), receipt)
    with pytest.raises(campaign.CampaignError, match='queue controller'):
        campaign.verify_receipt(descriptor, path, trial, running=True)


def test_superseded_grant_rejected():
    # The existing grant suite covers wrong owner, revocation, model/GPU/budget.
    from tests.unit.test_wsl_cuda_exploration_authority import body, grant, reader
    issue_reader, comments_reader = reader(body(grant()), after=body(grant()))
    with pytest.raises(authority.ExplorationGrantError, match='revoked'):
        authority.verify_owner_execution_grant(ledger.BUDGET_COMMENT_ID + 1,
                                               issue_reader=issue_reader, comments_reader=comments_reader)


def _frozen_fixture(tmp_path, monkeypatch):
    python = str(Path(sys.executable).absolute())
    identity = SimpleNamespace(python_executable=python, policy_sha256='a' * 64, distribution_fingerprint='b' * 64)
    host = dict(gpu_uuid='gpu', driver_version='driver', wsl_kernel='kernel', cuda_toolkit_version='12.8')
    manifest = {'server': {'path': '/server', 'sha256': 'c' * 64}, 'model': {'path': '/model', 'sha256': 'd' * 64}}
    python_identity = dict(python_executable=python, python_policy_sha256='a' * 64, python_fingerprint='b' * 64)
    timeouts = dict(startup_timeout_seconds=1, cleanup_timeout_seconds=1)
    freeze = dict(campaign_id=ledger.CAMPAIGN_ID, repository={'head': 'e' * 40, 'root': str(tmp_path)},
                  python=python_identity, host=host, manifest=manifest, environment={}, timeouts=timeouts)
    grant = dict(approved_base_head='e' * 40, **python_identity, **host, **timeouts,
                 server_binary='/server', server_sha256='c' * 64, model_path='/model', model_sha256='d' * 64)
    monkeypatch.setattr(campaign, 'verify_source', lambda *args: None)
    monkeypatch.setattr(campaign.physical_env, 'verify_environment', lambda **kw: identity)
    monkeypatch.setattr(campaign, 'host_identity', lambda: host)
    monkeypatch.setattr(shared, 'collect_candidate_manifest', lambda **kw: manifest)
    monkeypatch.setattr(shared, '_validate_frozen_server_environment', lambda *a: None)
    monkeypatch.setattr(campaign, 'gpu_clear', lambda: True)
    monkeypatch.setattr(campaign, 'port_clear', lambda: True)
    return freeze, grant


@pytest.mark.parametrize('field', ['gpu_uuid', 'driver_version', 'wsl_kernel', 'cuda_toolkit_version',
                                   'python_fingerprint', 'python_policy_sha256', 'python_executable',
                                   'model_path', 'model_sha256', 'server_binary', 'server_sha256',
                                   'startup_timeout_seconds', 'cleanup_timeout_seconds'])
def test_runtime_mismatch_rejected(tmp_path, monkeypatch, field):
    freeze, grant = _frozen_fixture(tmp_path, monkeypatch)
    grant[field] = 'wrong'
    with pytest.raises(campaign.CampaignError):
        campaign.verify_frozen(freeze, grant, tmp_path, freeze['repository'])


def test_changed_static_library_manifest_rejected(tmp_path, monkeypatch):
    freeze, grant = _frozen_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(shared, 'collect_candidate_manifest', lambda **kw: {'changed': True})
    with pytest.raises(campaign.CampaignError, match='static runtime closure'):
        campaign.verify_frozen(freeze, grant, tmp_path, freeze['repository'])


def test_unapproved_source_path_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(shared, '_verify_repository', lambda *a: None)
    monkeypatch.setattr(campaign.runner, '_require_base_is_ancestor', lambda *a: None)
    monkeypatch.setattr(shared, '_git', lambda root, *args: 'https://github.com/rinsakamo/relay-lm.git'
                        if args[0] == 'remote' else 'src/relaylm/forbidden.py')
    with pytest.raises(campaign.CampaignError, match='outside the grant'):
        campaign.verify_source(tmp_path, {'head': 'a' * 40},
                               {'approved_base_head': 'b' * 40, 'allowed_change_paths': ['tools/allowed.py']})


def test_no_missing_gpu_telemetry_inferred_as_release(monkeypatch):
    for result in [SimpleNamespace(returncode=1, stdout='', stderr=''),
                   SimpleNamespace(returncode=0, stdout='N/A\n', stderr=''),
                   SimpleNamespace(returncode=0, stdout='123\n', stderr=''),
                   SimpleNamespace(returncode=0, stdout='', stderr='unsupported')]:
        monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: result)
        assert campaign.gpu_clear() is False


def test_target_prelaunch_failure_seals_evidence_without_spawn(tmp_path, monkeypatch):
    freeze, grant = _launch_fixture(tmp_path, monkeypatch)
    grant['evidence_root'] = str(tmp_path)
    descriptor_path = campaign.paths(tmp_path, 'exp-01')['descriptor']
    descriptor = dict(campaign_id=ledger.CAMPAIGN_ID, python_executable=sys.executable,
                      trial_id='exp-01', freeze=str(tmp_path / 'freeze.json'),
                      comment_id=6000000000, grant_sha256='a' * 64,
                      repository={'root': str(tmp_path)})
    campaign.write(descriptor_path, descriptor)
    ledger.initialize_ledger(tmp_path / 'ledger.json', execution_comment_id=6000000000, execution_grant_sha256='a' * 64)
    ledger.reserve_trial(tmp_path / 'ledger.json', execution_comment_id=6000000000,
                         execution_grant_sha256='a' * 64, trial_descriptor_sha256=shared._sha256_file(descriptor_path),
                         frozen_checkout=str(tmp_path), receipt_path=tmp_path / 'exp-01-receipt.json',
                         output_root=tmp_path / 'exp-01-output')
    monkeypatch.setattr(campaign, 'verify_receipt', lambda *a, **kw: {})
    def drift(*args):
        raise campaign.CampaignError('prelaunch source drift')
    monkeypatch.setattr(campaign, 'verify_frozen', drift)
    monkeypatch.setattr(campaign, 'gpu_clear', lambda: True)
    monkeypatch.setattr(campaign, 'port_clear', lambda: True)
    def no_spawn(*args, **kwargs):
        pytest.fail('prelaunch failure must never spawn')
    monkeypatch.setattr(subprocess, 'Popen', no_spawn)
    assert campaign.target(descriptor_path) == 2
    output = tmp_path / 'exp-01-output'
    shared.verify_evidence_manifest(output)
    summary = campaign.read(output / 'summary.json')
    assert summary['server_launches'] == 0 and summary['status'] == 'BLOCKED'
    assert summary['cleanup']['verified'] is True
    with pytest.raises(FileExistsError):
        campaign.target(descriptor_path)
