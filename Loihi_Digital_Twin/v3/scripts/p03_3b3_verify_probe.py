#!/usr/bin/env python3
"""Strictly verify physical P03.3b3 HLS packet, DDR routing, and mutable paging."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

NAMES = (
    "magic", "version", "result", "error", "ps_width", "runtime_fault",
    "fault_phase", "dispatches", "barriers", "packets",
    "initial_page_ins", "page_ins", "page_outs", "page_operations",
    "last_page_bytes", "last_dispatch_count",
    "packet0_lo", "packet0_hi", "packet1_lo", "packet1_hi",
    "core1_ddr_event1", "core0_ddr_event0", "core1_resident_event1",
    "core1_config0", "timesteps", "last_bank",
    "core0_event0_count", "core1_event1_count",
    "global_status", "page_pending", "page_write_bursts",
    "page_read_bursts",
)


def verify(mailbox: Path, manifest: Path) -> bool:
    data = mailbox.read_bytes()
    if len(data) != 128:
        print(f"FAIL: P03.3b3 physical mailbox size {len(data)} != 128", file=sys.stderr)
        return False
    raw = struct.unpack("<32I", data)
    observed = dict(zip(NAMES, raw))
    fixture = json.loads(manifest.read_text(encoding="utf-8"))

    # An error=2 is a *preflight header failure before any dispatch*.
    # Never misreport the reused diagnostic words as generated packets.
    # The new A53 probe captures exact observed bytes for both records;
    # the old probe did not and can only be classified by its error code.
    if observed["error"] == 2:
        offsets = (0, 4, 8, 12, 16, 20, 24, 28, 44, 48, 52)
        if raw[7] == 0x48445233:  # HDR3 error-only mailbox overlay
            masks = (raw[8], raw[9])
            for core, mask in enumerate(masks):
                expected_header = (
                    0x3356544C, 0x31585443, 1, 0x1000, 0x80000,
                    core, 0, 0, 1 if core == 0 else 0, 0, 0,
                )
                header_words = raw[(10 + core * 11):(21 + core * 11)]
                print(
                    f"P03_3B3_HEADER_CORE{core}_FAIL_MASK=0x{mask:08X}",
                    file=sys.stderr,
                )
                for i, (offset, actual, expected_value) in enumerate(
                    zip(offsets, header_words, expected_header)
                ):
                    if (mask & (1 << i)) or actual != expected_value:
                        print(
                            "FAIL: P03.3b3 A53 DDR header "
                            f"core={core} offset=0x{offset:02X} "
                            f"address=0x{0x40000000 + core * 0x80000 + offset:08X} "
                            f"actual=0x{actual:08X} expected=0x{expected_value:08X}",
                            file=sys.stderr,
                        )
            if not any(masks):
                print(
                    "FAIL: P03.3b3 HDR3 overlay present but neither mismatch "
                    "mask is set; capture and inspect the raw 128-byte mailbox.",
                    file=sys.stderr,
                )
        else:
            print(
                "FAIL: P03.3b3 error=2 without HDR3 mismatch snapshot. "
                "Earlier probe firmware inverted validate_backing()'s "
                "0=success result and falsely reported a header error. "
                "Check the exact A53 ELF build identity and retry with "
                "the corrected startup condition.",
                file=sys.stderr,
            )
        print(
            "FAIL: P03.3b3 early DDR-header preflight "
            f"result=0x{observed['result']:08X} error={observed['error']} "
            "(no packet or page activity attempted)",
            file=sys.stderr,
        )
        return False

    packet0 = observed["packet0_lo"] | observed["packet0_hi"] << 32
    packet1 = observed["packet1_lo"] | observed["packet1_hi"] << 32

    expected = {
        "magic": 0x50334233,
        "version": 1,
        "result": 0x600D600D,
        "error": 0,
        "runtime_fault": 0,
        "dispatches": fixture["expected_dispatches"],
        "barriers": fixture["expected_barriers"],
        "packets": fixture["expected_routed_packets"],
        "initial_page_ins": fixture["expected_initial_page_ins"],
        "page_ins": fixture["expected_page_ins"],
        "page_outs": fixture["expected_page_outs"],
        "page_operations": fixture["expected_page_completed"],
        "last_page_bytes": 438272,
        "last_dispatch_count": 4,
        "core1_ddr_event1": fixture["expected_event1_core1"],
        "core0_ddr_event0": fixture["expected_event0_core0"],
        "core1_resident_event1": fixture["expected_event1_core1"],
        "core1_config0": fixture["core1"]["config0"],
        "timesteps": 2,
        "last_bank": 0,
        "core0_event0_count": 1,
        "core1_event1_count": 0,
        "global_status": 0,
        "page_pending": 0,
    }
    errors = [
        f"{key} actual=0x{observed[key]:X} expected=0x{value:X}"
        for key, value in expected.items() if observed[key] != value
    ]
    if ((observed["ps_width"] >> 8) & 3) != 2:
        errors.append(
            f"booted PS HPM0 width selector {((observed['ps_width'] >> 8) & 3)} != 2"
        )
    if packet0 != int(fixture["first_packet"], 16):
        errors.append(
            f"real core0 HLS packet actual=0x{packet0:016X} "
            f"expected={fixture['first_packet']}"
        )
    if packet1 != int(fixture["last_packet"], 16):
        errors.append(
            f"real core1 HLS packet actual=0x{packet1:016X} "
            f"expected={fixture['last_packet']}"
        )
    if observed["page_write_bursts"] == 0 or observed["page_read_bursts"] == 0:
        errors.append("expected physical DDR page-in and page-out AXI bursts")
    if errors:
        for failure in errors:
            print(f"FAIL: P03.3b3 {failure}", file=sys.stderr)
        print(
            "FAIL: P03.3b3 physical HLS packet delivery / dirty-page roundtrip"
            f" result=0x{observed['result']:08X}"
            f" first_fault={observed['runtime_fault']}"
            f" error={observed['error']} phase={observed['fault_phase']}",
            file=sys.stderr,
        )
        return False
    print(
        "PASS: P03.3b3 physical packet/page roundtrip "
        f"ps_width=128 first_packet=0x{packet0:016X} "
        f"second_packet=0x{packet1:016X} "
        f"core1_ddr_event1={observed['core1_ddr_event1']} "
        f"core0_ddr_event0={observed['core0_ddr_event0']} "
        f"page_ins={observed['page_ins']} page_outs={observed['page_outs']} "
        f"dispatches={observed['dispatches']} barriers={observed['barriers']} "
        f"routed_packets={observed['packets']}"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mailbox", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    return 0 if verify(args.mailbox, args.manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())
