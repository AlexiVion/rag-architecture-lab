# Hosting the read-only observatory

The repository's Python experiments, methods, versioned data, source code and tests are the authoritative research artifacts. GitHub Pages is an optional read-only viewer, not a model-serving backend or research validation step.

## Minimal publication procedure

1. In the repository's Settings > Pages select Build and deployment > GitHub Actions as source. This requires an owner/admin and cannot be done by a read-only integration.
2. Verify that main passes Offline research integrity, including the repository-replay and source-fingerprint checks.
3. Manually run .github/workflows/pages.yml (Publish static RAG evidence observatory) on main.
4. Open the URL returned by the deploy job. Verify all three navigation sections, the fictional Architecture Playground, the authenticated repository-document trace, original-source links and the local JSON import. Verify mobile and HTTPS.
5. Only after the public URL is independently verified, reference it as an optional research viewing resource.

GitHub Pages is not considered deployed merely because main builds. The Pages workflow is intentionally manual, so code updates do not automatically publish a new site.

## Security and scientific boundaries

- Pages serves only static HTML/CSS/JS/JSON from apps/observatory/dist; no API key, server-side Python, database or model inference is available.
- The default repository retrieval trace is actual Python BM25 and parent-child retrieval on eight versioned research documents. No relevance or answer accuracy has been measured.
- Locally imported raw benchmark traces remain in the user's browser and are not uploaded. Their source SHA256 is a file fingerprint, not independent validation.
- The historical V0/V1 SciFact reports contain aggregate results and may not supply original per-query rankings. Never infer them from averages.
- Keep source documents, large model weights, private datasets and secrets out of the static public output.

See REPOSITORY_RETRIEVAL_REPLAY.md for commands and EXPERIMENT_PROTOCOL.md for the scientific standard.
