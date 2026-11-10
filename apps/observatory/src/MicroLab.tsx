import { useEffect, useState } from "react";
import { loadMicroReplay } from "./microContracts";
import type { MicroReplay } from "./microContracts";

const REPO = "https://github.com/AlexiVion/rag-architecture-lab";
const STATUS_NOTE: Record<string, string> = {
  CONFLICT: "Two original documents disagree; no definitive value is published.",
  ANSWER: "The same structured literal value is present in the inspected sources.",
  INSUFFICIENT: "No source contains the requested field; no value is invented.",
  REVIEW: "The bounded source scan is incomplete; publication is blocked.",
};

export default function MicroLab() {
  const [replay, setReplay] = useState<MicroReplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  useEffect(() => {
    let alive = true;
    loadMicroReplay()
      .then((data) => { if (alive) setReplay(data); })
      .catch((err) => {
        if (alive) setError(err instanceof Error ? err.message : "Source verification failed");
      });
    return () => { alive = false; };
  }, []);

  const item = replay?.cases[selected];
  const byId = new Map(replay?.sources.map((s) => [s.id, s]) ?? []);
  return <>
    <header className="intro">
      <p className="eyebrow">MICRO-RAG v0.2 · CPU-FIRST EVIDENCE ENGINE</p>
      <h1>A system that knows when not to answer.</h1>
      <p>Inspect actual Python pipeline outcomes: exact original-source citations,
         conflicting facts, missing information and an incomplete evidence scan.
         The documents are invented. This page replays verified outputs; it does not run a live model.</p>
    </header>
    <div className="notice">
      <strong>Software demonstration, not scientific validation.</strong> The four cases are
      deterministic structured records. They do not prove open-domain source entailment,
      general NLI reliability or safe customer-facing QA.
    </div>
    {error ? <section className="error" role="alert">
      <strong>Verified replay unavailable.</strong><p>{error}</p>
      <p>No unverified factual output will be rendered.</p>
    </section> : !replay || !item ?
      <div className="loading" role="status">Verifying original document SHA256 and citations…</div> :
      <>
        <section className="micro-scenario-picker" aria-label="Select an executed RAG scenario">
          {replay.cases.map((candidate, index) =>
            <button key={candidate.id} type="button" aria-pressed={selected === index}
              onClick={() => setSelected(index)}>
              <small>CASE {String(index + 1).padStart(2, "0")}</small>
              <strong>{candidate.label}</strong>
              <span className={"micro-decision "+candidate.status.toLowerCase()}>
                {candidate.status}
              </span>
            </button>)}
        </section>
        <section className="panel" aria-label="Micro RAG decision">
          <header className="panel-head">
            <p className="eyebrow">ORIGINAL PYTHON PIPELINE OUTPUT · STATIC REPLAY</p>
            <h2>Why did the system make this decision?</h2>
          </header>
          <div className="panel-body">
            <p className="micro-question">{item.question}</p>
            <div className="micro-decision-summary">
              <span className={"micro-decision "+item.status.toLowerCase()}>{item.status}</span>
              <span>{STATUS_NOTE[item.status]}</span>
            </div>
            {item.answer !== null ?
              <p className="micro-answer">Verified literal value: <strong>{item.answer}</strong></p> :
              <p className="micro-answer no-answer">No answer published.</p>}
            <div className="micro-meta">
              <span>Original sources inspected: <strong>{item.inspected_doc_ids.length}</strong></span>
              <span>Candidate reader calls: <strong>{item.read_calls}</strong></span>
              <span>Full entity scan: <strong>{item.source_sweep_complete ? "Yes" : "No"}</strong></span>
              <span>Entity scan budget: <strong>{item.scan_budget}</strong></span>
            </div>
          </div>
        </section>
        <section className="panel" aria-label="Original cited sources">
          <header className="panel-head">
            <p className="eyebrow">VERBATIM SOURCE PROVENANCE</p>
            <h2>What the source records actually say</h2>
          </header>
          <div className="panel-body">
            <div className="micro-source-grid">
              {item.citations.length ? item.citations.map((citation, i) => {
                const source = byId.get(citation.doc_id);
                if (!source) return null;
                return <article className="micro-source" key={citation.doc_id+"-"+i}>
                  <p className="micro">{source.title} · {source.id}</p>
                  <blockquote>{citation.quote}</blockquote>
                  <p className="micro">Original offsets: {citation.start}–{citation.end}</p>
                  <details>
                    <summary>Inspect complete source and SHA256</summary>
                    <pre>{source.text}</pre>
                    <code>{source.sha256}</code>
                  </details>
                </article>;
              }) : <p className="micro">No cited value was found in the inspected documents.</p>}
            </div>
          </div>
        </section>
        <section className="panel" aria-label="Experiment boundaries">
          <header className="panel-head"><p className="eyebrow">REPRODUCIBILITY</p>
            <h2>The exact limits of this demonstration</h2></header>
          <div className="panel-body">
            <p className="micro">{replay.method}</p>
            <ul>{replay.limitations.map((limit, i) => <li key={i}>{limit}</li>)}</ul>
            <div className="doc-links">
              <a href={REPO+"/blob/main/scripts/micro/export_micro_v02_observatory.py"}
                target="_blank" rel="noreferrer">Reproduce this Python execution ↗</a>
              <a href={REPO+"/blob/main/docs/MICRO_V02_ONNX_RESULTS.md"}
                target="_blank" rel="noreferrer">Read real CPU quantization results ↗</a>
              <a href={REPO+"/issues/28"} target="_blank" rel="noreferrer">
                See open scientific reliability gates ↗</a>
            </div>
          </div>
        </section>
      </>}
  </>;
}
