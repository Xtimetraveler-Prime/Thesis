#!/usr/bin/env python3
"""Independent M05 D4.1b original Vivado read-only BD AXI-property audit.

No result can establish generated SmartConnect internals or 256->128 data
correctness. A structurally valid query therefore exits 3, AXI gate BLOCKED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from m05_12d4_warning_inventory import inspect_original, parse_warnings

PREFIX = "neuromorphic_v1_m05_12d4_readonly_bd_"
OLD_PREFIX = "neuromorphic_v1_m05_12d4_warning_inventory_"
SCOPE = "META|scope|M05_D4_1B_ORIGINAL_READ_ONLY_2025_2_BD_AXI_PROPERTIES"
SUCCESS = "M05_D4_READ_ONLY_BD_PROPERTIES_PASS|NO_GENERATION_NO_SYNTHESIS_NO_BOARD"
PROPS = (
    "CONFIG.PROTOCOL", "CONFIG.DATA_WIDTH", "CONFIG.ADDR_WIDTH", "CONFIG.ID_WIDTH",
    "CONFIG.AWUSER_WIDTH", "CONFIG.ARUSER_WIDTH", "CONFIG.WUSER_WIDTH",
    "CONFIG.BUSER_WIDTH", "CONFIG.RUSER_WIDTH",
    "CONFIG.MAX_BURST_LENGTH", "CONFIG.SUPPORTS_NARROW_BURST", "CONFIG.HAS_BURST",
    "CONFIG.HAS_WSTRB", "CONFIG.HAS_BRESP", "CONFIG.HAS_RRESP", "CONFIG.READ_WRITE_MODE",
    "CONFIG.NUM_READ_OUTSTANDING", "CONFIG.NUM_WRITE_OUTSTANDING",
    "CONFIG.HAS_CACHE", "CONFIG.HAS_LOCK", "CONFIG.HAS_PROT", "CONFIG.HAS_QOS",
    "CONFIG.HAS_REGION", "CONFIG.FREQ_HZ", "CONFIG.CLK_DOMAIN",
)
ENDPOINTS = (
    "ctrl_sc/S00_AXI", "ctrl_sc/M00_AXI", "ctrl_sc/M01_AXI",
    "ctrl_sc/M02_AXI", "ctrl_sc/M03_AXI", "ctrl_sc/M04_AXI", "ctrl_sc/M05_AXI",
    "dma_neurons/S_AXI_LITE", "dma_synapses/S_AXI_LITE",
    "dma_external/S_AXI_LITE", "dma_trace/S_AXI_LITE",
    "shell/s_axi", "hls/s_axi_control",
    "dma_neurons/M_AXI_MM2S", "mem_sc/S00_AXI",
    "dma_synapses/M_AXI_MM2S", "mem_sc/S01_AXI",
    "dma_external/M_AXI_MM2S", "mem_sc/S02_AXI",
    "dma_trace/M_AXI_S2MM", "mem_sc/S03_AXI",
    "mem_sc/M00_AXI", "ps/S_AXI_HP0_FPD",
)
WIDTHS = {
    "dma_neurons/M_AXI_MM2S": 256, "mem_sc/S00_AXI": 256,
    "dma_synapses/M_AXI_MM2S": 256, "mem_sc/S01_AXI": 256,
    "dma_external/M_AXI_MM2S": 256, "mem_sc/S02_AXI": 256,
    "dma_trace/M_AXI_S2MM": 256, "mem_sc/S03_AXI": 256,
    "mem_sc/M00_AXI": 128, "ps/S_AXI_HP0_FPD": 128,
}
PAIRS = (
    ("dma_neurons/M_AXI_MM2S", "mem_sc/S00_AXI"),
    ("dma_synapses/M_AXI_MM2S", "mem_sc/S01_AXI"),
    ("dma_external/M_AXI_MM2S", "mem_sc/S02_AXI"),
    ("dma_trace/M_AXI_S2MM", "mem_sc/S03_AXI"),
    ("mem_sc/M00_AXI", "ps/S_AXI_HP0_FPD"),
    ("ctrl_sc/M00_AXI", "dma_neurons/S_AXI_LITE"),
    ("ctrl_sc/M01_AXI", "dma_synapses/S_AXI_LITE"),
    ("ctrl_sc/M02_AXI", "dma_external/S_AXI_LITE"),
    ("ctrl_sc/M03_AXI", "dma_trace/S_AXI_LITE"),
    ("ctrl_sc/M04_AXI", "shell/s_axi"),
    ("ctrl_sc/M05_AXI", "hls/s_axi_control"),
)
CELLS = (("ctrl_sc", "CONFIG.NUM_SI", "1"),
         ("ctrl_sc", "CONFIG.NUM_MI", "6"),
         ("mem_sc", "CONFIG.NUM_SI", "4"),
         ("mem_sc", "CONFIG.NUM_MI", "1"))
TAIL = (
    "META|physical_board|NOT_AUTHORIZED",
    "META|generated_payload_field_map|NOT_PROVEN",
    "META|simulation|NOT_RUN",
    "META|synthesis|NOT_RUN",
    "READ_ONLY_QUERY|PASS|Genuine_original_BD_properties_only",
)
NUMERIC = re.compile(r"\d+\Z")


def parse(report: str, root: Path) -> dict:
    lines = report.splitlines()
    if not lines or not report.endswith("\n"):
        raise ValueError("missing or truncated vendor query report")
    expected_length = 3 + len(CELLS) + len(ENDPOINTS) * (len(PROPS) + 1) + len(TAIL)
    if len(lines) != expected_length or lines[0] != SCOPE or tuple(lines[-len(TAIL):]) != TAIL:
        raise ValueError("truncated, duplicate, or forged read-only vendor query schema")
    original = root.resolve(strict=True)
    xpr = original / "13_file_backed_project/m05_d3_output_products.xpr"
    bdname = "m05_12d3_real_signed32_hls_six_control_address_candidate"
    bd = original / ("13_file_backed_project/m05_d3_output_products.srcs/"
                      "sources_1/bd/" + bdname + "/" + bdname + ".bd")
    if lines[1:3] != ["PROJECT|" + str(xpr), "BD|" + str(bd)]:
        raise ValueError("read-only query project/BD path not the immutable original")
    pos = 3
    for cell, prop, value in CELLS:
        if lines[pos] != f"CELL|{cell}|{prop}|{value}":
            raise ValueError(f"SmartConnect SI/MI original configuration mismatch at {cell}/{prop}")
        pos += 1
    endpoint_values: dict[str, dict[str, str]] = {}
    nets: dict[str, str] = {}
    for endpoint in ENDPOINTS:
        parts = lines[pos].split("|")
        if (len(parts) != 3 or parts[:2] != ["NET", endpoint] or not parts[2]
                or "|" in parts[2] or any(c.isspace() for c in parts[2])):
            raise ValueError(f"missing/invalid single genuine interface net: {endpoint}")
        nets[endpoint] = parts[2]
        pos += 1
        values = {}
        for prop in PROPS:
            prefix = f"IFACE|{endpoint}|{prop}|"
            row = lines[pos]
            if not row.startswith(prefix) or "|" in row[len(prefix):]:
                raise ValueError(f"missing/duplicate/shifted interface property {endpoint}/{prop}")
            values[prop] = row[len(prefix):]
            pos += 1
        endpoint_values[endpoint] = values
        if endpoint in WIDTHS and values["CONFIG.DATA_WIDTH"] != str(WIDTHS[endpoint]):
            raise ValueError(f"genuine width-contract drift on {endpoint}")
    canonical_nets: dict[str, list[str]] = {}
    for a, b in PAIRS:
        if nets[a] != nets[b]:
            raise ValueError(f"original expected AXI net pair split {a} <> {b}")
        canonical_nets.setdefault(nets[a], []).extend((a, b))
    if len(canonical_nets) != len(PAIRS):
        raise ValueError("distinct AXI transactions unexpectedly share a single interface net")
    # Real readbacks are informational, not permission to silently translate
    # USER/ID or assume a generated 256-to-128-bit converter is correct.
    diffs = []
    sidebands = ("CONFIG.AWUSER_WIDTH", "CONFIG.ARUSER_WIDTH", "CONFIG.WUSER_WIDTH",
                 "CONFIG.RUSER_WIDTH", "CONFIG.BUSER_WIDTH", "CONFIG.ID_WIDTH")
    for a, b in PAIRS:
        for prop in sidebands:
            av, bv = endpoint_values[a][prop], endpoint_values[b][prop]
            if av != bv:
                diffs.append({"a": a, "b": b, "property": prop,
                              "a_value": av, "b_value": bv,
                              "classification": "UNRESOLVED_NEEDS_AXI_FIELD_PROOF"})
    return {
        "scope": "ORIGINAL_D3_VIVADO_READ_ONLY_AXIMM_AND_CONTROL_ENDPOINTS",
        "original_d3": str(original),
        "endpoints": len(ENDPOINTS), "memory_readback_widths": WIDTHS,
        "smartconnect": {"ctrl_sc": {"si": 1, "mi": 6},
                         "mem_sc": {"si": 4, "mi": 1}},
        "interface_nets": nets,
        "properties": endpoint_values,
        "sideband_property_disagreements": diffs,
        "generated_payload_bit_layout": "NOT_PROVEN",
        "protocol_integrity": "BLOCKED_UNTIL_GENERATED_ADAPTER_FUNCTIONAL_EVIDENCE",
        "physical_board": "NOT_AUTHORIZED",
        "simulation": "NOT_RUN", "synthesis": "NOT_RUN",
    }


def verify_original_and_inventory(original: Path, previous: Path) -> dict:
    orig = inspect_original(original)
    d4 = previous.resolve(strict=True)
    if (d4.is_symlink() or d4.name != "02_warning_inventory.json"
            or not d4.parent.name.startswith(OLD_PREFIX)
            or (d4.parent / "result.txt").read_text().strip() != "exit_status=3"):
        raise ValueError("prior owner original D4.1 read-only evidence identity/status invalid")
    prior = json.loads(d4.read_text())
    if prior != orig or len(prior["warnings"]) != 64:
        raise ValueError("prior original D4 inventory differs from unchanged original 2025.2 D3")
    return orig


def run(original: Path, previous: Path, report: Path, log: Path, output: Path) -> None:
    d4 = output.parent.resolve(strict=True)
    if (not d4.name.startswith(PREFIX) or output.name != "06_independent_bd_audit.json"
            or output.exists() or not d4.is_dir() or d4 == original.resolve()):
        raise ValueError("new D4.1b output must not overwrite previous owner evidence")
    original_dict = verify_original_and_inventory(original, previous)
    real_log = log.read_text()
    if SUCCESS not in real_log or "ERROR:" in real_log:
        raise ValueError("original Vivado read-only project query did not complete cleanly")
    details = parse(report.read_text(), original)
    details["original_d3_sha256"] = original_dict["original_file_sha256"]
    details["original_warning_occurrences"] = len(original_dict["warnings"])
    details["read_only_vivado_log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
    with output.open("x", encoding="utf-8") as fp:
        json.dump(details, fp, indent=2, sort_keys=True)
        fp.write("\n")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-d3", type=Path, required=True)
    p.add_argument("--previous-d4", type=Path, required=True)
    p.add_argument("--bd-report", type=Path, required=True)
    p.add_argument("--vivado-log", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        run(a.original_d3, a.previous_d4, a.bd_report, a.vivado_log, a.output)
    except (OSError, ValueError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"FAIL: original D4.1b Vivado endpoint-property audit: {exc}", file=sys.stderr)
        return 2
    print("READ-ONLY ORIGINAL VIVADO ENDPOINT AUDIT COMPLETE; AXI GENERATED-IP "
          "PROTOCOL/USER/ID/BURST GATE STILL BLOCKED (not an acceptance PASS)")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
