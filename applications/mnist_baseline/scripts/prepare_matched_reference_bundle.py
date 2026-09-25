from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.matched_bundle import scope_indices, write_matched_request_bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare immutable native-sparse MNIST schedules/golden outputs for external matched backends."
    )
    parser.add_argument("--scope", choices=("anchor", "corpus", "full"), default="anchor")
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist_baseline/frozen/mnist-v1"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("applications/mnist_baseline/build/matched-reference/anchor.bundle.json"),
    )
    args = parser.parse_args()

    indices = scope_indices(args.scope, args.frozen_root)
    output = write_matched_request_bundle(args.frozen_root, indices, args.output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    total_events = sum(int(case["total_input_events"]) for case in payload["cases"])
    print(
        f"matched MNIST bundle: scope={args.scope} cases={payload['case_count']} "
        f"events={total_events} output={output}"
    )
    print(
        "provenance: deployment_sha256="
        f"{payload['provenance']['deployment_sha256']} weight_storage_sha256="
        f"{payload['provenance']['weight_storage_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
