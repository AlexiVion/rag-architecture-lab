import { describe, expect, it } from "vitest";
import {
  validateFixture, validateGRF00, validateGRF01, validateModels
} from "./contracts";

const H00 = "962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016";
const H01 = "f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4";
const metric00 = {bm25: 0.5, graph_plus_bm25: 0.4, paired_delta: -0.1, paired_bootstrap_95ci: [-0.2, 0]};
const metric01 = {hybrid: 0.5, graph_hybrid: 0.4, graph_hybrid_minus_hybrid_delta: -0.1, paired_bootstrap_95ci: [-0.2, 0]};

describe("source-verified research contracts", () => {
  it("refuses fabricated GRF00 metric deltas and unknown source hash", () => {
    const original = { schema_version: 1, experiment_id: "GRF00-HOTPOTQA-DEV-01",
      source_report_sha256: H00, sample_count: 60, decision: "NO_GO", limitations: ["DEV"],
      metrics: {"recall@1": metric00, "recall@3": metric00, "recall@5": metric00}};
    expect(validateGRF00(original)).toBe(original);
    expect(() => validateGRF00({...original, source_report_sha256: "x"})).toThrow();
    expect(() => validateGRF00({...original, metrics: {...original.metrics,
      "recall@5": {...metric00, paired_delta: 0.2}}})).toThrow();
  });

  it("checks GRF01 source and paired metric arithmetic", () => {
    const original = {schema_version: 1, experiment_id: "GRF01-HOTPOTQA-DEV-01",
      source_report_sha256: H01, sample_count: 60, decision: "INCONCLUSIVE", limitations: ["DEV"],
      metrics: {"recall@1": metric01, "recall@3": metric01, "recall@5": metric01}};
    expect(validateGRF01(original)).toBe(original);
    expect(() => validateGRF01({...original, source_report_sha256: H00})).toThrow();
  });

  it("refuses fake generated-answer claims in public graph fixtures", () => {
    const fixture = {schema_version: 1, kind: "graph_evidence_fixture",
      publication_status: "illustrative_fixture_not_benchmark",
      corpus_sha256: "a".repeat(64), dataset: "fiction",
      graph: {documents: [{id:"d",title:"Proof",text:"A equals B."}],
        nodes: [{id:"a",label:"A",aliases:[]},{id:"b",label:"B",aliases:[]}],
        edges: [{id:"e",source:"a",target:"b",relation:"equals",document_id:"d",quote:"A equals B."}]},
      traces: [{id:"q",question:"What is A?",answer:null,generation_status:"not_run",
        answer_truth_status:"not_evaluated",ranked_sources:[{doc_id:"d",rank:1,score:1}],
        trace:{seed_entity_ids:["a"],ranked_document_ids:["d"],graph_hit_document_ids:["d"],
          paths:[{edge_ids:["e"],node_ids:["a","b"],hop_count:1,source_document_ids:["d"]}],
          max_hops:2,method:"synthetic",limitations:"No generator"}}]
    };
    expect(validateFixture(fixture)).toBe(fixture);
    expect(() => validateFixture({...fixture, traces: [{...fixture.traces[0], answer:"Invented [S1]"}]})).toThrow();
    expect(() => validateFixture({...fixture, graph: {...fixture.graph,
      edges: [{...fixture.graph.edges[0], quote:"Made up"}]}})).toThrow();
  });

  it("refuses registry with missing entries or invented measurements", () => {
    const models = [
      ...["e1","e2","e3"].map(id => ({id, role:"embedding",hub_id:id, execution_status:"not_run", measured_metrics:null})),
      ...["r1","r2"].map(id => ({id, role:"reranking",hub_id:id, execution_status:"not_run", measured_metrics:null})),
      ...["n1","n2"].map(id => ({id, role:"stance_nli",hub_id:id, execution_status:"not_run", measured_metrics:null})),
      ...["g1","g2","g3"].map(id => ({id, role:"generation",hub_id:id, execution_status:"not_run", measured_metrics:null}))
    ];
    const registry = {schema_version:1, model_count:10, models, previously_evaluated_baselines:[{},{},{},{}]};
    expect(validateModels(registry)).toBe(registry);
    expect(() => validateModels({...registry,models: models.slice(1)})).toThrow();
    expect(() => validateModels({...registry,models: models.map((m,i) => i===0 ?
      {...m,execution_status:"measured", measured_metrics:null} : m)})).toThrow();
  });
});
