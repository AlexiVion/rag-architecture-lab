import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import {
  loadPlayground, rankingAtStep, PLAYGROUND_STUDIES,
} from "./playgroundData";
import type {
  ArchitectureId, PlaygroundArtifact, PlaygroundDoc, Scenario, Study,
} from "./playgroundData";

type Explanation = "simple" | "technical" | "scientific";
const ARCHITECTURES: { id: ArchitectureId; name: string; note: string }[] = [
  { id: "bm25", name: "BM25", note: "Word matching" },
  { id: "hybrid", name: "Hybrid RRF", note: "Words + meaning" },
  { id: "rerank", name: "Hybrid + Reranking", note: "Extra ordering step" },
];
const STAGES = ["Question", "Search", "Combine", "Refine", "Compare"];
const LEVEL_TEXT: Record<Explanation, string> = {
  simple: "These are two ways to look for useful clues. Watch how a helpful document can move higher when the method changes.",
  technical: "BM25 orders matches by lexical signals. Hybrid combines two ranked lists by reciprocal rank fusion (RRF, k=60). The final reranking order is a scripted illustration, not a cross-encoder prediction.",
  scientific: "Document ranks and relevance tags in this interaction are authored examples, not empirical per-query SciFact measurements. Separately, the quality/latency panel uses published aggregate V0 and V1 results within each run's original hardware environment.",
};
const STAGE_NOTES: Record<ArchitectureId, string[]> = {
  bm25: [
    "This method receives the question.",
    "A lexical retriever orders documents by matching terms.",
    "Only the BM25 list is retained; there is no dense fusion.",
    "No cross-encoder is applied.",
    "Read the final word-matching order.",
  ],
  hybrid: [
    "This method receives the same question.",
    "BM25 retrieves candidates; a dense search provides a second list.",
    "Reciprocal Rank Fusion combines the two lists using their positions.",
    "This architecture does not add a second-stage reranker.",
    "Read the final fusion-based order.",
  ],
  rerank: [
    "This method receives the same question.",
    "BM25 and dense search provide candidate lists.",
    "Reciprocal Rank Fusion produces a combined list.",
    "A manually scripted reordering illustrates a possible cross-encoder stage.",
    "Read the illustrative order after the second stage.",
  ]
};
function fmt(v:number):string {
  return v.toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
}

function RankLane({ scene, method, step, side }: {
  scene:Scenario; method:ArchitectureId; step:number; side:"Left"|"Right";
}) {
  const order=rankingAtStep(scene,method,step);
  const index=new Map(order.map((id,i)=>[id,i]));
  const baseline=new Map(scene.rankings.bm25.map((id,i)=>[id,i]));
  const found=ARCHITECTURES.find(arch=>arch.id===method)!;
  const topDoc=scene.documents.find(doc=>doc.id===order[0])!;
  const showRanking=step>=1;
  return <section className="ap-lane" aria-label={side+" ranking"}>
    <div className="ap-lane-top">
      <div><span className="ap-small">{side.toUpperCase()} ARCHITECTURE</span>
        <h3>{found.name}</h3><p>{found.note}</p>
      </div>
      <span className="ap-lane-method">{STAGES[step]}</span>
    </div>
    <p className="ap-stage-note">{STAGE_NOTES[method][step]}</p>
    <div className="ap-doc-area">
      {showRanking ? <>
        <p className="ap-list-caption">DOCUMENT ORDER · ILLUSTRATIVE</p>
        <div className="ap-rank-list" role="list" aria-label={side+" illustrative ordered documents"}>
          {scene.documents.map((doc:PlaygroundDoc)=>{
            const position=index.get(doc.id)!;
            const difference=baseline.get(doc.id)!-position;
            const change=step<2 || difference===0 ? "—" : difference>0 ? "↑ "+difference : "↓ "+Math.abs(difference);
            return <div key={doc.id} className={"ap-rank-card"+(doc.relevant?" is-relevant":"")}
              role="listitem" aria-label={"Rank "+(position+1)+": "+doc.title+(doc.relevant?", illustrative relevant document":"")}
              style={{top:(position*69)+"px"} as CSSProperties}>
              <span className="ap-rank-number">{String(position+1).padStart(2,"0")}</span>
              <div className="ap-rank-text"><strong>{doc.title}</strong><small>{doc.summary}</small></div>
              <span className={"ap-rank-shift"+(difference>0&&step>=2?" positive":"")} title="Movement from the BM25 baseline">{change}</span>
            </div>;
          })}
        </div>
        <p className="ap-top-document" aria-live="polite">First: <strong>{topDoc.title}</strong>{topDoc.relevant?" · marked helpful in this example":""}</p>
      </> : <div className="ap-await">
        <span className="ap-await-mark" aria-hidden="true">?</span>
        <p>Both architectures start with the same question.</p>
        <span>Press Step or Play to reveal the document order.</span>
      </div>}
    </div>
  </section>;
}

