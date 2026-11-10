#!/usr/bin/env python3
"""Fail-closed source-only HLS-to-original-SmartConnect integration plan.

Rechecks original owner evidence when invoked as CLI. Describes width/role
adaptations only; NEVER claims a connected IP path, DDR, or board test.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

WIDTHS = (8, 16, 32, 64, 128, 256, 512)
SOURCES = (
    "hls/m04_lif_eval/m04_eval.cpp",
    "hls/m05_rolling/m05_rolling.cpp",
    "hls/m06_paged_rolling/m06_paged_rolling.cpp",
    "hls/m06_paged_rolling/m06_paged_rolling.hpp",
)


def plan(port: dict) -> dict:
    """Derive a nonfunctional connection plan from measured HLS pins only."""
    if not isinstance(port, dict) or (
        port.get("schema") != "m06-paged-hls-synthesized-port-readback-v1"
        or port.get("status") != "GENUINE_GENERATED_RTL_HEADER_ONLY_NOT_PL_CONNECTED"
        or port.get("tool_version") != "2025.2"
        or port.get("original_s00_s03_width") != 256
        or port.get("original_mem_sc_axi_connected") != "NOT_PROVEN"
        or port.get("physical_base_addresses") != "NOT_ALLOCATED"
        or port.get("actual_board") != "NOT_ACCESSED"
        or port.get("m06_complete") is not False
    ):
        raise ValueError("port audit does not describe an unconnected genuine M06 synthesis")
    if type(port.get("generated_rtl_count")) is not int or port["generated_rtl_count"] < 1:
        raise ValueError("generated RTL sources missing")
    sha = port.get("generated_top_sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
        raise ValueError("generated RTL top digest missing or malformed")
    digests = port.get("source_digest_subset")
    if not isinstance(digests, dict) or any(
        not isinstance(digests.get(k), str)
        or not re.fullmatch(r"[a-f0-9]{64}", digests[k]) for k in SOURCES
    ):
        raise ValueError("original M04/M05 and new M06 source identity missing")

    paths = []
    for key, expected_prefix, expected_role, expected_flag in (
        ("read_axi_master", "m_axi_gmem_read_", "READ_ONLY_SOURCE",
         "read_width_converter_needed"),
        ("write_axi_master", "m_axi_gmem_write_", "WRITE_ONLY_SOURCE",
         "write_width_converter_needed"),
    ):
        item = port.get(key)
        if not isinstance(item, dict) or item.get("prefix") != expected_prefix \
           or item.get("role") != expected_role:
            raise ValueError("missing or misclassified AXI master role: " + key)
        width, address = item.get("data_width"), item.get("addr_width")
        if type(width) is not int or width not in WIDTHS or \
           type(address) is not int or address < 16 or address > 64:
            raise ValueError("invalid measured AXI data/address width: " + key)
        converter = width != 256
        if type(port.get(expected_flag)) is not bool or port[expected_flag] != converter:
            raise ValueError("HLS audit adapter flag contradicts actual width: " + key)
        paths.append({
            "hls_bundle": expected_prefix[:-1],
            "generated_hls_data_width": width,
            "generated_hls_address_width": address,
            "original_smartconnect_address_width": 32,
            "address_guard_or_translation_required": address != 32,
            "address_mapping_status": ("HLS_HIGH_BITS_MUST_BE_BOUNDED_BEFORE_32BIT_ORIGINAL_SI"
                                       if address != 32 else "ADDRESS_WIDTH_ONLY_COMPATIBLE_NOT_CONNECTED"),
            "original_smartconnect_slave": "S00" if key == "read_axi_master" else "S03",
            "original_smartconnect_data_width": 256,
            "required_width_adapter": converter,
            "direct_connection_status": ("WIDTH_MISMATCH_DO_NOT_CONNECT_DIRECTLY"
                                         if converter else "WIDTH_ONLY_COMPATIBLE_NOT_CONNECTED"),
            "role": expected_role,
        })
    return {
        "schema": "m06-paged-hls-axi-link-plan-v1",
        "status": "SOURCE_ONLY_PORT_WIDTH_PLAN_NOT_CONNECTED_NOT_SIMULATED",
        "generated_top_sha256": sha,
        "source_digest_subset": {k: digests[k] for k in SOURCES},
        "original_smartconnect_upstream_width_bits": 256,
        "original_smartconnect_upstream_address_width_bits": 32,
        "original_smartconnect_downstream_width_bits": 128,
        "canonical_memory_bytes": 65536,
        "canonical_16byte_records": 4096,
        "canonical_page_bytes": 256,
        "canonical_last_legal_page": 255,
        "canonical_illegal_page": 256,
        "canonical_base": "UNALLOCATED_MUST_BE_IDENTICAL_ON_BOTH_HLS_PORTS",
        "shared_backing_memory": "REQUIRED_NOT_PROVEN",
        "paths": paths,
        "hard_gates": [
            "HLS_generated_RTL_CRTL_cosim_with_real_AXIM_models",
            "HLS_64bit_address_to_original_32bit_S00_S03_mapping_with_bounds",
            "original_AMD_SmartConnect_Stage_E_4096_boundary_and_quarantine",
            "genuine_generated_HLS_to_original_S00_S03_binding_and_width_converters",
            "read_after_dirty_write_B_response_fence_across_separate_masters",
            "AXI_burst_4KiB_boundary_strobe_ID_response_and_backpressure",
            "fault_timeout_poison_without_silent_neural_trace_commit",
            "full_M02_M03_exact_trace_and_16B_canonical_image_after_eviction",
            "offline_evidence_hash_and_original_IP_source_attestation",
        ],
        "physical_DDR_ownership": "NOT_AUTHORIZED_NOT_TESTED",
        "original_SmartConnect_connected": False,
        "m06_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hls-evidence", required=True, type=Path)
    parser.add_argument("--port-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    opts = parser.parse_args()
    try:
        if not opts.hls_evidence.is_dir() or not opts.port_audit.is_file():
            raise ValueError("owner HLS synthesis or port audit file is missing")
        # Refuse standalone JSON as proof; compare it to real immutable RTL.
        from m06_paged_hls_port_audit import audit
        measured = audit(opts.hls_evidence)
        reported = json.loads(opts.port_audit.read_text(encoding="utf-8"))
        if measured != reported:
            raise ValueError("supplied port JSON differs from genuine owner RTL readback")
        result = plan(measured)
        if opts.output.exists() or not opts.output.parent.is_dir():
            raise ValueError("output must be a new file inside an existing directory")
        with opts.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, sort_keys=True, indent=2)
            stream.write("\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("M06 source-only link plan REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print("M06 AXI width/role PLAN recorded; original IP link, coherency and DDR NOT PROVEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
