#!/usr/bin/env python3
"""Summarize A53-generated AXI read handshakes at both diagnostic boundaries."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import struct


UPSTREAM = {
    "addr": "net_slot_0_axi_araddr[39:0]",
    "size": "net_slot_0_axi_arsize[2:0]",
    "arvalid": "net_slot_0_axi_arvalid",
    "arready": "net_slot_0_axi_arready",
    "rdata": "net_slot_0_axi_rdata[31:0]",
    "rresp": "net_slot_0_axi_rresp[1:0]",
    "rvalid": "net_slot_0_axi_rvalid",
    "rready": "net_slot_0_axi_rready",
}
DOWNSTREAM = {
    "addr": "p03_ps_control_regs_0_p03_diag_araddr[31:0]",
    "arvalid": "p03_ps_control_regs_0_p03_diag_arvalid",
    "arready": "p03_ps_control_regs_0_p03_diag_arready",
    "rdata": "p03_ps_control_regs_0_p03_diag_rdata[31:0]",
    "rresp": "p03_ps_control_regs_0_p03_diag_rresp[0:0]",
    "rvalid": "p03_ps_control_regs_0_p03_diag_rvalid",
    "rready": "p03_ps_control_regs_0_p03_diag_rready",
}


def decode(path: Path, spec: dict[str, str], label: str) -> dict[int, list[int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        source = csv.reader(handle)
        columns = next(source)
        radix = next(source)
        if len(columns) != len(radix) or not radix[0].startswith("Radix"):
            raise ValueError(f"{path}: unexpected Vivado CSV format")
        indices: dict[str, int] = {}
        for logical, suffix in spec.items():
            matches = [i for i, column in enumerate(columns) if column.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError(
                    f"{path}: missing or ambiguous {logical} ({suffix}): {matches}"
                )
            indices[logical] = matches[0]

        requests: list[tuple[int, int, str]] = []
        responses: list[tuple[int, int, str]] = []
        count = 0
        for row in source:
            if not row or len(row) != len(columns):
                continue
            count += 1
            if row[indices["arvalid"]] == "1" and row[indices["arready"]] == "1":
                extra = f"size={row[indices['size']]}" if "size" in indices else ""
                requests.append((int(row[0]), int(row[indices["addr"]], 16), extra))
            if row[indices["rvalid"]] == "1" and row[indices["rready"]] == "1":
                responses.append(
                    (int(row[0]), int(row[indices["rdata"]], 16),
                     row[indices["rresp"]])
                )

    print(f"{label}: {count} samples, {len(requests)} AR, {len(responses)} R handshakes")
    for index, (sample, address, extra) in enumerate(requests):
        print(f"  AR[{index}] sample={sample} addr=0x{address:08X} {extra}")
    for index, (sample, data, resp) in enumerate(responses):
        print(f"   R[{index}] sample={sample} data=0x{data:08X} rresp={resp}")
    if len(requests) != len(responses):
        print(f"  INFO: captured window may omit requests or responses ({label})")
    # The standalone C program issues serialized 32-bit MMIO reads. The
    # association below is valid only when all AR/R handshakes are present.
    if len(requests) != len(responses):
        return {}
    by_addr: dict[int, list[int]] = {}
    for (_, address, _), (_, data, _) in zip(requests, responses):
        by_addr.setdefault(address, []).append(data)
    return by_addr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--base", type=lambda v: int(v, 0), required=True)
    args = parser.parse_args()
    root = args.capture_dir
    up = decode(root / "p03_2c_hpm0_capture.csv", UPSTREAM, "PS-facing AXI4")
    dn = decode(root / "p03_2c_mmio_slave_capture.csv", DOWNSTREAM, "MMIO slave AXI-Lite")
    mailbox_file = root / "p03_2c_a53_readonly_mailbox.bin"
    words = struct.unpack("<16I", mailbox_file.read_bytes())
    observed = words[4:8]
    expected = (0x4C543302, 0x00010000, 0x0001031F, 0xD1A60018)
    for offset, actual, wanted in zip((0, 4, 8, 0x18), observed, expected):
        address = args.base + offset
        print(
            f"A53 DDR mailbox: addr=0x{address:08X}, "
            f"value=0x{actual:08X}, expected=0x{wanted:08X}"
        )
        for label, channel in (("PS-facing", up), ("slave", dn)):
            data = channel.get(address)
            if data is None:
                print(f"  {label}: address not fully observed in this ILA window")
            else:
                print(f"  {label}: captured AXI RDATA={[f'0x{v:08X}' for v in data]}")
    if words[0] != 0x50335244 or words[13] != 0xC0DEF00D:
        print("WARNING: A53 mailbox missing valid magic or completion")
        return 2
    print("INFO: use request/response sample and channel evidence before attributing faults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
