#!/usr/bin/env python3
"""Offline passive .bit candidate auditor. No flashing, FPGA manager or MMIO."""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BIT = "bitstream_candidate/m08_d3_2_passive_fan_UNRELEASED.bit"
REPORT = "bitstream_candidate/61_unreleased_bitstream_readback.txt"
LEDGER = "96_candidate_evidence_sha256.txt"
EVIDENCE = {
    BIT, REPORT, "07_passive_bitgen_vivado.log",
    "08_passive_bitgen_vivado.jou", "65_prebit_pc_review.json",
    "66_pc_unreleased_bitstream_gate.json",
}
FIELDS = {
    "schema": "m08-d3-2-passive-unreleased-bitstream-v1",
    "candidate": "m08-d3a-passive-fan-v1",
    "part": "xck26-sfvc784-2LV-c",
    "ps_to_pl_axi": "DISABLED",
    "identity_slave": "ABSENT",
    "page_slave": "ABSENT",
    "fan_output": "A12_LVCMOS33",
    "bitstream": "CREATED_OFFLINE_UNRELEASED",
    "bit_bin": "NOT_CREATED",
    "dtbo": "NOT_CREATED",
    "boot_image": "NOT_CREATED",
    "board_programmed": "NO",
    "physical_fan_continuity": "NOT_PROVEN",
    "boot_rollback": "NOT_PROVEN",
    "physical_programming_authorized": "NO",
    "hardware_mmio_authorized": "NO",
    "original_quarantined_image_reused": "NO",
}


