# Security policy

This repository is a CPU-first research lab. Its public static observatory does not run an inference server and is not an authorization service.

## Supported releases

Only tagged releases are supported for reproducibility and dependency review. The current research branch is experimental until a release is announced.

## Reporting

If GitHub's **Report a vulnerability** option is enabled for this repository, use it to report vulnerabilities privately. Otherwise, contact the repository maintainer privately through an appropriate existing channel. Do **not** include secrets, exploit payloads or unredacted private documents in public GitHub issues.

For non-security defects, open a normal issue with steps to reproduce, software versions and minimal non-sensitive fixtures.

## Safety boundaries

- Treat all retrieved documents and model outputs as untrusted data.
- A syntactically valid source reference does **not** establish factual support.
- No generated factual answer from the experimental M2 pipeline should be automatically published.
- Never commit raw customer data, credentials, full private review packets, model weights or restricted datasets.
- Browser-facing artifacts must be curated, attributable, redacted and schema-checked.
- No public inference API is provided or endorsed.
