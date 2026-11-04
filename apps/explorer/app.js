const SVG = 'http://www.w3.org/2000/svg';
const POS = {
  rover:[102,90], navigation:[312,98], manufacturer:[530,93],
  probe:[100,262], sensor:[320,255], instrument:[530,264]
};
const $ = id => document.getElementById(id);
let dataset = null;
let activeTrace = 0;
let activePath = 0;
let selectedEdge = null;

function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = String(text);
  return element;
}
function svg(tag, attrs) {
  const element = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
  return element;
}
function assertArtifact(data) {
  if (data.schema_version !== 1 || data.kind !== 'graph_evidence_fixture'
    || data.publication_status !== 'illustrative_fixture_not_benchmark'
    || !Array.isArray(data.graph?.nodes) || !Array.isArray(data.graph?.edges)
    || !Array.isArray(data.graph?.documents) || !Array.isArray(data.traces)) {
    throw new Error('Unexpected data contract. The viewer accepts verified graph fixtures only.');
  }
  const docs = new Map(data.graph.documents.map(d => [d.id, d]));
  const nodes = new Map(data.graph.nodes.map(n => [n.id, n]));
  for (const edge of data.graph.edges) {
    const doc = docs.get(edge.document_id);
    if (!doc || !nodes.has(edge.source) || !nodes.has(edge.target)
      || !(String(doc.title) + '\n' + String(doc.text)).includes(edge.quote)) {
      throw new Error('Graph evidence does not resolve to a verbatim source.');
    }
  }
  for (const trace of data.traces) {
    if (trace.answer !== null || trace.generation_status !== 'not_run') {
      throw new Error('Fixture must not contain a fake generated answer.');
    }
  }
}
function getTrace() { return dataset.traces[activeTrace]; }
function activeEdges() {
  const trace = getTrace().trace;
  return new Set(selectedEdge ? [selectedEdge] : trace.paths[activePath]?.edge_ids ?? []);
}
function activeNodes() {
  const trace = getTrace().trace;
  const result = new Set(trace.seed_entity_ids);
  for (const eid of activeEdges()) {
    const edge = dataset.graph.edges.find(e => e.id === eid);
    if (edge) { result.add(edge.source); result.add(edge.target); }
  }
  return result;
}
function displayPath(path) {
  const byNode = new Map(dataset.graph.nodes.map(n => [n.id, n]));
  return path.node_ids.map(id => byNode.get(id)?.label ?? id).join('  →  ');
}
function renderQueries() {
  const list = $('queries'); list.replaceChildren();
  dataset.traces.forEach((trace, i) => {
    const button = el('button','query-option'+(i===activeTrace?' active':''));
    button.type='button';button.setAttribute('aria-pressed',String(i===activeTrace));
    button.append(el('span','query-index',String(i+1).padStart(2,'0')),document.createTextNode(trace.question));
    button.addEventListener('click',()=>{activeTrace=i;activePath=0;selectedEdge=null;render();});
    list.append(button);
  });
}
function renderPaths() {
  const trace = getTrace().trace;
  const list = $('paths');list.replaceChildren();
  $('path-count').textContent = String(trace.paths.length)+' paths found';
  trace.paths.forEach((path,i)=>{
    const btn=el('button','path-button'+(i===activePath && !selectedEdge?' active':''));
    btn.type='button';btn.setAttribute('aria-pressed',String(i===activePath && !selectedEdge));
    const left=el('span');left.append(el('strong',null,displayPath(path)),el('small',null, path.source_document_ids.join(' · ')));
    btn.append(left,el('span','path-hops',path.hop_count+' HOP'+(path.hop_count===1?'':'S')));
    btn.addEventListener('click',()=>{activePath=i;selectedEdge=null;render();});
    list.append(btn);
  });
  if (!trace.paths.length) list.append(el('p','empty-evidence','No graph path was found. The retriever used lexical fallback only.'));
}
function graphArrow(view) {
  const defs=svg('defs',{}), marker=svg('marker',{id:'arrow',viewBox:'0 0 10 10',refX:'8',refY:'5',markerWidth:'5',markerHeight:'5',orient:'auto'});
  marker.append(svg('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#6c859e'}));defs.append(marker);view.append(defs);
}
function renderGraph() {
  const host=$('graph-canvas');host.replaceChildren();
  const view=svg('svg',{viewBox:'0 0 635 335',role:'img','aria-label':'Graph with six curated entities; click evidence edges to inspect source documents'});
  graphArrow(view);
  const highlighted=activeEdges(), highlightedNodes=activeNodes();
  for (const edge of dataset.graph.edges) {
    const a=POS[edge.source], b=POS[edge.target];
    if(!a||!b)continue;
    const isActive=highlighted.has(edge.id);
    const line=svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],class:'edge'+(isActive?' active':''),tabindex:'0',role:'button','aria-label':edge.relation+' - inspect evidence','data-edge-id':edge.id});
    const inspect=()=>{selectedEdge=edge.id;render();};
    line.addEventListener('click',inspect);
    line.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();inspect();}});
    view.append(line);
    const label=svg('text',{x:(a[0]+b[0])/2,y:(a[1]+b[1])/2-11,'text-anchor':'middle',class:'edge-label'+(isActive?' active':'')});
    label.textContent=edge.relation.replaceAll('_',' ');view.append(label);
  }
  const seeds=new Set(getTrace().trace.seed_entity_ids);
  for (const node of dataset.graph.nodes) {
    const p=POS[node.id];if(!p)continue;
    const active=highlightedNodes.has(node.id);
    const group=svg('g',{class:'node-tap',tabindex:'0',role:'button','aria-label':'Entity '+node.label});
    const rect=svg('rect',{x:p[0]-75,y:p[1]-24,width:150,height:49,rx:11,class:'node-outer'+(active?' active':'')});
    const text=svg('text',{x:p[0],y:p[1]+5,'text-anchor':'middle',class:'node-label'+(active?' active':'')});
    text.textContent=node.label;
    group.append(rect,text);
    if(seeds.has(node.id)){const seed=svg('circle',{cx:p[0]-64,cy:p[1]-12,r:4,fill:'#68e9b8'});group.append(seed);}
    const choose=()=>{const match=getTrace().trace.paths.findIndex(path=>path.node_ids.includes(node.id));if(match>=0){activePath=match;selectedEdge=null;render();}};
    group.addEventListener('click',choose);
    group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}});
    view.append(group);
  }
  host.append(view);
  $('seed-label').textContent = 'Seed'+(seeds.size===1?'':'s')+': '+([...seeds].join(', ')||'none');
}
function renderEvidence() {
  const list=$('evidence-list');list.replaceChildren();
  const active=activeEdges();
  const edges=dataset.graph.edges.filter(edge=>active.has(edge.id));
  $('inspector-status').textContent=selectedEdge?'Inspecting a source-backed relationship.':'Original passages supporting the selected path.';
  const docs=new Map(dataset.graph.documents.map(d=>[d.id,d]));
  if(!edges.length)list.append(el('p','empty-evidence','No graph relation selected. Source evidence will appear here when a path is available.'));
  edges.forEach((edge,index)=>{
    const doc=docs.get(edge.document_id);
    const card=el('article','source-card');
    const heading=el('div','source-head');
    heading.append(el('span','source-index','S'+(index+1)),el('strong',null,doc.title),el('small',null,'EXACT QUOTE'));
    card.append(heading,el('blockquote','quote-text',edge.quote));
    const foot=el('div','source-bottom');
    foot.append(el('code',null,doc.id),el('span',null,edge.relation.replaceAll('_',' ')));
    card.append(foot);list.append(card);
  });
}
function render(){
  if(!dataset)return;
  renderQueries();renderPaths();renderGraph();renderEvidence();
  $('metric-nodes').textContent=String(dataset.graph.nodes.length).padStart(2,'0');
  $('metric-edges').textContent=String(dataset.graph.edges.length).padStart(2,'0');
  $('metric-paths').textContent=String(getTrace().trace.paths.length).padStart(2,'0');
  $('footer-fingerprint').textContent='corpus SHA256 '+dataset.corpus_sha256.slice(0,14)+'…';
}
function setupNavigation(){
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
    document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b===button));
    const label={overview:'Overview',graph:'Knowledge graph',evidence:'Evidence trace',research:'Research notes'}[button.dataset.view];
    $('current-section').textContent=label;
    const target={overview:'.intro',graph:'.network-panel',evidence:'.inspect-panel',research:'#benchmark-section'}[button.dataset.view];
    document.querySelector(target)?.scrollIntoView({behavior:'smooth',block:'start'});
  }));
  $('export-trace').addEventListener('click',()=>{
    if(!dataset)return;
    const payload={schema_version:1,publication_status:dataset.publication_status,dataset:dataset.dataset,corpus_sha256:dataset.corpus_sha256,example:getTrace(),graph:dataset.graph};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const link=el('a');link.href=url;link.download='raglab-'+getTrace().id+'.json';link.click();URL.revokeObjectURL(url);
  });
}
async function load(){
  setupNavigation();
  try{
    const response=await fetch('./data/demo.json',{cache:'no-store'});
    if(!response.ok)throw new Error('Fixture file missing. Run the offline exporter first.');
    const body=await response.json();assertArtifact(body);dataset=body;render();loadLocalBenchmark();loadGrf01Benchmark();
  }catch(error){
    $('load-error').hidden=false;
    $('load-error').textContent='Unable to load verified fixture: '+error.message+'. Serve this directory through a local HTTP server, not file://.';
  }
}
load();