class Rejected(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Rejected(reason)


def data(run: Path, relative: str, max_bytes=110_000_000) -> bytes:
    f = run / relative
    require(f.is_file() and not f.is_symlink(),
            "missing/symlinked candidate evidence: " + relative)
    for parent in f.relative_to(run).parents:
        if str(parent) != ".":
            require(not (run / parent).is_symlink(),
                    "symlinked candidate evidence directory")
    require(0 < f.stat().st_size < max_bytes,
            "implausible candidate evidence file length: " + relative)
    return f.read_bytes()


def import_parent(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    require(spec is not None and spec.loader is not None,
            "missing parent route source or native auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_gate() -> dict:
    route = import_parent("m08_d3_2_passive_route_gate.py", "bitgen_parent_source")
    try:
        parent = route.source_gate()
    except route.RouteRejected as exc:
        raise Rejected("parent no-AXI route source refused: " + str(exc)) from exc
    tcl = data(ROOT, "scripts/m08_d3_2_passive_bitstream_candidate.tcl", 200_000).decode()
    sh = data(ROOT, "scripts/run_m08_d3_2_passive_bitstream_pc.sh", 200_000).decode()
    active = [s.strip() for s in tcl.splitlines()
              if s.strip() and not s.lstrip().startswith("#")]
    require([s for s in active if s.startswith("write_bitstream")] ==
            ["write_bitstream -file $bit"],
            "exactly one non-overwriting explicit .bit creation required")
    for line in active:
        for forbidden in (
            "launch_runs ", "program_hw_devices", "open_hw",
            "connect_hw_server", "write_cfgmem", "write_hw_platform",
            "write_device_image", "exec ", "source ", "connect_bd_intf_net",
            "set_property PROGRAM.FILE", "create_project",
        ):
            require(not line.startswith(forbidden),
                    "unsafe active bitgen Tcl command: " + forbidden)
    for required in (
        "2025.2", "m08_d3_2_passive_synth_", "bitstream_candidate",
        "m08_d3_2_passive_fan_UNRELEASED.bit",
        "get_property $prop [get_bd_cells ps]",
        "get_bd_intf_pins -quiet $iface",
        "open_run impl_1", "get_property PACKAGE_PIN $fan",
        "get_property IOSTANDARD $fan", "hardware_mmio_authorized=NO",
        "bitstream=CREATED_OFFLINE_UNRELEASED",
        "physical_programming_authorized=NO",
        "M08_D3_2_PASSIVE_BITSTREAM_CANDIDATE_CREATED_OFFLINE_UNRELEASED_NO_BOARD",
    ):
        require(required in tcl, "bitgen Tcl missing safety constraint: " + required)
    for required in (
        "set -euo pipefail", "run_m08_d3_2_passive_route_pc.sh",
        "m08_d3_2_passive_route_report_review.py",
        "m08_d3_2_passive_bitstream_candidate.tcl",
        "m08_d3_2_passive_bitstream_gate.py",
        "96_candidate_evidence_sha256.txt",
    ):
        require(required in sh, "owner PC runner missing safety gate: " + required)
    require(sh.count("vivado -mode batch") == 1,
            "owner bitgen runner must invoke only one new Vivado stage")
    for forbidden in (
        "program_hw_devices", "write_cfgmem", "xmutil ", "/dev/mem",
        "/dev/uio", "sudo ", "ssh ", "scp ", "rm -rf",
    ):
        require(forbidden not in sh, "unsafe owner bitgen runner: " + forbidden)
    return {
        "status": "M08_D3_2_OFFLINE_UNRELEASED_PASSIVE_BITGEN_SOURCE_ACCEPTED",
        "parent": parent["status"],
        "bitgen_tcl_sha256": sha256(tcl.encode()).hexdigest(),
        "runner_sha256": sha256(sh.encode()).hexdigest(),
        "native_candidate_generated": False,
        "physical_programming_authorized": False,
        "protected_hpm0_authorized": False,
        "original_bad_bitstream_quarantined": True,
    }


def check_ledger(run: Path) -> dict:
    raw = data(run, LEDGER, 20_000).decode("ascii")
    lines = raw.splitlines()
    require(len(lines) == len(EVIDENCE), "incorrect candidate SHA receipt count")
    result = {}
    for line in lines:
        matched = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        require(matched is not None, "malformed candidate receipt")
        digest, name = matched.groups()
        require(name in EVIDENCE and name not in result,
                "unexpected or duplicated candidate receipt entry: " + name)
        require(sha256(data(run, name)).hexdigest() == digest,
                "candidate receipt digest mismatch: " + name)
        result[name] = digest
    require(set(result) == EVIDENCE, "candidate ledger is incomplete")
    return result


def native_candidate(run: Path, *, pre_ledger=False, parent=None) -> dict:
    require(run.is_dir() and not run.is_symlink()
            and re.fullmatch(r"m08_d3_2_passive_synth_[A-Za-z0-9]+", run.name)
            and run.parent.name == "M08",
            "invalid isolated new passive bitgen run")
    route = parent if parent is not None else import_parent(
        "m08_d3_2_passive_route_report_review.py", "bitgen_parent_native")
    try:
        reviewed = route.review_run(run)
    except route.ReviewRejected as exc:
        raise Rejected("route semantic/receipt review failed: " + str(exc)) from exc
    require(reviewed["status"] == "PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED"
            and reviewed["physical_programming_authorized"] is False,
            "parent native route gate unexpectedly approved hardware")
    raw_bit = data(run, BIT)
    require(100_000 < len(raw_bit) < 100_000_000,
            "candidate is too small/large to be plausible KV260 bitstream")
    unexpected = []
    for suffix in ("*.bit", "*.bin", "*.bit.bin", "*.dtbo", "*.xsa", "*.pdi"):
        for path in run.rglob(suffix):
            if path.is_symlink() or path.relative_to(run).as_posix() != BIT:
                unexpected.append(str(path.relative_to(run)))
    require(not unexpected, "unexpected extra image: " + ", ".join(unexpected[:4]))
    info = data(run, REPORT, 30_000).decode()
    fields = [line.split("=", 1) for line in info.splitlines()]
    require(all(len(x) == 2 for x in fields) and len(fields) == len(dict(fields)),
            "malformed or duplicated bitgen readback")
    mapped = dict(fields)
    for key, expected in FIELDS.items():
        require(mapped.get(key) == expected,
                "unreleased bitgen status invalid: " + key)
    require(re.fullmatch(r"2025\.2(?:\..+)?", mapped.get("vivado_version", ""))
            and mapped.get("board_part", "").startswith("xilinx.com:kv260_som:part0:")
            and "Complete!" in mapped.get("source_route_status", ""),
            "bitgen version, board or route identity invalid")
    require(mapped.get("bitstream_size_bytes") == str(len(raw_bit)),
            "actual candidate bytes differ from Vivado readback")
    log = data(run, "07_passive_bitgen_vivado.log", 8_000_000).decode()
    require("M08_D3_2_PASSIVE_BITSTREAM_CANDIDATE_CREATED_OFFLINE_UNRELEASED_NO_BOARD" in log,
            "native candidate success marker missing")
    require(not re.search(r"(?m)^(ERROR:|CRITICAL WARNING:)", log),
            "native bitgen log has error/critical warning")
    preliminary = json.loads(data(run, "65_prebit_pc_review.json", 80_000))
    require(preliminary.get("status") ==
            "PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED"
            and preliminary.get("physical_programming_authorized") is False,
            "pre-bitgen evidence illegally approved hardware")
    sha = sha256(raw_bit).hexdigest()
    if not pre_ledger:
        ledger = check_ledger(run)
        require(ledger[BIT] == sha, "candidate SHA receipt differs from binary")
    return {
        "status": ("M08_D3_2_CANDIDATE_PRE_LEDGER_CHECK_NO_BOARD" if pre_ledger
                   else "M08_D3_2_UNRELEASED_PASSIVE_BITSTREAM_SHA_ACCEPTED_NO_BOARD"),
        "bitstream_path": BIT,
        "bitstream_size_bytes": len(raw_bit),
        "bitstream_sha256": sha,
        "both_original_route_ledgers_verified": True,
        "new_candidate_ledger_verified": not pre_ledger,
        "physical_programming_authorized": False,
        "fan_cooling_and_stock_rollback_proven": False,
        "linux_mmio_authorized": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path)
    ap.add_argument("--pre-ledger", action="store_true")
    args = ap.parse_args()
    try:
        require(not args.pre_ledger or args.run_dir is not None,
                "--pre-ledger requires --run-dir")
        result = source_gate()
        if args.run_dir:
            result["native"] = native_candidate(args.run_dir, pre_ledger=args.pre_ledger)
    except (Rejected, ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print("M08_D3_2_OFFLINE_BITSTREAM_GATE_REJECTED_NO_BOARD: " + str(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
