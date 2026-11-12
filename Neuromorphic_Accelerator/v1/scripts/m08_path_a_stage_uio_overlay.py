#!/usr/bin/env python3
"""M08.2b Path A: OFFLINE UIO-binding overlay CANDIDATE from original evidence.

Never programs a board, installs a firmware package, changes fan service,
modprobes a kernel driver, or accesses any MMIO registers. Generates only a
fresh PC-side candidate with two exact device-tree register resources.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

STEM = "m08-v1-fan-page-uio-review"
BIT = "m08-v1-fan-page.bit.bin"
FAN_BIT_BIN_SHA = "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b"
FAN_BIT_BIN_BYTES = 7_797_692
FAN_BIT_SHA = "2d749451f46fe0660a9e78081cb6c92920a608ba16c084f37d2e1ab32f3e8af8"
PRIOR_DTBO_SHA = "2a3608d5c7f84f1c62e4324ca3b5538692b449a6b2b8a1a5a4a0399a5dd6fd4e"
REGISTERS = (
    ("m08-identity", 0xA0000000, 0x1000),
    ("m08-page", 0xA0001000, 0x1000),
)
SHELL = {"shell_type": "PL_FLAT", "num_slots": "1"}
DTS = """/dts-v1/;
/plugin/;

/*
 * M08.2b review-only overlay. Two 4KiB UIO candidates, no IRQ/DMA.
 * NOT a verified/installed driver binding or safe reconfiguration.
 * The external fan output remains routed A12 in the .bit.bin.
 */
&fpga_full {
    #address-cells = <2>;
    #size-cells = <2>;
    firmware-name = "m08-v1-fan-page-uio-review.bit.bin";
    resets = <&zynqmp_reset 0x74>, <&zynqmp_reset 0x75>,
             <&zynqmp_reset 0x76>, <&zynqmp_reset 0x77>;
};

/*
 * Original, live KV260 /axi is a simple-bus with exactly 2/2 cells.
 * Explicitly restate its EXISTING encoding in the overlay fragment so dtc
 * can validate both 16-byte reg properties without guessing 2/1 defaults.
 * This is NOT a new bus or address translation.
 */
