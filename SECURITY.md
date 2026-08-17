# Security Policy

RelayLM welcomes responsible security reports.

## Supported versions

The active `v1` product line receives security fixes during development and after the 1.0 release.

RelayLM 0.x on the frozen `main` branch is historical/reference material and is not an active security-maintenance target.

## Reporting a vulnerability

Please do **not** open a public Issue with exploit details, secrets, credentials, private data, or a proof of concept that could enable abuse.

Preferred reporting path:

1. Use GitHub's private vulnerability-reporting / Security Advisory flow for this repository when the **Report a vulnerability** option is available.
2. Include the affected version or commit, the affected surface, reproduction steps, realistic impact, and any known mitigation.
3. If the private reporting option is unavailable, contact the repository maintainer through GitHub without posting sensitive technical details publicly, and request a private reporting channel.

Do not commit real API keys, provider credentials, access tokens, private Character Packages, or other secrets as part of a report or reproduction.

## What to expect

A report will be triaged against the current `v1` authority and reproduced where possible. Security fixes follow the same RelayLM repository rules as other changes: one bounded responsibility, direct canonical convergence, exact-head CI, and no compatibility bridge or second authority path unless an explicit released compatibility contract requires one.

When a vulnerability affects a released version, disclosure and release timing should be coordinated so a fix can be made available before unnecessary exploit detail is published.
