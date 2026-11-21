#!/usr/bin/env python3
"""FIRST-ORIGINAL M32Q native image inspection (read only; ALWAYS EXIT 2).

No new route, bit SHA, DRC warning instance or timing report has been accepted.
This tool verifies presence, immutable receipt and source identity ONLY.
It MUST NOT approve a new D3.D.2E bitstream for physical programming.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/m08_d3d2e_queue_build.tcl"
RTL = ROOT / "rtl/m08/m08_d3d2e_tick_queue_lif_axil.v"
POR = ROOT / "rtl/m08_d3c_fabric_por.v"
BIT = "bitstream_candidate/m08_d3d2e_queue_lif_jtag_UNRELEASED.bit"
FILES = (
    "00_vivado.log", "01_vivado.jou", "02_vivado_exit.txt",
    "reports/10_fan_a12.xdc", "reports/11_fabric_por.v",
    "reports/12_synaptic_lif_axil.v", "reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt", "reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt", "reports/30_native_result.txt", BIT
)

class Reject(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise Reject(reason)

def digest(path: Path):
    require(path.is_file() and not path.is_symlink(),
            "missing, symlinked or non-file evidence: " + str(path))
    return sha256(path.read_bytes()).hexdigest()

def inspect(run: Path):
    # Never materialize or modify the original owner data.
    require(run.is_dir() and not run.is_symlink(), "not a real evidence directory")
    require(re.fullmatch(r"m08_d3d2e_queue_[A-Za-z0-9]{8}", run.name) is not None,
            "not a new D3.D.2E evidence directory")
    expected_base = Path.home() / "Thesis_Evidence" / "M08"
    require(not expected_base.is_symlink() and run.parent.resolve() == expected_base.resolve(),
            "symlinked evidence base or directory outside owner M08 evidence root")
    receipt = run / "99_evidence_sha256.txt"
    require(receipt.is_file() and not receipt.is_symlink(),
            "missing or symlinked original evidence ledger")
    lines = receipt.read_text(encoding="ascii").splitlines()
    require(len(lines) == len(FILES), "not exactly 12 original receipts")
    for line, name in zip(lines, FILES):
        require(re.fullmatch(r"[0-9a-f]{64}  " + re.escape(name), line)
                is not None, "missing/unexpected/reordered SHA receipt: " + name)
        expected = line[:64]
        require(digest(run / name) == expected,
                "original receipt bytes mismatch: " + name)
    require((run / "02_vivado_exit.txt").read_text().strip() == "vivado_build_exit=0",
            "Vivado build was not successful")
    native = (run / "reports/30_native_result.txt").read_text(encoding="ascii")
    metadata = {}
    for line in native.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            require(key not in metadata, "duplicate metadata key")
            metadata[key] = value
    fixed = {
        "schema": "m08-d3d2e-tick-queue-32-offline-build-v1",
        "wrapper_top": "m08_d3d2e_queue_lif_jtag_wrapper",
        "physical_neurons": "32", "physical_ticks": "4",
        "m06_original_edges": "5", "m06_original_external_events": "17",
        "event_fifo_capacity": "32", "event_mailbox_lifetime_capacity": "64",
        "queue_ingress_accepted_separate_from_service": "YES",
        "queue_service_tick_barriers": "4",
        "ps_to_pl_hpm": "DISABLED", "physical_event_stream_dma": "NO",
        "physical_m06_ddr": "NO", "ps_clock_dependency": "YES",
        "ps_pl0_clock_request_hz": "100000000",
        "ps_pl0_runtime_clock_proven": "NO",
        "new_image_owner_drc_review": "REQUIRED",
        "asynchronous_clock_domain_proven": "NO",
        "hardware_bitstream_programmed": "NO",
        "hardware_neural_execution_proven": "NO",
        "part": "xck26-sfvc784-2LV-c",
        "lif_base": "0xA0001000", "bram_map_base": "0xA0000000",
        "reset_mode": "FABRIC_POR_256_CYCLES",
    }
    for key, expected in fixed.items():
        require(metadata.get(key) == expected,
                "new-image native metadata mismatch: " + key)
    require(metadata.get("vivado_version", "").startswith("2025.2"),
            "not a Vivado 2025.2 native image")
    for key, src, copy in (
        ("builder_sha256", BUILD, None),
        ("lif_rtl_sha256", RTL, run / "reports/12_synaptic_lif_axil.v"),
        ("fabric_por_rtl_sha256", POR, run / "reports/11_fabric_por.v"),
    ):
        expected = digest(src)
        require(metadata.get(key) == expected, "source identity mismatch: " + key)
        if copy is not None:
            require(digest(copy) == expected, "copy identity mismatch: " + key)
    bit_bytes = (run / BIT).stat().st_size
    require(bit_bytes > 100_000 and str(bit_bytes) == metadata.get("bitstream_size_bytes"),
            "candidate bitstream size drift or implausible")
    require((run / "reports/20_route_drc.rpt").stat().st_size > 0,
            "no original routed DRC")
    require((run / "reports/21_route_timing.rpt").stat().st_size > 0,
            "no original routed timing")
    return {
        "sha_ledger_rows_verified": len(FILES),
        "new_original_candidate_sha256": digest(run / BIT),
        "new_original_candidate_bytes": bit_bytes,
        "drc_allowlist": "NONE_NEW_IMAGE_PENDING_HUMAN_REVIEW",
        "timing_acceptance": "NOT_REVIEWED",
        "image_specific_gate": "BLOCKED",
        "physical_programming": "NOT_AUTHORIZED",
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        data = inspect(args.run_dir)
        for key, value in data.items():
            print(f"{key}={value}")
        print("M08_D3D2E_FIRST_IMAGE_DRC_TIMING_SOURCE_AND_SHA_REVIEW_REQUIRED_NO_BOARD")
    except (Reject, ValueError, OSError, UnicodeError) as exc:
        print("M08_D3D2E_NATIVE_REVIEW_REJECTED: " + str(exc), file=sys.stderr)
    return 2  # UNCONDITIONAL: never release unreviewed candidate.

if __name__ == "__main__":
    raise SystemExit(main())
