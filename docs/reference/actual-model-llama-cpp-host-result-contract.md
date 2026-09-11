# llama.cpp one-shot host result contract

## Purpose

The generic RelayLM 1.0 llama.cpp transaction can invoke more than one repository-owned citable host. Host selection and host-result selection therefore form one explicit contract.

A transaction must never infer a host result by scanning the artifact directory for a plausible JSON file.

## Contract

Every selected host module is paired with exactly one declared summary filename before the transaction begins.

The ordinary Stage R default remains:

```text
host module:            relaylm.actual_model_stage_r_llama_cpp
host summary filename:  stage-r-llama-cpp-summary.json
```

A diagnostic selector may bind another repository-owned host and another declared filename. For the #2516 epistemic-formation host, the pair is:

```text
host module:            relaylm.actual_model_stage_r_llama_cpp_epistemic_formation
host summary filename:  epistemic-formation-t2-summary.json
```

The summary filename must be one non-empty filename located directly inside the transaction-owned artifact root. Absolute paths, parent traversal and nested paths are rejected before server/host execution.

After the selected host process returns, the transaction reads only the declared summary path. If that file does not exist, the transaction fails closed. Another JSON artifact does not substitute for the declared result.

The complete parsed host summary is embedded unchanged in the outer transaction summary. The outer transaction does not reinterpret a producer semantic classification or manufacture a semantic verdict.

## Exactly-once and accounting boundary

Changing the declared summary filename does not change the scientific transaction budget:

```text
server lifecycle       <= 1
host invocation        <= 1
semantic retry          = 0
replay                   = 0
fallback                 = 0
LM Studio contact        = 0
repository mutation      = 0
```

The filename contract is mechanical orchestration only. It is not permission to rerun a spent owner when a producer already completed.

In particular, #2529 remains immutable and must not be rerun. Its producer result exists independently of the historical outer lookup defect that motivated this contract.

## Selector rule

Repository-owned selector modules that replace the default host must declare the matching summary filename explicitly when calling the generic transaction. A selector must not rely on filename guessing from the module name, diagnostic name, fixture identity or directory contents.

## Failure behavior

The transaction fails closed when:

- the declared summary filename is empty;
- it is absolute;
- it contains parent traversal or a directory component;
- the declared artifact is absent after host completion;
- the declared artifact is not a JSON object.

An undeclared alternate JSON result is never accepted as rescue.

## Principle

> A pluggable host module requires an equally explicit producer-result contract.
