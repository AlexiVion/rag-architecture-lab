/** Read-only, unverified-on-client replay of first queries from one local benchmark JSON. */
export type SavedRank={doc_id:string;rank:number;score:number};
export type SavedQuery={id:string;text:string;rankings:Record<string,SavedRank[]>};
export type SavedReplay={
  schema_version:1; kind:"saved_benchmark_query_replay";
  status:"archived_original_per_query_not_independently_revalidated";
  dataset:string; source_archive_sha256:string; document_count:number;
  pipeline_names:string[]; query_selection:"first_N_original_order_without_qrel_selection";
  source_environment:Record<string,unknown>; queries:SavedQuery[]; limitations:string[];
};
const isObj=(v:unknown):v is Record<string,unknown>=>typeof v==="object"&&v!==null&&!Array.isArray(v);
const nonempty=(v:unknown):v is string=>typeof v==="string"&&v.length>0;
export function validateSavedReplay(value:unknown):SavedReplay{
  if(!isObj(value)||value.schema_version!==1||value.kind!=="saved_benchmark_query_replay"||
    value.status!=="archived_original_per_query_not_independently_revalidated"||
    value.query_selection!=="first_N_original_order_without_qrel_selection"||
    !nonempty(value.dataset)||!Number.isInteger(value.document_count)||(value.document_count as number)<1||
    typeof value.source_archive_sha256!=="string"||!/^[a-f0-9]{64}$/.test(value.source_archive_sha256)||
    !isObj(value.source_environment)||
    "accuracy" in value || "evaluation_verified" in value)
    throw Error("Invalid saved benchmark replay or unsupported validation claims");
  const methods=value.pipeline_names;
  if(!Array.isArray(methods)||methods.length<2||methods.length>4||
    new Set(methods).size!==methods.length||
    methods.some(m=>typeof m!=="string"||!["bm25","dense","hybrid","hybrid-rerank","bm25-rerank","dense-rerank"].includes(m)))
    throw Error("Invalid pipeline list");
  const cases=value.queries;
  if(!Array.isArray(cases)||cases.length<1||cases.length>20)throw Error("Invalid saved query count");
  const ids=new Set<string>();
  for(const query of cases){
    if(!isObj(query)||!nonempty(query.id)||!nonempty(query.text)||ids.has(query.id)||
      !isObj(query.rankings)||Object.keys(query.rankings).sort().join(",")!==[...methods].sort().join(","))
      throw Error("Mismatched pipeline or query provenance");
    ids.add(query.id);
    for(const key of methods){
      const list=query.rankings[key];
      if(!Array.isArray(list)||list.length<1||list.length>10)throw Error("Invalid ranked results");
      const docs=new Set<string>();
      for(const [i,row] of list.entries()){
        if(!isObj(row)||!nonempty(row.doc_id)||docs.has(row.doc_id)||row.rank!==i+1||
          typeof row.score!=="number"||!Number.isFinite(row.score))
          throw Error("Invalid or duplicated original score/rank");
        docs.add(row.doc_id);
      }
    }
  }
  if(!Array.isArray(value.limitations)||value.limitations.length<3||
    value.limitations.some(x=>!nonempty(x)))throw Error("Missing provenance limitations");
  return value as SavedReplay;
}