function StudyPlot({ study }: {study:Study}) {
  const [chosen, setChosen]=useState(study.points[0]!.id);
  useEffect(()=>setChosen(study.points[0]!.id),[study]);
  const logs=study.points.map(p=>Math.log10(p.latencyMs));
  const logMin=Math.min(...logs)-.16,logMax=Math.max(...logs)+.16;
  const x=(ms:number)=>86+(Math.log10(ms)-logMin)/(logMax-logMin)*500;
  const y=(mrr:number)=>213-(mrr-.585)/(.675-.585)*170;
  const point=study.points.find(p=>p.id===chosen)??study.points[0]!;
  return <div className="ap-study">
    <div className="ap-study-chart" role="group" aria-label="Measured MRR@10 against mean query latency within the selected experiment">
      <svg viewBox="0 0 660 265" role="img" aria-label={"Measured quality versus latency for "+study.name} preserveAspectRatio="xMidYMid meet">
        <line x1="85" y1="28" x2="85" y2="214" className="ap-axis"/>
        <line x1="85" y1="214" x2="612" y2="214" className="ap-axis"/>
        {[.60,.63,.66].map(m=><g key={m}>
          <line x1="85" y1={y(m)} x2="612" y2={y(m)} className="ap-grid-line"/>
          <text x="74" y={y(m)+4} textAnchor="end" className="ap-axis-tick">{m.toFixed(2)}</text>
        </g>)}
        <text x="88" y="16" className="ap-axis-title">MRR@10 · higher is better ↑</text>
        <text x="350" y="253" textAnchor="middle" className="ap-axis-title">Mean query time (ms, log scale) →</text>
        {study.points.map(p=><g key={p.id} onClick={()=>setChosen(p.id)} className="ap-svg-point">
          <title>{p.name+": MRR@10 "+p.mrr10.toFixed(4)+", mean "+fmt(p.latencyMs)+" ms"}</title>
          <circle cx={x(p.latencyMs)} cy={y(p.mrr10)} r={p.id===point.id?11:8} className={"ap-plot-point"+(p.id===point.id?" chosen":"")}/>
          <text x={x(p.latencyMs)} y={y(p.mrr10)-17} textAnchor="middle" className="ap-point-label">{p.name}</text>
        </g>)}
      </svg>
      <p className="ap-chart-note">Each point is a recorded aggregate measurement, not an animated example.</p>
    </div>
    <div className="ap-study-points" role="group" aria-label="Choose a measured point">
      {study.points.map(p=><button type="button" key={p.id} className={"ap-study-point"+(p.id===point.id?" active":"")}
        aria-pressed={p.id===point.id} onClick={()=>setChosen(p.id)}>
        <span>{p.name}</span><strong>{p.mrr10.toFixed(4)}</strong><small>{fmt(p.latencyMs)} ms</small>
      </button>)}
      <p aria-live="polite" className="ap-study-description">
        Selected: <strong>{point.name}</strong> · MRR@10 {point.mrr10.toFixed(4)} on the original study cohort.
      </p>
    </div>
  </div>;
}

