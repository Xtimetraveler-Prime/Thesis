#!/usr/bin/env python3
"""Read-only attestation for REAL Vivado 2025.2 standalone 32:256 width-IP output.

A generated AMD converter is not a simulated HLS-to-SmartConnect connection.
The wrapper's --pre-finalize mode runs inside the Vivado owner script before
the shell EXIT trap writes result/SHA manifests. Independent final audit must
also check that the original evidence is immutable after the runner exits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT_PREFIX = "m06_g3_real_amd_dwc_"
IPS = {
    "m06_g3_read_dwc": "READ_ONLY",
    "m06_g3_write_dwc": "WRITE_ONLY",
}
REQUIRED = {
    "CONFIG.PROTOCOL": "AXI4",
    "CONFIG.ADDR_WIDTH": "32",
    "CONFIG.SI_DATA_WIDTH": "32",
    "CONFIG.MI_DATA_WIDTH": "256",
    "CONFIG.SI_ID_WIDTH": "1",
    "CONFIG.FIFO_MODE": "0",
}
SOURCE_NAMES = ("scripts/m06_g3_generate_amd_dwc.tcl",
                "scripts/m06_g3_xci_path.tcl",
                "scripts/run_m06_g3_amd_dwc_ip.sh")


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as data:
        for block in iter(lambda: data.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _sha_manifest(src: str) -> dict[str, str]:
    items: dict[str, str] = {}
    for line in src.strip().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (\S+)", line)
        if not match or match[2] in items:
            raise ValueError("invalid original G3 script SHA manifest")
        items[match[2]] = match[1]
    return items


def audit(folder: Path, *, pre_finalize: bool = False) -> dict:
    folder = folder.resolve(strict=True)
    if not folder.is_dir() or not folder.name.startswith(ROOT_PREFIX):
        raise ValueError("expected distinct REAL original AMD Vivado width-IP evidence directory")
    version = (folder / "vivado_version.txt").read_text()
    if "2025.2" not in version:
        raise ValueError("not genuine Vivado 2025.2 evidence")
    log = (folder / "01_vivado_amd_dwc.log").read_text(errors="replace")
    if "M06_G3_REAL_AMD_DWC_IP_GENERATED_NOT_CONNECTED" not in log:
        raise ValueError("original Vivado IP generation PASS marker missing")
    if re.search(r"(?m)^(ERROR:|FATAL:)|\\bCRITICAL WARNING\\b", log):
        raise ValueError("Vivado generation contains an error or critical warning")
    readback: dict[str, str] = {}
    for line in (folder / "02_amd_dwc_configuration.tsv").read_text().splitlines():
        values = line.split("\t")
        if len(values) != 2 or values[0] in readback:
            raise ValueError("malformed/duplicated original IP parameter readback")
        readback[values[0]] = values[1]
    if readback.get("status") != "ORIGINAL_AMD_IP_GENERATED_NOT_CONNECTED" or (
        "2025.2" not in readback.get("tool_version", "") or
        readback.get("part") != "xck26-sfvc784-2LV-c" or
        readback.get("ip_count") != "2" or
        readback.get("original_smartconnect_connected") != "FALSE" or
        readback.get("generated_hls_connected") != "FALSE" or
        readback.get("physical_DDR") != "NOT_ACCESSED" or
        readback.get("m06_complete") != "FALSE"):
        raise ValueError("wrong generation status, target, or false integration claim")
    for ip, role in IPS.items():
        if readback.get(ip + ".CONFIG.READ_WRITE_MODE", "").upper() != role:
            raise ValueError("wrong original AMD converter role: " + ip)
        for key, value in REQUIRED.items():
            if readback.get(ip + "." + key, "").upper() != value.upper():
                raise ValueError("original AMD parameter mismatch: " + ip + " " + key)
    project = folder / "new_scratch_project"
    if not project.is_dir():
        raise ValueError("fresh IP project evidence missing")
    generated = sorted(project.rglob("*.xci"))
    if len(generated) != 2 or {p.stem for p in generated} != set(IPS):
        raise ValueError("expected exactly two actual AMD converter .xci products")
    for path in generated:
        if not path.resolve().is_relative_to(folder) or not path.is_file():
            raise ValueError("generated IP escaped fresh owner evidence directory")
    # This exact fresh-project XCI layout is what the vendor Tcl now uses
    # instead of the empty get_files -of_objects $ip query. No broad
    # search can substitute an old or original D3 source customization.
    for ip in IPS:
        required_xci = (project / "m06_g3_amd_dwc.srcs" / "sources_1" /
                        "ip" / ip / (ip + ".xci")).resolve()
        if required_xci not in generated or not required_xci.is_file():
            raise ValueError("exact fresh-project AMD XCI path missing: " + ip)
        if readback.get(ip + ".xci_source_path") != str(required_xci):
            raise ValueError("AMD XCI path readback differs from original generated file: " + ip)
    scripts = _sha_manifest((folder / "source_before_sha256.txt").read_text())
    if set(scripts) != set(SOURCE_NAMES):
        raise ValueError("G3 exact generator source provenance missing")

    if not pre_finalize:
        if (folder / "result.txt").read_text().strip() != "exit_status=0":
            raise ValueError("original Vivado width-IP runner returned failure")
        if (folder / "source_before_sha256.txt").read_bytes() != (
            folder / "source_after_sha256.txt").read_bytes():
            raise ValueError("G3 generator mutated during owner-run")
        paths = (folder / "03_real_amd_dwc_xci_paths.txt").read_text().splitlines()
        if paths != [str(p) for p in generated]:
            raise ValueError("untrusted original XCI path inventory")
        attest = _sha_manifest((folder / "04_real_amd_dwc_xci_sha256.txt").read_text())
        if attest != {str(p): _hash(p) for p in generated}:
            raise ValueError("original AMD converter XCI digests altered")
        if (folder / "scope.txt").read_text().strip() != (
            "genuine_vendor_converter_status=GENERATED_ONLY"):
            raise ValueError("false converter integration scope/status")

    return {
        "schema": "m06-g3-real-amd-dual-dwc-generated-only-v1",
        "status": "GENUINE_AMD_2025_2_WIDTH_IP_GENERATED_NOT_INTEGRATED",
        "pre_finalize_audit": pre_finalize,
        "source_commit": (folder / "commit.txt").read_text().strip(),
        "evidence_folder": str(folder),
        "ip_sha256": {p.name: _hash(p) for p in generated},
        "ip_roles": IPS,
        "source_digests": scripts,
        "widths": {"hls_si": 32, "vendor_mi": 256},
        "address_width": 32,
        "hls_generated_rtl_bound": False,
        "original_amd_smartconnect_bound": False,
        "actual_amd_width_ip_xsim": False,
        "cross_master_coherency": "NOT_TESTED",
        "physical_board_or_DDR": "NOT_ACCESSED",
        "m06_complete": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--pre-finalize", action="store_true")
    args = ap.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("output must be a new path in an existing folder")
        report = audit(args.evidence, pre_finalize=args.pre_finalize)
        with args.output.open("x", encoding="utf8") as fp:
            json.dump(report, fp, indent=2, sort_keys=True)
            fp.write("\n")
    except (OSError, ValueError, KeyError) as e:
        print("M06 G3 AMD real converter generation evidence REJECTED: " + str(e),
              file=sys.stderr)
        return 2
    print("M06 G3 original AMD dual AXI 32:256 converter output VERIFY ONLY; HLS/SmartConnect link, XSim and DDR NOT RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
