import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const files = [
  ["apps/explorer/data/demo.json", "apps/observatory/public/data/demo.json"],
  ["apps/explorer/data/grf00-summary.public.json", "apps/observatory/public/data/grf00-summary.public.json"],
  ["apps/explorer/data/grf01-summary.public.json", "apps/observatory/public/data/grf01-summary.public.json"],
  ["experiments/model_matrix_10_proposed.json", "apps/observatory/public/data/model_matrix.json"],
  ["experiments/micro_v02_observatory_replay.json", "apps/observatory/public/data/micro-v02-replay.json"],
  ["experiments/architecture_playground_illustrative.json", "apps/observatory/public/data/architecture-playground.json"],
  ["experiments/repo_retrieval_replay.json", "apps/observatory/public/data/repo-retrieval-replay.json"],
];
for (const [src, dest] of files) {
  const content = JSON.parse(await readFile(resolve(root, src), "utf8"));
  if (!content || typeof content !== "object") throw new Error("Invalid source JSON: " + src);
  const output = resolve(root, dest);
  await mkdir(dirname(output), { recursive: true });
  await cp(resolve(root, src), output);
  console.log("WEB01_PUBLIC_SOURCE=" + src);
}
const manifest = {
  schema_version: 1,
  status: "curated_read_only_local_research",
  sources: files.map(([source, publicPath]) => ({ source, publicPath })),
  generation_api: null,
  disclaimer: "The graph example is fictional. GRF00/GRF01 are audited DEV retrieval aggregates. No semantic truth is claimed."
};
await writeFile(resolve(root, "apps/observatory/public/data/public-manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