const PUBLISHED_GRF00_SOURCE_SHA256 = '962dc3b12d0086857ad94198cf2b1fff7a49ca5f7df069e9575a6daaf778f016';
const PUBLISHED_GRF01_SOURCE_SHA256 = 'f2167bc7220554b1864648c5c5de0b67544bfbdba585a4aeed8f466927fcb2b4';

// Only a missing local file may trigger the published read-only fallback.
// If a local audit artifact is present but corrupt, fail closed.
async function loadBenchmarkArtifact(localPath, publishedPath) {
  const local = await fetch(localPath, {cache:'no-store'});
  if (local.ok) return {data: await local.json(), origin: 'local'};
  if (local.status !== 404) throw new Error('Local result was not accessible');
  const publicResponse = await fetch(publishedPath, {cache:'no-store'});
  if (!publicResponse.ok) throw new Error('Published summary unavailable');
  return {data: await publicResponse.json(), origin: 'published'};
}

async function loadLocalBenchmark() {
  const status = $('benchmark-badge');
  try {
    const {data,origin} = await loadBenchmarkArtifact('./data/hotpotqa-summary.local.json','./data/grf00-summary.public.json');
    if (data.schema_version !== 1 || data.kind !== 'verified_retrieval_benchmark_aggregate'
      || data.experiment_id !== 'GRF00-HOTPOTQA-DEV-01' || data.sample_count !== 60
      || data.publication_status !== (origin==='local' ? 'verified_from_local_per_query_records' : 'published_operator_audit_summary')
      || data.source_report_sha256 !== PUBLISHED_GRF00_SOURCE_SHA256
      || !['NO_GO_GRAPH_FIRST_ON_THIS_DEV_SUBSET','INCONCLUSIVE_OR_MIXED_RESULTS'].includes(data.decision)) {
      throw new Error('Invalid or unaudited local benchmark summary');
    }
    status.textContent = data.decision.startsWith('NO_GO') ? 'NO-GO · GRAPH FIRST' : 'RESEARCH INCONCLUSIVE';
    const host = $('benchmark-metrics'); host.replaceChildren();
    for (const [key, label] of [['recall@1','Recall@1'],['recall@3','Recall@3'],['recall@5','Recall@5']]) {
      const m = data.metrics?.[key], lo = m?.paired_bootstrap_95ci?.[0], hi = m?.paired_bootstrap_95ci?.[1];
      if (![m?.bm25,m?.graph_plus_bm25,m?.paired_delta,lo,hi].every(v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=1)) {
        throw new Error('Invalid benchmark scores');
      }
      const card = el('div','bench-metric');
      card.append(el('span','bench-key',label),el('div','bench-values',`BM25 ${(m.bm25*100).toFixed(2)}% · Graph+BM25 ${(m.graph_plus_bm25*100).toFixed(2)}%`));
      const diff=el('div','bench-delta',`${m.paired_delta>=0?'+':''}${(m.paired_delta*100).toFixed(2)} pts`);
      if (m.paired_delta<0) diff.classList.add('negative');
      card.append(diff,el('small',null,`95% paired CI: [${(lo*100).toFixed(2)}, ${(hi*100).toFixed(2)}] pts`));
      host.append(card);
    }
    const groups = $('benchmark-groups'); groups.replaceChildren();
    for (const [id, label] of [['paths_present','Graph path found'],['paths_absent','No graph path']]) {
      const group=data.subgroups?.[id];
      if (!group || !Number.isInteger(group.cases) || group.cases<0
          || (group.mean_delta_recall_at_5!==null && !Number.isFinite(group.mean_delta_recall_at_5))) {
        throw new Error('Invalid benchmark subgroup');
      }
      const delta=group.mean_delta_recall_at_5;
      groups.append(el('span','bench-group',`${label}: ${group.cases} cases · ΔRecall@5: ${delta===null?'n/a':(delta*100).toFixed(2)+' pts'}`));
    }
    $('benchmark-provenance').textContent =
      `${origin==='local'?'Local saved-JSON audit':'Public aggregate reconstructed from successful operator audit log'} · HotpotQA DEV distractor · 60 questions · CC BY-SA 4.0 · Report SHA256 ${data.source_report_sha256.slice(0,16)}… · This is NOT an independent TEST benchmark; no generated answer metrics.`;
  } catch (error) {
    status.textContent = 'LOCAL RESULT PENDING';
    $('benchmark-metrics').textContent = 'No audited local results available. Run scripts/audit-grf00-hotpotqa-local.ps1 and refresh.';
    $('benchmark-groups').replaceChildren();
  }
}

