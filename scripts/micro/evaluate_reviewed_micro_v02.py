"""Score source-grouped reviewed QA labels, but never auto-certify reviewers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from raglab.micro_v02.__main__ import _load_json, load_documents
from raglab.micro_v02.pipeline import MicroRAG
from raglab.micro_v02.evaluation import write_json
from raglab.micro_v02.reviewed_eval import evaluate_reviewed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents",required=True)
    parser.add_argument("--records",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--iterations",type=int,default=2000,
                        help="Source-group bootstrap draws")
    args=parser.parse_args()
    rows=_load_json(args.records)
    if not isinstance(rows,list):
        raise ValueError("Reviewer case input must be a JSON list")
    result=evaluate_reviewed(
        MicroRAG(load_documents(args.documents)),
        rows,repetitions=args.iterations,
    )
    write_json(Path(args.output),result)
    print(json.dumps({
        "status":result["status"],
        "scientific_release_approved":result["scientific_release_approved"],
        "software_target_checks_met":result["software_target_checks_met"],
        "evaluation_only":result["evaluation_only"],
    },sort_keys=True))


if __name__=="__main__":
    main()
