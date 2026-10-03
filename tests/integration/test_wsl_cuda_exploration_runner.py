"""Actual public runner -> queue -> campaign module, without GPU or HTTP.

Only external git/Python policy/admission observations are replaced. The actual
registry, runner preparation, queue lock/receipt, subprocess and target execute.
The target must reject the budget comment before any physical side effect.
"""
import json
from pathlib import Path
import sys

from tools import physical_execution_queue as queue
from tools import relay_physical_run as runner
from tools.relay_physical_env import PhysicalEnvironmentIdentity
from tools import wsl_cuda_exploration as campaign


def test_public_runner_reaches_registered_target_and_rejects_non_grant(tmp_path, monkeypatch, capfd):
    repo = Path(__file__).resolve().parents[2]
    identity = PhysicalEnvironmentIdentity(
        home=tmp_path, manifest_path=tmp_path / 'python.json',
        python_executable=sys.executable, python_version=sys.version,
        implementation='cpython', policy_sha256='a' * 64, distribution_fingerprint='b' * 64)
    monkeypatch.setattr(runner, 'reexec_into_environment', lambda **kw: None)
    monkeypatch.setattr(runner, '_environment_identity', lambda root: identity)
    monkeypatch.setattr(runner, '_repo_identity', lambda root: ('a' * 40, 'b' * 40))
    monkeypatch.setattr(runner, '_current_branch', lambda root: 'v1')
    monkeypatch.setattr(runner, '_remote_head', lambda *a, **kw: 'a' * 40)
    monkeypatch.setattr(runner, '_require_base_is_ancestor', lambda *a: None)
    monkeypatch.setattr(runner, '_require_distributions', lambda *a: None)
    monkeypatch.setattr(queue, 'probe_external_busy', lambda **kw: ())
    # Separate test lease path; never contend with or inspect the physical GPU.
    original_config = runner.QueueConfig
    monkeypatch.setattr(runner, 'QueueConfig', lambda **kw: original_config(
        **kw, lock_root=tmp_path / 'locks', idle_confirmations=1))
    descriptor = tmp_path / 'descriptor.json'
    descriptor.write_text(json.dumps(dict(freeze=str(tmp_path / 'freeze.json'),
                                          comment_id=campaign.ledger.BUDGET_COMMENT_ID,
                                          grant_sha256='a' * 64)))
    receipt = tmp_path / 'receipt.json'
    result = runner.main(['--repo-root', str(repo), '--target', campaign.authority.TARGET,
                          '--receipt', str(receipt), '--', *campaign.child_args(descriptor)])
    assert result == 2
    saved = json.loads(receipt.read_text())
    assert saved['state'] == 'CHILD_EXITED' and saved['lease_state'] == 'RELEASED'
    assert saved['child_exit_code'] == 2
    assert saved['command_argv_sha256'] == runner._argv_sha256(
        [sys.executable, '-m', campaign.MODULE, *campaign.child_args(descriptor)])
    assert 'distinct later exact owner execution comment' in capfd.readouterr().err
    assert not (tmp_path / 'ledger.json').exists()
