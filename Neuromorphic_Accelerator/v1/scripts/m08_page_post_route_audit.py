#!/usr/bin/env python3
"""Independent consistency audit of original M08.2b.4a Vivado post-route outputs.

Source and file/report integrity ONLY. Real routed K26 timing evidence is
required; success still does NOT establish a bitstream, board programming,
physical DDR, Linux MMIO, unconstrained-path closure or DRC signoff.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

FILES = (
    "rtl/m08/m08_axil_readonly_identity.v",
    "rtl/m08/m08_host_staged_page_bank.sv",
    "rtl/m08/m08_axil_page_control.sv",
    "rtl/m08/m08_ps_page_safe_shell.v",
    "scripts/m08_page_ps_bd_candidate.tcl",
    "scripts/m08_page_bd_audit.py",
    "scripts/run_m08_page_bd.sh",
    "scripts/m08_page_post_route_candidate.tcl",
    "scripts/m08_page_post_route_audit.py",
    "scripts/run_m08_page_post_route.sh",
)
ORIGINALS = (
    "01_vivado_impl.log",
    "02_vivado_page_bd_readback.txt",
    "03_page_bd_export.tcl",
    "04_implementation_metrics.txt",
    "05_timing_summary_post_route.rpt",
    "06_utilization_post_route.rpt",
    "07_drc_post_route.rpt",
    "08_methodology_post_route.rpt",
    "09_clock_utilization_post_route.rpt",
    "10_m08_page_post_route.dcp",
)
MARKERS = (
    "M08_KV260_PS_BOARD_PRESET_APPLIED=1",
    "M08_PAGE_BD_DISTINCT_ID_AND_PAGE_4K_ADDRESS_SEGMENTS=1",
    "M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD",
    "M08_PAGE_GENUINE_NATIVE_WRAPPER_GENERATED=1",
    "M08_PAGE_GENUINE_NATIVE_SYNTH_AND_ROUTE_COMPLETED=1",
    "M08_PAGE_POST_ROUTE_TIMING_NONNEGATIVE_NO_BITSTREAM=1",
    "M08_PAGE_NATIVE_ROUTE_REPORTS_GENERATED_UNREVIEWED_DRC_NO_BOARD",
)
METRIC_KEYS = (
    "scope", "part", "vivado_version", "synthesis_status",
    "implementation_status", "synthesis_progress", "implementation_progress",
    "wns_ns", "whs_ns", "clock_count", "no_bitstream",
    "no_board_programming", "compute_enabled", "physical_ddr", "linux_mmio",
)


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def original(folder: Path, name: str) -> bytes:
    f = folder / name
    if f.is_symlink() or not f.is_file():
        raise ValueError("missing, symlinked or replaced original: " + name)
    data = f.read_bytes()
    if not data:
        raise ValueError("empty original evidence: " + name)
    return data


def audit_evidence(folder: Path, root: Path) -> dict:
    if not folder.is_dir() or folder.is_symlink() or not root.is_dir():
        raise ValueError("source root or original evidence directory invalid")
    if original(folder, "result.txt") != b"exit_status=0\n":
        raise ValueError("original Vivado route process not successful")
    expected = "".join(f"{sha(root / name)}  {name}\n" for name in FILES).encode()
    if original(folder, "source_sha256_before.txt") != expected:
        raise ValueError("source SHA256 does not match exact checked-out sources")
    if original(folder, "source_sha256_after.txt") != expected:
        raise ValueError("source was modified across native Vivado execution")

    log = original(folder, ORIGINALS[0]).decode("utf-8", errors="replace")
    if "ERROR:" in log or "CRITICAL WARNING:" in log or "Common 17-39" in log:
        raise ValueError("genuine native Vivado log contains severe error or warning")
    # The Tcl source is echoed in a genuine Vivado log. Only a separately
    # printed whole-line marker counts, not an echoed 'puts "MARKER"'.
    for marker in MARKERS:
        if sum(line.strip() == marker for line in log.splitlines()) != 1:
            raise ValueError("native Vivado marker missing/duplicated: " + marker)
    report = original(folder, ORIGINALS[1]).decode("utf-8").splitlines()
    expected_rows = (
        "META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD",
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|board_part|xilinx.com:kv260_som:part0:",
        "META|ps_preset|YES",
        "META|requested_clock_hz|100000000",
        "META|actual_clock_hz|",
        "META|page_source|rtl/m08/m08_ps_page_safe_shell.v",
        "META|compute_enabled|NO",
        "MASTER|M_AXI_HPM0_FPD|/ps/Data",
        "SLAVE_IDENTITY|/identity/S_AXI|/identity/S_AXI/",
        "SLAVE_PAGE|/page/S_AXI|/page/S_AXI/",
        "APERTURE_IDENTITY|/ps/Data/SEG_identity",
        "APERTURE_PAGE|/ps/Data/SEG_page",
        "META|validated_bd|YES",
        "META|routed_implementation|NOT_RUN",
        "META|bitstream|NOT_GENERATED",
        "META|linux_mmio|NOT_ACCESSED",
        "META|physical_ddr|NOT_ACCESSED",
        "META|physical_kv260|NOT_PROGRAMMED",
    )
    # These rows were printed DURING original BD validation before route;
    # routed status is established only by the separate native route metrics.
    if len(report) != len(expected_rows):
        raise ValueError("native PS BD readback row count changed")
    for i, (row, prefix) in enumerate(zip(report, expected_rows)):
        if not row.startswith(prefix):
            raise ValueError(f"native PS BD row {i} unexpected: {row!r}")
    ps_clock = report[6].split("|")
    if len(ps_clock) != 3 or not re.fullmatch(r"[0-9]+", ps_clock[2]):
        raise ValueError("missing actual K26 clock readback")
    actual_clock = int(ps_clock[2])
    if abs(actual_clock - 100_000_000) > 1000:
        raise ValueError("actual K26 clock outside accepted 1 kHz deviation")
    for marker in (
        f"M08_GENUINE_PS_PL0_CLOCK_HZ={actual_clock}",
        f"M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ={actual_clock}",
    ):
        if sum(line.strip() == marker for line in log.splitlines()) != 1:
            raise ValueError("actual clock marker missing/duplicated: " + marker)
    segments = []
    for row in report[12:14]:
        parts = row.split("|")
        if len(parts) != 4 or not all(parts):
            raise ValueError("missing real PS address segment details")
        if not re.fullmatch(r"0x[0-9a-fA-F]+", parts[2]) or not re.fullmatch(
            r"0x[0-9a-fA-F]+", parts[3]
        ):
            raise ValueError("non-hex address/readback from Vivado")
        addr, size = int(parts[2], 16), int(parts[3], 16)
        if addr < 0 or size != 4096 or addr % 4096 != 0 or addr + size > 2**32:
            raise ValueError("PS aperture invalid")
        segments.append((addr, size))
    if segments[0][0] < segments[1][0] + segments[1][1] and (
        segments[1][0] < segments[0][0] + segments[0][1]
    ):
        raise ValueError("identity and page PS apertures overlap")

    exported = original(folder, ORIGINALS[2]).decode("utf-8", errors="replace")
    flatten = exported.replace(chr(92) + chr(10), " ")
    connections = [x for x in flatten.splitlines() if x.lstrip().startswith(
        "connect_bd_intf_net"
    )]
    for left, right in (
        ("ps/M_AXI_HPM0_FPD", "ctrl_sc/S00_AXI"),
        ("ctrl_sc/M00_AXI", "identity/S_AXI"),
        ("ctrl_sc/M01_AXI", "page/S_AXI"),
    ):
        if not any(left in line and right in line for line in connections):
            raise ValueError("original export missing native AXI link "+left+"->"+right)
    if "m08_ps_page_safe_shell" not in exported:
        raise ValueError("original export missing safe page shell")

    metrics = original(folder, ORIGINALS[3]).decode("utf-8").splitlines()
    observed = {}
    for row in metrics:
        key = row.split("|")
        if len(key) != 3 or key[0] != "META" or key[1] in observed:
            raise ValueError("malformed or duplicate original route metric")
        observed[key[1]] = key[2]
    if set(observed) != set(METRIC_KEYS):
        raise ValueError("missing or unexpected actual native implementation metrics")
    if (observed["scope"] != "M08_GENUINE_LOCAL_KV260_PAGE_SAFE_POST_ROUTE" or
            observed["part"] != "xck26-sfvc784-2LV-c" or
            not observed["vivado_version"].startswith("2025.2") or
            observed["synthesis_progress"] != "100%" or
            observed["implementation_progress"] != "100%" or
            "Complete" not in observed["synthesis_status"] or
            "Complete" not in observed["implementation_status"]):
        raise ValueError("native synthesis/route did not finish on target")
    if (observed["no_bitstream"] != "YES" or
            observed["no_board_programming"] != "YES" or
            observed["compute_enabled"] != "NO" or
            observed["physical_ddr"] != "NOT_ACCESSED" or
            observed["linux_mmio"] != "NOT_ACCESSED"):
        raise ValueError("unsupported bitstream/physical claim or compute enabled")
    slacks = {}
    for name in ("wns_ns", "whs_ns"):
        try:
            number = float(observed[name])
        except ValueError as exc:
            raise ValueError("actual post-route timing slack is not numeric") from exc
        if not (-1e3 < number < 1e3) or number < 0:
            raise ValueError("actual setup/hold timing not nonnegative")
        slacks[name] = number
    if not observed["clock_count"].isdigit() or int(observed["clock_count"]) < 1:
        raise ValueError("no native implementation clocks")
    for name in ORIGINALS[4:9]:
        if len(original(folder, name)) < 50:
            raise ValueError("native routing report missing or implausibly short: " + name)
    if len(original(folder, ORIGINALS[9])) < 1024:
        raise ValueError("native checkpoint missing or implausibly short")
    return {
        "status": "ORIGINAL_OWNER_M08_KV260_ROUTE_EVIDENCE_CONSISTENT_DRC_REVIEW_REQUIRED",
        "source_sha256_manifest": sha(folder / "source_sha256_before.txt"),
        "original_digests": {name: sha(folder / name) for name in ORIGINALS},
        "native_synthesis_completed": True,
        "native_route_completed": True,
        "post_route_timing": slacks,
        "identity_addr": f"0x{segments[0][0]:08x}",
        "page_addr": f"0x{segments[1][0]:08x}",
        "clock_count": int(observed["clock_count"]),
        "original_drc_report_present_not_signed_off": True,
        "unconstrained_path_review_required": True,
        "bitstream_generated": False,
        "physical_kv260_programmed": False,
        "linux_mmio_accessed": False,
        "physical_ddr_accessed": False,
        "kernel_dma_ownership_proved": False,
        "signed16_inference_proved": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.output.exists() or args.output.is_symlink() or
                args.output.parent.resolve() != args.evidence_dir.resolve()):
            raise ValueError("audit output must be new and inside the source evidence folder")
        r = audit_evidence(args.evidence_dir, args.source_root)
        with args.output.open("x", encoding="utf-8") as dest:
            json.dump(r, dest, indent=2, sort_keys=True)
            dest.write("\n")
    except (ValueError, OSError, UnicodeError) as exc:
        print("M08_NATIVE_ROUTE_AUDIT_REJECTED:", exc, file=sys.stderr)
        return 2
    print("M08_NATIVE_POST_ROUTE_REPORT_AND_SHA_CONSISTENT_DRC_REVIEW_PENDING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
