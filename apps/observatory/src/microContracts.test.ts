import { describe, expect, it } from "vitest";
import sourceReplay from "../../../experiments/micro_v02_observatory_replay.json";
import { validateMicroReplayShape } from "./microContracts";

describe("MICRO-RAG verified Python software replay", () => {
  it("accepts the original four executed states and verbatim source offsets", () => {
    const result = validateMicroReplayShape(sourceReplay);
    expect(result.cases.map((c) => c.status)).toEqual([
      "CONFLICT", "ANSWER", "INSUFFICIENT", "REVIEW"
    ]);
    expect(result.cases[0]?.citations.map((c) => c.quote)).toEqual(["2015", "2012"]);
    expect(result.cases[1]?.answer).toBe("2019");
    expect(result.cases[2]?.citations).toHaveLength(0);
    expect(result.cases[3]?.source_sweep_complete).toBe(false);
  });

  it("refuses a modified quotation even if source ID still exists", () => {
    const data = structuredClone(sourceReplay);
    const quote = data.cases[0]?.citations[0];
    if (!quote) throw new Error("Fixture corruption");
    quote.quote = "fictitious";
    expect(() => validateMicroReplayShape(data)).toThrow(/verbatim original/);
  });

  it("refuses mismatched hashes and fabricated sources", () => {
    const data = structuredClone(sourceReplay);
    const citation = data.cases[1]?.citations[0];
    if (!citation) throw new Error("Fixture corruption");
    citation.document_sha256 = "a".repeat(64);
    expect(() => validateMicroReplayShape(data)).toThrow(/verbatim original/);
    citation.document_sha256 = sourceReplay.cases[1]!.citations[0]!.document_sha256;
    citation.doc_id = "missing-document";
    expect(() => validateMicroReplayShape(data)).toThrow(/not inspected or missing/);
  });

  it("never accepts a published answer on CONFLICT, REVIEW or INSUFFICIENT", () => {
    for (const position of [0, 2, 3]) {
      const data = structuredClone(sourceReplay);
      data.cases[position]!.answer = "2019";
      expect(() => validateMicroReplayShape(data)).toThrow(/Only ANSWER/);
    }
  });

  it("requires a truthful fixed fictional-software-replay label", () => {
    const data = structuredClone(sourceReplay);
    data.status = "PRODUCTION_CERTIFIED" as typeof data.status;
    expect(() => validateMicroReplayShape(data)).toThrow(/Unverified or mislabeled/);
  });
});
