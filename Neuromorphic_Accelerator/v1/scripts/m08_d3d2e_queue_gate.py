#!/usr/bin/env python3
"""D3.D.2E.1 M32Q queued-event source-only fail-closed gate. NEVER board release."""
from __future__ import annotations
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_d3d2d_event_gate as accepted_source_gate
import m08_d3d2d_event_vectors as oracle

RTL = ROOT / "rtl/m08/m08_d3d2e_tick_queue_lif_axil.v"
TB = ROOT / "rtl/m08/tb_m08_d3d2e_tick_queue_lif_axil.sv"
OLD_RTL = ROOT / "rtl/m08/m08_d3d2d_raw_event_lif_axil.v"

class Reject(ValueError):
    pass

def require(value, why):
    if not value:
        raise Reject(why)

def source():
    old = accepted_source_gate.source()
    require(old["status"] == "M08_D3D2D_RAW_17_EVENT_INGRESS_SOURCE_READY_PC_ONLY",
            "accepted D3.D.2D source contract drift")
    rtl, tb = RTL.read_text(), TB.read_text()
    require("module m08_d3d2e_tick_queue_lif_axil" in rtl,
            "new module identity missing")
    for term in (
        "MAGIC=32'h4D333251", "VERSION=32'h00060000",
        "reg signed [31:0] shadow_current [0:127]",
        "reg [4:0] fifo_neuron [0:31]",
        "reg [1:0] fifo_tick [0:31]",
        "reg signed [31:0] fifo_current [0:31]",
        "reg [5:0] fifo_depth, fifo_high_watermark",
        "reg [6:0] serviced_count",
        "reg [3:0] serviced_tick_mask",
        "reg [2:0] next_service_tick",
        "wire event_overflow=event_sum_ext[32] != event_sum_ext[31]",
        "fifo_depth == 6'd32", "event_count >= 7'd64",
        "shadow_current[event_index] <= event_sum_ext[31:0]",
        "fifo_current[fifo_wr_ptr] <= event_current",
        "fifo_depth <= fifo_depth + 1'b1",
        "currents[fifo_head_index] <=", "fifo_depth <= fifo_depth - 1'b1",
        "serviced_count <= serviced_count + 1'b1",
        "serviced_tick_mask[active_service_tick] <= 1'b1",
        "next_service_tick <= next_service_tick + 1'b1",
        "event_tick < last_accepted_tick",
        "serviced_count == event_count",
        "serviced_tick_mask == 4'hF",
        "PHASE_ROUTE", "PHASE_BASE", "PHASE_EXT",
        "PHASE_TOTAL", "PHASE_COMMIT",
        "three_scaled < 0 ? -((-three_scaled) >>> 2)",
        "spike_mask[edge_pre[route_slot]][tick - edge_delay[route_slot]]",
        "12'h040", "12'h044", "12'h048", "12'h04C",
        "12'h050", "12'h054", "12'h058",
    ):
        require(term in rtl, "missing new queue/neuronal source invariant: " + term)
    for term in (
        "module tb_m08_d3d2e_tick_queue_lif_axil",
        "vectors [0:629]", "service_all_ticks",
        "load_raw_events", "check_fabric_event_sums",
        "M08_D3D2E_REAL_RTL_17_EVENTS_TICK_SERVICE_PASS",
        "M08_D3D2E_FULL_128_BUCKET_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_RTL_PASS",
    ):
        require(term in tb, "missing clocked bench source invariant: " + term)
    for forbidden in ("program_hw_devices", "open_hw_manager", "connect_hw_server",
                      "run_hw_axi", "/dev/mem", "/dev/uio", "xmutil "):
        require(forbidden not in rtl and forbidden not in tb,
                "forbidden hardware action in source: " + forbidden)
    data = oracle.words()  # M02 dense/event and M03 exact sparse equality
    require(len(data) == 630, "original M06 signed event oracle changed")
    ticks = [int(data[580 + 3*k], 16) for k in range(17)]
    require(ticks == sorted(ticks) and {0,1,2,3} == set(ticks),
            "queue monotonic tick M06 fixture contract changed")
    return {
        "status": "M08_D3D2E_TICK_QUEUE_SOURCE_CANDIDATE_NO_BOARD",
        "new_module": "m08_d3d2e_tick_queue_lif_axil",
        "queue_capacity": 32,
        "accepted_event_limit": 64,
        "original_m06_events": 17,
        "original_m06_neurons": 32,
        "original_m06_ticks": 4,
        "original_m06_edges": 5,
        "expected_neural_and_input_checks": 512,
        "original_d3d2d_rtl_sha256": sha256(OLD_RTL.read_bytes()).hexdigest(),
        "new_queue_rtl_sha256": sha256(RTL.read_bytes()).hexdigest(),
        "new_queue_tb_sha256": sha256(TB.read_bytes()).hexdigest(),
        "native_candidate_routed": False,
        "new_image_drc_timing_sha_reviewed": False,
        "physical_programming_authorized": False,
        "physical_programmed": False,
        "independent_physical_acceptance": False,
        "asynchronous_ingress_proven": False,
        "original_m05_hls_physical": False,
        "physical_ddr": False,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only", action="store_true", required=True)
    parser.parse_args()
    try:
        print(json.dumps(source(), indent=2, sort_keys=True))
    except (Reject, OSError, ValueError, AssertionError) as exc:
        print("M08_D3D2E_QUEUE_SOURCE_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
