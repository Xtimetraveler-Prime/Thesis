from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.matched_summary import write_matched_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble scope-checked FPGA/Brian2Loihi/Catalyst matched MNIST evidence."
    )
    parser.add_argument(
        "--accepted-validation",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1/accepted_software_validation.json"),
    )
    parser.add_argument("--brian-suite", type=Path, required=True)
    parser.add_argument("--catalyst-suite", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("applications/mnist/build/matched-reference/comparison_summary.json"),
    )
    args = parser.parse_args()
    output = write_matched_summary(
        args.accepted_validation,
        args.brian_suite,
        args.catalyst_suite,
        args.output,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    print(
        f"matched comparison summary: cases={payload['matched_scope']['case_count']} "
        f"brian_prediction_agreement={payload['brian2loihi_matched_scope']['prediction_agreement_cases']} "
        f"catalyst_graph_prediction_agreement={payload['catalyst_matched_scope']['graph_prediction_agreement_cases']} "
        f"output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
