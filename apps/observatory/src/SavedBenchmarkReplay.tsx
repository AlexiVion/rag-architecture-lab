import { useState } from "react";
import { validateSavedReplay } from "./savedBenchmarkContract";
import type { SavedReplay } from "./savedBenchmarkContract";

export default function SavedBenchmarkReplay(){
  const [data,setData]=useState<SavedReplay|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [qid,setQid]=useState<string>("");
  const [left,setLeft]=useState<string>("");
  const [right,setRight]=useState<string>("");
  async function inspect(file:File|undefined){
    setError(null);setData(null);
    if(!file)return;
    if(file.size>3_000_000){setError("File exceeds the 3 MB local-view limit");return;}
    try{
      const parsed=validateSavedReplay(JSON.parse(await file.text()));
      setData(parsed);setQid(parsed.queries[0]!.id);
      setLeft(parsed.pipeline_names[0]!);setRight(parsed.pipeline_names[1]!);
    }catch(e){setError(e instanceof Error?e.message:"Invalid locally supplied replay");}
  }
  const query=data?.queries.find(x=>x.id===qid);
  const lane=(name:string)=>(
    <div className="rr-local-lane">
      <h5>{name}</h5>
      <ol>
        {query?.rankings[name]?.map(item=><li key={item.doc_id}>
          <span>{item.rank}</span><code title="Original dataset document ID">{item.doc_id}</code>
          <small title="Raw method-specific retrieval score">{item.score.toFixed(4)}</small>
        </li>)}
      </ol>
    </div>
  );
  return <details className="rr-saved">
    <summary>Inspect your own saved benchmark trace</summary>
    <p>Export a real stored benchmark JSON using the repository's offline exporter, then inspect the result here. The file stays in your browser and is not uploaded to a service.</p>
    <label htmlFor="rr-saved-file">Select exported replay JSON</label>
    <input id="rr-saved-file" type="file" accept=".json,application/json" onChange={e=>void inspect(e.target.files?.[0])}/>
    {error&&<p role="alert" className="rr-saved-error">{error}. No unverified results displayed.</p>}
    {data&&query&&<div className="rr-saved-results" role="region" aria-label="Locally imported original benchmark ranks">
      <p className="ap-small">UNREVALIDATED SAVED ARCHIVE · {data.dataset}</p>
      <label htmlFor="rr-local-query">Recorded query</label>
      <select id="rr-local-query" value={query.id} onChange={e=>setQid(e.target.value)}>{data.queries.map(q=><option key={q.id} value={q.id}>{q.text}</option>)}</select>
      <div className="rr-saved-methods">
        <label>Left pipeline <select aria-label="Left saved pipeline" value={left} onChange={e=>{const v=e.target.value;if(v===right)setRight(left);setLeft(v);}}>{data.pipeline_names.map(m=><option key={m}>{m}</option>)}</select></label>
        <label>Right pipeline <select aria-label="Right saved pipeline" value={right} onChange={e=>{const v=e.target.value;if(v===left)setLeft(right);setRight(v);}}>{data.pipeline_names.map(m=><option key={m}>{m}</option>)}</select></label>
      </div>
      <div className="rr-saved-lanes">{lane(left)}{lane(right)}</div>
      <p className="rr-saved-sha">Original archive SHA256: <code>{data.source_archive_sha256}</code></p>
      <p>These are first-N positions from the supplied stored run, not a new evaluation. The original data, model weights and revisions were not independently verified by this browser.</p>
    </div>}
  </details>;
}
