/** Publicly archived, genuinely executed Python retrieval; no relevance labels. */
export type ReplayRank = { doc_id: string; rank: number; score: number };
export type ReplayDoc = { id: string; title: string; sha256: string; url: string };
export type ReplayQuery = {
  id: string; text: string;
  rankings: { bm25: ReplayRank[]; parent_child_bm25: ReplayRank[] };
  qrels: null; answer: null; answer_evaluation: "not_evaluated";
};
export type RepoReplay = {
  schema_version: 1; kind: "repository_retrieval_execution";
  status: "measured_software_trace_unlabelled";
  dataset: "versioned_rag_lab_research_documents";
  selection: "fixed_eight_documents_three_questions";
  execution: { software: string; top_k: 5; corpus_sha256: string;
    code_sources: { path: string; sha256: string }[];
    pipelines: ["bm25","parent_child_bm25"];
    bm25: { k1: 1.5; b: 0.75 };
    parent_child: { candidate_k: 100; chunk_chars: 480; overlap_chars: 60 };
  };
  documents: ReplayDoc[]; queries: ReplayQuery[]; limitations: string[];
};
const shaOk = (v:unknown):v is string => typeof v==="string" && /^[a-f0-9]{64}$/.test(v);
const isObject = (v:unknown):v is Record<string,unknown> => typeof v==="object" && v!==null && !Array.isArray(v);
const nonempty = (v:unknown):v is string => typeof v==="string" && v.trim().length>0;
const finite = (v:unknown):v is number => typeof v==="number" && Number.isFinite(v);

export function validateRepoReplay(value:unknown):RepoReplay {
  if(!isObject(value) ||
    value.schema_version!==1 || value.kind!=="repository_retrieval_execution" ||
    value.status!=="measured_software_trace_unlabelled" ||
    value.dataset!=="versioned_rag_lab_research_documents" ||
    value.selection!=="fixed_eight_documents_three_questions" ||
    "metrics" in value || "accuracy" in value || "qrels" in value)
    throw Error("Unverified or misrepresented real retrieval replay");
  if(!isObject(value.execution) || value.execution.top_k!==5 ||
    !shaOk(value.execution.corpus_sha256) ||
    JSON.stringify(value.execution.pipelines)!==JSON.stringify(["bm25","parent_child_bm25"]) ||
    !isObject(value.execution.bm25) || value.execution.bm25.k1!==1.5 || value.execution.bm25.b!==.75 ||
    !isObject(value.execution.parent_child) || value.execution.parent_child.chunk_chars!==480 ||
    value.execution.parent_child.overlap_chars!==60 || value.execution.parent_child.candidate_k!==100 ||
    !Array.isArray(value.execution.code_sources) || value.execution.code_sources.length!==4)
    throw Error("Missing retrieval configuration or source fingerprint");
  for(const c of value.execution.code_sources){
    if(!isObject(c)||!nonempty(c.path)||!shaOk(c.sha256))throw Error("Missing code provenance");
  }
  if(!Array.isArray(value.documents)||value.documents.length!==8)throw Error("Missing repository documents");
  const ids=new Set<string>();
  for(const d of value.documents){
    if(!isObject(d)||!nonempty(d.id)||!nonempty(d.title)||!shaOk(d.sha256)||
      d.url!=="https://github.com/AlexiVion/rag-architecture-lab/blob/main/"+d.id ||
      !d.id.endsWith(".md") || d.id.includes("..") || ids.has(d.id))
      throw Error("Missing or duplicated original repository source");
    ids.add(d.id);
  }
  if(!Array.isArray(value.queries)||value.queries.length!==3)throw Error("Unexpected query selection");
  const seen=new Set<string>();
  for(const q of value.queries){
    if(!isObject(q)||!nonempty(q.id)||seen.has(q.id)||!nonempty(q.text)||
       q.qrels!==null||q.answer!==null||q.answer_evaluation!=="not_evaluated"||
       !isObject(q.rankings)||Object.keys(q.rankings).sort().join(",")!=="bm25,parent_child_bm25")
      throw Error("Trace falsely claims labelled or generated results");
    seen.add(q.id);
    for(const key of ["bm25","parent_child_bm25"]){
      const list=q.rankings[key];
      if(!Array.isArray(list)||list.length!==5)throw Error("Invalid source rank list");
      const unique=new Set<string>();
      for(let i=0;i<list.length;i++){
        const item=list[i];
        if(!isObject(item)||!nonempty(item.doc_id)||!ids.has(item.doc_id)||
          unique.has(item.doc_id)||item.rank!==i+1||!finite(item.score)||item.score<0)
          throw Error("Invalid source-backed rank or score");
        unique.add(item.doc_id);
      }
    }
  }
  if(!Array.isArray(value.limitations)||value.limitations.length<4 ||
     value.limitations.some(x=>!nonempty(x)))throw Error("Missing scientific limitations");
  return value as RepoReplay;
}
export async function loadRepoReplay():Promise<RepoReplay> {
  const response=await fetch(import.meta.env.BASE_URL+"data/repo-retrieval-replay.json",{cache:"no-store"});
  if(!response.ok)throw Error("Real Python trace unavailable");
  return validateRepoReplay(await response.json());
}