async function loadGrf01Benchmark() {
  const badge = $('grf01-badge'), host = $('grf01-metrics');
  try {
    const {data,origin} = await loadBenchmarkArtifact('./data/grf01-summary.local.json','./data/grf01-summary.public.json');
    if (data.schema_version !== 1 || data.kind !== 'verified_grf01_retrieval_aggregate'
      || data.publication_status !== (origin==='local'?'audited_local_existing_run':'published_operator_audit_summary')
      || data.experiment_id !== 'GRF01-HOTPOTQA-DEV-01'
      || data.sample_count !== 60
      || data.source_report_sha256 !== PUBLISHED_GRF01_SOURCE_SHA256
      || data.cohort_sha256 !== 'a560b1cbabe1ce6b4413f0f6f59759cd08e69ce49c5391e05b7c8767f81bd13f'
      || data.policy_sha256 !== 'fd28fe01f244fa27f731395bd522a331026eb1cfa6a6acb4bcf592db1fb942bb'
      || !['INCONCLUSIVE_NO_AUTOMATIC_PROMOTION','NO_GO_PRIMARY_RECALL_BELOW_BASELINE','PRIMARY_POSITIVE_PENDING_COST_AND_PROVENANCE_REVIEW'].includes(data.decision)) {
      throw new Error('Invalid or unverified GRF-01 study aggregate');
    }
    const inspected = [];
    for (const [key,label] of [['recall@1','Recall@1'],['recall@3','Recall@3'],['recall@5','Recall@5']]) {
      const metric = data.metrics?.[key];
      const lo = metric?.paired_bootstrap_95ci?.[0];
      const hi = metric?.paired_bootstrap_95ci?.[1];
      const values = [metric?.hybrid,metric?.graph_hybrid,metric?.graph_hybrid_minus_hybrid_delta,lo,hi];
      if (!values.every(n=>typeof n==='number' && Number.isFinite(n) && Math.abs(n)<=1)) {
        throw new Error('Missing or out-of-range measured retrieval metric');
      }
      inspected.push({label,metric,lo,hi});
    }
    const groups = [];
    for (const [id,title] of [['path_activated','Graph path active'],['no_path','No graph path']]) {
      const item = data.subgroups?.[id];
      if (!item || !Number.isInteger(item.cases) || item.cases<0
        || (item.mean_delta_recall_at_5!==null && !Number.isFinite(item.mean_delta_recall_at_5))) {
        throw new Error('Invalid observed graph subgroup');
      }
      groups.push({title,item});
    }
    if (groups.reduce((sum,x)=>sum+x.item.cases,0)!==60) throw new Error('Subgroup counts differ');
    badge.textContent = data.decision==='INCONCLUSIVE_NO_AUTOMATIC_PROMOTION'
      ? 'INCONCLUSIVE · KEEP HYBRID'
      : data.decision.startsWith('NO_GO') ? 'NO-GO · KEEP HYBRID' : 'POSITIVE · REVIEW REQUIRED';
    host.replaceChildren();
    for (const {label,metric,lo,hi} of inspected) {
      const card=el('div','bench-metric');
      card.append(el('span','bench-key',label));
      card.append(el('div','bench-values','Hybrid RRF '+(metric.hybrid*100).toFixed(2)+'% · Graph-Hybrid '+(metric.graph_hybrid*100).toFixed(2)+'%'));
      const delta=el('div','bench-delta',(metric.graph_hybrid_minus_hybrid_delta>=0?'+':'')+(metric.graph_hybrid_minus_hybrid_delta*100).toFixed(2)+' pts');
      if (metric.graph_hybrid_minus_hybrid_delta<0) delta.classList.add('negative');
      card.append(delta,el('small',null,'95% paired CI: ['+(lo*100).toFixed(2)+', '+(hi*100).toFixed(2)+'] pts'));
      host.append(card);
    }
    const groupHost=$('grf01-groups');groupHost.replaceChildren();
    for (const {title,item} of groups) {
      const delta=item.mean_delta_recall_at_5;
      groupHost.append(el('span','bench-group',title+': '+item.cases+' cases · ΔRecall@5 '+(delta===null?'n/a':(delta*100).toFixed(2)+' pts')+' · W/L/T '+item.wins+'/'+item.losses+'/'+item.ties));
    }
    $('grf01-source').textContent=(origin==='local'?'Local saved-JSON audit':'Public aggregate from operator audit log')+' · model revision '+data.model_revision.slice(0,12)+'… · report SHA256 '+data.source_report_sha256.slice(0,16)+'… · HotpotQA DEV CC BY-SA 4.0. These are source retrieval metrics, not answer accuracy.';
  } catch (error) {
    badge.textContent='AUDITED RESULT PENDING';
    host.textContent='Audited GRF-01 result unavailable. Run scripts/audit-grf01-local.ps1 and refresh.';
    $('grf01-groups').replaceChildren();
  }
}