&amba {
    #address-cells = <2>;
    #size-cells = <2>;
    m08-identity@a0000000 {
        compatible = "generic-uio";
        linux,uio-name = "m08-identity";
        reg = <0x0 0xa0000000 0x0 0x1000>;
        status = "okay";
    };
    m08-page@a0001000 {
        compatible = "generic-uio";
        linux,uio-name = "m08-page";
        reg = <0x0 0xa0001000 0x0 0x1000>;
        status = "okay";
    };
};
"""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_ledger(folder: Path, filename: str) -> dict[str, str]:
    led = folder / filename
    require(folder.is_dir() and not folder.is_symlink() and
            led.is_file() and not led.is_symlink(),
            "missing or symlinked original evidence/receipt: " + filename)
    entries = {}
    for row in led.read_text().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.\-/]+)", row)
        require(match is not None, "malformed original evidence SHA row")
        expected, rel = match.groups()
        ref = Path(rel)
        require(not ref.is_absolute() and ".." not in ref.parts and rel not in entries,
                "unsafe or duplicate original evidence path")
        path = folder / ref
        require(path.is_file() and not path.is_symlink() and sha(path) == expected,
                "original evidence missing/changed: " + rel)
        entries[rel] = expected
    return entries


def probe_block(log: str, name: str) -> str:
    start = "M08_PROBE_BEGIN|" + name + "\n"
    require(log.count(start) == 1, "missing/duplicate read-only probe " + name)
    body = log.split(start, 1)[1].split(
        "M08_PROBE_END|" + name + "|rc=", 1)
    require(len(body) == 2 and body[1].startswith("0\n"),
            "read-only probe failed: " + name)
    return body[0]


def validate_board(folder: Path) -> dict:
    observed = verify_ledger(folder, "04_evidence_sha256.txt")
    require("01_board_stdout.log" in observed, "genuine SSH stdout missing from ledger")
    raw = (folder / "01_board_stdout.log").read_text()
    require(raw.startswith("M08_PATH_A_LINUX_READ_ONLY_BEGIN\n") and
            raw.rstrip().endswith("M08_PATH_A_LINUX_READ_ONLY_END_NO_FPGA_CHANGES"),
            "original SSH read-only source missing completion markers")
    require("ZynqMP KV260 revB" in probe_block(raw, "model"),
            "not the accepted original K26 board")
    osinfo = probe_block(raw, "os_release")
    require('VERSION_ID="24.04"' in osinfo, "unexpected installed Linux")
    require("uio_pdrv_genirq.of_id=generic-uio" in probe_block(raw, "cmdline"),
            "kernel generic-uio of_id not proven")
    manager = probe_block(raw, "manager_service").splitlines()
    require(manager[:3] == ["active", "inactive", "active"],
            "board Linux manager/fan services changed from safe baseline")
    require("operating" in probe_block(raw, "fpga_manager"),
            "Linux FPGA manager not operating")
    require("k26-starter-kits_image_1" in probe_block(raw, "active_overlays"),
            "original K26 starter-kit PL not current")
    driver = probe_block(raw, "m08_kernel_mmio_binding_readiness")
    require("DRIVER_PRESENT=/sys/bus/platform/drivers/uio_pdrv_genirq" in driver and
            re.search(r"^uio_pdrv_genirq\s+\d+", driver, re.M) is not None,
            "genuine generic UIO kernel driver missing")
    require("M08_LINUX_ACCESSOR=NOT_YET_VALIDATED" in driver,
            "board already using a different M08 Linux binding")
    for old in ("axi-pmon",):
        require(driver.count(":" + old) == 4,
                "existing four AXI performance UIO nodes unexpected")
    symbols = probe_block(raw, "m08_live_dt_amba_fpga_symbols")
    for label in ("amba", "fpga_full", "zynqmp_reset"):
        require(re.search(
            r"^M08_DT_SYMBOL=" + label + r"\|/[^\n]+$", symbols, re.M
        ) is not None and "M08_DT_SYMBOL_MISSING=" + label not in symbols and
            "M08_DT_TARGET_NOT_FOUND=" + label not in symbols,
            "required live device-tree symbol missing: " + label)
    require("M08_DT_SYMBOL_INSPECTION_NO_OVERLAY_WRITE" in symbols,
            "original read-only DT symbol inspection incomplete")
    for prop in ("#address-cells", "#size-cells"):
        require("M08_DT_CELL_HEX=amba|" + prop + "|00000002" in symbols,
                "live AMBA bus is not independently verified as 2-cell address / size")
    # Presence of amba symbol and 2-cell widths supports DT encoding,
    # NOT successful driver bind or PS physical readback.
    # The generated overlay is NEVER authorized for installation here.
    return {
        "kernel_uio_driver": "uio_pdrv_genirq_LOADED",
        "kernel_of_id": "generic-uio",
        "live_dt_symbols": ["amba", "fpga_full", "zynqmp_reset"],
        "board_state": "ORIGINAL_K26_ACTIVE_FANCONTROL_ACTIVE",
    }


def validate_package(folder: Path) -> dict:
    covered = verify_ledger(folder, "99_evidence_sha256.txt")
    require(folder.name.startswith("m08_2b_path_a_linux_package_REVIEW_ONLY_"),
            "expected original first-stage PC package evidence folder")
    for path in (
        "m08-v1-fan-page/m08-v1-fan-page.bit.bin",
        "m08-v1-fan-page/m08-v1-fan-page.dtbo",
        "m08-v1-fan-page/shell.json",
        "05_package_review.json",
        "98_status.txt",
    ):
        require(path in covered, "original package evidence missing: " + path)
    review = json.loads((folder / "05_package_review.json").read_text())
    require(
        review.get("status") == "OFFLINE_PACKAGE_STAGED_NO_BOARD_NO_MMIO_ACCESS"
        and review.get("original_verified_bit_sha256") == FAN_BIT_SHA
        and review.get("bit_bin_sha256") == FAN_BIT_BIN_SHA
        and review.get("bit_bin_bytes") == FAN_BIT_BIN_BYTES
        and review.get("dtbo_sha256") == PRIOR_DTBO_SHA
        and review.get("device_tree_mmio_nodes") == "NONE_INTENTIONALLY"
        and review.get("linux_package_installed") is False
        and review.get("fpga_programmed") is False,
        "first-stage original offline package manifest inconsistent")
    payload = folder / "m08-v1-fan-page" / BIT
    require(payload.stat().st_size == FAN_BIT_BIN_BYTES and sha(payload) == FAN_BIT_BIN_SHA,
            "original bit.bin changed")
    require(json.loads((folder / "m08-v1-fan-page" / "shell.json").read_text()) == SHELL,
            "unexpected PL_FLAT metadata")
    require((folder / "98_status.txt").read_text() == "staging_status=success\n",
            "first-stage original PC package failed")
    return review


def verify_dtc_diagnostics(compile_log: str, decode_stderr: str) -> dict:
    """Never suppress original compiler diagnostics or invent DT runtime proof.

    Decompiling an unapplied DTBO may produce only the *documented*
    unresolved zynqmp_reset phandle warning. Any other warning is fatal.
    """
    require(not compile_log.strip(),
            "dtc compile emitted warnings/errors; review ORIGINAL tool log")
    lines = [line.strip() for line in decode_stderr.splitlines() if line.strip()]
    require(all(re.search(r"Warning \(resets_property\):.*Could not get phandle node", line)
                for line in lines),
            "dtc round-trip has unexpected warning/error (especially reg_format)")
    return {
        "compile_warnings": 0,
        "decode_warnings": len(lines),
        "decode_warning_scope": "UNRESOLVED_SYMBOLIC_RESET_PHANDLE_ONLY" if lines else "NONE",
    }


def validate_dtbo(text: str) -> dict:
    require(text.count('firmware-name = "' + STEM + '.bit.bin";') == 1,
            "compiled DTBO does not reference matching .bit.bin")
    section = text.split("__fixups__", 1)
    require(len(section) == 2, "no genuine Linux overlay symbol fixups")
    for symbol in ("fpga_full", "zynqmp_reset", "amba"):
        require(re.search(r"\b" + symbol + r"\s*=", section[1]) is not None,
                "overlay missing fixup symbol " + symbol)
    require("resets = " in section[0],
            "FPGA region reset list absent")
    # Both the stock-shaped fpga_full and the separate AMBA fragment
    # must explicitly declare the 2/2 widths from the genuine live DT.
    for prop in ("#address-cells = <0x02>;", "#size-cells = <0x02>;"):
        require(section[0].count(prop) == 2,
                "both FPGA/AMBA fragments must explicitly declare 2/2 bus cells")
    require(text.count('"generic-uio"') == 2,
            "exactly two Linux generic-uio bindings required")
    devices = {}
    for label, address, length in REGISTERS:
        pattern = r"\b" + re.escape(label) + r"@" + f"{address:x}" + r"\s*\{(.*?)\};"
        match = re.search(pattern, text, flags=re.S)
        require(match is not None, "missing UIO resource node " + label)
        body = match.group(1)
        require(re.search(r'compatible\s*=\s*"generic-uio";', body) is not None
                and re.search(
                    r'linux,uio-name\s*=\s*"' + re.escape(label) + r'";', body
                ) is not None and "status = \"okay\"" in body,
                "wrong UIO device-name/compatible for " + label)
        raw_reg = re.search(r"\breg\s*=\s*<([^>]+)>;", body)
        require(raw_reg is not None, "missing UIO reg " + label)
        cells = [int(token, 0) for token in raw_reg.group(1).split()]
        require(cells == [0, address, 0, length],
                "physical UIO reg moved or wrong size " + label)
        require("interrupts" not in body and "dma" not in body.lower(),
                "unexpected IRQ/DMA claim for safe page")
        devices[label] = {"base": f"0x{address:08x}", "bytes": length}
    require(len(devices) == 2, "expected exactly two M08 Linux resources")
    return devices


def record_hashes(folder: Path) -> None:
    lines = []
    for item in sorted(folder.rglob("*")):
        if item.is_file() and item.name != "99_evidence_sha256.txt":
            lines.append(f"{sha(item)}  {item.relative_to(folder)}")
    (folder / "99_evidence_sha256.txt").write_text("\n".join(lines) + "\n")


def stage_package(staged: Path, board: Path, outbase: Path) -> Path:
    require(staged.resolve() != board.resolve(), "original board/package folder collision")
    before = validate_package(staged)
    observed = validate_board(board)
    require(outbase.is_dir() and not outbase.is_symlink(), "trusted PC evidence parent missing")
    path = outbase.resolve()
    require(str(path) not in ("/", "/lib/firmware", "/lib", "/boot", "/etc") and
            not str(path).startswith(("/lib/firmware/", "/boot/", "/etc/")),
            "never stage into live kernel/firmware/boot directories")
    require(not (path == staged.resolve() or staged.resolve() in path.parents or
                 path == board.resolve() or board.resolve() in path.parents),
            "never write a new package inside original owner evidence")
    require(shutil.which("dtc") is not None, "PC dtc executable required")
    folder = Path(tempfile.mkdtemp(
        prefix="m08_2b_path_a_uio_overlay_REVIEW_ONLY_", dir=outbase))
    try:
        app = folder / STEM
        app.mkdir()
        source = staged / "m08-v1-fan-page" / BIT
        output = app / f"{STEM}.bit.bin"
        shutil.copyfile(source, output)
        require(sha(output) == FAN_BIT_BIN_SHA and
                output.stat().st_size == FAN_BIT_BIN_BYTES,
                "new staged copy of original converted bitstream differs")
        (app / "shell.json").write_text(json.dumps(SHELL, indent=2) + "\n")
        (folder / "00_inputs.json").write_text(json.dumps({
            "schema": "m08-path-a-uio-candidate-input-v1",
            "original_package_dir": str(staged.resolve()),
            "original_package_ledger_sha256": sha(staged / "99_evidence_sha256.txt"),
            "original_board_evidence_dir": str(board.resolve()),
            "original_board_ledger_sha256": sha(board / "04_evidence_sha256.txt"),
            "verified_bit_bin_sha256": FAN_BIT_BIN_SHA,
            "board": observed,
            "original_package_status": before["status"],
            "deployment_approval": False,
        }, sort_keys=True, indent=2) + "\n")
        dts = folder / f"{STEM}.dts"
        dts.write_text(DTS)
        dtbo = app / f"{STEM}.dtbo"
        with (folder / "01_dtc_compile.log").open("x") as log:
            proc = subprocess.run(
                ["dtc", "-@", "-I", "dts", "-O", "dtb", "-o", str(dtbo), str(dts)],
                cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=False)
        require(proc.returncode == 0, "native DT compilation failed")
        native_compile_log = (folder / "01_dtc_compile.log").read_text()
        result = subprocess.run(
            ["dtc", "-I", "dtb", "-O", "dts", str(dtbo)],
            cwd=folder, capture_output=True, text=True, check=False)
        (folder / "02_dtbo_decompiled.log").write_text(
            result.stdout + "\n-- STDERR --\n" + result.stderr
        )
        require(result.returncode == 0, "native decompilation failed")
        dtc_review = verify_dtc_diagnostics(native_compile_log, result.stderr)
        devices = validate_dtbo(result.stdout)
        review = {
            "schema": "m08-path-a-dual-uio-linux-overlay-v1",
            "status": "OFFLINE_DUAL_UIO_CANDIDATE_NOT_INSTALLED",
            "driver": "uio_pdrv_genirq",
            "compatible": "generic-uio",
            "shell_type": "PL_FLAT",
            "bit_bin_sha256": sha(output),
            "dtbo_sha256": sha(dtbo),
            "identity_and_page": devices,
            "dtc_diagnostics": dtc_review,
            "compiler_reg_format_clean": True,
            "live_kernel_binding_verified": False,
            "active_pl_replaced": False,
            "kernel_resource_probes_verified": False,
            "uio_mmap_verified": False,
            "fan_cooling_during_reconfiguration": "NOT_VERIFIED",
            "physical_ps_axi_64word_readback": False,
        }
        (folder / "03_review.json").write_text(
            json.dumps(review, indent=2, sort_keys=True) + "\n")
        (folder / "98_status.txt").write_text("staging_status=success\n")
    except Exception as e:
        (folder / "98_status.txt").write_text(
            "staging_status=failed\nerror=" + str(e) + "\n")
        record_hashes(folder)
        raise ValueError(f"preserve original failed candidate in {folder}: {e}") from e
    record_hashes(folder)
    return folder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--staged-dir", required=True, type=Path)
    ap.add_argument("--board-evidence-dir", required=True, type=Path)
    ap.add_argument("--evidence-base", required=True, type=Path)
    args = ap.parse_args()
    try:
        folder = stage_package(args.staged_dir, args.board_evidence_dir,
                               args.evidence_base)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as e:
        print("M08_PATH_A_DUAL_UIO_OFFLINE_REJECTED:", e, file=sys.stderr)
        return 2
    print("M08_PATH_A_DUAL_UIO_REVIEW_ONLY_DTBO_CREATED_NOT_INSTALLED")
    print("M08_PATH_A_DUAL_UIO_EVIDENCE_DIR=" + str(folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
