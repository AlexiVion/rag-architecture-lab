import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { loadObservatory } from "./contracts";
import type { GRF00, GRF01, ObservatoryData } from "./contracts";
import ResearchDemo from "./ResearchDemo";
import RealRetrievalReplay from "./RealRetrievalReplay";
import ArchitecturePlayground from "./ArchitecturePlayground";

type Page = "research" | "experiments" | "methodology";
const PAGES: { id: Page; label: string }[] = [
  { id: "research", label: "Research" },
  { id: "experiments", label: "Experiments" },
  { id: "methodology", label: "Methodology" },
];
const REPO = "https://github.com/AlexiVion/rag-architecture-lab";
const docs = (name: string) => REPO + "/blob/main/" + name;
const pct = (value: number) => (value * 100).toFixed(2).replace(/0+$/, "").replace(/\.$/, "") + "%";
function isPage(v: string): v is Page { return PAGES.some((p) => p.id === v); }
function fromHash(): Page {
  const value = window.location.hash.slice(1);
  return isPage(value) ? value : "research";
}

function SourceLink({ href, children }: { href: string; children: ReactNode }) {
  return <a href={href} target="_blank" rel="noreferrer" className="source-link">{children}<span aria-hidden="true"> ↗</span></a>;
}
function SectionTitle({ index, title, intro }: { index: string; title: string; intro: string }) {
  return <div className="section-intro">
    <p className="overline">{index}</p>
    <h2>{title}</h2>
    <p>{intro}</p>
  </div>;
}
function MetricBars({ heading, rows, scale = 1 }: { heading: string; rows: { label: string; value: number; printed: string; emphasis?: boolean }[]; scale?: number }) {
  return <div className="metric-bars" role="group" aria-label={heading}>
    <p className="detail-label">{heading}</p>
    {rows.map((row) => <div className="metric-row" key={row.label}>
      <div className="metric-row-label"><span>{row.label}</span><strong>{row.printed}</strong></div>
      <div className="metric-track"><span className={row.emphasis ? "metric-fill emphasis" : "metric-fill"} style={{width: Math.min(100, Math.max(0, row.value / scale * 100)) + "%"}} /></div>
    </div>)}
  </div>;
}

