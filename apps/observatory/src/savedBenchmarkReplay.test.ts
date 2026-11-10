import {describe,expect,it} from "vitest";
import {validateSavedReplay} from "./savedBenchmarkReplay";
const base={
  schema_version:1,kind:"saved_benchmark_query_replay",status:"archived_original_per_query_not_independently_revalidated",
  dataset:"beir/scifact/test",source_archive_sha256:"a".repeat(64),document_count:5183,
  pipeline_names:["bm25","hybrid"],query_selection:"first_N_original_order_without_qrel_selection",
  source_environment:{python:"3.11",platform:"local"},
  queries:[{id:"1",text:"A real question",rankings:{
    bm25:[{doc_id:"a",rank:1,score:1.2}],
    hybrid:[{doc_id:"b",rank:1,score:.02}],
  }}],limitations:["Original archive, not rerun","No new model execution","No independent validation"]
};
describe("saved local benchmark replay",()=>{
  it("accepts matched original score/position records",()=>{
    expect(validateSavedReplay(base).queries[0]!.rankings.bm25[0]!.doc_id).toBe("a");
  });
  it("rejects mismatched scores, claimed validation and changed method cohorts",()=>{
    expect(()=>validateSavedReplay({...base,status:"scientifically_validated"})).toThrow();
    expect(()=>validateSavedReplay({...base,source_archive_sha256:"?"})).toThrow();
    expect(()=>validateSavedReplay({...base,pipeline_names:["bm25","dense"]})).toThrow();
    const q=base.queries[0]!;
    expect(()=>validateSavedReplay({...base,queries:[{...q,rankings:{...q.rankings,bm25:[{doc_id:"a",rank:2,score:1}]}}]})).toThrow();
    expect(()=>validateSavedReplay({...base,accuracy:1})).toThrow();
  });
});
