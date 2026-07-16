"""Characterization: Primary MEM formation and speaker-provenance behavior.

Locks the currently implemented invariants:

- safe ordinary memory (``free_to_update`` / ``ordinary_memory``) forms
  autonomously through the canonical M3 chain without a per-item approval
  token;
- the E1-R3 formation summary preserves the speaker-provenance partition and
  never promotes assistant acknowledgement/speculation to a user fact;
- malformed schemas, unknown enums, missing lineage, and low-authority
  promotion policies fail closed at the M3b write preflight.

These tests describe today's behavior, not the target architecture.
"""
from __future__ import annotations

import json

import pytest

from _relaymem_characterization_support import (
    eligibility_of,
    form_primary_memory,
    prepare_store,
    read_control_text,
)
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_source_lineage,
    build_relaymem_primary_write_preflight_dry_run,
)
from relaylm.relaymem_provenance_formation_summary import (
    build_relaymem_primary_formation_summary,
)

NAMESPACE = "characterization-ns-a"


@pytest.fixture()
def store(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    prepare_store(root)
    return root


def _preflight(candidates):
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="manual_import",
        source_event_id="characterization-preflight",
        namespace=NAMESPACE,
    )
    return build_relaymem_primary_write_preflight_dry_run(
        candidates=candidates,
        source_lineage_artifact=lineage,
        enabled=True,
        dry_run_only=True,
    )


def _candidate(**updates):
    value = {
        "candidate_id": "characterization-candidate",
        "source_event_kind": "manual_import",
        "memory_layer": "primary",
        "memory_kind": "recent_project_event",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
    }
    value.update(updates)
    return value


class TestOrdinaryAutonomousFormation:
    def test_safe_ordinary_memory_forms_without_per_item_approval(self, store):
        # The canonical formation chain needs only enabled/apply gates; no
        # approval token, reviewer, or held-queue step exists on this path.
        memory_id = form_primary_memory(
            store,
            namespace=NAMESPACE,
            candidate_id="cand-ordinary",
            title="favorite tea",
            summary="The user prefers black tea.",
        )
        decision = eligibility_of(store, namespace=NAMESPACE, physical_id=memory_id)
        assert decision.eligible is True
        assert decision.reason_id == "eligible_current_active"
        # Durable effects: one page plus reconciled index/log control entries.
        page = store / "memory" / "mem" / "primary" / "projects" / f"{memory_id}.md"
        assert page.is_file()
        assert memory_id in read_control_text(store, "index.md")
        assert memory_id in read_control_text(store, "log.md")

    def test_formed_page_preserves_source_provenance_partition(self, store):
        memory_id = form_primary_memory(
            store,
            namespace=NAMESPACE,
            candidate_id="cand-provenance",
            title="favorite tea",
            summary="The user prefers black tea.",
        )
        page_text = (
            store / "memory" / "mem" / "primary" / "projects" / f"{memory_id}.md"
        ).read_text(encoding="utf-8")
        # The page keeps governance metadata (source kind, policy, scope,
        # lineage) alongside the summary rather than merging them.
        assert 'source_event_kind: "manual_import"' in page_text
        assert 'promotion_policy: "free_to_update"' in page_text
        assert 'safety_scope: "ordinary_memory"' in page_text
        assert 'summary_origin: "trusted_in_process_summary"' in page_text
        index_entries = [
            json.loads(line.split("relaymem-primary-index-entry-v0", 1)[1].rstrip("> -"))
            for line in read_control_text(store, "index.md").splitlines()
            if "relaymem-primary-index-entry-v0" in line
        ]
        assert [entry["namespace"] for entry in index_entries] == [NAMESPACE]


