from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from mnist_app.characterization_runtime import (
    expected_tick_cycles,
    expected_tick_synapse_visits,
    validate_timing_result,
    write_timing_runtime_tcl,
)
from mnist_app.runtime import build_runtime_request, write_runtime_request


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Physically characterize one MNIST runtime request with the passive "
            "M12.5 tick-cycle boundary."
        )
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
        default=Path("applications/mnist/build/mnist-10"),
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Build the request and exact expected cycle vector without invoking Vivado hardware.",
    )
    args = parser.parse_args()

    request = build_runtime_request(
        args.frozen_root,
        profile=args.profile,
        mnist_test_index=args.index,
    )
    request_dir = args.build_dir / "timing_requests" / f"{args.profile}-index{args.index:05d}"
    request_json, events_tsv = write_runtime_request(request, request_dir)
    visits = expected_tick_synapse_visits(request, args.frozen_root)
    expected_cycles = expected_tick_cycles(request, args.frozen_root)
    expectation = {
        "schema": "neuromorphic-twin-mnist-timing-expectation-v1",
        "profile": request.profile,
        "mnist_test_index": request.mnist_test_index,
        "label": request.label,
        "events_per_tick": [len(events) for events in request.external_schedule],
        "synapse_visits_per_tick": list(visits),
        "expected_tick_cycles": list(expected_cycles),
        "expected_total_cycles": sum(expected_cycles),
        "expected_latency_ms_at_100mhz": sum(expected_cycles) / 100_000.0,
        "equation": "170 + 4*external_events + 4*CSR_synapse_visits per tick",
        "evidence_status": "prediction from M12.5 physically measured no-route timing decomposition",
    }
    expectation_path = request_dir / "timing_expectation.json"
    expectation_path.write_text(
        json.dumps(expectation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        f"MNIST-10 timing request: profile={request.profile} index={request.mnist_test_index} "
        f"label={request.label} events={request.total_events} "
        f"visits={sum(visits)} expected_cycles={sum(expected_cycles)} "
        f"expected_latency_ms={sum(expected_cycles) / 100_000.0:.6f}"
    )
    print(f"request:     {request_json}")
    print(f"events:      {events_tsv}")
    print(f"expectation: {expectation_path}")
    if args.prepare_only:
        return 0

    vivado = shutil.which("vivado")
    if vivado is None:
        raise SystemExit("Vivado is not on PATH. Source Vivado 2025.2 settings64.sh first.")

    artifact_dir = args.build_dir / "artifacts"
    bitstream = artifact_dir / "neuromorphic_twin_mnist_10.bit"
    probes = artifact_dir / "neuromorphic_twin_mnist_10.ltx"
    source_tcl = Path("applications/mnist/fpga/vivado/classify_mnist_09_runtime.tcl")
    timing_tcl = args.build_dir / "classify_mnist_10_timing.tcl"
    for path in (bitstream, probes, source_tcl):
        if not path.is_file():
            raise SystemExit(
                f"Required timing artifact missing: {path}. "
                "Run applications/mnist/fpga/run_mnist_10_bitstream.sh first."
            )
    write_timing_runtime_tcl(source_tcl, timing_tcl)

    result_json = request_dir / "physical_timing_result.json"
    cmd = [
        vivado,
        "-mode",
        "batch",
        "-source",
        str(timing_tcl),
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
    comparison = validate_timing_result(request, args.frozen_root, payload)
    comparison_path = request_dir / "timing_comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    status = "PASS" if comparison["passed"] else "FAIL"
    print(
        f"MNIST-10 {status}: profile={request.profile} index={request.mnist_test_index} "
        f"prediction={comparison['physical_prediction']} golden={comparison['golden_prediction']} "
        f"physical_cycles={comparison['physical_total_cycles']} "
        f"expected_cycles={comparison['expected_total_cycles']} "
        f"physical_latency_ms={comparison['physical_latency_ms']:.6f} "
        f"mismatches={comparison['mismatches']}"
    )
    print(f"comparison: {comparison_path}")
    return 0 if comparison["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
