from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    OVERLAY_TAG,
    apply_overlay_to_production_request_body,
    assert_production_schema_unchanged,
    build_overlay_extraction_request_body,
    expected_retained_source_event_id,
    load_retained_formation_binding,
)
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput, CognitionPassRequest, CognitionReasoningMode, CognitionStructuredOutputMode
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import EXTRACTION_WIRE_SCHEMA


REVISION = "sha256:" + "a" * 64
T2 = "The parcel is still closed, so what is inside remains unknown."
STABLE_SOURCE = f"stage-r:{REVISION}:primary:turn-2"


def _input(*, content: str = T2, event_id: str = "evt-run-local") -> CognitiveInput:
    return CognitiveInput(identity=Identity("Synthetic diagnostic identity."), state_classes={"user.fact": "ordinary current fact"}, state=(), context=(), input=Event.create(type="message", actor="user", payload={"content": content}, event_id=event_id, timestamp="2026-01-01T00:00:00+00:00"))


def _payload() -> dict[str, object]:
    return {"diagnostic": "epistemic-formation-t2", "mechanical_validation": "pass", "items": [{"subject_span": "what is inside", "unknown_evidence_span": "remains unknown", "source_event_id": STABLE_SOURCE}]}


def _binding(tmp_path: Path):
    path = tmp_path / "retained.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    return load_retained_formation_binding(path=path, scenario_set_revision=REVISION, authoritative_t2_content=T2)


class _Provider:
    model = "synthetic-model"

    def _resolve_llama_cpp_pass_request(self, *, pass_request, reasoning_request):
        assert reasoning_request is None
        assert pass_request is not None
        return OpenAICompatibleDecodingConfig(temperature=0, top_p=1), OpenAICompatibleReasoningRequest(mode="off")

    def _llama_cpp_reasoning_fields(self, request):
        assert request is not None and request.mode == "off"
        return {"reasoning_effort": "none"}


def _pass_request() -> CognitionPassRequest:
    return CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF, temperature=0, top_p=1, structured_output_mode=CognitionStructuredOutputMode.NATIVE)


def test_expected_retained_source_identity_is_revision_bound() -> None:
    assert expected_retained_source_event_id(REVISION) == STABLE_SOURCE


def test_retained_binding_accepts_only_three_semantic_item_fields(tmp_path: Path) -> None:
    binding = _binding(tmp_path)
    assert binding.items[0].source_event_id == STABLE_SOURCE
    bad = _payload()
    bad["items"][0]["expected_kind"] = "unresolved"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(Exception, match="fields are not exact"):
        load_retained_formation_binding(path=bad_path, scenario_set_revision=REVISION, authoritative_t2_content=T2)


def test_retained_binding_rejects_revision_or_span_drift(tmp_path: Path) -> None:
    payload = _payload()
    payload["items"][0]["source_event_id"] = "stage-r:sha256:" + "b" * 64 + ":primary:turn-2"
    path = tmp_path / "wrong-source.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception, match="source_event_id"):
        load_retained_formation_binding(path=path, scenario_set_revision=REVISION, authoritative_t2_content=T2)
    payload = _payload()
    payload["items"][0]["unknown_evidence_span"] = "not in T2"
    path = tmp_path / "wrong-span.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception, match="substring"):
        load_retained_formation_binding(path=path, scenario_set_revision=REVISION, authoritative_t2_content=T2)


def test_overlay_rebinds_only_provenance_and_preserves_production_request(tmp_path: Path) -> None:
    extraction = CognitionExtractionInput(cognitive_input=_input(), assistant_response="I cannot know until the parcel is opened.")
    request = build_overlay_extraction_request_body(provider=_Provider(), extraction_input=extraction, pass_request=_pass_request(), binding=_binding(tmp_path))
    assert_production_schema_unchanged(request)
    assert request.retained_source_event_id == STABLE_SOURCE
    assert request.run_local_source_event_id == "evt-run-local"
    assert request.model_overlay == ({"subject_span": "what is inside", "unknown_evidence_span": "remains unknown", "source_event_id": "E0"},)
    baseline = request.baseline_body
    overlaid = request.body
    assert set(baseline) == set(overlaid)
    assert baseline["model"] == overlaid["model"]
    assert baseline["stream"] == overlaid["stream"]
    assert baseline["temperature"] == overlaid["temperature"]
    assert baseline["top_p"] == overlaid["top_p"]
    assert baseline["reasoning_effort"] == overlaid["reasoning_effort"] == "none"
    assert baseline["response_format"] == overlaid["response_format"]
    assert baseline["messages"][0] == overlaid["messages"][0]
    baseline_user = baseline["messages"][1]["content"]
    overlay_user = overlaid["messages"][1]["content"]
    assert overlay_user.startswith(baseline_user)
    assert "<PASS_1_RESPONSE_JSON>" in overlay_user
    assert "I cannot know until the parcel is opened." in overlay_user
    assert "state_candidates" in overlay_user
    assert "continuity_candidates" in overlay_user
    assert STABLE_SOURCE not in overlay_user
    assert "evt-run-local" not in overlay_user
    overlay_block = overlay_user.split(f"<{OVERLAY_TAG}>\n", 1)[1].split(f"\n</{OVERLAY_TAG}>", 1)[0]
    parsed = json.loads(overlay_block)
    assert set(parsed) == {"formed_epistemic_observations"}
    item = parsed["formed_epistemic_observations"][0]
    assert set(item) == {"subject_span", "unknown_evidence_span", "source_event_id"}
    assert item["source_event_id"] == "E0"
    assert "box_contents_question" not in overlay_block
    assert '"kind"' not in overlay_block
    assert '"key"' not in overlay_block
    assert '"op"' not in overlay_block
    assert '"value"' not in overlay_block
    assert overlaid["response_format"]["json_schema"]["schema"] == EXTRACTION_WIRE_SCHEMA


def test_overlay_builder_fails_closed_on_production_t2_content_drift(tmp_path: Path) -> None:
    extraction = CognitionExtractionInput(cognitive_input=_input(content="different current input"), assistant_response="response")
    with pytest.raises(Exception, match="authoritative Stage-R T2"):
        build_overlay_extraction_request_body(provider=_Provider(), extraction_input=extraction, pass_request=_pass_request(), binding=_binding(tmp_path))


def test_apply_overlay_does_not_mutate_baseline() -> None:
    baseline = {"model": "m", "messages": [{"role": "system", "content": "system"}, {"role": "user", "content": "production"}], "stream": False}
    original = copy.deepcopy(baseline)
    overlaid = apply_overlay_to_production_request_body(baseline_body=baseline, model_overlay=({"subject_span": "s", "unknown_evidence_span": "e", "source_event_id": "E0"},))
    assert baseline == original
    assert overlaid is not baseline
    assert overlaid["messages"][1]["content"].startswith("production")
