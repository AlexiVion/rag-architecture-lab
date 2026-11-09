/** WEB-01 public schema: source-verified, read-only artifacts. */
export type GraphDocument = { id: string; title: string; text: string };
export type GraphNode = { id: string; label: string; aliases: string[] };
export type GraphEdge = {
  id: string; source: string; target: string;
  relation: string; document_id: string; quote: string;
};
export type EvidencePath = {
  edge_ids: string[]; node_ids: string[]; hop_count: number;
  source_document_ids: string[];
};
export type QuestionTrace = {
  id: string; question: string; answer: null;
  generation_status: "not_run"; answer_truth_status: "not_evaluated";
  ranked_sources: { doc_id: string; rank: number; score: number }[];
  trace: {
    seed_entity_ids: string[];
    ranked_document_ids: string[];
    graph_hit_document_ids: string[];
    paths: EvidencePath[];
    max_hops: number;
    method: string;
    limitations: string;
  };
};
export type GraphFixture = {
  schema_version: 1; kind: "graph_evidence_fixture";
  publication_status: "illustrative_fixture_not_benchmark";
  corpus_sha256: string; dataset: string;
  extraction_method: string;
  graph: { documents: GraphDocument[]; nodes: GraphNode[]; edges: GraphEdge[] };
  traces: QuestionTrace[];
};
export type GRF00Metric = {
  bm25: number; graph_plus_bm25: number; paired_delta: number;
  paired_bootstrap_95ci: [number, number];
};
export type GRF01Metric = {
  hybrid: number; graph_hybrid: number;
  graph_hybrid_minus_hybrid_delta: number;
  paired_bootstrap_95ci: [number, number];
};
export type GRF00 = {
  schema_version: 1; experiment_id: "GRF00-HOTPOTQA-DEV-01";
  decision: string; sample_count: number; dataset: string;
  dataset_license: string; source_report_sha256: string;
  metrics: Record<"recall@1" | "recall@3" | "recall@5", GRF00Metric>;
  limitations: string[];
};
export type GRF01 = {
  schema_version: 1; experiment_id: "GRF01-HOTPOTQA-DEV-01";
  decision: string; sample_count: number; dataset: string;
  dataset_license: string; source_report_sha256: string;
  metrics: Record<"recall@1" | "recall@3" | "recall@5", GRF01Metric>;
  limitations: string[];
};
export type ModelEntry = {
  id: string; role: string; hub_id: string; revision: string | null;
  license_review: string; execution_status: string;
  measured_metrics: Record<string, unknown> | null;
  special_license_note?: string;
};
export type ModelRegistry = {
  schema_version: 1; registry_id: string;
  status: string; model_count: 10;
  models: ModelEntry[];
  previously_evaluated_baselines: { id: string; role: string; hub_id: string; historical_status: string }[];
};
export type ObservatoryData = {
  fixture: GraphFixture; grf00: GRF00; grf01: GRF01; registry: ModelRegistry;
};

const REPORT_HASHES = {
  grf00: "962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016",
  grf01: "f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4",
} as const;
export const metricNames = ["recall@1", "recall@3", "recall@5"] as const;

function obj(value: unknown, context: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error(context + " must be a JSON object");
  return value as Record<string, unknown>;
}
function array(value: unknown, context: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(context + " must be an array");
  return value;
}
function str(value: unknown, context: string): string {
  if (typeof value !== "string" || value.trim() === "")
    throw new Error(context + " must be a nonempty string");
  return value;
}
function num(value: unknown, context: string): number {
  if (typeof value !== "number" || !Number.isFinite(value))
    throw new Error(context + " must be finite");
  return value;
}
function strings(value: unknown, context: string): string[] {
  return array(value, context).map((item) => str(item, context + " item"));
}
function unique(items: string[], context: string): void {
  if (items.length !== new Set(items).size) throw new Error("Duplicate " + context);
}
function isHash(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}

