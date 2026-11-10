import { describe, expect, it } from "vitest";
import input from "../../../experiments/architecture_playground_illustrative.json";
import { validatePlayground, rrfRanking, rankingAtStep, PLAYGROUND_STUDIES } from "./playgroundData";

describe("Architecture Playground data integrity", () => {
  it("accepts exactly three complete illustrative scenarios and five documents each", () => {
    const data = validatePlayground(input);
    expect(data.scenarios).toHaveLength(3);
    expect(data.scenarios.every((scenario) => scenario.documents.length === 5)).toBe(true);
    expect(data.status).toBe("FICTIONAL_RANKINGS_NOT_MEASURED");
  });
  it("rejects measured/real-run claims on authored rankings", () => {
    expect(() => validatePlayground({...input, status:"REAL_SCIFACT_RANKINGS"})).toThrow();
    expect(() => validatePlayground({...input, measured:true})).toThrow();
  });
  it("rejects duplicate IDs and incomplete permutations", () => {
    const scene = input.scenarios[0]!;
    expect(() => validatePlayground({...input, scenarios: [
      {...scene, documents:[scene.documents[0],scene.documents[0],...scene.documents.slice(2)]}, ...input.scenarios.slice(1)
    ]})).toThrow();
    expect(() => validatePlayground({...input, scenarios: [
      {...scene, rankings:{...scene.rankings, bm25:[...scene.rankings.bm25.slice(0,4), "unknown"]}}, ...input.scenarios.slice(1)
    ]})).toThrow();
  });
  it("checks that relevance flags are illustrative booleans", () => {
    const scene = input.scenarios[0]!;
    expect(() => validatePlayground({...input, scenarios: [
      {...scene, documents:[{...scene.documents[0],relevant:"YES"},...scene.documents.slice(1)]}, ...input.scenarios.slice(1)
    ]})).toThrow();
  });
  it("computes canonical reciprocal rank fusion without invented measurements", () => {
    const scene = validatePlayground(input).scenarios[0]!;
    const hybrid = rrfRanking(scene.rankings.bm25,scene.rankings.dense,60);
    expect(hybrid[0]).toBe("p1");
    expect([...hybrid].sort()).toEqual(scene.rankings.bm25.slice().sort());
    expect(() => rrfRanking(["d1","d1"],["d2","d1"])).toThrow();
  });
  it("preserves BM25 → hybrid → illustrative rerank stage semantics", () => {
    const scene = validatePlayground(input).scenarios[0]!;
    expect(rankingAtStep(scene,"bm25",1)).toEqual(scene.rankings.bm25);
    expect(rankingAtStep(scene,"hybrid",1)).toEqual(scene.rankings.bm25);
    expect(rankingAtStep(scene,"hybrid",2)).toEqual(rrfRanking(scene.rankings.bm25,scene.rankings.dense));
    expect(rankingAtStep(scene,"rerank",2)).toEqual(rrfRanking(scene.rankings.bm25,scene.rankings.dense));
    expect(rankingAtStep(scene,"rerank",3)).toEqual(scene.rankings.rerank);
    expect(rankingAtStep(scene,"hybrid",4)).toEqual(rrfRanking(scene.rankings.bm25,scene.rankings.dense));
    expect(() => rankingAtStep(scene,"hybrid",5)).toThrow();
  });
  it("keeps V0 and V1 performance on separate declared hardware", () => {
    expect(PLAYGROUND_STUDIES).toHaveLength(2);
    expect(PLAYGROUND_STUDIES[0]!.id).toBe("v0");
    expect(PLAYGROUND_STUDIES[1]!.id).toBe("v1");
    expect(PLAYGROUND_STUDIES[0]!.points.find((p) => p.id==="bm25")?.mrr10).toBe(.6328);
    expect(PLAYGROUND_STUDIES[1]!.points.find((p) => p.id==="rerank")?.latencyMs).toBe(3706.43);
    expect(PLAYGROUND_STUDIES.every((study) => study.report.startsWith("https://github.com/"))).toBe(true);
  });
});

import { getDocumentXRay } from "./xrayRankMath";

describe("Document X-Ray fidelity to authored teaching rankings", () => {
  it("returns actual authored positions and deterministic RRF contributions for the roots example", () => {
    const s=validatePlayground(input).scenarios[0]!;
    const item=getDocumentXRay(s,"p1");
    expect(item.document.id).toBe("p1");
    expect(item.positions).toEqual({bm25:2,dense:1,hybrid:1,rerank:1});
    expect(item.parts.bm25).toBeCloseTo(1/62,12);
    expect(item.parts.dense).toBeCloseTo(1/61,12);
    expect(item.parts.total).toBeCloseTo(1/62+1/61,12);
    expect(item.movement.hybridFromBm25).toBe(1);
    expect(item.movement.rerankFromHybrid).toBe(0);
  });
  it("refuses unknown documents without fabricating a result", () => {
    const s=validatePlayground(input).scenarios[0]!;
    expect(() => getDocumentXRay(s,"unlisted")).toThrow(/unknown document/i);
  });
  it("keeps all three scenarios consistent with RRF and their authored reranking", () => {
    for(const scene of validatePlayground(input).scenarios){
      const ranks=rrfRanking(scene.rankings.bm25,scene.rankings.dense);
      for(const document of scene.documents){
        const view=getDocumentXRay(scene,document.id);
        expect(view.positions.bm25).toBe(scene.rankings.bm25.indexOf(document.id)+1);
        expect(view.positions.dense).toBe(scene.rankings.dense.indexOf(document.id)+1);
        expect(view.positions.hybrid).toBe(ranks.indexOf(document.id)+1);
        expect(view.positions.rerank).toBe(scene.rankings.rerank.indexOf(document.id)+1);
        expect(view.parts.total).toBeCloseTo(view.parts.bm25+view.parts.dense,12);
      }
    }
  });
});
