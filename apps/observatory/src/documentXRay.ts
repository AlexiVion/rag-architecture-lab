/** Document-level explanation derived only from the verified fictional teaching corpus. */
import { rrfRanking } from "./playgroundData";
import type { PlaygroundDoc, Scenario } from "./playgroundData";

export type DocumentXRayData = {
  document: PlaygroundDoc;
  positions: { bm25: number; dense: number; hybrid: number; rerank: number };
  parts: { bm25: number; dense: number; total: number };
  movement: { hybridFromBm25: number; rerankFromHybrid: number };
};
export function getDocumentXRay(scene: Scenario, docId: string): DocumentXRayData {
  const document = scene.documents.find(d => d.id === docId);
  if (!document) throw new Error("Unknown document: " + docId);
  const bm25 = scene.rankings.bm25.indexOf(docId) + 1;
  const dense = scene.rankings.dense.indexOf(docId) + 1;
  const hybrid = rrfRanking(scene.rankings.bm25, scene.rankings.dense, 60).indexOf(docId) + 1;
  const rerank = scene.rankings.rerank.indexOf(docId) + 1;
  if ([bm25, dense, hybrid, rerank].some(position => position < 1)) {
    throw new Error("Incomplete document ranking: " + docId);
  }
  const first = 1 / (60 + bm25);
  const second = 1 / (60 + dense);
  return {
    document,
    positions: { bm25, dense, hybrid, rerank },
    parts: { bm25: first, dense: second, total: first + second },
    movement: { hybridFromBm25: bm25 - hybrid, rerankFromHybrid: hybrid - rerank },
  };
}
