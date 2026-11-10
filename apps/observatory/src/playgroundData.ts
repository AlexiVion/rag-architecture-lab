/** Strict source-labeled teaching data and separately scoped measured SciFact aggregates. */
export type ArchitectureId = "bm25" | "hybrid" | "rerank";
export type PlaygroundDoc = { id: string; title: string; summary: string; relevant: boolean };
export type Scenario = {
  id: string; label: string; question: string; documents: PlaygroundDoc[];
  rankings: { bm25: string[]; dense: string[]; rerank: string[] };
};
export type PlaygroundArtifact = {
  schema_version: 1; status: "FICTIONAL_RANKINGS_NOT_MEASURED";
  description: string; scenarios: Scenario[];
};
export type Study = {
  id: "v0" | "v1"; name: string; environment: string; cohort: string;
  report: string;
  points: { id: string; name: string; mrr10: number; latencyMs: number }[];
};
const REPO = "https://github.com/AlexiVion/rag-architecture-lab/blob/main/";
export const PLAYGROUND_STUDIES: Study[] = [
  {
    id: "v0", name: "V0 / sparse, dense, hybrid",
    environment: "GitHub Actions · Ubuntu 24.04 · same V0 run",
    cohort: "BEIR SciFact test · 5,183 documents · 300 queries",
    report: REPO + "benchmarks/V0_RESULTS.md",
    points: [
      { id: "bm25", name: "BM25", mrr10: .6328, latencyMs: 7.52 },
      { id: "dense", name: "Dense", mrr10: .6047, latencyMs: 26.17 },
      { id: "hybrid", name: "Hybrid RRF", mrr10: .6484, latencyMs: 51.86 }
    ],
  },
  {
    id: "v1", name: "V1 / hybrid and reranker (50)",
    environment: "Windows 11 · AMD Ryzen 7 5700U · same V1 run",
    cohort: "BEIR SciFact test · 5,183 documents · 300 queries",
    report: REPO + "benchmarks/V1_RESULTS.md",
    points: [
      { id: "hybrid", name: "Hybrid RRF", mrr10: .6484, latencyMs: 34.53 },
      { id: "rerank", name: "Hybrid + Cross-Encoder (50)", mrr10: .6615, latencyMs: 3706.43 }
    ],
  }
];
function object(value: unknown, name: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(name + " must be an object");
  }
  return value as Record<string, unknown>;
}
function str(value: unknown, name: string): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(name + " must be nonempty text");
  }
  return value;
}
function unique(values: string[], name: string): void {
  if (new Set(values).size !== values.length) throw new Error(name + " contains duplicate IDs");
}
function fields(value: Record<string, unknown>, keys: string[], name: string): void {
  for (const key of Object.keys(value)) if (!keys.includes(key)) {
    throw new Error("Unrecognized " + name + " field: " + key);
  }
  for (const key of keys) if (!(key in value)) {
    throw new Error("Missing " + name + " field: " + key);
  }
}
function array(value: unknown, name: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(name + " must be an array");
  return value;
}
function ranking(value: unknown, ids: string[], name: string): string[] {
  const results = array(value, name).map(x => str(x, name + " entry"));
  if (results.length !== ids.length) throw new Error(name + " must cover all documents");
  unique(results, name);
  if (results.some(id => !ids.includes(id))) throw new Error(name + " contains an unknown document");
  return results;
}
export function validatePlayground(input: unknown): PlaygroundArtifact {
  const root = object(input, "Playground source");
  fields(root, ["schema_version", "status", "description", "scenarios"], "source");
  if (root.schema_version !== 1 || root.status !== "FICTIONAL_RANKINGS_NOT_MEASURED") {
    throw new Error("Only explicitly fictional rankings may appear in this visualization");
  }
  if (!str(root.description, "source description").toLowerCase().includes("fictional"))
    throw new Error("Mandatory fictional data disclosure is missing");
  const cases = array(root.scenarios, "scenarios");
  if (cases.length !== 3) throw new Error("Expected three fixed educational questions");
  const parsed: Scenario[] = cases.map((raw, index) => {
    const s = object(raw, "scenario " + index);
    fields(s, ["id","label","question","documents","rankings"], "scenario");
    const docs = array(s.documents, "documents");
    if (docs.length !== 5) throw new Error("Exactly five bounded teaching documents required");
    const documents = docs.map((rawDoc) => {
      const d = object(rawDoc, "document");
      fields(d, ["id","title","summary","relevant"], "document");
      if (typeof d.relevant !== "boolean") throw new Error("Relevance must be an illustrative boolean");
      return {
        id: str(d.id,"document ID"), title: str(d.title,"document title"),
        summary: str(d.summary,"document summary"), relevant:d.relevant
      };
    });
    const ids = documents.map(d => d.id);
    unique(ids, "document IDs");
    if (!documents.some(d => d.relevant) || documents.every(d => d.relevant))
      throw new Error("An educational scenario needs relevant and irrelevant documents");
    const ranks = object(s.rankings, "rankings");
    fields(ranks, ["bm25", "dense", "rerank"], "rankings");
    return {
      id:str(s.id,"scenario ID"), label:str(s.label,"scenario label"),
      question:str(s.question,"question"), documents,
      rankings:{
        bm25:ranking(ranks.bm25,ids,"BM25 ranking"),
        dense:ranking(ranks.dense,ids,"dense ranking"),
        rerank:ranking(ranks.rerank,ids,"illustrative reordering")
      }
    };
  });
  unique(parsed.map(s => s.id),"scenario IDs");
  return {
    schema_version:1,status:"FICTIONAL_RANKINGS_NOT_MEASURED",
    description:root.description as string,scenarios:parsed
  };
}
export function rrfRanking(bm25: string[], dense: string[], k = 60): string[] {
  if (!Number.isFinite(k) || k <= 0 || !Number.isInteger(k) ||
      bm25.length !== dense.length || !bm25.length) throw new Error("Invalid RRF inputs");
  unique(bm25, "BM25 ranking"); unique(dense,"dense ranking");
  if (bm25.some(id => !dense.includes(id))) throw new Error("RRF rankings contain different documents");
  const bmPos=new Map(bm25.map((id,i)=>[id,i+1]));
  const densePos=new Map(dense.map((id,i)=>[id,i+1]));
  return bm25.slice().sort((a,b)=>{
    const score=(id:string)=>1/(k+bmPos.get(id)!)+1/(k+densePos.get(id)!);
    return score(b)-score(a) || bmPos.get(a)!-bmPos.get(b)!;
  });
}
export function rankingAtStep(scene:Scenario, method:ArchitectureId, step:number):string[] {
  if (!Number.isInteger(step) || step<0 || step>4) throw new Error("Unknown stage");
  if (!["bm25","hybrid","rerank"].includes(method)) throw new Error("Unknown architecture");
  if (step<=1 || method==="bm25") return scene.rankings.bm25;
  if (step===2 || method==="hybrid") return rrfRanking(scene.rankings.bm25,scene.rankings.dense);
  return scene.rankings.rerank;
}
export async function loadPlayground():Promise<PlaygroundArtifact> {
  const response=await fetch(import.meta.env.BASE_URL+"data/architecture-playground.json",{cache:"no-store"});
  if (!response.ok) throw new Error("Illustrative teaching corpus unavailable");
  return validatePlayground(await response.json());
}
