from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from mnist_app.runtime import (
    build_runtime_request,
    validate_runtime_result,
    write_runtime_request,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify one MNIST test image on the reusable dual-profile FPGA runtime."
    )
    parser.add_argument("--profile", required=True, choices=("cropped-dense", "native-sparse"))
    parser.add_argument("--index", required=True, type=int)
    parser.add_argument(
        "--frozen-root",
        type=Path,
        default=Path("applications/mnist/frozen/mnist-v1"),
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path("applications/mnist/build/mnist-09"),
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Generate/verify the host request without invoking Vivado hardware.",
    )
    args = parser.parse_args()

    request = build_runtime_request(
        args.frozen_root,
        profile=args.profile,
        mnist_test_index=args.index,
    )
    request_dir = args.build_dir / "requests" / f"{args.profile}-index{args.index:05d}"
    request_json, events_tsv = write_runtime_request(request, request_dir)
    print(
        f"MNIST-09 request: profile={request.profile} index={request.mnist_test_index} "
        f"label={request.label} events={request.total_events} "
        f"golden_prediction={request.golden_prediction}"
    )
    print(f"request: {request_json}")
    print(f"events:  {events_tsv}")
    if args.prepare_only:
        return 0

    vivado = shutil.which("vivado")
    if vivado is None:
        raise SystemExit("Vivado is not on PATH. Source Vivado 2025.2 settings64.sh first.")

    artifact_dir = args.build_dir / "artifacts"
    bitstream = artifact_dir / "neuromorphic_twin_mnist_09.bit"
    probes = artifact_dir / "neuromorphic_twin_mnist_09.ltx"
    tcl = Path("applications/mnist/fpga/vivado/classify_mnist_09_runtime.tcl")
    for path in (bitstream, probes, tcl):
        if not path.is_file():
            raise SystemExit(
                f"Required runtime artifact missing: {path}. "
                "Run applications/mnist/fpga/run_mnist_09_bitstream.sh first."
            )

    result_json = request_dir / "physical_result.json"
    cmd = [
        vivado,
        "-mode",
        "batch",
        "-source",
        str(tcl),
        "-tclargs",
        str(bitstream),
        str(probes),
        str(request.profile_id),
        request.profile,
        str(request.mnist_test_index),
        str(events_tsv),
        str(result_json),
    ]
    subprocess.run(cmd, check=True)

    payload = json.loads(result_json.read_text(encoding="utf-8"))
    comparison = validate_runtime_result(request, payload)
    comparison_path = request_dir / "comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    status = "PASS" if comparison["passed"] else "FAIL"
    print(
        f"MNIST-09 {status}: profile={request.profile} index={request.mnist_test_index} "
        f"label={request.label} prediction={comparison['physical_prediction']} "
        f"golden={comparison['golden_prediction']} mismatches={comparison['mismatches']}"
    )
    print(f"comparison: {comparison_path}")
    return 0 if comparison["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
