# Architecture Decision Records

This directory records only decisions that are costly to rediscover or reverse.

ADRs are not a log of every implementation choice. Ordinary current behavior belongs in `docs/architecture/`, `docs/contracts/`, and `docs/reference/`.

Use an ADR when a decision fixes a durable architectural constraint or explains why an apparently simpler alternative is intentionally rejected.

Current accepted decisions:

- `0001-one-cognitive-generation.md` — one semantic cognitive generation per ordinary turn;
- `0002-event-state-separation.md` — Event occurrence/provenance is separate from Canonical State truth;
- `0003-direct-canonical-convergence.md` — internal compatibility bridges and dual authority are prohibited in v1.

If an ADR is superseded, keep it for history, mark its status `Superseded`, and link the replacement ADR. Current behavior must still be reflected in canonical authority docs.
