import { useEffect, useState } from "react";
import { loadMicroReplay } from "./microContracts";
import type { MicroCase, MicroDecision, MicroReplay } from "./microContracts";

const meanings: Record<MicroDecision, { label: string; explanation: string }> = {
  CONFLICT: {
    label: "Two sources disagree.",
    explanation: "Different original documents give incompatible literal values. The system refuses to select one.",
  },
  ANSWER: {
    label: "The sources agree.",
    explanation: "The inspected structured records contain the same value, so the pipeline returns it with exact quotations.",
  },
  INSUFFICIENT: {
    label: "The information is missing.",
    explanation: "A completed structured-source check found no supported value. The system does not invent one.",
  },
  REVIEW: {
    label: "Not enough evidence was inspected.",
    explanation: "The source scan stopped before covering every relevant record, so the system requires review.",
  },
};

export default function ResearchDemo() {
  const [replay, setReplay] = useState<MicroReplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    let active = true;
    loadMicroReplay()
      .then((value) => { if (active) setReplay(value); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "The research artifact could not be verified");
      });
    return () => { active = false; };
  }, []);

  const current: MicroCase | undefined = replay?.cases[selected];
  const description = current ? meanings[current.status] : null;
  const sourceIndex = new Map(replay?.sources.map((s) => [s.id, s]) ?? []);

  return (
    <section className="demonstration" id="demonstration" aria-labelledby="demo-title">
      <div className="section-intro">
        <p className="overline">02 / A reproducible software example</p>
        <h2 id="demo-title">What happens when evidence disagrees?</h2>
        <p>Explore the actual decisions of the experimental Python pipeline using four small, fictional sets of structured source records.</p>
      </div>
      {error ? (
        <div role="alert" className="demo-error">
          <strong>Verified evidence is unavailable.</strong>
          <p>{error}</p>
          <p>No unverified result is displayed.</p>
        </div>
      ) : !replay || !current || !description ? (
        <p className="loading" role="status">Verifying source documents and SHA256 signatures…</p>
      ) : (
        <div className="demo-shell">
          <div className="case-selector" role="group" aria-label="Choose an evidence scenario">
            {replay.cases.map((item, i) => (
              <button
                type="button"
                key={item.id}
                className={i === selected ? "case-button active" : "case-button"}
                aria-pressed={i === selected}
                onClick={() => setSelected(i)}
              >
                <span className="case-index">0{i + 1}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
          <div className="demo-content">
            <div className="question-block">
              <p className="detail-label">QUESTION</p>
              <h3>{current.question}</h3>
            </div>
            <div className="source-grid" aria-label="Original inspected evidence">
              {current.citations.length ? current.citations.map((citation, i) => {
                const source = sourceIndex.get(citation.doc_id);
                return (
                  <div className="source-box" key={citation.doc_id + "-" + i}>
                    <p className="detail-label">SOURCE {i + 1}</p>
                    <strong className="source-quote">“{citation.quote}”</strong>
                    <p className="source-name">{source?.title ?? citation.doc_id}</p>
                    <details className="technical-details">
                      <summary>Verify source</summary>
                      <code>{citation.doc_id} · offsets {citation.start}–{citation.end}</code>
                      <code>SHA256: {citation.document_sha256}</code>
                      {source && <p>{source.text}</p>}
                    </details>
                  </div>
                );
              }) : (
                <div className="empty-source">
                  <strong>No cited value found</strong>
                  <p>The inspected sources did not contain the requested structured value.</p>
                </div>
              )}
            </div>
            <div className={"decision-box " + current.status.toLowerCase()} role="region" aria-label="Recorded pipeline decision">
              <div>
                <span className="detail-label">RECORDED DECISION</span>
                <span className={"decision-tag " + current.status.toLowerCase()}>{current.status}</span>
              </div>
              <h3>{description.label}</h3>
              <p>{description.explanation}</p>
              {current.answer && <p className="answer-value">Returned literal value: <strong>{current.answer}</strong></p>}
              {!current.answer && <p className="no-answer">No definitive answer published.</p>}
              <details className="technical-details">
                <summary>See execution details</summary>
                <p>Sources inspected: {current.inspected_doc_ids.length}. Reader calls: {current.read_calls}. Complete source scan: {current.source_sweep_complete ? "yes" : "no"}.</p>
                {current.warnings.map((warning) => <p key={warning}>{warning}</p>)}
              </details>
            </div>
          </div>
        </div>
      )}
      <p className="demo-disclaimer">
        <strong>Scope:</strong> a prerecorded, hash-verified execution of an actual Python pipeline using fictional structured data. Not live inference, semantic entailment or validated open-domain RAG.
      </p>
    </section>
  );
}
