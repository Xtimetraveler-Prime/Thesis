#!/usr/bin/env python3
"""Host-only B1.3 784×N→10 synthetic wire/DDR-ID proof, not an FPGA runner."""
from __future__ import annotations

import argparse
import hashlib
import json

from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b13_streaming import (
    StreamingEpochGuard, decode_ingress_frame, encode_ingress_frame,
)
from p06_b12_synthetic_probe import synthetic_dense_network


def run(hidden: int) -> dict:
    result = compile_synapse_aware(
        synthetic_dense_network(hidden), B12Options(readout_population="z"))
    payload = encode_ingress_frame(result, bytes([255] * 784))
    decoded = decode_ingress_frame(payload, result)
    guard = StreamingEpochGuard(result, payload)
    profile = guard.static_worst_case()
    assert decoded.routes == tuple(sorted((
        route.input_index, route.destination_core, route.destination_axon)
        for route in result.compiled.ingress_routes))
    assert len(decoded.events(0)) == 784 * len(profile["external_per_core"][:-1])
    assert len(decoded.events(25)) == 0
    assert max(profile["current_worst_per_core"]) <= 4096
    assert profile["p05_diagnostic_stream_compatible"] is False
    return {
        "schema": profile["schema"],
        "synthetic_network_shape": [784, hidden, 10],
        "deployment_sha256": result.compiled.fingerprint,
        "capacity_audit_sha256": result.capacity_audit["audit_sha256"],
        "full_ingress_wire_sha256": hashlib.sha256(payload).hexdigest(),
        "ingress_wire_bytes": len(payload),
        "input_pixels_sha256": decoded.image_sha256,
        "logical_cores": profile["logical_cores"],
        "input_fanout_routes": profile["ingress_routes"],
        "all_255_events_per_input_tick": profile["all_255_input_tick_external_events"],
        "all_255_events_over_25_ticks": profile["all_255_over_25_ticks_external_events"],
        "worst_current_events_per_core": profile["current_worst_per_core"],
        "max_current_events_any_core": profile["max_core_current_bank_events"],
        "max_emitted_packets_any_core": profile["max_core_emitted_packets"],
        "bytes_per_ddr_context": profile["full_ddr_image_bytes_each"],
        "physical_execution": profile["physical_execution"],
        "old_P05_abi_compatible": False,
        "official_test_access": "NONE",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hidden", type=int, default=40, help="1..1000 synthetic hidden neurons")
    args = parser.parse_args()
    report = run(args.hidden)
    print(json.dumps(report, indent=2, sort_keys=True))
    print("P06_B13_SYNTHETIC_STREAMING_CONTRACT_PASS=1")


if __name__ == "__main__":
    main()
