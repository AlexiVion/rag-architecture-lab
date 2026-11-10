import { useEffect, useState } from "react";
import SavedBenchmarkReplay from "./SavedBenchmarkReplay";
import { loadRepoReplay } from "./repoReplay";
import type { RepoReplay, ReplayQuery, ReplayDoc, ReplayRank } from "./repoReplay";

const METHODS=[
  {key:"bm25" as const,name:"BM25",note:"Rank full research documents by lexical overlap"},
  {key:"parent_child_bm25" as const,name:"Parent–Child BM25",note:"Search 480-character passages, then return parent documents"},
];
function Lane({q,docs,method,chosen,onChoose}:{q:ReplayQuery;docs:Map<string,ReplayDoc>;method:typeof METHODS[number];chosen:string|null;onChoose:(id:string)=>void}) {
  const other=method.key==="bm25"?"parent_child_bm25":"bm25";
  const opposite=new Map(q.rankings[other].map(x=>[x.doc_id,x.rank]));
  return <div className="rr-lane">
    <div className="rr-lane-head"><h4>{method.name}</h4><p>{method.note}</p></div>
    <ol className="rr-ranked">
      {q.rankings[method.key].map((item:ReplayRank)=>{
        const doc=docs.get(item.doc_id)!;
        const position=opposite.get(item.doc_id);
        const movement=position===undefined?"Outside other top 5":position===item.rank?"Same position":position>item.rank?"Higher here by "+(position-item.rank):"Lower here by "+(item.rank-position);
        return <li key={item.doc_id}>
          <button type="button" aria-pressed={chosen===item.doc_id} onClick={()=>onChoose(item.doc_id)}
            className={"rr-entry"+(chosen===item.doc_id?" selected":"")}>
            <span className="rr-rank">{String(item.rank).padStart(2,"0")}</span>
            <span className="rr-entry-name"><strong>{doc.title}</strong><small>{movement}</small></span>
            <span className="rr-score" title="Method-specific raw score; not comparable across methods">{item.score.toFixed(3)}</span>
          </button>
        </li>;
      })}
    </ol>
  </div>;
}

export default function RealRetrievalReplay(){
  const [data,setData]=useState<RepoReplay|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [qid,setQid]=useState("q01");
  const [docId,setDocId]=useState<string|null>(null);
  useEffect(()=>{
    let active=true;
    loadRepoReplay().then(v=>{if(active)setData(v);})
      .catch(e=>{if(active)setError(e instanceof Error?e.message:"Real trace could not be validated");});
    return()=>{active=false;};
  },[]);
  const query=data?.queries.find(x=>x.id===qid)??data?.queries[0];
  const docs=new Map(data?.documents.map(d=>[d.id,d])??[]);
  const selected=docId?docs.get(docId):null;
  const common=query?query.rankings.bm25.filter(x=>query.rankings.parent_child_bm25.some(y=>y.doc_id===x.doc_id)).length:0;
  return <section id="real-retrieval-replay" className="rr-section" aria-labelledby="rr-title">
    <div className="section-intro">
      <p className="overline">ENGINEERING REPLAY / ACTUAL PYTHON RETRIEVAL</p>
      <h2 id="rr-title">Real documents. Real retrieval.</h2>
      <p>Two implemented retrievers search the same eight versioned research documents. Explore the original rank lists, not a simulated document race.</p>
    </div>
    {error?<div className="demo-error" role="alert"><strong>Trace unavailable or unverifiable.</strong><p>{error}</p><p>No invented fallback is displayed.</p></div>:
    !data||!query?<p className="loading" role="status">Checking archived Python execution…</p>:
    <div className="rr-workspace">
      <div className="rr-chooser">
        <label htmlFor="rr-question">Choose a recorded question</label>
        <select id="rr-question" value={query.id} onChange={e=>{setQid(e.target.value);setDocId(null);}}>
          {data.queries.map(q=><option value={q.id} key={q.id}>{q.text}</option>)}
        </select>
        <p><strong>{common}/5</strong> documents shared by both top-five lists. This does not establish retrieval quality.</p>
      </div>
      <div className="rr-grid">
        {METHODS.map(m=><Lane key={m.key} q={query} docs={docs} method={m} chosen={docId} onChoose={setDocId}/>)}
      </div>
      {selected&&<div className="rr-detail" role="region" aria-label="Original document provenance">
        <div><p className="ap-small">DOCUMENT PROVENANCE</p><h4>{selected.title}</h4><code>SHA256: {selected.sha256}</code></div>
        <a href={selected.url} target="_blank" rel="noreferrer">Read original source ↗</a>
        <button type="button" onClick={()=>setDocId(null)}>Close inspection</button>
      </div>}
      <div className="rr-notice">
        <strong>Actual code execution ≠ validated scientific finding.</strong>
        <p>The three queries are authored, with no human qrels and no factual-answer evaluation. Ranking scores use different units across methods. This is not a rerun of V0/V1 SciFact, and no neural model ran.</p>
        <a href="https://github.com/AlexiVion/rag-architecture-lab/blob/main/docs/REPOSITORY_RETRIEVAL_REPLAY.md" target="_blank" rel="noreferrer">Reproduce the Python trace ↗</a>
      </div>
    </div>}
    <SavedBenchmarkReplay />
  </section>;
}