export function validateFixture(input: unknown): GraphFixture {
  const data = obj(input, "fixture");
  if (data.schema_version !== 1 || data.kind !== "graph_evidence_fixture" ||
      data.publication_status !== "illustrative_fixture_not_benchmark")
    throw new Error("Unverified graph fixture publication status");
  if (!isHash(data.corpus_sha256)) throw new Error("Missing corpus fingerprint");
  str(data.dataset, "dataset");
  const graph = obj(data.graph, "graph");
  const documents = array(graph.documents, "graph documents").map((x) => obj(x, "document"));
  const nodes = array(graph.nodes, "graph nodes").map((x) => obj(x, "node"));
  const edges = array(graph.edges, "graph edges").map((x) => obj(x, "edge"));
  if (!documents.length || !nodes.length || !edges.length) throw new Error("Empty graph");
  unique(documents.map((d) => str(d.id, "document id")), "document ids");
  unique(nodes.map((n) => str(n.id, "node id")), "node ids");
  unique(edges.map((e) => str(e.id, "edge id")), "edge ids");
  const docs = new Map(documents.map((d) => [String(d.id), d]));
  const nodeIds = new Set(nodes.map((n) => String(n.id)));
  const edgeById = new Map(edges.map((e) => [String(e.id), e]));
  for (const node of nodes) {
    str(node.label, "node label");
    if (!Array.isArray(node.aliases) || node.aliases.some((a) => typeof a !== "string"))
      throw new Error("Invalid node aliases");
  }
  for (const edge of edges) {
    const doc = docs.get(str(edge.document_id, "edge document"));
    const src = str(edge.source, "edge source");
    const target = str(edge.target, "edge target");
    if (!doc || !nodeIds.has(src) || !nodeIds.has(target))
      throw new Error("Edge has missing document or entity");
    if (!(str(doc.title, "document title") + "\n" + str(doc.text, "document text"))
          .includes(str(edge.quote, "source quotation")))
      throw new Error("Graph relationship lacks verbatim source evidence");
  }
  const traces = array(data.traces, "traces").map((x) => obj(x, "trace"));
  if (!traces.length) throw new Error("No research questions");
  unique(traces.map((t) => str(t.id, "trace id")), "trace ids");
  for (const trace of traces) {
    str(trace.question, "question");
    if (trace.answer !== null || trace.generation_status !== "not_run" ||
        trace.answer_truth_status !== "not_evaluated")
      throw new Error("Fixture falsely claims a generated or verified answer");
    const meta = obj(trace.trace, "retrieval trace");
    const ranked = array(trace.ranked_sources, "ranked sources");
    const rankedIds = ranked.map((r) => {
      const entry = obj(r, "ranked source");
      num(entry.rank, "rank");
      num(entry.score, "retrieval score");
      const id = str(entry.doc_id, "ranked source id");
      if (!docs.has(id)) throw new Error("Ranked source missing from graph");
      return id;
    });
    if (JSON.stringify(rankedIds) !== JSON.stringify(strings(meta.ranked_document_ids, "trace ranked ids")))
      throw new Error("Rank order and trace provenance disagree");
    const seeds = strings(meta.seed_entity_ids, "seed entity ids");
    if (seeds.some((id) => !nodeIds.has(id))) throw new Error("Unknown seed entity");
    for (const pathRaw of array(meta.paths, "paths")) {
      const path = obj(pathRaw, "evidence path");
      const eids = strings(path.edge_ids, "path edge ids");
      const nids = strings(path.node_ids, "path node ids");
      const sourceIds = strings(path.source_document_ids, "path source docs");
      if (num(path.hop_count, "hop count") !== eids.length ||
          eids.length < 1 || eids.length > 2 || nids.length !== eids.length + 1)
        throw new Error("Invalid graph path length");
      const expectedDocs: string[] = [];
      eids.forEach((edgeId, i) => {
        const edge = edgeById.get(edgeId);
        if (!edge) throw new Error("Unknown edge in path");
        if (!new Set([edge.source, edge.target]).has(nids[i]) ||
            !new Set([edge.source, edge.target]).has(nids[i + 1]))
          throw new Error("Disconnected graph evidence path");
        const doc = String(edge.document_id);
        if (!expectedDocs.includes(doc)) expectedDocs.push(doc);
      });
      if (JSON.stringify(expectedDocs) !== JSON.stringify(sourceIds))
        throw new Error("Graph path source provenance mismatch");
    }
  }
  return input as GraphFixture;
}

