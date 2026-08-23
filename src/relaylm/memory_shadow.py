from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any

from relaylm.memory_provenance import MemoryTemporalScope
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import StateRecord


class _Decision(Enum):
    CONFLICT = "conflict"
    COMPATIBLE = "compatible"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class _Addressing:
    heading: bool
    assignments: tuple[str, ...]

    @property
    def inline(self) -> bool:
        return bool(self.assignments)


@dataclass(frozen=True, slots=True)
class _DegreeClaim:
    semantic_terms: tuple[str, ...]
    degree: float

    @property
    def is_positive(self) -> bool:
        return bool(self.semantic_terms) and self.semantic_terms[0] != "not"

    @property
    def is_valid_negation(self) -> bool:
        return (
            len(self.semantic_terms) > 1
            and self.semantic_terms[0] == "not"
            and self.semantic_terms[1] != "not"
        )


def memory_chunk_is_shadowed(
    *,
    chunk: MemoryChunk,
    active_state: tuple[StateRecord, ...],
) -> bool:
    """Return whether lower-authority MEMORY conflicts with active State.

    The parser is intentionally bounded. It recognizes only the explicit structural
    forms already admitted by the frozen Context Compiler grammar; everything else
    falls back to the existing lexical authority check rather than expanding NLP.
    """

    if chunk.temporal_authority.temporal_scope is MemoryTemporalScope.HISTORICAL:
        return False

    heading_terms = frozenset(_lexical_terms(" ".join(chunk.heading_path)))
    for record in active_state:
        addressing = _addressing_for_record(
            content=chunk.content,
            heading_terms=heading_terms,
            key=record.key,
        )
        if not addressing.heading and not addressing.inline:
            if chunk.temporal_authority.temporal_scope is MemoryTemporalScope.CURRENT:
                if _freeform_conflicts(chunk.content, record):
                    return True
            continue

        if isinstance(record.value, bool):
            decision = _boolean_decision(chunk.content, addressing, record.value)
        elif (degree_value := _reserved_degree_state_value(record.value)) is not None:
            decision = _degree_decision(
                content=chunk.content,
                key=record.key,
                addressing=addressing,
                current_semantic=degree_value[0],
                current_degree=degree_value[1],
            )
        elif (current_scalar := _simple_scalar_state_value_text(record.value)) is not None:
            decision = _scalar_decision(
                content=chunk.content,
                addressing=addressing,
                current_scalar=current_scalar,
            )
        else:
            decision = _Decision.FALLBACK

        if decision is _Decision.CONFLICT:
            return True
        if decision is _Decision.COMPATIBLE:
            continue
        if _fallback_lexical_conflict(chunk.content, record):
            return True

    return False


def _addressing_for_record(
    *,
    content: str,
    heading_terms: frozenset[str],
    key: str,
) -> _Addressing:
    key_terms = _lexical_terms(key)
    return _Addressing(
        heading=bool(key_terms) and all(term in heading_terms for term in key_terms),
        assignments=_explicit_state_key_assignment_values(content, key),
    )


def _freeform_conflicts(content: str, record: StateRecord) -> bool:
    claims = _bounded_freeform_state_key_claims(content, record.key)
    if isinstance(record.value, bool):
        return any(
            (value := _explicit_boolean_claim_value(claim)) is not None
            and value is not record.value
            for claim in claims
        )

    if (degree_value := _reserved_degree_state_value(record.value)) is not None:
        current_terms = _lexical_terms(degree_value[0])
        current_degree = degree_value[1]
        for claim_text in claims:
            claim = _parse_degree_claim(claim_text)
            if claim is None:
                continue
            if claim.is_valid_negation:
                if claim.semantic_terms[1:] == current_terms and claim.degree == current_degree:
                    return True
                continue
            if claim.is_positive and (
                claim.semantic_terms != current_terms or claim.degree != current_degree
            ):
                return True
        return False

    current_scalar = _simple_scalar_state_value_text(record.value)
    if current_scalar is None:
        return False
    current_terms = _lexical_terms(current_scalar)
    for claim in claims:
        terms = _lexical_terms(claim)
        if _is_valid_negation(terms):
            if terms[1:] == current_terms:
                return True
            continue
        if terms != current_terms:
            return True
    return False


