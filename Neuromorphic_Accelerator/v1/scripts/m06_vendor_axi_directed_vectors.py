#!/usr/bin/env python3
"""Independent SOURCE-ONLY AXI4 SmartConnect directed stimulus/golden vectors.

This is INPUT for a future true original-2025.2 vendor RTL simulation,
not its result. No source in this script instantiates or simulates AMD IP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m06_axi_transport import (
    UPSTREAM_BYTES, DOWNSTREAM_BYTES, plan_aligned_incr, split_256_to_128,
)

SCHEMA = "m06-direct-vendor-axi-bfm-stimulus-v1-NOT_EXECUTED"


def vector_suite() -> dict:
    # Disjoint offset-only memory regions; DO NOT use these as actual DDR
    # physical addresses. The hardware BFM must map all ports to its own
    # simulated scratch array and prove the actual endpoint address width.
    region = bytearray((13*i + 17) & 0xff for i in range(0x7000))
    scenarios = []
    for si in range(4):
        start = 0x1000 + si*0x1000
        input_words = []
        expected_halves = []
        for beat in range(8):
            data = bytes((19*si + 7*beat + 3*lane + 11) & 255
                         for lane in range(UPSTREAM_BYTES))
            mask = (0xffffffff if beat % 2 == 0 else
                    0x80010001 if beat % 3 == 1 else 0x00ff00ff)
            input_words.append({
                "wdata_256_le_hex": data.hex(), "wstrb_32_hex": f"{mask:08x}",
                "wlast": beat == 7,
            })
            for half, (d, strobe) in enumerate(split_256_to_128(data, mask)):
                addr = start + beat*32 + half*16
                for lane in range(16):
                    if strobe & (1 << lane):
                        region[addr+lane] = d[lane]
                expected_halves.append({
                    "address_offset": addr,
                    "wdata_128_le_hex": d.hex(),
                    "wstrb_16_hex": f"{strobe:04x}",
                    "wlast_128": beat == 7 and half == 1,
                })
        readback = [bytes(region[start+32*i:start+32*(i+1)]).hex()
                    for i in range(8)]
        plan = plan_aligned_incr(start, 256, max_bytes=256, axid=0)
        scenarios.append({
            "scenario": f"independent_si{si}_partial_strobes_write_then_read",
            "si_index": si, "address_offset": start,
            "transaction": "WRITE_THEN_READ",
            "upstream_beats": 8, "downstream_beats": 16,
            "upstream_len": 7, "downstream_len": 15,
            "upstream_size": 5, "downstream_size": 4,
            "upstream_id": 0,
            "upstream_write_beats": input_words,
            "expected_downstream_write_beats": expected_halves,
            "expected_upstream_read_beats_le_hex": readback,
            "expected_response": "OKAY",
            "test_scope": "STIMULUS_ONLY_NO_VENDOR_RUN",
            "source_planner_burst_count": len(plan),
        })
    # Independent 4KiB edge reads: a single 96-byte burst would be illegal
    # (AXI4 4KiB rule); two individual legal INCR bursts are required.
    b = plan_aligned_incr(0x0fe0, 96, max_bytes=96, axid=0)
    scenarios.append({
        "scenario": "4k_split_read_after_si0_masked_write",
        "transaction": "READ_SPLIT",
        "si_index": 0,
        "planned_address_offsets": [item.address for item in b],
        "planned_upstream_beats": [item.upstream_beats for item in b],
        "planned_downstream_beats": [2*item.upstream_beats for item in b],
        "expected_read_words_le_hex": [
            bytes(region[at:at+32]).hex() for at in range(0x0fe0,0x1040,32)
        ],
        "source_only": True,
    })
    # Stress the 128-beat upstream / 256-beat downstream conversion limit.
    b = plan_aligned_incr(0x6000, 4096, max_bytes=4096, axid=0)
    scenarios.append({
        "scenario": "maximum_legal_128x256_to_256x128_read",
        "transaction": "READ",
        "si_index": 1,
        "address_offset": 0x6000,
        "upstream_beats": 128, "downstream_beats": 256,
        "upstream_len": 127, "downstream_len": 255,
        "upstream_size": 5, "downstream_size": 4,
        "expected_payload_sha256": hashlib.sha256(
            bytes(region[0x6000:0x7000])).hexdigest(),
        "expected_rresp": "OKAY",
        "source_planner_burst_count": len(b),
        "source_only": True,
    })
    return {
        "schema": SCHEMA,
        "original_mem_sc_SI": 4,
        "model_si_width_bits": 256,
        "model_mi_width_bits": 128,
        "address_interpretation": "LOGICAL_OFFSETS_ONLY_NOT_OS_DDR",
        "stimulus_generated_without_vendor_ip": True,
        "true_vivado_xsim_executed": False,
        "source_case_count": len(scenarios),
        "initial_memory_formula": "(13*byte_address + 17) & 0xff",
        "data_word_hex_order": "least-significant first byte = lowest address",
        "stall_plan": {
            "downstream_awready_wready_arready": "periodically low; BFM must assert stable VALID and all sidebands",
            "upstream_rready_bready": "periodically low; verify stable VALID,data,last,response",
            "watchdog": "fail on >10000 cycles without completion",
        },
        "error_cases_not_fabricated_as_vendor_results": [
            "downstream RRESP SLVERR propagated to upstream response",
            "downstream BRESP SLVERR propagated to upstream response",
            "unknown write acknowledgement must quarantine state",
        ],
        "scenarios": scenarios,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    try:
        if a.output.exists():
            raise ValueError("refuse to overwrite original/new owner evidence")
        a.output.parent.resolve(strict=True)
        out = vector_suite()
        with a.output.open("x", encoding="utf-8") as f:
            json.dump(out, f, sort_keys=True, indent=2)
            f.write("\n")
    except (OSError, ValueError) as e:
        print(f"M06 SOURCE-ONLY AXI STIMULUS GENERATION FAILED: {e}", file=sys.stderr)
        return 2
    print("M06 SOURCE-ONLY GOLDEN STIMULUS COMPLETE: "
          f"{out['source_case_count']} scenarios, vendor XSim NOT RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
