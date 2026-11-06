"""One explicitly requested paid Jev batch over a saved analysis, without OCR reruns.

Supply TYPESAFE_API_KEY through the process environment or a secret manager.
The script never writes credentials. It does not retry a failed request.
"""

import argparse
import json
from pathlib import Path

from app.schemas.analysis import Analysis
from app.services.decision import judge_fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="evaluation/public-image-result.json")
    parser.add_argument("--output", default="evaluation/public-image-jev-result.json")
    args = parser.parse_args()
    analysis = Analysis.model_validate(json.loads(Path(args.input).read_text())["analysis"])
    decision = judge_fields(analysis.fields)
    report = {"input": args.input, "decision": decision.model_dump(mode="json"),
        "note": "One batch. Suggestions only; original evidence and conflicts unchanged."}
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(decision.model_dump_json(indent=2))
    if decision.status != "ok":
        raise SystemExit("Jev did not return valid recommendations; see saved result. No retry was made.")


if __name__ == "__main__":
    main()