def _boolean_decision(
    content: str,
    addressing: _Addressing,
    current: bool,
) -> _Decision:
    if addressing.inline:
        values = tuple(_explicit_boolean_claim_value(value) for value in addressing.assignments)
        if values and all(value is not None for value in values):
            return (
                _Decision.CONFLICT
                if any(value is not current for value in values)
                else _Decision.COMPATIBLE
            )

    if addressing.heading and not addressing.inline:
        body = _single_atx_heading_body_value(content)
        if body is not None and (value := _explicit_boolean_claim_value(body)) is not None:
            return _Decision.CONFLICT if value is not current else _Decision.COMPATIBLE

    return (
        _Decision.CONFLICT
        if _contains_explicit_opposite_boolean_value(content, current_value=current)
        else _Decision.COMPATIBLE
    )


def _scalar_decision(
    *,
    content: str,
    addressing: _Addressing,
    current_scalar: str,
) -> _Decision:
    current_terms = _lexical_terms(current_scalar)

    if addressing.inline:
        term_sets = tuple(_lexical_terms(value) for value in addressing.assignments)
        if len(term_sets) >= 2 and all(term_sets):
            return _evaluate_scalar_terms(term_sets, current_terms)
        if len(term_sets) == 1:
            terms = term_sets[0]
            if addressing.heading and terms:
                return _evaluate_scalar_terms(term_sets, current_terms)
            if _is_valid_negation(terms):
                return (
                    _Decision.CONFLICT
                    if terms[1:] == current_terms
                    else _Decision.COMPATIBLE
                )

    if addressing.heading and not addressing.inline:
        body = _single_atx_heading_body_value(content)
        if body is not None:
            terms = _lexical_terms(body)
            if _is_valid_negation(terms):
                return (
                    _Decision.CONFLICT
                    if terms[1:] == current_terms
                    else _Decision.COMPATIBLE
                )

    return _Decision.FALLBACK


def _evaluate_scalar_terms(
    term_sets: tuple[tuple[str, ...], ...],
    current_terms: tuple[str, ...],
) -> _Decision:
    for terms in term_sets:
        if _is_valid_negation(terms):
            if terms[1:] == current_terms:
                return _Decision.CONFLICT
            continue
        if terms != current_terms:
            return _Decision.CONFLICT
    return _Decision.COMPATIBLE


def _degree_decision(
    *,
    content: str,
    key: str,
    addressing: _Addressing,
    current_semantic: str,
    current_degree: float,
) -> _Decision:
    current_terms = _lexical_terms(current_semantic)

    if addressing.inline:
        claims = tuple(_parse_degree_claim(value) for value in addressing.assignments)
        decision = _evaluate_structural_degree_claims(
            claims=claims,
            current_terms=current_terms,
            current_degree=current_degree,
            locality_ok=(
                not addressing.heading
                or len(_explicit_degree_hint_assignments(
                    content,
                    key=key,
                    heading_addresses_key=True,
                ))
                == len(addressing.assignments)
            ),
            single_heading_inline=addressing.heading and len(addressing.assignments) == 1,
        )
        if decision is not _Decision.FALLBACK:
            return decision

    if addressing.heading and not addressing.inline:
        body_values = _atx_heading_body_values(content)
        if body_values:
            claims = tuple(_parse_degree_claim(value) for value in body_values)
            exact_claims = tuple(claim for claim in claims if claim is not None)
            explicit_degree_count = len(
                _explicit_degree_hint_assignments(
                    content,
                    key=key,
                    heading_addresses_key=True,
                )
            )

            # A single exact negated pair remains a local claim even when the
            # heading body also contains unrelated prose.
            negated = tuple(claim for claim in exact_claims if claim.is_valid_negation)
            if len(negated) == 1 and explicit_degree_count == 1:
                claim = negated[0]
                return (
                    _Decision.CONFLICT
                    if claim.semantic_terms[1:] == current_terms
                    and claim.degree == current_degree
                    else _Decision.COMPATIBLE
                )

            if len(exact_claims) == 1 and exact_claims[0].is_positive and explicit_degree_count == 1:
                claim = exact_claims[0]
                if claim.semantic_terms != current_terms or claim.degree != current_degree:
                    return _Decision.CONFLICT

            if len(exact_claims) >= 2 and explicit_degree_count == len(exact_claims):
                decision = _evaluate_degree_set(
                    exact_claims,
                    current_terms=current_terms,
                    current_degree=current_degree,
                )
                if decision is not _Decision.FALLBACK:
                    return decision

    return _Decision.FALLBACK


