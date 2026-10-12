#!/usr/bin/env python3
"""Reproduce the P03.2c dual-ILA VERSION read localization from Vivado CSVs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re


def read_capture(path: Path, signals: dict[str, str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        rows = csv.reader(source)
        header = next(rows)
        radix = next(rows)
        if len(radix) != len(header) or not radix[0].startswith("Radix"):
            raise ValueError(f"{path}: malformed Vivado CSV radix header")
        locations = {}
        for signal, suffix in signals.items():
            matches = [i for i, name in enumerate(header) if name.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError(f"{path}: {signal} expected one column, got {matches}")
            locations[signal] = matches[0]
        samples = [
            {"sample": row[0], **{key: row[idx] for key, idx in locations.items()}}
            for row in rows
        ]
    if not samples:
        raise ValueError(f"{path}: capture has no samples")
    return samples


def one_handshake_pair(
    samples: list[dict[str, str]], label: str, address: int, expected: int
) -> dict[str, str]:
    requests = [
        sample for sample in samples
        if sample["arvalid"] == "1" and sample["arready"] == "1"
    ]
    responses = [
        sample for sample in samples
        if sample["rvalid"] == "1" and sample["rready"] == "1"
    ]
    if len(requests) != 1 or len(responses) != 1:
        raise AssertionError(
            f"{label}: expected exactly one AR and R handshake, got "
            f"{len(requests)} and {len(responses)}"
        )
    accepted = int(requests[0]["araddr"], 16)
    returned = int(responses[0]["rdata"], 16)
    if accepted != address or returned != expected:
        raise AssertionError(
            f"{label}: 0x{accepted:08X} -> 0x{returned:08X}, expected "
            f"0x{address:08X} -> 0x{expected:08X}"
        )
    print(
        f"PASS: {label} AR sample={requests[0]['sample']} "
        f"address=0x{accepted:08X}; R sample={responses[0]['sample']} "
        f"data=0x{returned:08X}"
    )
    return responses[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--downstream", type=Path, required=True)
    parser.add_argument("--xsdb", type=Path, required=True)
    parser.add_argument("--address", type=lambda v: int(v, 0), default=0xA4000004)
    parser.add_argument("--expected", type=lambda v: int(v, 0), default=0x00010000)
    args = parser.parse_args()

    upstream = read_capture(args.upstream, {
        "araddr": "net_slot_0_axi_araddr[39:0]",
        "arvalid": "net_slot_0_axi_arvalid",
        "arready": "net_slot_0_axi_arready",
        "rdata": "net_slot_0_axi_rdata[31:0]",
        "rvalid": "net_slot_0_axi_rvalid",
        "rready": "net_slot_0_axi_rready",
        "rresp": "net_slot_0_axi_rresp[1:0]",
        "rlast": "net_slot_0_axi_rlast",
        "arsize": "net_slot_0_axi_arsize[2:0]",
    })
    downstream = read_capture(args.downstream, {
        "araddr": "p03_ps_control_regs_0_p03_diag_araddr[31:0]",
        "arvalid": "p03_ps_control_regs_0_p03_diag_arvalid",
        "arready": "p03_ps_control_regs_0_p03_diag_arready",
        "rdata": "p03_ps_control_regs_0_p03_diag_rdata[31:0]",
        "rvalid": "p03_ps_control_regs_0_p03_diag_rvalid",
        "rready": "p03_ps_control_regs_0_p03_diag_rready",
        "rresp_low": "p03_ps_control_regs_0_p03_diag_rresp[0:0]",
    })
    up = one_handshake_pair(upstream, "PS-facing AXI4", args.address, args.expected)
    dn = one_handshake_pair(
        downstream, "MMIO-slave AXI4-Lite", args.address, args.expected
    )
    if up["rresp"] != "OKAY" or up["rlast"] != "1" or up["arsize"] != "4 bytes":
        raise AssertionError("PS-facing AXI4 response status or size is wrong")
    if dn["rresp_low"] != "0":
        raise AssertionError("MMIO-slave RRESP[0] indicates an error")
    print("PASS: upstream RRESP=OKAY, RLAST=1, ARSIZE=4 bytes")

    result = args.xsdb.read_text(encoding="utf-8", errors="replace")
    pattern = rf"(?im)^\s*{args.address:08X}:\s*([0-9a-f]{{8}})\s*$"
    match = re.search(pattern, result)
    if not match:
        raise AssertionError("XSDB result for address not found")
    observed = int(match.group(1), 16)
    print(f"INFO: XSDB reported 0x{observed:08X}")
    if observed != args.expected:
        print(
            "LOCALIZED: PL/slave and converter correctly returned data; "
            "XSDB readout disagrees beyond the measured PL-to-PS boundary."
        )
    else:
        print("PASS: XSDB and PL response agree")


if __name__ == "__main__":
    main()
