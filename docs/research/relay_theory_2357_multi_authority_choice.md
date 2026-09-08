# Relay Theory #2357 — Multi-authority choice / causal-port Grand Null

This note records the bounded executable interpretation introduced by the #2357 transaction. It is research evidence, not architecture authority.

The tested comparison separates four layers that must not be conflated:

1. concrete owner/player names;
2. anonymous control-domain partition over writable decision ports;
3. information read edges and causal/concurrency constraints;
4. exact stochastic terminal laws and decision probes.

The executable null is stronger than “use a stochastic game”. It asks whether named players themselves carry operational content once read/write authority and causal information flow are explicit.

Current bounded candidate:

```text
concrete player name
  -> gauge candidate

anonymous control-domain partition
+ read edges
+ causal stage / concurrency
+ exact stochastic laws
  -> operational residue candidate
```

The tests deliberately keep objective/utility outside the transition interface. Objectives change policy selection and strategic probes without changing the physical/causal port process itself.

A stochastic-game-like formalism therefore remains a useful derived IR candidate, especially for imperfect-information or concurrent strategic analysis, but named game-player ontology is not granted primitive status by this transaction.

Refs #2352 #2353 #2357 #2209 PR #2346 PR #2356.
