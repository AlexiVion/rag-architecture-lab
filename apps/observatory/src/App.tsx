import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { loadObservatory, metricNames } from "./contracts";
import MicroLab from "./MicroLab";
import type { GraphFixture, GRF00, GRF01, ObservatoryData, QuestionTrace } from "./contracts";

type Page="overview"|"micro"|"experiments"|"pipeline"|"graph"|"evidence"|"models"|"methodology";
const NAV: {id:Page;name:string;icon:string}[]=[
  {id:"overview",name:"Overview",icon:"◈"},
  {id:"micro",name:"MICRO-RAG v0.2",icon:"◉"},
  {id:"experiments",name:"Experiments",icon:"▥"},
  {id:"pipeline",name:"Pipeline",icon:"⇄"},
  {id:"graph",name:"Knowledge graph",icon:"⌘"},
  {id:"evidence",name:"Evidence review",icon:"▣"},
  {id:"models",name:"Model lab",icon:"◎"},
  {id:"methodology",name:"Methodology",icon:"◇"}
];
const repo="https://github.com/AlexiVion/rag-architecture-lab";
const pct=(x:number)=>(x*100).toFixed(1)+"%";
const signed=(x:number)=>(x>0?"+":"")+(x*100).toFixed(2)+" pp";
const initialPage=():Page=>{
  const found=NAV.find(i=>i.id===window.location.hash.slice(1));
  return found?.id??"overview";
};
function Chip({children,tone="neutral"}:{children:ReactNode;tone?:"neutral"|"warn"|"good"|"bad"}){
  return <span className={"chip "+tone}>{children}</span>;
}
function Intro({tag,title,body}:{tag:string;title:string;body:string}){
  return <header className="intro"><p className="eyebrow">{tag}</p><h1>{title}</h1><p>{body}</p></header>;
}
function Panel({title,eyebrow,children}:{title:string;eyebrow?:string;children:ReactNode}){
  return <section className="panel" aria-label={title}><header className="panel-head">
    {eyebrow&&<p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2></header><div className="panel-body">{children}</div></section>;
}
function Overview({data,go}:{data:ObservatoryData;go:(p:Page)=>void}){
  return <>
    <Intro tag="OPEN-SOURCE RESEARCH · SOURCE FIRST" title="Evidence, made visible."
      body="Compare retrieval architectures, trace original document provenance and inspect why grounded-answer experiments fail. Verified sources, visible uncertainty, no fake live inference."/>
    <div className="hero-actions"><button className="button primary" onClick={()=>go("micro")}>Explore four-state MICRO-RAG ↗</button>
      <button className="button outline" onClick={()=>go("graph")}>Explore the evidence graph ↗</button>
      <button className="button outline" onClick={()=>go("experiments")}>Inspect measured results</button></div>
    <div className="notice"><strong>Research boundary.</strong> The source graph is a three-document fictional fixture. GRF-00 and GRF-01 are audited DEV retrieval studies. M2 factual support remains NO-GO for automatic publication.</div>
    <div className="stats">
      <div><span className="eyebrow">SOURCE DOCUMENTS</span><strong>{data.fixture.graph.documents.length}</strong><small>Curated fiction</small></div>
      <div><span className="eyebrow">QUOTED EDGES</span><strong>{data.fixture.graph.edges.length}</strong><small>Exact source passages</small></div>
      <div><span className="eyebrow">MEASURED STUDIES</span><strong>02</strong><small>DEV retrieval only</small></div>
      <div><span className="eyebrow">M2 PUBLICATION</span><strong className="bad-text">NO-GO</strong><small>Semantic support unverified</small></div>
    </div>
    <div className="columns">
      <Panel title="When the graph loses" eyebrow="GRF-00 · MEASURED">
        <MetricStudy study={data.grf00} kind="00"/>
        <p className="micro">Graph-first was worse than BM25 at Recall@5 on 60 HotpotQA DEV questions.</p>
        <button className="link-button" onClick={()=>go("experiments")}>See all paired metrics →</button>
      </Panel>
      <Panel title="What a two-hop path means" eyebrow="EVIDENCE FIXTURE">
        <div className="path-card"><span>Aster Rover</span><em>uses</em><span>Orion Navigation System</span><em>developed by</em><span>Meridian Robotics</span></div>
        <p className="micro">This illustrates source-linked graph traversal; the system did not generate a verified answer.</p>
        <button className="link-button" onClick={()=>go("evidence")}>Open original source text →</button>
      </Panel>
    </div>
  </>;
}
function MetricStudy({study,kind}:{study:GRF00|GRF01;kind:"00"|"01"}){
  const [metric,setMetric]=useState<typeof metricNames[number]>("recall@5");
  const m=study.metrics[metric];
  const before=kind==="00"?(m as GRF00["metrics"]["recall@5"]).bm25:(m as GRF01["metrics"]["recall@5"]).hybrid;
  const after=kind==="00"?(m as GRF00["metrics"]["recall@5"]).graph_plus_bm25:(m as GRF01["metrics"]["recall@5"]).graph_hybrid;
  const diff=kind==="00"?(m as GRF00["metrics"]["recall@5"]).paired_delta:(m as GRF01["metrics"]["recall@5"]).graph_hybrid_minus_hybrid_delta;
  const source=kind==="00"?"BM25":"Hybrid RRF";
  const candidate=kind==="00"?"Graph-first + BM25":"Graph-Hybrid";
  return <>
    <div className="metric-tabs" role="group" aria-label="Select Recall at K">
      {metricNames.map(k=><button type="button" key={k} aria-pressed={metric===k}
        onClick={()=>setMetric(k)}>{k}</button>)}</div>
    <div className="compare-rows">
      {[{name:source,value:before},{name:candidate,value:after}].map(row=><div key={row.name}>
        <div className="bar-label"><span>{row.name}</span><strong>{pct(row.value)}</strong></div>
        <div className="bar-track"><div className="bar-value" style={{width:pct(row.value)}}/></div>
      </div>)}
    </div>
    <div className="difference"><strong className={diff<0?"bad-text":"good-text"}>{signed(diff)}</strong><span> paired delta</span></div>
    <p className="micro">95% paired bootstrap CI: [{signed(m.paired_bootstrap_95ci[0])}, {signed(m.paired_bootstrap_95ci[1])}]</p>
    <p className="micro">Original report SHA256: <code>{study.source_report_sha256}</code></p>
  </>;
}
function Experiments({data}:{data:ObservatoryData}){
  return <>
    <Intro tag="RETRIEVAL BENCHMARKS · REAL NEGATIVE RESULTS" title="Trade-offs, not just wins."
      body="Two separately controlled HotpotQA DEV studies. Compare candidates within each cohort only, with paired uncertainty and exact source-report provenance."/>
    <div className="columns"><Panel title="GRF-00 · Graph-first vs BM25" eyebrow="NO-GO · 60 DEV QUESTIONS">
      <MetricStudy study={data.grf00} kind="00"/></Panel>
    <Panel title="GRF-01 · Graph-Hybrid vs Hybrid RRF" eyebrow="INCONCLUSIVE · 60 DEV QUESTIONS">
      <MetricStudy study={data.grf01} kind="01"/></Panel></div>
    <Panel title="What the data cannot establish" eyebrow="EXPERIMENTAL LIMITS">
      <div className="columns"><div><h3>GRF-00</h3><ul>{data.grf00.limitations.map((x,i)=><li key={i}>{x}</li>)}</ul></div>
      <div><h3>GRF-01</h3><ul>{data.grf01.limitations.map((x,i)=><li key={i}>{x}</li>)}</ul></div></div>
      <div className="notice small">Recall@K uses retrieval relevance labels, not claim entailment, factual-answer accuracy or real-world GraphRAG safety. Results from different exposed DEV cohorts are not directly comparable.</div>
    </Panel>
  </>;
}
function Questions({fixture,selected,setSelected}:{fixture:GraphFixture;selected:number;setSelected:(n:number)=>void}){
  return <div className="query-picker" role="group" aria-label="Select evidence question">
    {fixture.traces.map((t,i)=><button type="button" key={t.id} aria-pressed={selected===i}
      onClick={()=>setSelected(i)}><small>QUESTION {String(i+1).padStart(2,"0")}</small><span>{t.question}</span></button>)}
  </div>;
}
function Pipeline({fixture,trace}:{fixture:GraphFixture;trace:QuestionTrace}){
  const stages=[
    ["01","Question","Recorded",trace.question],
    ["02","Retrieval","Executed",String(trace.ranked_sources.length)+" original documents ranked"],
    ["03","Graph","Executed",String(trace.trace.paths.length)+" paths, up to "+trace.trace.max_hops+" hops"],
    ["04","Evidence context","Source-backed","Only original documents and exact source quotes"],
    ["05","Generator","Not run","The static fixture invokes no language model"],
    ["06","Citations & support","Not evaluated","No generated claims or semantic truth judgement"],
  ];
  return <>
    <Intro tag="PIPELINE / TRACE INSPECTOR" title="Every stage has a boundary."
      body="A real retrieval trace over a curated graph: see precisely which stages executed and which model-dependent stages were never run."/>
    <Panel title="Execution stages" eyebrow={trace.id}><div className="stages">
      {stages.map(([step,title,status,detail],i)=><article className="stage" key={step}>
        <div className="stage-meta"><span>{step}</span><Chip tone={i<4?"good":"warn"}>{status}</Chip></div>
        <h3>{title}</h3><p>{detail}</p>
      </article>)}
    </div></Panel>
    <Panel title="Ranked documents" eyebrow="SOURCE TRACE">
      <ol className="ranked">{trace.ranked_sources.map(r=><li key={r.doc_id}>
        <strong>{fixture.graph.documents.find(d=>d.id===r.doc_id)?.title??r.doc_id}</strong>
        <span>{r.doc_id} · rank {r.rank} · score {r.score.toFixed(3)}</span></li>)}</ol>
    </Panel>
  </>;
}
function Graph({fixture,trace}:{fixture:GraphFixture;trace:QuestionTrace}){
  const [active,setActive]=useState<string|null>(null);
  const coords:[number,number][]=[[140,102],[380,102],[620,102],[140,282],[380,282],[620,282]];
  const pos:Record<string,[number,number]>={};
  fixture.graph.nodes.forEach((n,i)=>{pos[n.id]=coords[i]??[120,100+i*30];});
  const selected=fixture.graph.edges.find(e=>e.id===active);
  const path=trace.trace.paths[0];
  const related=new Set(selected?[selected.id]:(path?.edge_ids??[]));
  const hotNodes=new Set([...(trace.trace.seed_entity_ids),...fixture.graph.edges.filter(e=>related.has(e.id)).flatMap(e=>[e.source,e.target])]);
  const label=(id:string)=>fixture.graph.nodes.find(n=>n.id===id)?.label??id;
  return <>
    <Intro tag="GRAPH / PROVENANCE NETWORK" title="Trace the source of every edge."
      body="Entity nodes, source-linked relations and two-hop evidence paths from the original fictional fixture. Inspect any relation through the keyboard-accessible list."/>
    <div className="columns graph-columns">
      <Panel title="Evidence network" eyebrow="CURATED · NO MODEL EXTRACTION">
        <div className="graph-svg"><svg viewBox="0 0 760 384" role="img" aria-label="Six entities with source-backed edges and an active retrieval path">
          {fixture.graph.edges.map(e=>{
            const a=pos[e.source],b=pos[e.target];if(!a||!b)return null;
            return <g key={e.id}><line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className={related.has(e.id)?"edge active":"edge"}/>
              <text x={(a[0]+b[0])/2} y={(a[1]+b[1])/2-12} textAnchor="middle" className="edge-caption">{e.relation.replaceAll("_"," ")}</text></g>;
          })}
          {fixture.graph.nodes.map(n=>{
            const p=pos[n.id];if(!p)return null;
            return <g key={n.id}><rect x={p[0]-91} y={p[1]-25} width="182" height="50" rx="11" className={hotNodes.has(n.id)?"node active":"node"}/>
              <text x={p[0]} y={p[1]+5} textAnchor="middle" className="node-label">{n.label}</text></g>;
          })}
        </svg></div>
        <p className="micro">SVG is visual only. Choose an edge below to reveal its source text.</p>
      </Panel>
      <Panel title="Source relation explorer" eyebrow={trace.id}>
        <div className="edge-options">{fixture.graph.edges.map(edge=><button
          key={edge.id} onClick={()=>setActive(edge.id)} aria-pressed={active===edge.id}>
          <strong>{label(edge.source)} → {label(edge.target)}</strong><small>{edge.relation.replaceAll("_"," ")}</small>
        </button>)}</div>
        <div className="quote-box">
          {selected?<><span className="eyebrow">{selected.document_id} · EXACT QUOTE</span><blockquote>{selected.quote}</blockquote></>:
          <><span className="eyebrow">SELECTED TRACE PATH</span><p>{path?.node_ids.map(label).join(" → ")??"No graph path; lexical fallback"}</p>
            <small>{path?.source_document_ids.join(" · ")??"No graph evidence found"}</small></>}
        </div>
      </Panel>
    </div>
  </>;
}
function Evidence({fixture,trace}:{fixture:GraphFixture;trace:QuestionTrace}){
  const [selected,setSelected]=useState<string|null>(null);
  const docId=selected??trace.ranked_sources[0]?.doc_id;
  const doc=fixture.graph.documents.find(d=>d.id===docId);
  const relations=fixture.graph.edges.filter(e=>e.document_id===docId);
  function download(){
    if(!doc)return;
    const payload={publication_status:fixture.publication_status,corpus_sha256:fixture.corpus_sha256,
      question:trace.question,document:doc,relations,generation_status:"not_run",semantic_truth:"not_evaluated"};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download="raglab-evidence-"+doc.id+".json";
    link.click();URL.revokeObjectURL(url);
  }
  return <>
    <Intro tag="EVIDENCE REVIEW / DOCUMENT INSPECTOR" title="A citation is not a fact."
      body="Examine original retrieved text, rank, source identity and the exact passages that justify graph relationships."/>
    <div className="columns evidence-columns"><Panel title="Ranked sources" eyebrow="CHOOSE A DOCUMENT">
      <div className="edge-options">{trace.ranked_sources.map(r=><button aria-pressed={docId===r.doc_id}
        key={r.doc_id} onClick={()=>setSelected(r.doc_id)}><span>RANK {r.rank} · {r.doc_id}</span>
        <strong>{fixture.graph.documents.find(d=>d.id===r.doc_id)?.title??r.doc_id}</strong></button>)}</div>
      </Panel>
      <Panel title="Verbatim source" eyebrow={docId??"NO DOCUMENT"}>{doc?
        <><h3>{doc.title}</h3><blockquote className="full-quote">{doc.text}</blockquote>
          {relations.map(e=><div className="quote-box" key={e.id}><span className="eyebrow">{e.relation} · {e.id}</span><p>{e.quote}</p></div>)}
          <button className="button outline" onClick={download}>Export verified source JSON ↓</button></>:
        <p>No source selected.</p>}</Panel></div>
    <div className="notice"><strong>No generated answer.</strong> This fixture does not establish claim truth or correct abstention. M2 requires independently verified evidence support.</div>
  </>;
}
function Models({data}:{data:ObservatoryData}){
  const groups: [string, string][]=[["embedding","Embedding models"],["reranking","Rerankers"],["stance_nli","Evidence / NLI"],["generation","Generators"]];
  return <>
    <Intro tag="MODEL LAB / TEN ADDITIONAL CANDIDATES" title="Proposals are not measured results."
      body="Four model roles, ten additional candidates, and four separate historical baselines. Revision, licensing and measured-role checks are explicit release gates."/>
    <div className="notice"><strong>Registry status: proposed.</strong> These models have not all been run, and no score is invented for candidates without a verified experiment.</div>
    {groups.map(([role,title])=><Panel key={role} title={title} eyebrow={role.toUpperCase()}>
      <div className="table-wrap"><table><thead><tr><th>Model</th><th>Hub ID</th><th>Revision</th><th>Status</th><th>License</th></tr></thead><tbody>
        {data.registry.models.filter(m=>m.role===role).map(m=><tr key={m.id}><td>{m.id}</td>
          <td><code>{m.hub_id}</code>{m.special_license_note&&<p className="micro bad-text">{m.special_license_note}</p>}</td>
          <td>{m.revision??"Not pinned"}</td><td><Chip tone="warn">{m.execution_status.replaceAll("_"," ")}</Chip></td>
          <td>{m.license_review??"Pending"}</td></tr>)}
      </tbody></table></div></Panel>)}
    <Panel title="Historical baselines" eyebrow="NOT INCLUDED IN THE TEN NEW CANDIDATES">
      <div className="table-wrap"><table><thead><tr><th>Model</th><th>Role</th><th>Recorded status</th></tr></thead><tbody>
        {data.registry.previously_evaluated_baselines.map(m=><tr key={m.id}><td><code>{m.hub_id}</code></td>
          <td>{m.role}</td><td>{m.historical_status.replaceAll("_"," ")}</td></tr>)}
      </tbody></table></div>
    </Panel>
  </>;
}
function Methodology({data}:{data:ObservatoryData}){
  const links=[["Experiment protocol","docs/EXPERIMENT_PROTOCOL.md"],
    ["WOW v1.0 blueprint","docs/RELEASE_WOW_BLUEPRINT.md"],
    ["Release gate matrix","docs/RELEASE_EXECUTION_MATRIX.md"],
    ["Measured graph benchmark","docs/GRF_01_HYBRID_RRF_PROTOCOL.md"],
    ["Ten-model registry","experiments/model_matrix_10_proposed.json"]];
  return <>
    <Intro tag="METHODS / LIMITS / ATTRIBUTION" title="Every result has a trail."
      body="Methods, dataset splits, code revisions and the original report hashes should always be accessible. The observatory avoids decorative live gauges and unsupported claims."/>
    <div className="columns"><Panel title="Public provenance" eyebrow="HASHED SOURCE REPORTS">
      <dl className="provenance"><dt>Illustrative corpus</dt><dd><code>{data.fixture.corpus_sha256}</code></dd>
        <dt>GRF-00 original report</dt><dd><code>{data.grf00.source_report_sha256}</code></dd>
        <dt>GRF-01 original report</dt><dd><code>{data.grf01.source_report_sha256}</code></dd>
        <dt>Benchmark dataset license</dt><dd>{data.grf00.dataset_license}</dd>
        <dt>Generated-answer truth</dt><dd>NOT EVALUATED</dd></dl></Panel>
      <Panel title="Reproduce the study" eyebrow="OPEN SOURCE">
        <p>Inspect the exact code and documented experiment protocol. The hosted app is a read-only visualization; local CPU model studies are separate and may require optional weights.</p>
        <div className="doc-links">{links.map(([title,path])=><a href={repo+"/blob/feat/research-lab-architecture-catalog-20261104/"+path}
          key={path} rel="noreferrer" target="_blank">{title} ↗</a>)}</div></Panel></div>
    <Panel title="Known failures are part of the evidence" eyebrow="SCIENTIFIC HONESTY"><ul className="limitations">
      <li>Graph-first DEV retrieval underperformed BM25; this does not prove GraphRAG universally fails.</li>
      <li>Graph-Hybrid did not show a reliable benefit over Hybrid RRF in the separate exposed DEV cohort.</li>
      <li>Qwen M2 synthetic controls passed 7/24 narrow checks, while three negative-evidence drafts were accepted by the original syntax-only pipeline. Automatic factual publication remains NO-GO.</li>
      <li>The post-hoc guard blocked original errors but rejected eight of eight authored valid paraphrases in a later stress suite.</li>
      <li>The MOD-10 registry contains proposed models, not a completed ten-model benchmark.</li>
      <li>The manually curated Aster graph demonstrates evidence paths, not measured general multi-hop QA or source entailment.</li>
    </ul></Panel>
  </>;
}
export default function App(){
  const [data,setData]=useState<ObservatoryData|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [page,setPage]=useState<Page>(initialPage);
  const [queryIndex,setQueryIndex]=useState(0);
  const [theme,setTheme]=useState<"dark"|"light">("dark");
  useEffect(()=>{
    let alive=true;
    loadObservatory().then(d=>{if(alive)setData(d);}).catch(err=>{
      if(alive)setError(err instanceof Error?err.message:"Unverified source data");
    });
    const onHash=()=>setPage(initialPage());
    window.addEventListener("hashchange",onHash);
    return ()=>{alive=false;window.removeEventListener("hashchange",onHash);};
  },[]);
  useEffect(()=>{document.documentElement.dataset.theme=theme;},[theme]);
  const trace=data?.fixture.traces[queryIndex]??data?.fixture.traces[0];
  function go(next:Page){
    setPage(next);window.location.hash=next;window.scrollTo({top:0,behavior:"instant"});
  }
  return <div className="shell">
    <a className="skip" href="#main">Skip to main content</a>
    <aside className="sidebar"><a href="#overview" className="brand" onClick={()=>go("overview")}>
        <span className="brand-mark">R<span>/</span>L</span><span><strong>RAG / LAB</strong><small>ARCHITECTURE OBSERVATORY</small></span>
      </a>
      <p className="sidebar-label">EXPLORE THE LAB</p><nav aria-label="Research sections">
        {NAV.map(link=><button key={link.id} aria-current={page===link.id?"page":undefined}
          onClick={()=>go(link.id)}><span aria-hidden="true">{link.icon}</span>{link.name}</button>)}
      </nav>
      <div className="side-status"><span className="eyebrow">RESEARCH STATUS</span>
        <p><span className="status-dot"/> Experimental · source verified</p>
        <small>M2 factual support and ten-model measurements remain open.</small></div>
      <a className="side-link" href={repo} target="_blank" rel="noreferrer">GitHub repository ↗</a>
    </aside>
    <div className="main-column"><header className="topbar"><p>Research workspace <span> / </span><strong>{NAV.find(n=>n.id===page)?.name}</strong></p>
        <div><Chip tone="warn">NO LIVE INFERENCE</Chip>
          <button className="theme" aria-label={theme==="dark"?"Use light theme":"Use dark theme"}
            onClick={()=>setTheme(theme==="dark"?"light":"dark")}>{theme==="dark"?"☼":"◐"}</button>
          <a href={repo} target="_blank" rel="noreferrer">Source ↗</a></div>
      </header>
      <main id="main" className="main">
        {error?<div className="error" role="alert"><strong>Artifact validation failed.</strong>
          <p>{error}</p><p>No unverified result will be displayed.</p></div>:!data||!trace?
          <div className="loading" role="status">Validating public source artifacts…</div>:<>
            {(["graph","pipeline","evidence"] as Page[]).includes(page)&&
              <Questions fixture={data.fixture} selected={queryIndex} setSelected={setQueryIndex}/>}
            {page==="overview"&&<Overview data={data} go={go}/>}
            {page==="micro"&&<MicroLab/>}
            {page==="experiments"&&<Experiments data={data}/>}
            {page==="pipeline"&&<Pipeline fixture={data.fixture} trace={trace}/>}
            {page==="graph"&&<Graph key={trace.id} fixture={data.fixture} trace={trace}/>}
            {page==="evidence"&&<Evidence key={trace.id} fixture={data.fixture} trace={trace}/>}
            {page==="models"&&<Models data={data}/>}
            {page==="methodology"&&<Methodology data={data}/>}
          </>}
      </main><footer>RAG Architecture Lab · Portfolio research preview <span>·</span> Evidence-first retrieval · No model server</footer>
    </div>
  </div>;
}
