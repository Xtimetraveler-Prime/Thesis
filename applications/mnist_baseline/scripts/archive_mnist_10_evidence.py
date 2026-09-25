from __future__ import annotations

import argparse
import json
from pathlib import Path

from mnist_app.characterization_evidence import archive_physical_timing_evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the four accepted MNIST-10 physical timing runs and archive "
            "their compact evidence outside the ignored build tree."
        )
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path("applications/mnist_baseline/build/mnist-10"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("applications/mnist_baseline/evidence/mnist-10/physical-timing-v1"),
    )
    args = parser.parse_args()

    manifest_path = archive_physical_timing_evidence(args.build_dir, args.output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(
        "MNIST-10 physical timing evidence archived: "
        f"cases={manifest['case_count']} all_passed={manifest['all_passed']}"
    )
    for case in manifest["cases"]:
        print(
            f"  {case['profile']:14s} index={case['mnist_test_index']:5d} "
            f"label={case['label']} cycles={case['total_cycles']} "
            f"latency_ms={case['latency_ms_at_100mhz']:.6f} "
            f"prediction={case['physical_prediction']}"
        )
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