export default function ArchitecturePlayground() {
  const [corpus,setCorpus]=useState<PlaygroundArtifact|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [scenarioId,setScenarioId]=useState("plants");
  const [left,setLeft]=useState<ArchitectureId>("bm25");
  const [right,setRight]=useState<ArchitectureId>("hybrid");
  const [step,setStep]=useState(0);
  const [playing,setPlaying]=useState(false);
  const [explanation,setExplanation]=useState<Explanation>("simple");
  const [studyId,setStudyId]=useState<Study["id"]>("v0");

  useEffect(()=>{
    let alive=true;
    loadPlayground().then(d=>{if(alive)setCorpus(d);})
      .catch(e=>{if(alive)setError(e instanceof Error?e.message:"Illustrative source verification failed");});
    return()=>{alive=false;};
  },[]);

  useEffect(()=>{
    if(!playing)return;
    if(step>=4){setPlaying(false);return;}
    const timer=window.setTimeout(()=>setStep(current=>Math.min(current+1,4)),900);
    return()=>window.clearTimeout(timer);
  },[playing,step]);

  const scenario=corpus?.scenarios.find(s=>s.id===scenarioId)??corpus?.scenarios[0];
  const study=PLAYGROUND_STUDIES.find(s=>s.id===studyId)!;
  function reset(){setPlaying(false);setStep(0);}
  function changeLeft(value:ArchitectureId){
    if(value===right)setRight(left);
    setLeft(value);reset();
  }
  function changeRight(value:ArchitectureId){
    if(value===left)setLeft(right);
    setRight(value);reset();
  }
  return <section id="architecture-playground" className="ap-section" aria-labelledby="ap-heading">
    <header className="section-intro">
      <p className="overline">01 / COMPARE RETRIEVAL METHODS</p>
      <h2 id="ap-heading">Architecture Playground</h2>
      <p>One question. Two ways to find evidence. Watch how documents move when the retrieval architecture changes.</p>
    </header>
    {error ? <div role="alert" className="demo-error"><strong>Teaching source data unavailable.</strong><p>{error}</p><p>No unverified rankings will be shown.</p></div>
    : !scenario ? <p className="loading" role="status">Validating illustrative teaching records…</p>
    : <>
      <div className="ap-frame" role="region" aria-label="Educational architecture comparison">
        <div className="ap-controls">
          <label className="ap-form-control ap-question-control">Teaching question
            <select aria-label="Teaching question" value={scenario.id} onChange={e=>{setScenarioId(e.target.value);reset();}}>
              {corpus!.scenarios.map(s=><option key={s.id} value={s.id}>{s.question}</option>)}
            </select>
          </label>
          <div className="ap-method-controls">
            <label className="ap-form-control">Left architecture
              <select aria-label="Left architecture" value={left} onChange={e=>changeLeft(e.target.value as ArchitectureId)}>
                {ARCHITECTURES.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </label>
            <span className="ap-versus" aria-hidden="true">vs</span>
            <label className="ap-form-control">Right architecture
              <select aria-label="Right architecture" value={right} onChange={e=>changeRight(e.target.value as ArchitectureId)}>
                {ARCHITECTURES.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </label>
          </div>
        </div>
        <p className="ap-selected-question"><span>THE SAME QUESTION FOR BOTH METHODS</span><strong>{scenario.question}</strong></p>
        <div className="ap-transport">
          <div>
            <p className="ap-step-status" role="status" aria-live="polite">Stage {step+1} of 5 <span>· {STAGES[step]}</span></p>
            <div className="ap-progress" aria-hidden="true">{STAGES.map((s,i)=><span key={s} className={i<=step?"current":""}/>)}</div>
          </div>
          <div className="ap-actions">
            <button type="button" className="ap-play" onClick={()=>{
              if(playing){setPlaying(false);}else{if(step===4)setStep(0);setPlaying(true);}
            }}>{playing?"Pause":"Play"}</button>
            <button type="button" onClick={()=>{setPlaying(false);setStep(s=>Math.min(4,s+1));}} disabled={step===4}>Step</button>
            <button type="button" onClick={reset}>Reset</button>
          </div>
        </div>
        <div className="ap-lanes">
          <RankLane scene={scenario} method={left} step={step} side="Left"/>
          <RankLane scene={scenario} method={right} step={step} side="Right"/>
        </div>
        <div className="ap-legend">
          <span><i className="ap-legend-square" aria-hidden="true"/> Helpful for the teaching question</span>
          <span>↑ / ↓ = change from the BM25 example ranking</span>
        </div>
      </div>
      <p className="ap-disclosure"><strong>Illustrative rankings, not SciFact outputs.</strong> These are fictional teaching documents with authored word-search, dense-search and scripted reranker orders. Hybrid RRF is computed from those two example lists using k=60. No live models are running.</p>
      <div className="ap-explanation">
        <fieldset className="ap-levels" aria-label="Explanation level">
          <legend>EXPLANATION</legend>
          {(["simple","technical","scientific"] as const).map(level=><label key={level} className={explanation===level?"selected":""}>
            <input type="radio" name="ap-level" value={level} checked={explanation===level} onChange={()=>setExplanation(level)}/>
            {level[0]!.toUpperCase()+level.slice(1)}
          </label>)}
        </fieldset>
        <p className="ap-level-text">{LEVEL_TEXT[explanation]}</p>
      </div>
    </>}
    <div className="ap-measured" aria-labelledby="ap-measured-title">
      <div className="section-intro">
        <p className="overline">MEASURED RESEARCH · SEPARATE FROM THE ANIMATION</p>
        <h3 id="ap-measured-title">What did the real experiments measure?</h3>
        <p>Compare aggregate retrieval quality and mean query latency within one benchmark run. Different hardware measurements are never mixed on the same plot.</p>
      </div>
      <label className="ap-form-control ap-study-select">Recorded study
        <select value={studyId} aria-label="Recorded study" onChange={e=>setStudyId(e.target.value as Study["id"])}>
          {PLAYGROUND_STUDIES.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </label>
      <p className="ap-study-env"><strong>{study.cohort}</strong><span>{study.environment}</span></p>
      <StudyPlot study={study}/>
      <p className="ap-study-footer">MRR@10 measures ranking of relevant retrieved documents, <strong>not answer correctness</strong>. Indexing time is excluded from these query latencies. <a href={study.report} target="_blank" rel="noreferrer">Read the original measurements ↗</a></p>
    </div>
  </section>;
}
