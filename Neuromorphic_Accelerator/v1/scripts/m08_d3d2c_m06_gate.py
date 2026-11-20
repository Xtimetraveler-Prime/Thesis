#!/usr/bin/env python3
"""D3.D.2C M06 32-neuron source-only gate. NO BOARD. NO BITSTREAM APPROVAL.

The prior D3.D.2B physical result and its RTL/bitstream are immutable.
This gate deliberately provides NO native --run-dir or JTAG programming path.
New bitstream, DRC/timing, identity and physical audit need a separate phase.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2b_synaptic_gate as predecessor
import m08_d3d2c_m06_vectors as oracle

RTL=ROOT/"rtl/m08/m08_d3d2c_m06_32_lif_axil.v"
TB=ROOT/"rtl/m08/tb_m08_d3d2c_m06_32_lif_axil.sv"
VECTORS=ROOT/"scripts/m08_d3d2c_m06_vectors.py"

class Reject(ValueError):
    pass

def source()->dict:
    try:
        accepted=predecessor.source()
    except (predecessor.Reject,ValueError) as exc:
        raise Reject("previous physically accepted RTL/source drift: "+str(exc)) from exc
    if accepted["rtl_sha256"]!=predecessor.OWNER_ORIGINAL_RTL_SHA:
        raise Reject("prior owner synapse bitstream RTL provenance drift")
    texts=[path.read_text() for path in (RTL,TB,VECTORS)]
    rtl,tb,vectors=texts
    requirements=(
        "module m08_d3d2c_m06_32_lif_axil",
        "MAGIC=32'h4D33324E",
        "VERSION=32'h00040000",
        "cfg_initial [0:31]", "cfg_threshold [0:31]",
        "membrane [0:31]", "spike_mask [0:31]",
        "trace_voltage [0:127]", "trace_syn_current [0:127]",
        "edge_pre [0:7]", "edge_post [0:7]",
        "edge_delay[validate_idx] == 2'd0",
        "cfg_nonce != 0 && cfg_edge_count <= 4'd8",
        "wire [6:0] compute_index = {neuron,tick}",
        "scaled_three", # see RTL source for real name
        "three_quarter_trunc",
        "three_scaled < 0 ? -((-three_scaled) >>> 2)",
        "spike_mask[edge_pre[route_slot]][tick - edge_delay[route_slot]]",
        "reg signed [19:0] syn_accum",
        "reg signed [16:0] leak_bias_stage",
        "reg signed [33:0] external_stage",
        "reg signed [33:0] total_stage",
        "PHASE_ROUTE", "PHASE_BASE", "PHASE_EXT",
        "PHASE_TOTAL", "PHASE_COMMIT",
        "if (route_slot < cfg_edge_count)",
        "if (edge_active_now)",
        "syn_accum <= syn_accum + selected_weight",
        "total_stage <= external_stage +",
        "update_phase <= PHASE_COMMIT",
        "trace_syn_current[compute_index] <=",
        "{{12{syn_accum[19]}},syn_accum}",
        "trace_voltage[compute_index] <= next_voltage",
        "spike_mask[neuron][tick] <= fired",
        "if (neuron == 5'd31)",
        "12'h100", "12'h500", "12'h900", "12'hD00",
        "if (busy)",
        "s_axi_bresp <= SLVERR",
    )
    requirements=tuple("three_scaled" if item=="scaled_three" else item for item in requirements)
    for needle in requirements:
        if needle not in rtl:
            raise Reject("new 32-neuron hardware semantic absent: "+needle)
    # The original 32-level carry/LUT spike-to-voltage chain must NOT be
    # reintroduced: clock-to-clock sequential routing and staged arithmetic
    # are part of the new timing-fix acceptance contract.
    for path in (
        "synaptic_sum = synaptic_sum +",
        "trace_syn_current[compute_index] <= synaptic_sum[31:0]",
        "wire signed [63:0] total =",
    ):
        if path in rtl:
            raise Reject("old monolithic routed datapath reintroduced: "+path)
    for forbidden in (
        "program_hw_devices", "open_hw_manager", "connect_hw_server",
        "run_hw_axi", "xmutil ", "/dev/uio", "/dev/mem", "sudo ", "ssh ",
    ):
        if forbidden in rtl or forbidden in tb or forbidden in vectors:
            raise Reject("new source includes forbidden physical operation "+forbidden)
    for needle in (
        "M08_D3D2C_M06_FULL_128_VOLTAGE_SPIKE_SYN_CURRENT_RTL_PASS",
        "M08_D3D2C_M06_32X4_REAL_RTL_PARITY_PASS",
        "vectors [0:578]", "verify_neuron(", "verify_syn(",
        "32'h4D33324E", "32'h00040000",
    ):
        if needle not in tb:
            raise Reject("M06 RTL bench missing exact parity boundary: "+needle)
    if len(oracle.words())!=oracle.WORDS or oracle.WORDS!=579:
        raise Reject("M06 32-neuron reference geometry drift")
    return dict(
        status="M08_D3D2C_M06_32_NEURON_RTL_SOURCE_READY_PC_ONLY",
        original_m06_neurons=32,
        original_m06_ticks=4,
        original_m06_synapses=5,
        original_m06_external_events=17,
        external_event_coalescing_in_fpga=False,
        original_m06_hls_physically_integrated=False,
        owner_new_vivado_native_accepted=False,
        new_fpga_programmed=False,
        physical_32_neuron_m02_parity_verified=False,
        source_only=True,
        clock_cycles_per_neuron_expression="configured_active_edges + 5",
        neuron_update_pipelined=True,
        physical_clock_hz_verified=False,
        routed_timing_closed=False,
        rtl_sha256=sha256(RTL.read_bytes()).hexdigest(),
        bench_sha256=sha256(TB.read_bytes()).hexdigest(),
        oracle_sha256=sha256(VECTORS.read_bytes()).hexdigest(),
    )

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-only",action="store_true",required=True)
    p.parse_args()
    try:
        print(json.dumps(source(),sort_keys=True,indent=2))
        return 0
    except (Reject,ValueError,OSError,KeyError,AssertionError) as exc:
        print("M08_D3D2C_SOURCE_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
