import archived from "../../../experiments/repo_retrieval_replay.json";
import {describe,expect,it} from "vitest";
import {validateRepoReplay} from "./repoReplay";
describe("actual source-backed repository replay",()=>{
  it("accepts the original Python execution without asserting quality",()=>{
    const replay=validateRepoReplay(archived);
    expect(replay.queries).toHaveLength(3);
    expect(replay.documents).toHaveLength(8);
    expect(replay.queries[0]!.rankings.bm25[0]!.doc_id).toBe("benchmarks/V0_RESULTS.md");
    expect(replay.queries[0]!.qrels).toBeNull();
  });
  it("rejects invented relevance labels, source hashes and ranks",()=>{
    expect(()=>validateRepoReplay({...archived,status:"SciFact_evaluated"})).toThrow();
    expect(()=>validateRepoReplay({...archived,queries:[{...archived.queries[0],qrels:{"README.md":1}},...archived.queries.slice(1)]})).toThrow();
    expect(()=>validateRepoReplay({...archived,documents:[{...archived.documents[0],sha256:"fake"},...archived.documents.slice(1)]})).toThrow();
    const item=archived.queries[0]!;
    expect(()=>validateRepoReplay({...archived,queries:[{...item,rankings:{...item.rankings,bm25:[{...item.rankings.bm25[0],rank:5},...item.rankings.bm25.slice(1)]}},...archived.queries.slice(1)]})).toThrow();
    expect(()=>validateRepoReplay({...archived,accuracy:1})).toThrow();
  });
});
