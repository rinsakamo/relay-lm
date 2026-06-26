from pathlib import Path

path = Path("relaylm/relaymem_slp_scheduler_queue_lane.py")
body = path.read_text(encoding="utf-8")
start_anchor = '    if result.status in {"claim_not_applied", "claim_lost_before_rehydrate"}:'
end_anchor = "\n\n\ndef _fault"
start = body.find(start_anchor)
end = body.find(end_anchor, start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit("O1C mapping repair range not found")
replacement = '''    if result.status in {"claim_not_applied", "claim_lost_before_rehydrate"}:
        return _lane(
            status="candidate_changed",
            no_immediate_work=False,
            retryable=True,
            reasons=reasons or ("queue_claim_conflict",),
            **common,
        )
    if result.status == "source_blocked":
        return _lane(
            status="unsafe_state",
            no_immediate_work=True,
            unsafe=True,
            reasons=reasons or ("queue_source_blocked",),
            **common,
        )
    if result.status == "source_retryable":
        return _lane(
            status="failed",
            no_immediate_work=True,
            retryable=True,
            reasons=reasons or ("queue_source_retryable",),
            **common,
        )
    if result.status == "worker_completed" and (
        result.retryable or result.worker_status == "retry_released"
    ):
        return _lane(
            status="retry_released",
            no_immediate_work=False,
            retryable=True,
            reasons=reasons or ("queue_retry_released",),
            **common,
        )
    if result.status == "worker_completed" and result.worker_invoked:
        return _lane(
            status="executed",
            no_immediate_work=False,
            reasons=reasons or ("queue_worker_executed",),
            **common,
        )
    return _lane(
        status="failed",
        no_immediate_work=True,
        retryable=bool(result.retryable),
        reasons=reasons or ("queue_delegate_failed",),
        **common,
    )'''
updated = body[:start] + replacement + body[end:]
if updated == body:
    raise SystemExit("O1C mapping repair made no change")
path.write_text(updated, encoding="utf-8")
print("O1C mapping repaired")
