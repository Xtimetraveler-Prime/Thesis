#!/usr/bin/env python3
"""M08.2b Path A: PC-only, REVIEW-ONLY Kria firmware staging.

Convert the EXACT owner-verified fan-preserving .bit with AMD bootgen;
compile a stock-shaped fpga_full overlay using native dtc; generate PL_FLAT
metadata. No board connection, no module binding, no firmware installation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

STEM = "m08-v1-fan-page"
ORIGINAL_BIT_SHA = "2d749451f46fe0660a9e78081cb6c92920a608ba16c084f37d2e1ab32f3e8af8"
ORIGINAL_BIT_BYTES = 7_797_831
OLD_UNFANNED_SHA = "170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf"
AUDIT_STATUS = "M08_K26_NEW_FAN_BITSTREAM_OFFLINE_ONLY_NO_LINUX_NO_BOARD"
# No UIO or generic-uio nodes: kernel ownership remains unverified.
DTS = """/dts-v1/;
/plugin/;

/* Review-only M08.2b Path A, based on original K26 starter-kit overlay.
 * Same fpga_full / zynqmp_reset fixup symbols; do not copy 0xffffffff
 * unresolved phandles from dtc output as if they were actual values.
 * No M08 Linux memory ownership is asserted here.
 */
&fpga_full {
    #address-cells = <2>;
    #size-cells = <2>;
    firmware-name = "m08-v1-fan-page.bit.bin";
    resets = <&zynqmp_reset 0x74>, <&zynqmp_reset 0x75>,
             <&zynqmp_reset 0x76>, <&zynqmp_reset 0x77>;
};
"""
SHELL = {"shell_type": "PL_FLAT", "num_slots": "1"}
EXPECTED_RELEASE_FILES = (
    "01_original_route_preflight.json",
    "02_vivado_fan_bitstream.log",
    "02_vivado_fan_bitstream_exit.txt",
    "03_source_sha256_after.txt",
    "04_fan_release_timing.rpt",
    "05_m08_path_a_fan_page.bit",
    "06_fan_bitstream_metrics.txt",
    "07_fan_bitstream_independent_audit.json",
)


def require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check_release(release: Path) -> dict:
    require(release.is_dir() and not release.is_symlink()
            and release.name.startswith("m08_2b_path_a_fan_bitstream_"),
            "original owner offline bitstream evidence directory required")
    ledger = release / "08_evidence_sha256.txt"
    require(ledger.is_file() and not ledger.is_symlink(), "missing original release SHA ledger")
    seen = set()
    for row in ledger.read_text().splitlines():
        found = re.fullmatch(r"([0-9a-f]{64})  ([a-zA-Z0-9_.]+)", row)
        require(found is not None, "malformed original release SHA line")
        expected, name = found.groups()
        require(name not in seen, "duplicate original release SHA entry")
        seen.add(name)
        target = release / name
        require(target.is_file() and not target.is_symlink() and sha(target) == expected,
                "original release evidence mismatch: " + name)
    require(all(item in seen for item in EXPECTED_RELEASE_FILES),
            "incomplete ORIGINAL release evidence ledger")
    require((release / "05_m08_path_a_fan_page.bit").stat().st_size == ORIGINAL_BIT_BYTES,
            "new fan bitstream exact byte count mismatch")
    require(sha(release / "05_m08_path_a_fan_page.bit") == ORIGINAL_BIT_SHA,
            "new fan bitstream original SHA mismatch")
    audit = json.loads((release / "07_fan_bitstream_independent_audit.json").read_text())
    require(audit.get("status") == AUDIT_STATUS and
            audit.get("bitstream_sha256") == ORIGINAL_BIT_SHA and
            audit.get("bitstream_bytes") == ORIGINAL_BIT_BYTES and
            audit.get("fan_pin") == "A12" and
            audit.get("fan_iostandard") == "LVCMOS33" and
            audit.get("fpga_programmed") is False and
            audit.get("linux_overlay_installed") is False and
            audit.get("ps_axi_readback_verified") is False,
            "original independent fan-bitstream audit missing or false claim")
    require(sha(release / "05_m08_path_a_fan_page.bit") != OLD_UNFANNED_SHA,
            "UNFANNED M08 bitstream is not acceptable for Path A")
    require((release / "02_vivado_fan_bitstream_exit.txt").read_text().strip()
            == "vivado_exit_status=0", "genuine native write_bitstream failed")
    log = (release / "02_vivado_fan_bitstream.log").read_text(errors="replace")
    require("write_bitstream completed successfully" in log and
            "M08_PATH_A_NEW_OFFLINE_FAN_BITSTREAM_EMITTED_NOT_PROGRAMMED" in log and
            "ERROR:" not in log and "CRITICAL WARNING:" not in log,
            "original vendor bitstream log not accepted")
    metrics = (release / "06_fan_bitstream_metrics.txt").read_text()
    require("META|fan_pin|A12\n" in metrics and
            "META|board_programmed|NO\n" in metrics and
            "META|compute_enabled|NO\n" in metrics,
            "original M08 physical/compute guard missing")
    return audit


def verify_overlay_text(text: str) -> None:
    # dtc decode prints unresolved 0xffffffff placeholders for fixups.
    # The __fixups__ symbols are the relevant offline correctness signal.
    require('"m08-v1-fan-page.bit.bin"' in text,
            "compiled overlay firmware-name mismatch")
    require("fpga_full" in text and "zynqmp_reset" in text and
            "__fixups__" in text, "missing AMD symbol fixup references")
    require(not re.search(r"\bgeneric-uio\b|\buio_pdrv_genirq\b|/dev/mem", text),
            "unverified Linux MMIO binding in package")
    require("m08-identity" not in text and "m08-page@" not in text,
            "unverified Linux register device ownership in package")


def write_ledger(folder: Path) -> None:
    lines = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.name != "99_evidence_sha256.txt":
            lines.append(f"{sha(path)}  {path.relative_to(folder)}")
    (folder / "99_evidence_sha256.txt").write_text("\n".join(lines) + "\n")


def native(args: list[str], cwd: Path, output: Path) -> None:
    with output.open("x", encoding="utf-8") as log:
        result = subprocess.run(args, cwd=cwd, stdout=log,
                                stderr=subprocess.STDOUT, check=False)
    require(result.returncode == 0,
            "native conversion failed (preserved log): " + str(output))


def stage(release: Path, base: Path) -> Path:
    # Validate genuine originals BEFORE creating any new evidence.
    check_release(release)
    require(base.is_dir() and not base.is_symlink(), "trusted PC evidence parent required")
    safe = base.resolve()
    require(safe != release.resolve() and release.resolve() not in safe.parents,
            "refusing to create staging outputs within original owner release evidence")
    require(not (safe == Path("/lib") or safe == Path("/lib/firmware") or
                 safe == Path("/boot") or safe == Path("/etc") or
                 str(safe).startswith(("/lib/firmware/", "/boot/", "/etc/"))),
            "refusing a Linux firmware/boot destination")
    for cmd in ("bootgen", "dtc"):
        require(shutil.which(cmd) is not None, "native PC utility missing: " + cmd)
    folder = Path(tempfile.mkdtemp(
        prefix="m08_2b_path_a_linux_package_REVIEW_ONLY_", dir=base))
    try:
        pkg = folder / STEM
        pkg.mkdir()
        build = folder / "build_inputs"
        build.mkdir()
        original = release / "05_m08_path_a_fan_page.bit"
        copy = build / f"{STEM}.bit"
        shutil.copyfile(original, copy)
        require(sha(copy) == ORIGINAL_BIT_SHA, "copy of verified M08 .bit changed")
        (build / "conversion.bif").write_text(
            f"all:{{{STEM}.bit}}\n")
        (folder / "00_source_sha256.txt").write_text(
            f"{sha(Path(__file__))}  {Path(__file__).name}\n")
        (folder / "01_inputs.json").write_text(json.dumps({
            "schema": "m08-path-a-offline-package-input-v1",
            "release_folder": str(release.resolve()),
            "verified_original_bitstream_sha256": ORIGINAL_BIT_SHA,
            "original_release_ledger_sha256": sha(release / "08_evidence_sha256.txt"),
            "required_shell_type": "PL_FLAT",
            "deployment_authorized": False,
        }, indent=2, sort_keys=True) + "\n")
        native(["bootgen", "-arch", "zynqmp", "-process_bitstream",
                "bin", "-image", "conversion.bif"], build,
               folder / "02_bootgen_original.log")
        converted = build / f"{STEM}.bit.bin"
        require(converted.is_file() and not converted.is_symlink()
                and 1_000_000 < converted.stat().st_size < 50_000_000,
                "genuine bootgen ZynqMP bit.bin missing or implausibly short")
        shutil.copyfile(converted, pkg / f"{STEM}.bit.bin")
        (folder / f"{STEM}.dts").write_text(DTS)
        native(["dtc", "-@", "-I", "dts", "-O", "dtb",
                "-o", str(pkg / f"{STEM}.dtbo"),
                str(folder / f"{STEM}.dts")], folder,
               folder / "03_dtc_original.log")
        decoded = subprocess.run(
            ["dtc", "-I", "dtb", "-O", "dts",
             str(pkg / f"{STEM}.dtbo")],
            cwd=folder, capture_output=True, text=True, check=False)
        (folder / "04_dtbo_roundtrip_original.log").write_text(
            decoded.stdout + "\n-- STDERR --\n" + decoded.stderr)
        require(decoded.returncode == 0,
                "native DTBO could not be decompiled")
        verify_overlay_text(decoded.stdout)
        (pkg / "shell.json").write_text(json.dumps(SHELL, indent=2) + "\n")
        require(json.loads((pkg / "shell.json").read_text()) == SHELL,
                "staged PL_FLAT shell metadata inconsistent")
        manifest = {
            "schema": "m08-path-a-linux-package-review-only-v1",
            "status": "OFFLINE_PACKAGE_STAGED_NO_BOARD_NO_MMIO_ACCESS",
            "shell_type": "PL_FLAT",
            "stock_k26_shell_type": "XRT_FLAT",
            "original_verified_bit_sha256": ORIGINAL_BIT_SHA,
            "bit_bin_sha256": sha(pkg / f"{STEM}.bit.bin"),
            "bit_bin_bytes": (pkg / f"{STEM}.bit.bin").stat().st_size,
            "dtbo_sha256": sha(pkg / f"{STEM}.dtbo"),
            "device_tree_mmio_nodes": "NONE_INTENTIONALLY",
            "kernel_uio_binding": "NOT_VERIFIED",
            "fan_pwm_during_reconfiguration": "NOT_VERIFIED",
            "linux_package_installed": False,
            "fpga_programmed": False,
            "ps_axi_readback_verified": False,
        }
        (folder / "05_package_review.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        (folder / "98_status.txt").write_text("staging_status=success\n")
    except Exception as exc:
        (folder / "98_status.txt").write_text(
            "staging_status=failed\nerror=" + str(exc) + "\n")
        write_ledger(folder)
        raise RuntimeError(f"OFFLINE staging stopped; preserve {folder}: {exc}") from exc
    write_ledger(folder)
    return folder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", type=Path, required=True)
    ap.add_argument("--evidence-base", type=Path, required=True)
    args = ap.parse_args()
    try:
        folder = stage(args.release_dir, args.evidence_base)
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print("M08_PATH_A_LINUX_PACKAGE_OFFLINE_REJECTED:", exc, file=sys.stderr)
        return 2
    print("M08_PATH_A_LINUX_REVIEW_ONLY_PACKAGE_STAGED_NOT_INSTALLED")
    print("M08_PATH_A_LINUX_PACKAGE_EVIDENCE_DIR=" + str(folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
