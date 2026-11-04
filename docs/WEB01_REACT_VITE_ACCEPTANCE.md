# WEB-01 — Seven-view typed observatory, React + TypeScript + Vite

**Status:** implementation committed on the research branch; **new frontend CI test/build and browser QA pending**. Nothing changes local Python pipeline, defaults, archival model runs, or benchmark findings.

## What is implemented

`apps/observatory` is a **read-only, static** React SPA with seven task-specific sections: Overview, Experiments, Pipeline, Knowledge graph, Evidence review, Model lab and Methodology. It supports selecting three source-backed fictional questions, comparing within-study paired retrieval metrics with confidence intervals, inspecting original document quotes and graph path evidence, exporting an explicitly ungenerated evidence packet, a model status table, accessible navigation and responsive light/dark themes.

The app does not report fictional graph retrieval as measured QA. It distinguishes **GRF-00 = NO-GO**, **GRF-01 = INCONCLUSIVE**, **M2 auto-answer publication = NO-GO**, and **MOD-10 ten candidate models = PROPOSED**. It does not host Qwen, execute model inference, accept arbitrary document uploads or claim automatically verified entailment.

## Public source controls

Original curated sources in `apps/explorer/data` remain the only authoritative fixture/DEV summary files. The build script `apps/observatory/scripts/prepare-data.mjs` copies them, plus `experiments/model_matrix_10_proposed.json`, into gitignored `apps/observatory/public/data`.

`src/contracts.ts` validates the expected schema and graph provenance: unique graph documents/entities/edges, exact quotation contained within the source document, ranked/source path/edge connectivity, model unexecuted state, frozen original GRF-00/GRF-01 report hashes, measured paired-delta arithmetic and model-role registry integrity. Invalid artifacts fail closed with a visible source-validation error instead of invented UI numbers. React renders source content as text (no untrusted HTML injection).

## Commands and cross-platform verification

```bash
cd apps/observatory
npm install
npm run check
npm run build
npm run dev
```

Open localhost:4874. A static build is produced in `dist`; `base: "./"` supports GitHub Pages project paths. The backend Python fixture still validates separately through `scripts/verify-wow-r0-local.ps1`.

The single `.github/workflows/offline-tests.yml` job performs Python tests and source checks, then Node 22 frontend typecheck/unit tests/build, and verifies output files. `.github/workflows/pages.yml` rebuilds from authoritative JSON and uploads **only the static dist folder** after merge to main and GitHub Pages configuration.

**Important:** `npm install` must be replaced with a committed lockfile + `npm ci` before final reproducible v1.0; browser/e2e/a11y/perf QA must be recorded and a **real public URL** verified. A build PASS does not certify screen-reader ergonomics or visual parity.

## Remaining WEB-01 acceptance

1. Node dependency lockfile, typechecking and unit testing PASS from clean install.
2. Chrome/Firefox browser keyboard, responsive layout and automated accessibility smoke PASS.
3. Accurate public experiment data under a validated manifest; no inferred graph score or claim-support metric.
4. Public GitHub Pages deployment reachable and verified through real browser interactions after integration.
5. Screenshots/short walkthrough tied to the exact launched commit, not a design mock.

The scientific G1/G2/G3 gates remain separate and open where independent evidence is still missing.