function Research({ navigate }: { navigate: (page: Page) => void }) {
  return <article className="page-content research-page">
    <section className="hero">
      <p className="overline">Independent research · Retrieval-augmented generation</p>
      <h1>How small can <em>reliable RAG</em> be?</h1>
      <p className="hero-lead">An open-source investigation into evidence-grounded question answering with small models and limited CPU resources.</p>
      <div className="hero-actions">
        <a className="primary-action" href="#architecture-playground">Compare architectures <span aria-hidden="true">↗</span></a>
        <button type="button" className="text-action" onClick={() => navigate("experiments")}>View measured results <span aria-hidden="true">→</span></button>
      </div>
      <p className="project-status"><span className="status-circle" /> Research in progress <span aria-hidden="true">·</span> ≤135M active neural parameters is a proposed full-pipeline research constraint, not an achieved validated system.</p>
    </section>
    <ArchitecturePlayground />
    <ResearchDemo />
    <section className="process-section" aria-labelledby="how-title">
      <SectionTitle index="03 / THE RESEARCH APPROACH" title="Four steps. One question of trust." intro="Retrieving a document and producing a supported answer are different tasks. The laboratory measures where that chain succeeds and fails." />
      <div className="process-list" id="how-title">
        {[
          ["01", "Retrieve", "Find candidate sources using lexical, dense or hybrid search."],
          ["02", "Read", "Extract a candidate claim or test a constrained language model."],
          ["03", "Inspect", "Trace exact quotations and check whether evidence is missing or incompatible."],
          ["04", "Decide", "Return a supported structured value or withhold an answer for review."],
        ].map(([number,title,body]) => <div className="process-step" key={number}>
          <span>{number}</span><div><h3>{title}</h3><p>{body}</p></div>
        </div>)}
      </div>
    </section>
    <section className="closing-row">
      <div>
        <p className="overline">WHAT IS VERIFIED</p>
        <h3>Measured retrieval, inspectable decisions.</h3>
        <p>Published CPU experiments, negative results, versioned source artifacts, and tests are available for review.</p>
      </div>
      <div>
        <p className="overline">WHAT REMAINS OPEN</p>
        <h3>Independent factual reliability.</h3>
        <p>Natural-language end-to-end performance, calibrated abstention, and human-reviewed holdout evaluation remain research objectives.</p>
      </div>
    </section>
    <div className="bottom-action">
      <button type="button" className="text-action" onClick={() => navigate("experiments")}>Explore the experiments <span aria-hidden="true">→</span></button>
    </div>
  </article>;
}
function GraphStudy({ grf00, grf01 }: { grf00: GRF00; grf01: GRF01 }) {
  const zero = grf00.metrics["recall@5"];
  const one = grf01.metrics["recall@5"];
  return <section className="study secondary-study">
    <div className="study-heading">
      <div><p className="overline">04 / GRAPH RETRIEVAL</p><h2>When a more complex method does not help.</h2></div>
      <span className="study-scope">HotpotQA DEV · two distinct cohorts</span>
    </div>
    <div className="two-metrics">
      <div>
        <h3>Graph-first vs BM25</h3>
        <MetricBars heading="Recall@5 · 60 DEV questions" rows={[
          {label:"BM25",value:zero.bm25,printed:pct(zero.bm25),emphasis:true},
          {label:"Graph-first + BM25",value:zero.graph_plus_bm25,printed:pct(zero.graph_plus_bm25)}
        ]}/>
        <p>The tested graph-first policy underperformed BM25 on this cohort.</p>
        <SourceLink href={docs("benchmarks/GRF00_HOTPOTQA_DEV_60_NO_GO_20261104.md")}>Study and limitations</SourceLink>
      </div>
      <div>
        <h3>Graph-hybrid vs Hybrid RRF</h3>
        <MetricBars heading="Recall@5 · separate 60-question cohort" rows={[
          {label:"Hybrid RRF",value:one.hybrid,printed:pct(one.hybrid),emphasis:true},
          {label:"Graph-hybrid",value:one.graph_hybrid,printed:pct(one.graph_hybrid)}
        ]}/>
        <p>The primary comparison was inconclusive; no general graph benefit was established.</p>
        <SourceLink href={docs("benchmarks/GRF01_HOTPOTQA_DEV_FROZEN_20261104.md")}>Study and limitations</SourceLink>
      </div>
    </div>
  </section>;
}
function Experiments({data}:{data:ObservatoryData}) {
  return <article className="page-content experiments-page">
    <header className="page-heading">
      <p className="overline">Empirical studies · documented results</p>
      <h1>What the experiments actually show.</h1>
      <p>Research outcomes, including negative results. Each comparison is limited to its documented task, dataset and execution environment.</p>
    </header>
    <section className="study featured-study">
      <div className="study-heading">
        <div><p className="overline">01 / RETRIEVAL QUALITY</p><h2>Combining retrieval methods improved ranking.</h2></div>
        <span className="study-scope">BEIR SciFact · 5,183 documents · 300 queries</span>
      </div>
      <div className="study-split">
        <MetricBars heading="MRR@10 · higher is better" scale={.8} rows={[
          {label:"BM25", value:.6328, printed:"0.6328"},
          {label:"Dense embeddings", value:.6047, printed:"0.6047"},
          {label:"Hybrid RRF", value:.6484, printed:"0.6484", emphasis:true},
        ]}/>
        <div className="study-reading">
          <h3>Measured result</h3>
          <p>Hybrid retrieval ranked the first relevant source best in this experiment. This measures retrieval relevance, <strong>not generated-answer accuracy.</strong></p>
          <SourceLink href={docs("benchmarks/V0_RESULTS.md")}>Read the original report</SourceLink>
        </div>
      </div>
    </section>
    <section className="study">
      <div className="study-heading">
        <div><p className="overline">02 / QUALITY VERSUS COMPUTE</p><h2>A small ranking gain carried a large CPU cost.</h2></div>
        <span className="study-scope">Cross-encoder · 50 candidates · local CPU</span>
      </div>
      <div className="compare-figures">
        <div><span>MRR@10</span><strong>0.6484 <em>→</em> 0.6615</strong><small>Hybrid → reranked</small></div>
        <div><span>Mean query latency</span><strong>34.53 <em>→</em> 3,706.43 <small>ms</small></strong><small>Measured local CPU comparison</small></div>
      </div>
      <p className="study-note">This is a trade-off, not evidence that reranking is always too slow. Candidate depth, CPU/GPU choice, model and batching change the result.</p>
      <SourceLink href={docs("benchmarks/V1_RESULTS.md")}>Read the timing and ranking report</SourceLink>
    </section>
    <section className="study">
      <div className="study-heading">
        <div><p className="overline">03 / TINY READER MODELS</p><h2>Finding evidence did not mean a tiny generator could use it.</h2></div>
        <span className="study-scope">SQuAD2 public DEV · 32 questions</span>
      </div>
      <div className="compare-figures">
        <div><span>Task-trained extractive MiniLM · 33.4M</span><strong>24 / 32</strong><small>Exact-match reference answers</small></div>
        <div><span>Pythia-14M and SmolLM2-135M</span><strong>0 / 16</strong><small>Exact answers on the answerable questions in tested setups</small></div>
      </div>
      <p className="study-note">This is <strong>not a matched-training model comparison</strong>: the extractive reader was fine-tuned on SQuAD2, while the generators were not. The study isolates a practical failure mode under narrow prompts and budgets.</p>
      <SourceLink href={docs("docs/MICRO_ORACLE_VS_EXTRACTIVE_RESULTS.md")}>Read the controlled model study</SourceLink>
    </section>
    <GraphStudy grf00={data.grf00} grf01={data.grf01}/>
    <section className="study">
      <div className="study-heading">
        <div><p className="overline">05 / INFERENCE OPTIMIZATION</p><h2>Quantization reduced model-file size and batch time.</h2></div>
        <span className="study-scope">Ragability pair classification · same public benchmark</span>
      </div>
      <div className="compare-figures three">
        <div><span>Model weight file</span><strong>−69.2%</strong><small>PyTorch FP32 → ONNX INT8</small></div>
        <div><span>Measured batch time</span><strong>−38.1%</strong><small>One sequential CPU run</small></div>
        <div><span>Correct pair labels</span><strong>261 <em>→</em> 269</strong><small>Out of 318 correlated pairs</small></div>
      </div>
      <p className="study-note">No whole-system RAM or end-to-end RAG speed claim follows from these measurements. The derived pairs are correlated.</p>
      <SourceLink href={docs("docs/MICRO_V02_ONNX_RESULTS.md")}>Read the quantization study</SourceLink>
    </section>
    <section className="study">
      <div className="study-heading">
        <div><p className="overline">06 / CONTRADICTORY REFERENCES</p><h2>Off-the-shelf NLI did not transfer cleanly to viewpoint grouping.</h2></div>
        <span className="study-scope">ConfRAG DEV · 16 original question groups</span>
      </div>
      <MetricBars heading="Different-viewpoint pair accuracy · task-transfer diagnostic" rows={[
        {label:"Lexical Jaccard control",value:164/240,printed:"164 / 240",emphasis:true},
        {label:"DeBERTa NLI",value:124/240,printed:"124 / 240"},
        {label:"MiniLM2 NLI",value:120/240,printed:"120 / 240"},
      ]}/>
      <p className="study-note">The 240 pairs are <strong>not independent questions</strong>. Different annotated viewpoints do not necessarily contradict each other; this is not an end-to-end factual QA score.</p>
      <SourceLink href={docs("docs/PAPER_01_CONFRAG_DEV_RESULTS.md")}>Read the source and uncertainty audit</SourceLink>
    </section>
    <RealRetrievalReplay />
  </article>;
}
function Methodology() {
  return <article className="page-content methodology-page">
    <header className="page-heading">
      <p className="overline">Methods · source provenance · limitations</p>
      <h1>Results are useful only with their conditions.</h1>
      <p>The laboratory documents what was measured, what remains unverified and how to reproduce the underlying code and experiments.</p>
    </header>
    <section className="method-block">
      <h2>What is measured</h2>
      <p>Retrieval ranking, small-model task performance, citation provenance and selected CPU batch timings. Experiments document their source cohorts, checkpoints and original reports. No metric is treated as a universal quality score.</p>
      <div className="method-columns">
        <div><h3>Measured</h3><p>BEIR SciFact retrieval and reranking, public HotpotQA graph cohorts, small-model CPU pilots, NLI transfer diagnostics and quantization.</p></div>
        <div><h3>Not yet measured independently</h3><p>General factual correctness of a complete real-document RAG system, calibrated answer risk, held-out human-reviewed semantic support and full-pipeline CPU efficiency.</p></div>
      </div>
    </section>
    <section className="method-block">
      <h2>How evidence is handled</h2>
      <ol className="method-steps">
        <li><strong>Sources are identified.</strong> Each stored document has a provenance identity; the structured demo checks original quote offsets and document hashes.</li>
        <li><strong>Comparisons are bounded.</strong> Results from separate datasets or CPU environments are not presented as controlled head-to-head rankings.</li>
        <li><strong>Failures stay visible.</strong> Negative graph experiments and unsuccessful tiny-model generations are recorded rather than discarded.</li>
        <li><strong>Uncertainty is disclosed.</strong> Correlated derived pairs are not treated as independent observations; public development data do not count as sealed holdouts.</li>
      </ol>
    </section>
    <section className="method-block">
      <h2>Research status</h2>
      <p>A working manuscript explores selective question answering on commodity CPUs with a total budget of ≤135M active neural parameters. The proposed confirmatory study requires a real-document pipeline, matched baselines and independently reviewed data. The paper has not been submitted or peer-reviewed.</p>
      <div className="paper-links">
        <SourceLink href={docs("docs/RESEARCH_STATUS.md")}>Research status</SourceLink>
        <SourceLink href={docs("docs/PAPER_01_MICRO_CPU_FRONTIER_PROTOCOL.md")}>Experimental protocol</SourceLink>
        <SourceLink href={docs("docs/REPRODUCIBILITY.md")}>Reproducibility guide</SourceLink>
        <SourceLink href={docs("papers/micro-cpu-frontier/WORKING_MANUSCRIPT.md")}>Working manuscript</SourceLink>
      </div>
    </section>
    <section className="method-block last">
      <h2>Reproduce the software</h2>
      <p>Default integrity checks do not require paid inference APIs, neural weight downloads or a hosted database. Model-backed studies have separate data and environment requirements.</p>
      <pre className="code-sample">{'git clone ' + REPO + '.git\ncd rag-architecture-lab\npython -m pip install -e ".[dev]"\npython -m pytest -q\npython -m raglab.release_readiness'}</pre>
      <p className="method-small">Python 3.11+. An independent replication must additionally pin datasets, model revisions, hardware, seeds and result artifacts.</p>
    </section>
  </article>;
}
export default function App() {
  const [page,setPage] = useState<Page>(fromHash);
  const [theme,setTheme] = useState<"light"|"dark">("light");
  const [data,setData] = useState<ObservatoryData | null>(null);
  const [error,setError] = useState<string | null>(null);
  useEffect(() => {
    const change = () => setPage(fromHash());
    window.addEventListener("hashchange",change);
    return () => window.removeEventListener("hashchange",change);
  },[]);
  useEffect(() => { document.documentElement.dataset.theme = theme; },[theme]);
  useEffect(() => {
    let mounted=true;
    loadObservatory()
      .then((value) => { if(mounted) setData(value); })
      .catch((reason:unknown) => { if(mounted) setError(reason instanceof Error ? reason.message : "Source verification failed"); });
    return () => { mounted=false; };
  },[]);
  function navigate(next:Page) {
    window.location.hash=next;
    setPage(next);
    window.scrollTo({top:0,behavior:"auto"});
  }
  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="site-header">
      <div className="header-inner">
        <button type="button" className="brand" aria-label="RAG Architecture Lab, research home" onClick={() => navigate("research")}>
          <span className="brand-symbol" aria-hidden="true">R<span>/</span></span>
          <span>RAG Architecture Lab</span>
        </button>
        <nav aria-label="Research sections" className="header-nav">
          {PAGES.map((item) => <button type="button" key={item.id} aria-current={item.id===page ? "page" : undefined} onClick={() => navigate(item.id)}>{item.label}</button>)}
        </nav>
        <div className="header-tools">
          <button type="button" className="theme-switch" onClick={() => setTheme(theme==="light"?"dark":"light")} aria-label={theme==="light"?"Use dark theme":"Use light theme"}>{theme==="light"?"◐":"☼"}</button>
          <a className="header-source" href={REPO} target="_blank" rel="noreferrer">GitHub <span aria-hidden="true">↗</span></a>
        </div>
      </div>
    </header>
    <main id="main-content" className="site-main">
      {page==="research" ? <Research navigate={navigate}/> : page==="experiments" ? (
        error ? <div role="alert" className="data-error"><h1>Verified study data unavailable</h1><p>{error}</p><p>The interface will not invent results.</p></div> :
        !data ? <p role="status" className="loading">Validating published study data…</p> :
        <Experiments data={data}/>
      ) : <Methodology/>}
    </main>
    <footer className="site-footer">
      <span>RAG Architecture Lab · Independent research software</span>
      <span>Recorded experiments · No live model inference · <a href={REPO} target="_blank" rel="noreferrer">Source code ↗</a></span>
    </footer>
  </>;
}
