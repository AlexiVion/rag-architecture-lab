/** M6 public artifact contract: offline Python engine replay, NOT live inference. */
export type MicroDecision = "ANSWER" | "CONFLICT" | "INSUFFICIENT" | "REVIEW";
export type MicroSource = {
  id: string; title: string; text: string; sha256: string;
};
export type MicroCitation = {
  doc_id: string; start: number; end: number;
  quote: string; document_sha256: string;
};
export type MicroCase = {
  id: string; label: string; question: string; status: MicroDecision;
  answer: string | null; citations: MicroCitation[];
  inspected_doc_ids: string[]; retrieved_doc_ids: string[];
  source_sweep_complete: boolean; read_calls: number;
  scan_budget: number; warnings: string[];
};
export type MicroReplay = {
  schema_version: 1; kind: "micro_v02_engine_execution_replay";
  status: "FICTIONAL_STRUCTURED_CPU_SOFTWARE_REPLAY_NOT_LIVE_AI";
  generated_by: string; source_fixture: string;
  sources: MicroSource[]; cases: MicroCase[];
  method: string; limitations: string[];
};
const HASH = /^[a-f0-9]{64}$/;
const STATES: MicroDecision[] = [
  "CONFLICT", "ANSWER", "INSUFFICIENT", "REVIEW"
];

function object(x: unknown, label: string): Record<string, unknown> {
  if (typeof x !== "object" || x === null || Array.isArray(x))
    throw new Error(label + " must be an object");
  return x as Record<string, unknown>;
}
function text(x: unknown, label: string): string {
  if (typeof x !== "string" || !x.trim())
    throw new Error(label + " must be nonempty text");
  return x;
}
function list(x: unknown, label: string): unknown[] {
  if (!Array.isArray(x)) throw new Error(label + " must be an array");
  return x;
}
function integer(x: unknown, label: string): number {
  if (!Number.isSafeInteger(x) || (x as number) < 0)
    throw new Error(label + " must be a nonnegative integer");
  return x as number;
}
function hash(x: unknown, label: string): string {
  if (typeof x !== "string" || !HASH.test(x))
    throw new Error(label + " has invalid SHA256");
  return x;
}
function stringList(x: unknown, label: string): string[] {
  return list(x, label).map((v) => text(v, label + " entry"));
}

export function validateMicroReplayShape(input: unknown): MicroReplay {
  const root = object(input, "Micro replay");
  if (root.schema_version !== 1
      || root.kind !== "micro_v02_engine_execution_replay"
      || root.status !== "FICTIONAL_STRUCTURED_CPU_SOFTWARE_REPLAY_NOT_LIVE_AI")
    throw new Error("Unverified or mislabeled Micro replay");
  text(root.generated_by, "generator"); text(root.source_fixture, "source fixture");
  text(root.method, "execution method");
  const limitations = stringList(root.limitations, "limitations");
  if (!limitations.some((x) => x.toLowerCase().includes("fictional")))
    throw new Error("Fictional-data disclosure is mandatory");
  const sources = list(root.sources, "sources").map((value) => {
    const s = object(value, "source");
    return {
      id: text(s.id, "source ID"),
      title: text(s.title, "source title"),
      text: text(s.text, "original source text"),
      sha256: hash(s.sha256, "source"),
    };
  });
  if (!sources.length || sources.length > 20)
    throw new Error("Expected bounded original source count");
  if (new Set(sources.map((s) => s.id)).size !== sources.length)
    throw new Error("Duplicate source IDs");
  const byId = new Map(sources.map((s) => [s.id, s]));
  const cases = list(root.cases, "cases").map((value) => {
    const c = object(value, "case");
    const id = text(c.id, "case ID");
    const status = text(c.status, "status") as MicroDecision;
    if (!STATES.includes(status)) throw new Error("Unknown replay state");
    const answer = c.answer;
    if (answer !== null && typeof answer !== "string")
      throw new Error("Answer must be null or a string");
    if ((status === "ANSWER") !== (typeof answer === "string" && !!answer.trim()))
      throw new Error("Only ANSWER may publish a nonempty answer");
    const inspected_doc_ids = stringList(c.inspected_doc_ids, "inspected sources");
    const retrieved_doc_ids = stringList(c.retrieved_doc_ids, "retrieved sources");
    for (const sourceId of [...inspected_doc_ids, ...retrieved_doc_ids]) {
      if (!byId.has(sourceId)) throw new Error("Replay refers to unknown source ID");
    }
    const citations = list(c.citations, "citations").map((value) => {
      const cite = object(value, "citation");
      const doc_id = text(cite.doc_id, "citation source");
      const source = byId.get(doc_id);
      if (!source || !inspected_doc_ids.includes(doc_id))
        throw new Error("Citation source not inspected or missing");
      const start = integer(cite.start, "citation start");
      const end = integer(cite.end, "citation end");
      const quote = text(cite.quote, "source quote");
      const document_sha256 = hash(cite.document_sha256, "citation");
      if (end <= start || end > source.text.length ||
          source.text.slice(start, end) !== quote ||
          source.sha256 !== document_sha256)
        throw new Error("Source citation does not match verbatim original");
      return { doc_id, start, end, quote, document_sha256 };
    });
    if (status === "ANSWER" &&
        (!citations.length || citations.some((cite) => cite.quote !== answer)))
      throw new Error("Answer differs from its exact original source quotations");
    if (status === "CONFLICT" &&
        (new Set(citations.map((cite) => cite.doc_id)).size < 2 ||
         new Set(citations.map((cite) => cite.quote)).size < 2))
      throw new Error("Conflict requires incompatible values from distinct original sources");
    if (status === "REVIEW" && c.source_sweep_complete !== false)
      throw new Error("Demo review must have incomplete source coverage");
    if (typeof c.source_sweep_complete !== "boolean")
      throw new Error("Missing source coverage status");
    return {
      id,
      label: text(c.label, "case label"),
      question: text(c.question, "question"),
      status, answer: answer as string | null,
      citations, inspected_doc_ids, retrieved_doc_ids,
      source_sweep_complete: c.source_sweep_complete,
      warnings: stringList(c.warnings, "warnings"),
      read_calls: integer(c.read_calls, "reader calls"),
      scan_budget: integer(c.scan_budget, "scan budget"),
    };
  });
  if (cases.length !== STATES.length ||
      cases.some((c, i) => c.status !== STATES[i]) ||
      new Set(cases.map((c) => c.id)).size !== cases.length)
    throw new Error("Four ordered distinct replay decisions required");
  return {
    schema_version: 1, kind: "micro_v02_engine_execution_replay",
    status: "FICTIONAL_STRUCTURED_CPU_SOFTWARE_REPLAY_NOT_LIVE_AI",
    generated_by: root.generated_by as string,
    source_fixture: root.source_fixture as string,
    sources, cases, method: root.method as string, limitations,
  };
}

async function sourceSha256(textValue: string): Promise<string> {
  if (!crypto?.subtle?.digest) throw new Error("Browser SHA256 unavailable");
  const bytes = new TextEncoder().encode(textValue);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
}

export async function loadMicroReplay(): Promise<MicroReplay> {
  const response = await fetch(import.meta.env.BASE_URL + "data/micro-v02-replay.json");
  if (!response.ok) throw new Error("Micro replay artifact unavailable");
  const parsed = validateMicroReplayShape(await response.json());
  for (const source of parsed.sources) {
    if (await sourceSha256(source.text) !== source.sha256)
      throw new Error("Original source hash failed verification");
  }
  return parsed;
}
