import { getDocumentXRay } from "./documentXRay";
import { rankingAtStep } from "./playgroundData";
import type { ArchitectureId, Scenario } from "./playgroundData";

export type Explanation = "simple" | "technical" | "scientific";
type Props = {
  scene: Scenario;
  docId: string;
  left: ArchitectureId;
  right: ArchitectureId;
  step: number;
  explanation: Explanation;
  onClose: () => void;
};
const movement = (delta: number) => delta === 0
  ? "No change"
  : delta > 0 ? "↑ " + delta + (delta === 1 ? " place" : " places")
  : "↓ " + Math.abs(delta) + (delta === -1 ? " place" : " places");

export default function DocumentXRay({ scene, docId, left, right, step, explanation, onClose }: Props) {
  const result = getDocumentXRay(scene, docId);
  const { document, positions, parts } = result;
  const leftRank = rankingAtStep(scene, left, step).indexOf(docId) + 1;
  const rightRank = rankingAtStep(scene, right, step).indexOf(docId) + 1;
  const stages = [
    { name: "BM25", rank: positions.bm25, source: "Authored word-search list", status: "Example" },
    { name: "Dense", rank: positions.dense, source: "Authored meaning-search list", status: "Example" },
    { name: "Hybrid RRF", rank: positions.hybrid, source: "Computed from both example lists", status: "Calculated" },
    { name: "Scripted reranking", rank: positions.rerank, source: "Authored reorder; no model ran", status: "Example" },
  ];
  return <section id="document-xray" className="ap-xray" role="region" aria-label="Document X-Ray">
    <div className="ap-xray-heading">
      <div>
        <p className="ap-small">DOCUMENT X-RAY · ILLUSTRATIVE DOCUMENT</p>
        <h3>{document.title}</h3>
        <p>{document.summary}</p>
      </div>
      <button type="button" className="ap-xray-close" aria-label="Close inspection" onClick={onClose}>Close <span aria-hidden="true">×</span></button>
    </div>
    <div className="ap-xray-relevance">
      <span className={document.relevant ? "ap-xray-status helpful" : "ap-xray-status"}>{document.relevant ? "Marked relevant" : "Marked not relevant"}</span>
      <span>Label assigned for this fictional teaching question.</span>
    </div>
    <div className="ap-xray-journey" aria-label="Document rank across four architecture stages">
      {stages.map((stage,index) => <div key={stage.name} className="ap-xray-stop">
        <div className="ap-xray-stop-index">0{index+1} <span aria-hidden="true">→</span></div>
        <h4>{stage.name}</h4>
        <div className="ap-xray-position">#{stage.rank}</div>
        <small>{stage.source}</small>
        <span className={stage.status === "Calculated" ? "ap-xray-tag computed" : "ap-xray-tag"}>{stage.status}</span>
      </div>)}
    </div>
    <div className="ap-xray-current" aria-live="polite">
      <strong>At stage {step+1} of 5</strong>
      <span>Left: #{leftRank}</span>
      <span>Right: #{rightRank}</span>
      <span className="ap-xray-movement">Hybrid versus BM25: {movement(result.movement.hybridFromBm25)}</span>
    </div>
    <div className="ap-xray-explain">
      <div className="ap-xray-meaning">
        {explanation === "simple" && <p>Think of two friends voting for the most useful clue. The word-based list puts this document at <strong>#{positions.bm25}</strong>, the meaning-based list at <strong>#{positions.dense}</strong>. Combining their positions puts it at <strong>#{positions.hybrid}</strong>. This is a fictional example, not a live AI search.</p>}
        {explanation === "technical" && <p>RRF combines two position-based terms with <code>k=60</code>. Each authored rank contributes <code>1/(k+rank)</code>; higher combined scores yield a new sorted order. This document moves {movement(result.movement.hybridFromBm25).toLowerCase()} relative to the authored BM25 order.</p>}
        {explanation === "scientific" && <p>No BM25 term weights, embedding similarity or cross-encoder scores were measured. BM25, Dense and reranking positions are manually authored. The RRF score and Hybrid position alone are deterministically calculated from the fictional input lists.</p>}
      </div>
      <div className="ap-xray-equation">
        <p className="ap-small">RRF ARITHMETIC · K=60</p>
        <div className="ap-xray-fractions">
          <code>1 / (60 + {positions.bm25})</code>
          <span>+</span>
          <code>1 / (60 + {positions.dense})</code>
        </div>
        <div className="ap-xray-values">
          <span>{parts.bm25.toFixed(6)}</span><span>+</span><span>{parts.dense.toFixed(6)}</span>
        </div>
        <div className="ap-xray-total"><span>Calculated combined score</span><strong>{parts.total.toFixed(6)}</strong></div>
        <p>Exact reciprocal-rank arithmetic on authored positions, not a model confidence score.</p>
      </div>
    </div>
    <p className="ap-xray-disclaimer"><strong>Author-created ranks are not SciFact measurements.</strong> The original empirical study results remain in the separate measured comparison below. This inspection explains deterministic ranking and does not establish factual QA quality.</p>
  </section>;
}
