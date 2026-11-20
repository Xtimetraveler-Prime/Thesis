#!/usr/bin/env python3
"""Fail-closed D3.D.2A four-neuron source and genuine-owner-native evidence gate.

PC-only. No JTAG, Vivado build, PS access, DDR or hardware programming.
An unreviewed new bitstream DRC warning profile is NEVER inherited from D3.D.1.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import m08_d3d_neuron_gate as predecessor
import m08_d3c_jtag_bram_gate as d3c
from m08_d3d2a_four_vectors import FIXTURES, format_fixture

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/m08_d3d2a_four_build.tcl"
RUNNER = ROOT / "scripts/run_m08_d3d2a_four_pc.sh"
RTL = ROOT / "rtl/m08/m08_d3d2a_four_lif_axil.v"
POR = ROOT / "rtl/m08_d3c_fabric_por.v"
BIT_REL = "bitstream_candidate/m08_d3d2a_four_lif_jtag_UNRELEASED.bit"
FILES = (
    "00_vivado.log", "01_vivado.jou", "02_vivado_exit.txt",
    "reports/10_fan_a12.xdc", "reports/11_fabric_por.v",
    "reports/12_four_lif_axil.v", "reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt", "reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt", "reports/30_native_result.txt", BIT_REL,
)
SCHEMA = "m08-d3d2a-four-neuron-offline-build-v1"
OLD_BIT = "b071adcec0ba33077cdf70543d5cc9c354f6746bcc8138e8c741c41a3cbb1c8b"


class Reject(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise Reject(message)


def read(path: Path, maximum: int = 12000000) -> bytes:
    require(path.is_file() and not path.is_symlink(), "missing/symlinked " + str(path))
    require(0 < path.stat().st_size <= maximum, "empty/too large " + str(path))
    return path.read_bytes()


def source() -> dict:
    try:
        predecessor.source()
    except predecessor.Reject as exc:
        raise Reject("D3.D.1 baseline source invalid: " + str(exc)) from exc
    builder = read(BUILDER, 200000).decode()
    runner = read(RUNNER, 60000).decode()
    rtl = read(RTL, 50000).decode()
    active = "\n".join(line for line in builder.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
    for token in (
        "m08_d3d2a_four_", "2025.2", "xck26-sfvc784-2LV-c",
        "CONFIG.PSU__USE__M_AXI_GP0 0",
        "CONFIG.PSU__USE__M_AXI_GP1 0",
        "CONFIG.PSU__USE__M_AXI_GP2 0",
        "CONFIG.PSU__TTC0__WAVEOUT__IO EMIO",
        "CONFIG.NUM_SI 1 CONFIG.NUM_MI 2",
        "m08_d3d2a_four_lif_axil lif",
        "m08_d3c_fabric_por fabric_por",
        "0xA0000000", "0xA0001000",
        "m08_d3d2a_four_lif_jtag_UNRELEASED.bit",
        "set_property top $wrapper_top [current_fileset]",
        "if {$wrapper_top ne \"m08_d3d2a_four_lif_jtag_wrapper\"}",
        "validate_bd_design -force",
        "report_timing_summary -file", "report_drc -file",
        "write_bitstream -file $bit",
        "ps/pl_clk0", "fabric_por/aresetn",
        "fabric_por_rtl_sha256", "lif_rtl_sha256", "builder_sha256",
        "FOUR_NEURONS_FOUR_TICKS_SIGNED16_NO_SYNAPSES",
        "12_four_lif_axil.v",
    ):
        require(token in active, "missing expected native-builder boundary: " + token)
    require(builder.count("write_bitstream -file $bit") == 1,
            "native builder must create exactly one bitstream")
    for unsafe in (
        "program_hw_devices", "open_hw_manager", "connect_hw_server",
        "run_hw_axi", "xmutil", "sudo ", "ssh ", "/dev/mem",
        "/dev/uio", "loadapp", "unloadapp", "rm -rf",
    ):
        require(unsafe not in active and unsafe not in runner,
                "offline build contains forbidden hardware operation: " + unsafe)
    for token in (
        "m08_d3d2a_four_gate.py", "m08_d3d2a_four_build.tcl",
        "mktemp -d", "sha256sum -c", "99_evidence_sha256.txt",
        "12_four_lif_axil.v", "m08_d3d2a_four_lif_jtag_UNRELEASED.bit",
    ):
        require(token in runner, "owner native runner missing: " + token)
    for token in (
        "module m08_d3d2a_four_lif_axil", "PROTOCOL AXI4LITE",
        "MAGIC=32'h4D344C46", "VERSION=32'h00020000",
        "membrane[neuron] <= next_voltage",
        "trace_voltage[compute_index] <= next_voltage",
        "spike_mask[neuron][tick] <= fired",
        "run_count <= run_count + 1",
        "cfg_threshold[3] > 0", "total > 64'sd32767",
        "half_trunc", "s_axi_rresp <= SLVERR",
        "if (busy)", "if (tick == 2'd3)",
    ):
        require(token in rtl, "four-neuron compute RTL missing: " + token)
    require("m08_d3d_lif_axil.v" not in active and
            "m08_d3d_lif_jtag_UNRELEASED.bit" not in active,
            "builder must not regenerate or re-label accepted one-neuron image")
    require(len(FIXTURES) == 2 and len({f.name for f in FIXTURES}) == 2,
            "M02 four-neuron fixtures incomplete")
    for f in FIXTURES:
        require(len(format_fixture(f).split("|")) == 55,
                "invalid M02 four-neuron fixture wire schema")
    return {
        "status": "M08_D3D2A_FOUR_NEURON_SOURCE_ACCEPTED_PC_ONLY_NO_NATIVE",
        "hardware_executed": False,
        "synaptic_routing_proven": False,
        "builder_sha256": sha256(builder.encode()).hexdigest(),
        "lif_rtl_sha256": sha256(rtl.encode()).hexdigest(),
    }


def inspect_new_drc(report: str) -> dict:
    # No automatic carry-forward of vendor warnings from the different RTL/BD.
    # The first original four-neuron native report MUST be reviewed before an
    # exact, source-anchored vendor allowlist can be proposed.
    counts = re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$", report)
    require(len(counts) == 1, "new native DRC missing unambiguous count")
    require(int(counts[0]) == 0,
            "NEW_D3D2A_DRC_REVIEW_REQUIRED: new original vendor/debug "
            f"warning count={counts[0]}; do NOT waive/rebuild/reprogram")
    require(not re.search(r"(?m)^[A-Z]+-\d+#\d+\s+(?:Warning|Critical Warning|Error)",
                          report),
            "new native DRC has detail despite zero summary")
    require(not re.search(r"(?m)^\|\s*[A-Z]+-\d+\s*\|", report),
            "new native DRC has summary rules despite zero count")
    return {"drc_checks": 0, "drc_review_status": "ZERO_NEW_FINDINGS"}


def native(folder: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink() and
            re.fullmatch(r"m08_d3d2a_four_[A-Za-z0-9]+", folder.name) is not None
            and folder.parent.name == "M08",
            "not a dedicated new four-neuron owner native run directory")
    receipt = read(folder/"99_evidence_sha256.txt", 12000).decode("ascii").splitlines()
    require(len(receipt) == len(FILES), "wrong original native SHA row count")
    for name, line in zip(FILES, receipt):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        require(match is not None and match.group(2) == name,
                "wrong native SHA row/order: " + name)
        path = folder/name
        require(not path.parent.is_symlink(), "symlinked native evidence parent")
        data = read(path, 100000000 if name == BIT_REL else 12000000)
        require(sha256(data).hexdigest() == match.group(1),
                "original owner native evidence SHA mismatch: " + name)
    require(read(folder/"02_vivado_exit.txt", 80).decode().strip() ==
            "vivado_build_exit=0", "new native Vivado failed")
    rows = [line.split("=", 1) for line in
            read(folder/"reports/30_native_result.txt", 20000).decode().splitlines()]
    require(all(len(row) == 2 for row in rows) and len(dict(rows)) == len(rows),
            "invalid new four-neuron native result receipt")
    values = dict(rows)
    for k, v in {
        "schema": SCHEMA,
        "wrapper_top": "m08_d3d2a_four_lif_jtag_wrapper",
        "part": "xck26-sfvc784-2LV-c",
        "bram_map_base": "0xA0000000",
        "lif_base": "0xA0001000",
        "ps_to_pl_hpm": "DISABLED",
        "ps_clock_dependency": "YES",
        "reset_mode": "FABRIC_POR_256_CYCLES",
        "fan_route": "TTC0_WAVEOUT2_TO_A12",
        "bram_depth_words": "1024",
        "bram_width_bits": "32",
        "neural_mode": "FOUR_NEURONS_FOUR_TICKS_SIGNED16_NO_SYNAPSES",
        "hardware_bitstream_programmed": "NO",
        "hardware_neural_execution_proven": "NO",
    }.items():
        require(values.get(k) == v, "new native metadata mismatch: " + k)
    for k, src in (("builder_sha256",BUILDER),
                   ("fabric_por_rtl_sha256",POR),("lif_rtl_sha256",RTL)):
        require(values.get(k) == sha256(read(src,200000)).hexdigest(),
                "new RTL/builder source provenance mismatch: " + k)
    require(read(folder/"reports/11_fabric_por.v",20000) == read(POR,20000) and
            read(folder/"reports/12_four_lif_axil.v",50000) == read(RTL,50000),
            "native embedded RTL not identical to reviewed source")
    require(values.get("vivado_version", "").startswith("2025.2") and
            values.get("board_part", "").startswith("xilinx.com:kv260_som:part0:"),
            "wrong native Vivado or board preset")
    bit = read(folder/BIT_REL,100000000)
    digest = sha256(bit).hexdigest()
    require(len(bit) > 100000 and values.get("bitstream_size_bytes") == str(len(bit)),
            "new four-neuron bitstream missing/unexpected size")
    require(digest not in (OLD_BIT, d3c.OLD_FAILED,
                           d3c.PREV_PASSIVE, predecessor.R2_BIT_SHA),
            "reused prior image, not real new four-neuron bitstream")
    log = read(folder/"00_vivado.log").decode(errors="replace")
    require("M08_D3D2A_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d2a_four_lif_jtag_wrapper" in log and
            "M08_D3D2A_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in log,
            "new native top/build success unproven")
    require(not any(re.match(r"^(ERROR:|CRITICAL WARNING:)", x)
                    for x in log.splitlines()),
            "genuine new Vivado build has error/critical warning")
    drc = inspect_new_drc(
        read(folder/"reports/20_route_drc.rpt",3000000).decode(errors="replace"))
    try:
        timing = d3c.inspect_timing(
            read(folder/"reports/21_route_timing.rpt",3000000).decode(errors="replace"))
    except d3c.Reject as exc:
        raise Reject("new native timing rejected: " + str(exc)) from exc
    return {
        "status": "M08_D3D2A_NATIVE_FOUR_NEURON_OFFLINE_ACCEPTED_NO_BOARD",
        "candidate_sha256": digest,
        "candidate_path": str((folder/BIT_REL).resolve()),
        "candidate_bytes": len(bit),
        "hardware_programmed": False,
        "neural_execution_proven": False,
        **drc, **timing,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    choices = p.add_mutually_exclusive_group(required=True)
    choices.add_argument("--source-only", action="store_true")
    choices.add_argument("--run-dir", type=Path)
    args = p.parse_args()
    try:
        result = source()
        if args.run_dir is not None:
            result["native"] = native(args.run_dir)
    except (Reject, predecessor.Reject, d3c.Reject, OSError, ValueError,
            UnicodeError, KeyError) as exc:
        print("M08_D3D2A_FOUR_PC_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
