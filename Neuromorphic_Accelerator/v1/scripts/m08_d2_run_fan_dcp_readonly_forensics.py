#!/usr/bin/env python3
"""D2 OWNER-PC ONLY: SHA-pinned ORIGINAL K26 fan-route checkpoint forensics.

Invokes genuine Vivado 2025.2 in batch to read existing routed DCP and emit
NEW timing/DRC/reset/clock reports, without bitstream writing or board access.
Strictly diagnostic: does not establish Linux runtime clocks, HPM0 availability,
ATB settings, physical AXI reads or safe hardware deployment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
TCL = SCRIPTS / "m08_d2_fan_dcp_readonly_forensics.tcl"
EXPECTED_ORIGINAL_DCP_SHA256 = (
    "aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e"
)
SUCCESS = "M08_D2_NATIVE_FAN_DCP_READONLY_INSPECTION_COMPLETED_NO_BOARD"
EXPECTED_INPUT = "48_fan_post_route.dcp"
EXPECTED_RECEIPT = "52_evidence_sha256.txt"
SOURCE_PATHS = (
    "scripts/m08_d2_run_fan_dcp_readonly_forensics.py",
    "scripts/m08_d2_fan_dcp_readonly_forensics.tcl",
    "scripts/m08_page_ps_bd_candidate.tcl",
    "scripts/m08_path_a_fan_bd_candidate.tcl",
    "rtl/m08/m08_axil_readonly_identity.v",
    "rtl/m08/m08_axil_page_control.sv",
    "rtl/m08/m08_ps_page_safe_shell.v",
)
REQUIRED_REPORTS = (
    "10_dcp_identity.txt",
    "11_dcp_timing.rpt",
    "12_dcp_drc.rpt",
    "13_dcp_methodology.rpt",
    "14_dcp_clock_utilization.rpt",
    "15_dcp_clock_interaction.rpt",
    "16_dcp_reset_net_inventory.txt",
)
REQUIRED_ORIGINAL_LEDGER_ROWS = (
    "48_fan_post_route.dcp",
    "41_fan_timing_post_route.rpt",
    "43_fan_drc_post_route.rpt",
    "44_fan_methodology_post_route.rpt",
    "46_fan_io_post_route.rpt",
    "49_independent_fan_route_audit.json",
)


class ForensicRejected(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ForensicRejected(reason)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_original_ledger(route: Path) -> dict[str, str]:
    """Never change a byte in the immutable ORIGINAL fan-route evidence."""
    require(route.is_dir() and not route.is_symlink(), "original route folder missing/symlinked")
    require(route.name.startswith("m08_2b_path_a_fan_route_"),
            "refuse different routed design or unrelated folder")
    ledger = route / EXPECTED_RECEIPT
    require(ledger.is_file() and not ledger.is_symlink(), "original SHA ledger absent")
    rows: dict[str, str] = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        require(m is not None, "malformed original SHA ledger line")
        sha, name = m.groups()
        require(name not in rows, "duplicate original SHA ledger entry")
        rows[name] = sha
    require(set(REQUIRED_ORIGINAL_LEDGER_ROWS).issubset(rows),
            "original ledger lacks full route/DRC/methodology evidence")
    require(rows[EXPECTED_INPUT] == EXPECTED_ORIGINAL_DCP_SHA256,
            "original DCP SHA does not match previously accepted fan-routed identity")
    for name, expected in rows.items():
        target = route / name
        require(target.is_file() and not target.is_symlink(), "missing original receipt file " + name)
        require(digest(target) == expected, "original receipt SHA mismatch " + name)
    return rows


def check_owner_pc() -> None:
    model = Path("/proc/device-tree/model")
    if model.exists():
        require("KV260" not in model.read_bytes().decode(errors="replace"),
                "M08 D2 vendor checkpoint forensics must NOT execute on KV260")
    require(platform.system() == "Linux", "PC Linux host required")
    require(shutil.which("vivado") is not None, "genuine Vivado required on owner PC")


def make_evidence(base: Path, route: Path) -> Path:
    require(base.is_dir() and not base.is_symlink(),
            "existing safe owner evidence base required")
    resolved = base.resolve()
    # The usual owner evidence base is the PARENT of the original route
    # archive. Creating a NEW sibling directory there is safe; creating the
    # output base inside the immutable original route directory is not.
    original = route.resolve()
    require(resolved != original and original not in resolved.parents,
            "forensic output base must not be original route or a child of it")
    require(resolved != Path("/") and not str(resolved).startswith(
        ("/etc/", "/boot/", "/lib/", "/sys/", "/proc/", "/dev/", "/run/")),
        "forbidden forensic output location")
    return Path(tempfile.mkdtemp(prefix="m08_d2_fan_dcp_READONLY_", dir=resolved))


def create_sha_receipt(folder: Path) -> None:
    lines = []
    for p in sorted(folder.iterdir()):
        if (p.is_file() and not p.is_symlink()
                and p.name != "99_evidence_sha256.txt"):
            lines.append(digest(p) + "  " + p.name)
    (folder / "99_evidence_sha256.txt").write_text("\n".join(lines) + "\n")


def execute(route: Path, base: Path) -> tuple[Path, bool]:
    check_owner_pc()
    rows = read_original_ledger(route)
    dcp = route / EXPECTED_INPUT
    require(digest(dcp) == EXPECTED_ORIGINAL_DCP_SHA256,
            "original checkpoint changed between ledger and tool input")
    require(TCL.is_file() and not TCL.is_symlink(), "missing original forensic Tcl")
    before = {name: digest(ROOT / name) for name in SOURCE_PATHS}
    folder = make_evidence(base, route)
    success = False
    try:
        (folder / "00_original_inputs.json").write_text(
            json.dumps({
                "schema": "m08-d2-owner-original-fan-dcp-inputs-v1",
                "original_route_dir": str(route.resolve()),
                "original_route_receipt_sha256": digest(route / EXPECTED_RECEIPT),
                "original_route_file_count": len(rows),
                "expected_original_dcp_sha256": EXPECTED_ORIGINAL_DCP_SHA256,
                "new_source_sha256_before": before,
                "vivado_required": "2025.2",
                "offline_only": True,
                "physical_mmio_authorized": False,
            }, sort_keys=True, indent=2) + "\n")
        with (folder / "01_native_vivado.log").open("x", encoding="utf-8") as log:
            # No shell, no JTAG, and no Vivado design-modifying command.
            proc = subprocess.run(
                ["vivado", "-mode", "batch", "-nolog", "-nojournal", "-notrace",
                 "-source", str(TCL),
                 "-tclargs", str(dcp.resolve()), str(folder.resolve()),
                 EXPECTED_ORIGINAL_DCP_SHA256],
                cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=False)
        (folder / "02_vivado_exit.txt").write_text("vivado_exit_status=" + str(proc.returncode) + "\n")
        after = {name: digest(ROOT / name) for name in SOURCE_PATHS}
        (folder / "03_source_sha256_after.json").write_text(
            json.dumps(after, sort_keys=True, indent=2) + "\n")
        log_text = (folder / "01_native_vivado.log").read_text(errors="replace")
        success = (proc.returncode == 0 and before == after
                   and digest(dcp) == EXPECTED_ORIGINAL_DCP_SHA256
                   and sum(line.strip() == SUCCESS for line in log_text.splitlines()) == 1
                   and all((folder / filename).is_file() and
                           (folder / filename).stat().st_size > 0
                           for filename in REQUIRED_REPORTS))
        review = {
            "schema": "m08-d2-owner-original-fan-dcp-inspection-review-v1",
            "status": ("NATIVE_OFFLINE_DCP_REPORTS_GENERATED_REVIEW_PENDING"
                       if success else "NATIVE_DCP_INSPECTION_FAILED_OR_INCOMPLETE"),
            "original_dcp_sha256": EXPECTED_ORIGINAL_DCP_SHA256,
            "original_route_unchanged": digest(dcp) == EXPECTED_ORIGINAL_DCP_SHA256,
            "new_sources_unchanged": before == after,
            "vivado_exit_status": proc.returncode,
            "required_reports_present": success,
            "physical_axil_read_verified": False,
            "runtime_pl_clock_or_reset_verified": False,
            "atb_config_verified": False,
            "firewall_isolation_verified": False,
            "hardware_safe_to_test": False,
            "new_bitstream_generated": False,
        }
        (folder / "98_review.json").write_text(json.dumps(review, indent=2, sort_keys=True) + "\n")
    finally:
        create_sha_receipt(folder)
    return folder, success


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--route-dir", required=True, type=Path)
    ap.add_argument("--evidence-base", type=Path,
                    default=Path.home() / "Thesis_Evidence" / "M08")
    opts = ap.parse_args()
    try:
        folder, success = execute(opts.route_dir, opts.evidence_base)
    except (ForensicRejected, OSError, UnicodeError) as exc:
        print("M08_D2_DCP_PREFLIGHT_REJECTED_NO_BOARD: " + str(exc), file=sys.stderr)
        return 2
    print("M08_D2_FORENSIC_EVIDENCE_DIR=" + str(folder))
    print("M08_D2_ORIGINAL_OWNER_EVIDENCE_PRESERVED=" + EXPECTED_ORIGINAL_DCP_SHA256)
    if not success:
        print("M08_D2_DCP_NATIVE_REVIEW_INCOMPLETE_NO_BOARD", file=sys.stderr)
        return 2
    print("M08_D2_DCP_NATIVE_REPORTS_GENERATED_REVIEW_PENDING_NO_BOARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
