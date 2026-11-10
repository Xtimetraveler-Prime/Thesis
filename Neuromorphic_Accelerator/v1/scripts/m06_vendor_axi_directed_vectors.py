#!/usr/bin/env python3
"""M06 original-port-ROLE-correct AXI BFM stimulus; NOT vendor XSim results.

Based on REAL 2026-11-09 owner Vivado D3 port readback: S00-02 are
256-bit READ_ONLY; S03 is 256-bit WRITE_ONLY; M00 is 128-bit READ_WRITE.
All SIs have CONFIG.ID_WIDTH=0, CONFIG.HAS_BURST=0, and
CONFIG.MAX_BURST_LENGTH=16; M00 has a 32-beat maximum. A generic
128-upstream-beat 256-downstream-beat vector is NOT legal for this D3.
Use SINGLE-BEAT SI transfers until authentic original generated HDL
exposes exact AWLEN/ARLEN semantics; even the two-beat downsizing result
is a hypothesis to CHECK against vendor IP, not a simulated PASS.
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
    UPSTREAM_BYTES, split_256_to_128, join_128_to_256,
)

SCHEMA = "m06-original-role-safe-axi-bfm-stimulus-v2-NOT_EXECUTED"
MEMORY_BYTES = 0x2000  # Must match rtl/m06/m06_axi128_scratch_mem.sv
WRITER = "S03"
READERS = ("S00", "S01", "S02")
PORT_ROLES = {**{port: "READ_ONLY" for port in READERS},
              WRITER: "WRITE_ONLY"}

ORIGINAL_CONTRACT = {
    **{f"mem_sc/{port}_AXI": {
        "CONFIG.PROTOCOL": "AXI4",
        "CONFIG.DATA_WIDTH": "256",
        "CONFIG.ADDR_WIDTH": "32",
        "CONFIG.ID_WIDTH": "0",
        "CONFIG.READ_WRITE_MODE": role,
        "CONFIG.HAS_BURST": "0",
        "CONFIG.MAX_BURST_LENGTH": "16",
    } for port, role in PORT_ROLES.items()},
    "mem_sc/M00_AXI": {
        "CONFIG.DATA_WIDTH": "128",
        "CONFIG.ADDR_WIDTH": "49",
        "CONFIG.ID_WIDTH": "0",
        "CONFIG.READ_WRITE_MODE": "READ_WRITE",
        "CONFIG.HAS_BURST": "1",
        "CONFIG.MAX_BURST_LENGTH": "32",
    },
    "ps/S_AXI_HP0_FPD": {
        "CONFIG.DATA_WIDTH": "128",
        "CONFIG.ID_WIDTH": "6",
        "CONFIG.AWUSER_WIDTH": "1",
        "CONFIG.ARUSER_WIDTH": "1",
    },
}


def validate_original_report(text: str) -> dict:
    """Validate exact property lines; never infer a functional AXI PASS."""
    properties: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("ENDPOINT_PROPERTY|"):
            continue
        fields = line.split("|", 3)
        if len(fields) != 4:
            raise ValueError("malformed original endpoint property")
        _, endpoint, key, value = fields
        if key in properties.setdefault(endpoint, {}):
            raise ValueError("duplicate original endpoint property")
        properties[endpoint][key] = value
    for endpoint, expected in ORIGINAL_CONTRACT.items():
        for key, value in expected.items():
            actual = properties.get(endpoint, {}).get(key)
            if actual != value:
                raise ValueError(
                    f"original port role/width/burst contradiction: {endpoint} "
                    f"{key} expected {value!r}, got {actual!r}")
    if (text.splitlines().count(
            "RESULT|ORIGINAL_PORTS_CAPTURED_FOR_ONE_VENDOR_FUNCTIONAL_XSIM_TRIAL") != 1):
        raise ValueError("missing original completed owner Vivado source capture")
    return {
        "real_port_source_attached": True,
        "real_capture_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "real_vendor_functional_axi": "NOT_EXECUTED",
    }


def vector_suite(port_report: str | None = None) -> dict:
    if port_report is None:
        provenance = {
            "real_port_source_attached": False,
            "source": "OWNER_PASTED_VIVADO_ENDPOINT_PROPERTIES_2026_11_09",
            "real_vendor_functional_axi": "NOT_EXECUTED",
        }
    else:
        provenance = validate_original_report(port_report)
    image = bytearray((13*i + 17) & 0xff for i in range(MEMORY_BYTES))
    cases = []
    write_offsets = (0x0fe0, 0x1000, 0x1020, 0x1040)
    if any(at < 0 or at + UPSTREAM_BYTES > MEMORY_BYTES for at in write_offsets):
        raise AssertionError('BFM stimulus exceeds 8KiB scratch RTL address space')
    write_masks = (0xffffffff, 0x80010001, 0x00ff00ff, 0x0000ffff)
    # All four WRITE transactions MUST originate from original S03.
    for idx, (at, mask) in enumerate(zip(write_offsets, write_masks)):
        before = bytes(image[at:at+32])
        payload = bytes((17*idx + 3*lane + 11) & 255
                        for lane in range(UPSTREAM_BYTES))
        low, high = split_256_to_128(payload, mask)
        halves = []
        for half, (data, strb) in enumerate((low, high)):
            address = at + half*16
            for lane in range(16):
                if strb & (1 << lane):
                    image[address+lane] = data[lane]
            halves.append({
                "address_offset": address,
                "downstream_data_128_le_hex": data.hex(),
                "downstream_wstrb_16_hex": f"{strb:04x}",
                "expected_downstream_wlast": half == 1,
            })
        cases.append({
            "case": f"WRITE_S03_one_256b_beat_mask_{idx}",
            "source_port": WRITER,
            "direction": "WRITE",
            "legal_single_beat_upstream_axi": True,
            "upstream_address_offset": at,
            "upstream_beat_count": 1,
            "upstream_awlen": 0,
            "upstream_awsize": 5,
            "upstream_wlast": True,
            "upstream_wdata_256_le_hex": payload.hex(),
            "upstream_wstrb_32_hex": f"{mask:08x}",
            "before_memory_256_le_hex": before.hex(),
            "expected_after_memory_256_le_hex": bytes(image[at:at+32]).hex(),
            "expected_downstream_two_halves": halves,
            "expected_write_response": "OKAY",
            "expected_original_no_id_or_user_fields": True,
            "vendor_status": "NOT_EXECUTED",
        })
    # Validate SAME shared memory was updated by S03 using THREE different
    # original READ_ONLY masters, no fictitious write on S00-S02.
    final_read_words = [bytes(image[at:at+32]).hex() for at in write_offsets]
    for reader in READERS:
        cases.append({
            "case": f"READ_{reader}_after_S03_masked_writes",
            "source_port": reader,
            "direction": "READ",
            "independent_single_beat_read_address_offsets": list(write_offsets),
            "upstream_arlen_each": 0,
            "upstream_arsize_each": 5,
            "expected_upstream_rdata_256_le_hex": list(final_read_words),
            "expected_upstream_rlast_each": True,
            "expected_read_response_each": "OKAY",
            "expected_original_no_id_or_user_fields": True,
            "vendor_status": "NOT_EXECUTED",
        })
    # Three individually legal aligned reads on either side of a 4KiB
    # boundary; one 96-byte burst across that boundary is expressly NOT SENT.
    edge_offsets = (0x0fe0, 0x1000, 0x1020)
    cases.append({
        "case": "READ_S00_4KiB_boundary_three_independent_single_beats",
        "source_port": "S00",
        "direction": "READ_SPLIT",
        "separate_upstream_address_offsets": list(edge_offsets),
        "upstream_beat_count_per_transaction": 1,
        "expected_256b_words_le_hex": [
            bytes(image[at:at+32]).hex() for at in edge_offsets],
        "never_issue_one_4KiB_crossing_burst": True,
        "vendor_status": "NOT_EXECUTED",
    })
    # NOT an executable vector yet: HAS_BURST=0 at the original SI.
    # Verify AWLEN/ARLEN pins at exact generated HDL first. Even if multi-
    # beat is exposed, 16 upstream beats is max (not the generic 128).
    cases.append({
        "case": "BLOCKED_CAPABILITY_PROBE_MULTI_BEAT",
        "direction": "NOT_EXECUTABLE_PENDING_ACTUAL_VENDOR_PORT_HEADER",
        "original_si_has_burst": 0,
        "original_si_max_burst_beats": 16,
        "original_mi_max_burst_beats": 32,
        "generic_128_upstream_beat_stress_excluded": True,
        "pending": "actual generated vendor AWLEN/ARLEN and conversion BFM",
        "vendor_status": "NOT_EXECUTED",
    })
    if len(cases) != 9:
        raise AssertionError("unexpected original-role corrected stimulus count")
    return {
        "schema": SCHEMA,
        "original_port_role_contract": PORT_ROLES,
        "model_upstream_width_bits": 256,
        "model_downstream_width_bits": 128,
        "original_si_has_burst_property": 0,
        "original_si_max_burst_length_property": 16,
        "original_mi_max_burst_length_property": 32,
        "actual_burst_pin_semantics": "NOT_YET_INSPECTED_IN_VENDOR_HDL",
        "physical_address_meaning": "SYNTHETIC_TESTBENCH_OFFSETS_NOT_REAL_DDR",
        "source_only": True,
        "vendor_smartconnect_executed": False,
        "source_port_report_provenance": provenance,
        "memory_initial_formula": "(13*byte_address + 17) & 0xff",
        "write_order": [case["case"] for case in cases if case["direction"] == "WRITE"],
        "read_order": [case["case"] for case in cases
                       if case["direction"].startswith("READ")],
        "scenarios": cases,
        "scenario_count": len(cases),
        "rresp_bresp_error_injection": "PENDING_REAL_VENDOR_BFM",
        "stall_watchdog": "PENDING_REAL_VENDOR_BFM",
        "true_vendor_axi_result": "NOT_EXECUTED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--port-report", type=Path,
                   help="optional existing original 02_original_mem_sc_ports.txt")
    args = p.parse_args()
    try:
        if args.output.exists():
            raise ValueError("refuse overwrite of original/user evidence")
        args.output.parent.resolve(strict=True)
        port_text = (args.port_report.read_text(encoding="utf-8")
                     if args.port_report else None)
        suite = vector_suite(port_text)
        with args.output.open("x", encoding="utf-8") as f:
            json.dump(suite, f, sort_keys=True, indent=2)
            f.write("\n")
    except (ValueError, OSError) as exc:
        print(f"M06 ORIGINAL-ROLE STIMULUS FAILED: {exc}", file=sys.stderr)
        return 2
    print("M06 ORIGINAL-ROLE SAFE AXI BFM INPUTS GENERATED: "
          "S03 write, S00/S01/S02 reads, 4KiB split; "
          "vendor XSim NOT RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