class TestFormationSummaryProvenance:
    def test_only_user_assertions_become_candidate_facts(self):
        result = build_relaymem_primary_formation_summary(
            character_id="char-a",
            namespace=NAMESPACE,
            source_event_kind="turn",
            governed_messages=[
                {"role": "user", "content": "My favorite tea is Assam."},
                {"role": "assistant", "content": "Got it, noted."},
                {"role": "assistant", "content": "Maybe you also like Darjeeling."},
            ],
        )
        assert result.status == "formed"
        payload = result.memory_candidate_payload
        assert payload["factual_source"] == "user_assertion_only"
        assert payload["assistant_text_included_as_user_fact"] is False
        assert payload["summary_text"] == "My favorite tea is Assam."
        summary = result.formation_summary
        assert summary["speaker_provenance_preserved"] is True
        assert summary["assistant_text_promoted_to_user_fact"] is False
        counts = summary["provenance_counts"]
        assert counts["user_assertion_evidence"] == 1
        assert counts["assistant_acknowledgement_evidence"] == 1
        assert counts["assistant_speculation_or_non_factual_evidence"] == 1
        # Assistant speculation stays outside the candidate payload entirely.
        assert "Darjeeling" not in payload["summary_text"]
        assert "noted" not in payload["summary_text"]

    def test_assistant_only_turn_cannot_form_a_user_fact(self):
        result = build_relaymem_primary_formation_summary(
            character_id="char-a",
            namespace=NAMESPACE,
            source_event_kind="turn",
            governed_messages=[
                {"role": "assistant", "content": "I will remember you like tea."},
            ],
        )
        assert result.status == "blocked_no_user_assertion"
        assert result.memory_candidate_payload is None
        assert "user_assertion_evidence_missing" in result.blocked_reasons

    def test_unknown_speaker_role_fails_closed(self):
        result = build_relaymem_primary_formation_summary(
            character_id="char-a",
            namespace=NAMESPACE,
            source_event_kind="turn",
            governed_messages=[
                {"role": "narrator", "content": "The user likes tea."},
            ],
        )
        assert result.memory_candidate_payload is None
        assert "ambiguous_provenance" in result.blocked_reasons

    def test_non_conversation_roles_are_excluded_not_promoted(self):
        result = build_relaymem_primary_formation_summary(
            character_id="char-a",
            namespace=NAMESPACE,
            source_event_kind="turn",
            governed_messages=[
                {"role": "system", "content": "The user likes tea."},
                {"role": "user", "content": "I do like tea."},
            ],
        )
        assert result.status == "formed"
        summary = result.formation_summary
        assert summary["provenance_counts"]["excluded_evidence"] == 1
        assert result.memory_candidate_payload["summary_text"] == "I do like tea."


class TestWritePreflightFailsClosed:
    def test_free_to_update_ordinary_scope_is_the_autonomous_path(self):
        result = _preflight([_candidate()])
        operation = result["operations"][0]
        assert operation["preflight_status"] == "eligible"
        assert operation["blocked_reasons"] == []
        assert operation["idempotency_key"]

    def test_review_required_policy_blocks_autonomous_apply(self):
        result = _preflight(
            [_candidate(promotion_policy="review_required", safety_scope="held_for_review")]
        )
        operation = result["operations"][0]
        assert operation["preflight_apply_eligible"] is False
        assert (
            "promotion_policy_blocks_autonomous_apply:review_required"
            in operation["blocked_reasons"]
        )
        # Held-for-review candidates still receive an idempotency key so a
        # later governed apply can be correlated, but never apply eligibility.
        assert operation["idempotency_key"]

    def test_unknown_promotion_policy_fails_closed(self):
        result = _preflight([_candidate(promotion_policy="yolo_mode")])
        operation = result["operations"][0]
        assert "unsupported_promotion_policy" in operation["blocked_reasons"]
        assert operation["preflight_apply_eligible"] is False
        assert operation["idempotency_key"] == ""

    def test_unknown_memory_kind_fails_closed(self):
        result = _preflight([_candidate(memory_kind="galactic_memory")])
        operation = result["operations"][0]
        assert "unsupported_memory_kind" in operation["blocked_reasons"]
        assert operation["preflight_apply_eligible"] is False

    def test_policy_scope_mismatch_fails_closed(self):
        result = _preflight(
            [_candidate(promotion_policy="review_required", safety_scope="ordinary_memory")]
        )
        operation = result["operations"][0]
        assert (
            "promotion_policy_safety_scope_mismatch" in operation["blocked_reasons"]
        )
        assert operation["preflight_apply_eligible"] is False

    def test_missing_lineage_fails_closed(self):
        result = build_relaymem_primary_write_preflight_dry_run(
            candidates=[_candidate()],
            source_lineage_artifact=None,
            enabled=True,
            dry_run_only=True,
        )
        operation = result["operations"][0]
        assert operation["preflight_apply_eligible"] is False
        assert operation["idempotency_key"] == ""