function validateMetric(metric: unknown, baseline: string, candidate: string, delta: string): void {
  const data = obj(metric, "metric");
  const before = num(data[baseline], "baseline metric");
  const after = num(data[candidate], "candidate metric");
  const reported = num(data[delta], "paired delta");
  if (before < 0 || before > 1 || after < 0 || after > 1 ||
      Math.abs(after - before - reported) > 1e-9)
    throw new Error("Measured retrieval delta contradicts its source");
  const ci = array(data.paired_bootstrap_95ci, "confidence interval");
  if (ci.length !== 2 || num(ci[0], "ci lower") > num(ci[1], "ci upper"))
    throw new Error("Invalid paired bootstrap interval");
}
export function validateGRF00(input: unknown): GRF00 {
  const data = obj(input, "GRF-00");
  if (data.schema_version !== 1 || data.experiment_id !== "GRF00-HOTPOTQA-DEV-01" ||
      data.source_report_sha256 !== REPORT_HASHES.grf00 || data.sample_count !== 60)
    throw new Error("GRF-00 source audit mismatch");
  str(data.decision, "study decision");
  strings(data.limitations, "research limitations");
  const metrics = obj(data.metrics, "GRF-00 metrics");
  metricNames.forEach((name) => validateMetric(metrics[name], "bm25", "graph_plus_bm25", "paired_delta"));
  return input as GRF00;
}
export function validateGRF01(input: unknown): GRF01 {
  const data = obj(input, "GRF-01");
  if (data.schema_version !== 1 || data.experiment_id !== "GRF01-HOTPOTQA-DEV-01" ||
      data.source_report_sha256 !== REPORT_HASHES.grf01 || data.sample_count !== 60)
    throw new Error("GRF-01 source audit mismatch");
  str(data.decision, "study decision");
  strings(data.limitations, "research limitations");
  const metrics = obj(data.metrics, "GRF-01 metrics");
  metricNames.forEach((name) => validateMetric(metrics[name], "hybrid", "graph_hybrid", "graph_hybrid_minus_hybrid_delta"));
  return input as GRF01;
}
export function validateModels(input: unknown): ModelRegistry {
  const data = obj(input, "model registry");
  const models = array(data.models, "model candidates").map((x) => obj(x, "model"));
  if (data.schema_version !== 1 || data.model_count !== 10 || models.length !== 10)
    throw new Error("The MOD-10 candidate contract requires ten entries");
  unique(models.map((m) => str(m.id, "model id")), "model ids");
  const groups = new Map<string, number>();
  for (const model of models) {
    str(model.hub_id, "hub model ID");
    const role = str(model.role, "model role");
    groups.set(role, (groups.get(role) ?? 0) + 1);
    if (model.measured_metrics !== null && model.execution_status !== "measured")
      throw new Error("Unknown experiment measurement status");
    if (model.execution_status === "measured" && model.measured_metrics === null)
      throw new Error("Model reported measured without evidence");
  }
  for (const [role, expected] of Object.entries({embedding: 3, reranking: 2, stance_nli: 2, generation: 3}))
    if (groups.get(role) !== expected) throw new Error("MOD-10 role split changed");
  if (array(data.previously_evaluated_baselines, "existing baselines").length !== 4)
    throw new Error("Four historical baselines expected");
  return input as ModelRegistry;
}

async function fetchJSON(path: string): Promise<unknown> {
  const response = await fetch(import.meta.env.BASE_URL + "data/" + path, {cache: "no-store"});
  if (!response.ok) throw new Error("Unable to load public source: " + path);
  return response.json() as Promise<unknown>;
}
export async function loadObservatory(): Promise<ObservatoryData> {
  const [fixture, grf00, grf01, registry] = await Promise.all([
    fetchJSON("demo.json"),
    fetchJSON("grf00-summary.public.json"),
    fetchJSON("grf01-summary.public.json"),
    fetchJSON("model_matrix.json"),
  ]);
  return {
    fixture: validateFixture(fixture),
    grf00: validateGRF00(grf00),
    grf01: validateGRF01(grf01),
    registry: validateModels(registry),
  };
}
