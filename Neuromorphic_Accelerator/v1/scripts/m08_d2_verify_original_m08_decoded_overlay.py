#!/usr/bin/env python3
"""Offline attest the original M08 deployed UIO DTBO's decompiled evidence.

Requires only the THREE original PC-generated text outputs. Never launches
dtc, executes a staging script, accesses devices, changes firmware or writes
files. SHA verifies the DTS against its native receipt before interpreting
the exact two fragments and symbolic overlay fixups.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ORIGINAL_M08_DTBO_SHA = "2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed"
EXPECTED_DTS_SHA = "772c6b0bb299d0bf0665cc79063a198d331dc9543249e5c62f7f0cff18d9aabe"
NAMES = ("00_review.json", "12_m08.dts", "22_m08_dtc_stderr.txt")
EXPECTED_WINDOWS = {"m08-identity": "a0000000", "m08-page": "a0001000"}
CLOCK_AFI_PROPERTIES = ("assigned-clocks", "assigned-clock-rates", "clock-names",
                        "clocks", "xlnx,fclk", "xlnx,afi-fpga", "config-afi")


class EvidenceRejected(ValueError):
    pass


def must(ok: bool, message: str) -> None:
    if not ok:
        raise EvidenceRejected(message)


def read(folder: Path, name: str) -> tuple[str, str]:
    p = folder / name
    must(p.is_file() and not p.is_symlink(), "missing/symlinked original: " + name)
    b = p.read_bytes()
    must(bool(b), "empty original: " + name)
    return b.decode("utf-8"), sha256(b).hexdigest()


def inspect(folder: Path) -> dict:
    must(folder.is_dir() and not folder.is_symlink(), "invalid owner evidence folder")
    bodies, shas = {}, {}
    for name in NAMES:
        bodies[name], shas[name] = read(folder, name)
    review = json.loads(bodies["00_review.json"])
    must(review.get("schema") == "m08-d2-owner-pc-dtbo-decompile-v1"
         and review.get("status") == "ORIGINAL_M08_DTS_COPY_CREATED_STOCK_ABSENT_NO_BOARD"
         and review.get("m08_only") is True
         and review.get("stock_dtbo_compared") is False
         and review.get("originals_unchanged") is True
         and review.get("runtime_clock_reset_hpm0_afi_or_atb_verified") is False
         and review.get("hardware_retry_authorized") is False
         and review.get("original_quarantined_image_reloaded") is False,
         "original M08-only review metadata not accepted")
    data = review.get("files")
    must(isinstance(data, dict) and set(data) == {"m08"},
         "unexpected original DTBO sources")
    record = data["m08"]
    must(record.get("original_sha256") == ORIGINAL_M08_DTBO_SHA
         and record.get("decompiled_sha256") == shas["12_m08.dts"]
         and shas["12_m08.dts"] == EXPECTED_DTS_SHA
         and record.get("original_verified_again_after_dtc") is True
         and record.get("dtc_exit_status") == 0
         and Path(record.get("original_path", "")).name ==
             "m08-v1-fan-page-uio-review.dtbo"
         and Path(record.get("decompiled_file", "")).name == "12_m08.dts",
         "M08 DTBO SHA, original file receipt or native dtc status mismatch")

    dts = bodies["12_m08.dts"]
    must(dts.startswith("/dts-v1/;") and dts.count("fragment@0 {") == 1
         and dts.count("fragment@1 {") == 1
         and dts.count("__overlay__ {") == 2
         and dts.count("__fixups__ {") == 1,
         "original DTS fragment/fixup layout changed")
    must(dts.count("target = <0xffffffff>;") == 2,
         "original targets no longer symbolic fixups")
    for literal in (
        'firmware-name = "m08-v1-fan-page-uio-review.bit.bin";',
        "resets = <0xffffffff 0x74 0xffffffff 0x75 0xffffffff 0x76 0xffffffff 0x77>;",
        'fpga_full = "/fragment@0:target:0";',
        'amba = "/fragment@1:target:0";',
        'zynqmp_reset = "/fragment@0/__overlay__:resets:0\\0/fragment@0/__overlay__:resets:8\\0/fragment@0/__overlay__:resets:16\\0/fragment@0/__overlay__:resets:24";',
    ):
        must(literal in dts, "expected symbolic original DT overlay entry missing: " + literal)
    for name, address in EXPECTED_WINDOWS.items():
        pattern = (
            r"m08-" + re.escape(name.split("m08-", 1)[1]) + r"@" + address
            + r"\s*\{\s*compatible = \"generic-uio\";"
            + r"\s*linux,uio-name = \"" + name + r"\";"
            + r"\s*reg = <0x00 0x" + address + r" 0x00 0x1000>;"
            + r"\s*status = \"okay\";\s*\}")
        must(re.search(pattern, dts) is not None,
             "missing/wrong original generic UIO window: " + name)
    must(dts.count('compatible = "generic-uio";') == 2,
         "unreviewed extra/missing generic UIO")
    # In the ORIGINAL native 961-byte decoded overlay, none of these clock
    # and AFI directives appear. No claim is made about stock/base DT/boot.
    must(not any(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(prop) + r"\s*(?:=|;)",
                           dts) for prop in CLOCK_AFI_PROPERTIES),
         "clock/AFI directives present; requires fresh engineering review")
    stderr = bodies["22_m08_dtc_stderr.txt"]
    stderr_lines = stderr.splitlines()
    must(len(stderr_lines) == 1
         and re.fullmatch(
             r".+/12_m08\.dts: Warning \(resets_property\): "
             r"/fragment@0/__overlay__:resets: "
             r"Could not get phandle node for \(cell 1\)", stderr_lines[0]) is not None,
         "unexpected native dtc warning/error")
    return {
        "schema": "m08-d2-original-deployed-uio-dtbo-offline-attestation-v1",
        "status": "ORIGINAL_M08_DEPLOYED_OVERLAY_VERIFIED_CLOCK_AFI_NOT_DECLARED",
        "input_sha256": shas,
        "original_dtbo_sha256_recorded": ORIGINAL_M08_DTBO_SHA,
        "decoded_dts_sha256_verified": EXPECTED_DTS_SHA,
        "fragments": {
            "fpga_full": "firmware_and_four_symbolic_reset_references",
            "amba": "two_4KiB_generic_UIO_nodes",
        },
        "clock_afi": {
            "any_explicit_clock_or_afi_config_in_this_original_overlay": False,
            "proves_failed_boot_clock_off": False,
            "proves_failed_boot_afi_wrong": False,
            "base_tree_or_firmware_configuration": "UNKNOWN",
        },
        "warning": "ONLY_UNRESOLVED_SYMBOLIC_RESET_PHANDLE_WHILE_DECOMPILING_UNAPPLIED_OVERLAY",
        "stock_dtbo_present": False,
        "physical_runtime_proven": False,
        "hardware_retest_authorized": False,
        "original_quarantined_m08_image_reloaded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.evidence_dir)
    except (EvidenceRejected, UnicodeError, OSError, ValueError) as exc:
        print("M08_D2_ORIGINAL_M08_DTBO_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