def _evaluate_structural_degree_claims(
    *,
    claims: tuple[_DegreeClaim | None, ...],
    current_terms: tuple[str, ...],
    current_degree: float,
    locality_ok: bool,
    single_heading_inline: bool,
) -> _Decision:
    if not claims or any(claim is None for claim in claims):
        return _Decision.FALLBACK
    exact = tuple(claim for claim in claims if claim is not None)

    if len(exact) == 1:
        claim = exact[0]
        if claim.is_valid_negation:
            if single_heading_inline and not locality_ok:
                return _Decision.FALLBACK
            return (
                _Decision.CONFLICT
                if claim.semantic_terms[1:] == current_terms and claim.degree == current_degree
                else _Decision.COMPATIBLE
            )
        if claim.is_positive and (
            claim.semantic_terms != current_terms or claim.degree != current_degree
        ):
            return _Decision.CONFLICT
        return _Decision.FALLBACK

    if not locality_ok:
        return _Decision.FALLBACK
    return _evaluate_degree_set(
        exact,
        current_terms=current_terms,
        current_degree=current_degree,
    )


def _evaluate_degree_set(
    claims: tuple[_DegreeClaim, ...],
    *,
    current_terms: tuple[str, ...],
    current_degree: float,
) -> _Decision:
    if all(claim.is_positive for claim in claims):
        return (
            _Decision.CONFLICT
            if any(
                claim.semantic_terms != current_terms or claim.degree != current_degree
                for claim in claims
            )
            else _Decision.FALLBACK
        )

    if all(claim.is_valid_negation for claim in claims):
        return (
            _Decision.CONFLICT
            if any(
                claim.semantic_terms[1:] == current_terms and claim.degree == current_degree
                for claim in claims
            )
            else _Decision.COMPATIBLE
        )

    if all(claim.is_positive or claim.is_valid_negation for claim in claims):
        has_positive = any(claim.is_positive for claim in claims)
        has_negative = any(claim.is_valid_negation for claim in claims)
        if has_positive and has_negative:
            for claim in claims:
                if claim.is_valid_negation:
                    if claim.semantic_terms[1:] == current_terms and claim.degree == current_degree:
                        return _Decision.CONFLICT
                elif claim.semantic_terms != current_terms or claim.degree != current_degree:
                    return _Decision.CONFLICT
            return _Decision.COMPATIBLE

    return _Decision.FALLBACK


def _fallback_lexical_conflict(content: str, record: StateRecord) -> bool:
    if (degree_value := _reserved_degree_state_value(record.value)) is not None:
        semantic, degree = degree_value
        if not _contains_lexical_value(content, semantic):
            return True
        addressing = _contains_explicit_state_key_assignment(content, record.key)
        explicit_degrees = _explicit_degree_hint_assignments(
            content,
            key=record.key,
            heading_addresses_key=not addressing or _heading_text_addresses_key(content, record.key),
        )
        return bool(explicit_degrees and any(candidate != degree for candidate in explicit_degrees))

    current_values = tuple(
        value_text
        for value_text in _value_lexical_strings(record.value)
        if _lexical_terms(value_text)
    )
    return bool(
        current_values
        and not any(_contains_lexical_value(content, value_text) for value_text in current_values)
    )


def _heading_text_addresses_key(content: str, key: str) -> bool:
    lines = content.splitlines()
    heading = next((line for line in lines if line.strip()), "")
    match = re.fullmatch(r"\s{0,3}#{1,6}\s+(.+)", heading)
    if match is None:
        return False
    heading_terms = frozenset(_lexical_terms(match.group(1)))
    key_terms = _lexical_terms(key)
    return bool(key_terms) and all(term in heading_terms for term in key_terms)


def _parse_degree_claim(claim: str) -> _DegreeClaim | None:
    explicit = _explicit_reserved_degree_claim(claim)
    if explicit is None:
        return None
    return _DegreeClaim(_lexical_terms(explicit[0]), explicit[1])


def _is_valid_negation(terms: tuple[str, ...]) -> bool:
    return len(terms) > 1 and terms[0] == "not" and terms[1] != "not"


def _simple_scalar_state_value_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value if _lexical_terms(value) else None
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _atx_heading_body_values(content: str) -> tuple[str, ...] | None:
    lines = content.splitlines()
    first_nonempty_index = next(
        (index for index, line in enumerate(lines) if line.strip()),
        None,
    )
    if first_nonempty_index is None:
        return None
    if re.fullmatch(r"\s{0,3}#{1,6}\s+\S.*", lines[first_nonempty_index]) is None:
        return None
    return tuple(line.strip() for line in lines[first_nonempty_index + 1 :] if line.strip())


def _single_atx_heading_body_value(content: str) -> str | None:
    body_lines = _atx_heading_body_values(content)
    if body_lines is None or len(body_lines) != 1:
        return None
    return body_lines[0]


