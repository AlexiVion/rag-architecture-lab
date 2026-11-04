"""M2-SYNTH-01: fixed 24-case synthetic QA protocol and narrow observable metrics.

This is not an independent natural-language semantic truth benchmark. Source
facts and expected responses derive from hand-authored fictional templates.
No test qrels, commercial API, model, embeddings or external files are needed.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

STUDY_ID = "M2-SYNTH-01-SEALED-DEV-TEMPLATE-QA"
SCHEMA_VERSION = 1
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
PROMPT_SHA256 = "2351f8f969281b7e92c9a827c8f3da79643d75a88c06f6c1c53faf68b25d3246"
PROMPT_VERSION = "m2-v02-cited-or-abstain-v1"
ABSTAIN = "INSUFFICIENT_EVIDENCE"
CATEGORIES = ("answerable", "irrelevant", "conflicting", "no_context")
SOURCE_TEMPLATE_VERSION = "M2-SYNTH-01-v1"

# None of these fictional entities or firms appear in M2-LIVE-01/02
# or in the fixed few-shot instruction examples. Six groups are frozen.
GROUPS = (
    ("Kestrel Explorer", "Quill Vector Unit", "Fjord Dynamics",
     "Mantis Flyer", "Helix Pressure Unit", "Crescent Labs"),
    ("Boreal Cartographer", "Prism Course Module", "Oakwave Systems",
     "Cinder Vessel", "Cobalt Radar Unit", "Vantage Mechanica"),
    ("Mistral Rover", "Lumen Wayfinder", "Tundra Research",
     "Vesper Drone", "Gale Optical Sensor", "Oxbow Devices"),
    ("Carmine Surveyor", "Delta Route Array", "Harborline Robotics",
     "Orchid Skimmer", "Vivid Sonar Beacon", "Cairn Instruments"),
    ("Ravenna Probe", "Nimbus Compass Unit", "Brightfield Engineering",
     "Saffron Orbiter", "Polar Thermal Sensor", "Falcon Workshop"),
    ("Arden Crawler", "Pulsar Guidance Node", "Thornwood Automation",
     "Pioneer Glider", "Juniper Altitude Gauge", "Bluepeak Science"),
)


def _doc(doc_id: str, title: str, text: str) -> dict[str, str]:
    return {"id": doc_id, "title": title, "text": text}


def build_cases() -> list[dict[str, Any]]:
    """Return 6 x 4 deterministic, balanced source/question controls.

    Gold data are separate from sources; callers must NEVER add expected_*
    fields to question prompts or the generator context.
    """
    cases = []
    for group, (vehicle, instrument, maker, foil_vehicle, foil_instrument, foil_maker) in enumerate(GROUPS, start=1):
        question = f"Which company developed the {instrument} installed on the {vehicle}?"
        prefix = f"M2S{group:02d}"
        specs = (
            (
                "answerable",
                [_doc(prefix + "-a", f"Equipment record: {vehicle}",
                      f"The {instrument} installed on the {vehicle} was developed by {maker}.")],
                "answer", maker,
            ),
            (
                "irrelevant",
                [_doc(prefix + "-i", f"Equipment inventory: {vehicle}",
                      f"The {vehicle} has a navigation device. Separately, the "
                      f"{foil_instrument} installed on the {foil_vehicle} was developed by {foil_maker}.")],
                "abstain", None,
            ),
            (
                "conflicting",
                [_doc(prefix + "-c1", f"Equipment claim A: {vehicle}",
                      f"The {instrument} installed on the {vehicle} was developed by {maker}."),
                 _doc(prefix + "-c2", f"Equipment claim B: {vehicle}",
                      f"The {instrument} installed on the {vehicle} was developed by {foil_maker}.")],
                "abstain", None,
            ),
            ("no_context", [], "abstain", None),
        )
        for category, docs, behavior, reference in specs:
            cases.append({
                "case_id": f"{prefix}-{category}",
                "category": category,
                "question": question,
                "sources": docs,
                "expected_behavior": behavior,
                "expected_literal_if_answerable": reference,
                "forbidden_distractor_literal": foil_maker,
                "source_selection": "fixed_templates_no_retrieval_benchmark",
            })
    assert len(cases) == 24
    return cases


def canonical_sha256(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def frozen_cases_sha256() -> str:
    return canonical_sha256(build_cases())


EXPECTED_CASES_SHA256 = "05e778d4b541d397c27a000d4042549d84b90d047a28f1bbf16b289bda6a3826"


def validate_protocol() -> list[dict[str, Any]]:
    cases = build_cases()
    if canonical_sha256(cases) != EXPECTED_CASES_SHA256:
        raise ValueError("M2-SYNTH-01 case corpus deviates from preregistered SHA256")
    counts = Counter(item["category"] for item in cases)
    if counts != {label: 6 for label in CATEGORIES}:
        raise ValueError("Unexpected case-class distribution")
    if len({item["case_id"] for item in cases}) != len(cases):
        raise ValueError("Repeated synthetic case identifier")
    if any(item["category"] == "no_context" and item["sources"] for item in cases):
        raise ValueError("A no-context source was contaminated")
    if any(item["category"] != "no_context" and not item["sources"] for item in cases):
        raise ValueError("Nonempty evidence condition lacks sources")
    if any(item["expected_literal_if_answerable"] in item["question"]
           for item in cases if item["category"] == "answerable"):
        raise ValueError("Answer leaked into a question")
    return cases


def score_observation(case: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    """NARROW deterministic control score, never a claim-level entailment judge."""
    if case["case_id"] != observation.get("case_id"):
        raise ValueError("Case ID differs from frozen case")
    category = case["category"]
    expected_calls = int(category != "no_context")
    if type(observation.get("model_calls")) is not int or observation["model_calls"] != expected_calls:
        raise ValueError("Wrong model call count")
    if observation.get("sent_to_external_system") is not False:
        raise ValueError("External publication in a quarantine-only experiment")
    if observation.get("source_ids") != [doc["id"] for doc in case["sources"]]:
        raise ValueError("Evidence IDs differ from frozen source mapping")
    raw = observation.get("raw_candidate")
    if category == "no_context":
        if raw is not None or observation.get("pipeline_status") != "abstained_no_context":
            raise ValueError("No-context must skip generator and abstain")
        return {
            "case_id": case["case_id"], "category": category,
            "control_success": True, "literal_match_diagnostic": None,
            "syntax_v2_pass": False, "abstention_marker_exact": False,
            "model_attempts_factual_answer_when_abstention_expected": False,
            "score_type": "deterministic_empty_context_control",
        }
    if not isinstance(raw, str) or not raw:
        raise ValueError("Actual model candidate text absent")
    if type(observation.get("syntax_v2_pass")) is not bool:
        raise ValueError("Opt-in syntactic citation verdict missing")
    syntax_v2 = observation["syntax_v2_pass"]
    exact_abstention = raw.strip() == ABSTAIN
    literal = case["expected_literal_if_answerable"]
    match = literal.lower() in raw.lower() if literal else None
    foil = case["forbidden_distractor_literal"].lower() in raw.lower()
    if category == "answerable":
        # Deliberately only a literal+syntax proxy. No automatic entailment.
        success = bool(match and syntax_v2 and not foil and not exact_abstention)
    else:
        success = exact_abstention
    return {
        "case_id": case["case_id"], "category": category,
        "control_success": success,
        "literal_match_diagnostic": match,
        "syntax_v2_pass": syntax_v2,
        "abstention_marker_exact": exact_abstention,
        "model_attempts_factual_answer_when_abstention_expected": (
            category in ("irrelevant", "conflicting") and not exact_abstention
        ),
        "score_type": (
            "literal_value_plus_source_syntax_proxy" if category == "answerable"
            else "exact_abstention_marker_control"
        ),
    }


def aggregate_controls(scores: list[dict[str, Any]]) -> dict[str, Any]:
    if len(scores) != 24 or len({row["case_id"] for row in scores}) != 24:
        raise ValueError("Expected exactly 24 distinct scored synthetic controls")
    cases = validate_protocol()
    if [s["case_id"] for s in scores] != [c["case_id"] for c in cases]:
        raise ValueError("Scored cases do not follow frozen case order")
    groups = {}
    for category in CATEGORIES:
        members = [row for row in scores if row["category"] == category]
        if len(members) != 6:
            raise ValueError("Unbalanced category score")
        groups[category] = {
            "n": 6,
            "success_count": sum(row["control_success"] for row in members),
            "control_success_rate": sum(row["control_success"] for row in members) / 6,
            "experimental_syntax_pass_count": sum(row["syntax_v2_pass"] for row in members),
            "model_declared_abstention_count": sum(row["abstention_marker_exact"] for row in members),
            "factual_attempts_when_abstention_expected": sum(
                row["model_attempts_factual_answer_when_abstention_expected"]
                for row in members
            ),
        }
    return {
        "study_id": STUDY_ID,
        "source_cases_sha256": EXPECTED_CASES_SHA256,
        "prompt_sha256": PROMPT_SHA256,
        "total_cases": 24,
        "by_category": groups,
        "primary_metric_name": "synthetic_control_success_rate_NOT_semantic_accuracy",
        "primary_control_success_rate": sum(row["control_success"] for row in scores) / 24,
        "semantics_warning": (
            "Programmatic gold is valid only within authored fictional templates. "
            "Answerable class uses a literal+syntax proxy, not sentence entailment. "
            "No human-labelled source truth, model-wide faithfulness or test independence is established."
        ),
    }
