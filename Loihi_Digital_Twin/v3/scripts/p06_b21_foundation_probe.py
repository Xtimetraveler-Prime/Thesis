#!/usr/bin/env python3
"""B2.1 OFF-BOARD SEEDED / UNTRAINED training-foundation test.

No real training, downloads, MNIST official test, frozen checkpoint, FPGA,
DDR writes or Track A edits. By default run 40 hidden, one synthetic uint8
frame and original NetworkSpec independent 26-tick numerical oracle.
Optional --hidden 1000 --no-numerical --pack performs larger DENSE structural
resource admission only, CPU/RAM-intensive on an ordinary Linux workstation.
"""
from __future__ import annotations

import argparse
import json

import torch

from loihi_twin_v2.p06_b21_training_foundation import (
    B21IntegerSNN, B21Settings, foundation_manifest,
)
from loihi_twin_v2.p06_b14_monolithic import pixel_schedule_independent, simulate_monolithic
from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware


def run(hidden: int, *, numerical: bool, pack: bool) -> dict:
    settings = B21Settings(hidden_neurons=hidden)
    model = B21IntegerSNN.initialized(settings)
    manifest = foundation_manifest(settings, model)
    manifest["model_state"] = "SEEDED_UNTRAINED_B2_1_FOUNDATION"
    if numerical or pack:
        source = model.to_network_spec()
        manifest["source_graph_sha256"] = source.fingerprint
        assert len(source.input_projections[0].connections) == 784 * hidden
        assert len(source.projections[0].connections) == 10 * hidden
        if numerical:
            pixels = bytes((i * 37 + 11) % 256 for i in range(784))
            schedule = {"pixels": pixel_schedule_independent(pixels)}
            reference = simulate_monolithic(source, schedule, readout_population="readout")
            with torch.no_grad():
                actual = tuple(int(v) for v in model(
                    torch.tensor([list(pixels)], dtype=torch.uint8))[0])
            assert actual == reference.readout_spike_counts
            manifest["independent_26_tick_reference_sha256"] = reference.trace_sha256
            manifest["numerical_parity"] = "PASS_SYNTHETIC_SINGLE_FRAME"
            manifest["output_spike_counts"] = list(actual)
        if pack:
            packed = compile_synapse_aware(source, B12Options(readout_population="readout"))
            ledger = packed.capacity_audit
            assert all(c["logical_synapse_bytes"] <= 131072 for c in ledger["cores"])
            assert all(c["worst_current_bank_events"] <= 4096 for c in ledger["cores"])
            manifest.update({
                "packed_logical_core_count": ledger["logical_core_count"],
                "packed_ddr_backing_bytes": ledger["backing_bytes"],
                "packed_mapping_sha256": packed.compiled.fingerprint,
                "packed_capacity_audit_sha256": ledger["audit_sha256"],
                "B1_2_packed_mapping_verified_for_this_weight_set": True,
                "physical_kv260_execution": "NOT_TESTED",
            })
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hidden", type=int, default=40)
    parser.add_argument("--no-numerical", action="store_true",
                        help="omit 26-tick single-image numerical check")
    parser.add_argument("--pack", action="store_true",
                        help="run genuine B1.2 P03/P02 packing (large networks CPU/RAM-intensive)")
    args = parser.parse_args()
    report = run(args.hidden, numerical=not args.no_numerical, pack=args.pack)
    print(json.dumps(report, indent=2, sort_keys=True))
    print("P06_B21_TRAINING_FOUNDATION_PASS=1")
    print("P06_B21_OFFICIAL_TEST_STATUS=SEALED")
    print("P06_B21_TRAINING_STATUS=NOT_STARTED")


if __name__ == "__main__":
    main()