def _bounded_freeform_state_key_claims(content: str, key: str) -> tuple[str, ...]:
    key_terms = _lexical_terms(key)
    if not key_terms:
        return ()
    key_pattern = r"[\s_]+".join(re.escape(term) for term in key_terms)
    patterns = (
        re.compile(rf"^\s*current\s+{key_pattern}(?!\w)\s+is\s+(.+?)(?:[.!?])?\s*$"),
        re.compile(
            rf"^\s*(?:the\s+)?{key_pattern}(?!\w)\s+is\s+(?:currently|now)\s+"
            r"(.+?)(?:[.!?])?\s*$"
        ),
    )
    normalized_content = _normalize_lexical_text(content)
    return tuple(
        match.group(1).strip()
        for line in normalized_content.splitlines()
        for pattern in patterns
        if (match := pattern.search(line)) is not None
    )


def _explicit_boolean_claim_value(claim: str) -> bool | None:
    terms = _lexical_terms(claim)
    if terms == ("true",):
        return True
    if terms == ("false",):
        return False
    if terms == ("not", "true"):
        return False
    if terms == ("not", "false"):
        return True
    return None


def _explicit_reserved_degree_claim(claim: str) -> tuple[str, float] | None:
    match = re.fullmatch(
        r"\s*(.+?)\s*;\s*degree_hint\s*[:=]\s*"
        r"(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:e[+-]?\d+)?)\s*",
        _normalize_lexical_text(claim),
    )
    if match is None:
        return None
    semantic = match.group(1).strip()
    if not _lexical_terms(semantic):
        return None
    return semantic, float(match.group(2))


def _reserved_degree_state_value(value: Any) -> tuple[str, float] | None:
    if not isinstance(value, dict) or set(value) != {"semantic", "degree_hint"}:
        return None
    semantic = value.get("semantic")
    degree = value.get("degree_hint")
    if not isinstance(semantic, str) or not semantic.strip():
        return None
    if isinstance(degree, bool) or not isinstance(degree, (int, float)):
        return None
    if not 0.0 <= degree <= 1.0:
        return None
    return semantic, float(degree)


def _explicit_degree_hint_assignments(
    content: str,
    *,
    key: str,
    heading_addresses_key: bool,
) -> tuple[float, ...]:
    normalized_content = _normalize_lexical_text(content)
    if heading_addresses_key:
        scopes = (normalized_content,)
    else:
        normalized_key = _normalize_lexical_text(key)
        key_pattern = rf"(?<!\w){re.escape(normalized_key)}\s*[:=]"
        scopes = tuple(
            line
            for line in normalized_content.splitlines()
            if re.search(key_pattern, line) is not None
        )
    return tuple(
        float(match.group(1))
        for scope in scopes
        for match in re.finditer(
            r"(?<!\w)degree_hint\s*[:=]\s*"
            r"(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:e[+-]?\d+)?)(?![\w.])",
            scope,
        )
    )


def _contains_explicit_opposite_boolean_value(content: str, *, current_value: bool) -> bool:
    terms = frozenset(_lexical_terms(content))
    current_term = "true" if current_value else "false"
    opposite_term = "false" if current_value else "true"
    return opposite_term in terms and current_term not in terms


def _explicit_state_key_assignment_values(content: str, key: str) -> tuple[str, ...]:
    normalized_key = _normalize_lexical_text(key)
    if not normalized_key:
        return ()
    normalized_content = _normalize_lexical_text(content)
    pattern = re.compile(rf"(?<!\w){re.escape(normalized_key)}\s*[:=]\s*")
    values: list[str] = []
    for line in normalized_content.splitlines():
        matches = tuple(pattern.finditer(line))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
            values.append(line[match.end() : end].strip())
    return tuple(values)


def _contains_explicit_state_key_assignment(content: str, key: str) -> bool:
    return bool(_explicit_state_key_assignment_values(content, key))


def _contains_lexical_value(content: str, value_text: str) -> bool:
    content_terms = _lexical_terms(content)
    value_terms = _lexical_terms(value_text)
    if not value_terms or len(value_terms) > len(content_terms):
        return False
    width = len(value_terms)
    return any(
        content_terms[index : index + width] == value_terms
        for index in range(len(content_terms) - width + 1)
    )


def _value_lexical_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(text for nested in value.values() for text in _value_lexical_strings(nested))
    if isinstance(value, (list, tuple)):
        return tuple(text for nested in value for text in _value_lexical_strings(nested))
    if value is None or isinstance(value, bool):
        return ()
    if isinstance(value, (int, float)):
        return (str(value),)
    return ()


def _normalize_lexical_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _lexical_terms(text: str) -> tuple[str, ...]:
    normalized = _normalize_lexical_text(text).replace("_", " ")
    return tuple(term for term in re.split(r"[^\w]+", normalized) if term)
