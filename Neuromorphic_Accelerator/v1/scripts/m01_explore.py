#!/usr/bin/env python3
"""M01 no-board, no-overwrite reproducible DDR *traffic* comparison CLI.

Run from any working directory; source namespace is resolved relative to this
script. No Vivado, JTAG, external files, neural weights, or MNIST required.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m01_residency import (
    LOCALITIES, StudyConfig, run_study,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neuron-count", type=int, default=4096)
    parser.add_argument("--state-bytes", type=int, default=16)
    parser.add_argument("--resident-budget-bytes", type=int, default=2048)
    parser.add_argument("--block-neurons", type=int, default=16)
    parser.add_argument("--hybrid-pinned-neurons", type=int, default=32)
    parser.add_argument("--max-transfer-bytes", type=int, default=256)
    parser.add_argument("--active-neurons", type=int, default=64)
    parser.add_argument("--requests", type=int, default=512)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--locality", choices=(*LOCALITIES, "both"), default="both")
    parser.add_argument("--illustrative-transaction-overhead-ns", type=float)
    parser.add_argument("--illustrative-bandwidth-mbps", type=float)
    parser.add_argument("--out", type=Path,
                        help="exclusive-create JSON path (never overwrite); omit to print JSON")
    a = parser.parse_args(argv)
    config = StudyConfig(
        neuron_count=a.neuron_count,
        state_bytes=a.state_bytes,
        resident_budget_bytes=a.resident_budget_bytes,
        block_neurons=a.block_neurons,
        hybrid_pinned_neurons=a.hybrid_pinned_neurons,
        max_transfer_bytes=a.max_transfer_bytes,
    )
    try:
        config.validate()
        localities = LOCALITIES if a.locality == "both" else (a.locality,)
        studies = {
            locality: run_study(
                config,
                active_neurons=a.active_neurons,
                requests=a.requests,
                seed=a.seed,
                locality=locality,
                illustrative_transaction_overhead_ns=(
                    a.illustrative_transaction_overhead_ns
                ),
                illustrative_bandwidth_mbps=a.illustrative_bandwidth_mbps,
            )
            for locality in localities
        }
        payload = {
            "experiment": "M01_COLD_STATE_RESIDENCY_PC_ONLY",
            "warning": (
                "MODELED WRITING STATE-ACCESS TRAFFIC, NOT ACTUAL LIF INFERENCE, "
                "SNN EVENTS, KV260 LATENCY, DDR TIMING, BANDWIDTH, OR ENERGY"
            ),
            "studies": studies,
        }
        output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if a.out is None:
            sys.stdout.write(output)
        else:
            # 'x' refuses existing regular files and symlinks (including broken
            # symlinks); no established evidence is ever silently replaced.
            with a.out.open("x", encoding="utf-8") as handle:
                handle.write(output)
            print(f"M01_PC_ONLY_RESULT_PATH={a.out}")
        print("M01_PC_ONLY_TRAFFIC_MODEL_PASS=1", file=sys.stderr)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
