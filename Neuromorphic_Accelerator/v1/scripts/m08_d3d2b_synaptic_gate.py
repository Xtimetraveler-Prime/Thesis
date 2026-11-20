#!/usr/bin/env python3
"""D3.D.2B new recurrent-synapse four-neuron source and native Vivado gate.

PC only. Original D3.D.2A physical proof remains immutable. A future, DIFFERENT
routed bitstream is not owner-accepted until exact new DRC warnings, source,
timing and original evidence are reviewed. No board operations are permitted.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import m08_d3d2a_four_gate as predecessor
import m08_d3c_jtag_bram_gate as d3c
from m08_d3d2b_synaptic_vectors import FIXTURES, format_fixture, FIELD_COUNT

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/m08/m08_d3d2b_synaptic_lif_axil.v"
BUILDER = ROOT / "scripts/m08_d3d2b_synaptic_build.tcl"
RUNNER = ROOT / "scripts/run_m08_d3d2b_synaptic_pc.sh"
POR = ROOT / "rtl/m08_d3c_fabric_por.v"
BIT_REL = "bitstream_candidate/m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit"
SCHEMA = "m08-d3d2b-synaptic-routing-offline-build-v1"
FILES = (
    "00_vivado.log", "01_vivado.jou", "02_vivado_exit.txt",
    "reports/10_fan_a12.xdc", "reports/11_fabric_por.v",
    "reports/12_synaptic_lif_axil.v", "reports/20_route_drc.rpt",
    "reports/21_route_timing.rpt", "reports/22_route_utilization.rpt",
    "reports/23_route_clocks.rpt", "reports/30_native_result.txt", BIT_REL,
)


class Reject(ValueError):
    pass


def check(value: bool, reason: str) -> None:
    if not value:
        raise Reject(reason)


def read(path: Path, maximum: int=12000000) -> bytes:
    check(path.is_file() and not path.is_symlink(),
          "missing/symlinked native evidence " + str(path))
    check(0 < path.stat().st_size <= maximum, "empty/oversized " + str(path))
    return path.read_bytes()


def source() -> dict:
    try:
        predecessor.source()
    except (predecessor.Reject, ValueError) as exc:
        raise Reject("D3.D.2A accepted baseline source failed: "+str(exc)) from exc
    rtl = read(RTL,60000).decode()
    builder = read(BUILDER,120000).decode()
    runner = read(RUNNER,15000).decode()
    active = "\n".join(
        ln for ln in builder.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#"))
    for key in (
        "module m08_d3d2b_synaptic_lif_axil",
        "MAGIC=32'h4D34534E", "VERSION=32'h00030000",
        "edge_pre [0:7]", "edge_post [0:7]", "edge_weight [0:7]",
        "edge_delay [0:7]", "cfg_edge_count <= 4'd8",
        "edge_delay[validate_idx] == 2'd0",
        "spike_mask[edge_pre[route_idx]][tick - edge_delay[route_idx]]",
        "synaptic_sum = synaptic_sum +",
        "trace_syn_current[compute_index] <= synaptic_sum[31:0]",
        "trace_voltage[compute_index] <= next_voltage",
        "spike_mask[neuron][tick] <= fired",
        "total > 64'sd32767", "run_count <= run_count + 1",
        "if (busy)", "if (!done) s_axi_rresp <= SLVERR",
    ):
        check(key in rtl, "missing routed neural hardware semantic: "+key)
    for key in (
        "m08_d3d2b_synaptic_lif_axil lif",
        "m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit",
        "m08_d3c_fabric_por fabric_por",
        "CONFIG.NUM_SI 1 CONFIG.NUM_MI 2",
        "CONFIG.PSU__USE__M_AXI_GP0 0",
        "CONFIG.PSU__USE__M_AXI_GP1 0",
        "CONFIG.PSU__USE__M_AXI_GP2 0",
        "CONFIG.PSU__TTC0__WAVEOUT__IO EMIO",
        "ps/pl_clk0", "fabric_por/aresetn", "0xA0000000",
        "0xA0001000", "12_synaptic_lif_axil.v",
        "if {$wrapper_top ne \"m08_d3d2b_synaptic_lif_jtag_wrapper\"}",
        "validate_bd_design -force", "report_timing_summary -file",
        "report_drc -file", "write_bitstream -file $bit",
        "lif_rtl_sha256", "builder_sha256", "2025.2",
    ):
        check(key in active, "builder cannot meet D3.D.2B native boundary: "+key)
    for forbidden in (
        "program_hw_devices", "open_hw_manager", "connect_hw_server",
        "run_hw_axi", "xmutil", "sudo ", "ssh ", "/dev/mem",
        "/dev/uio", "loadapp", "unloadapp", "rm -rf",
    ):
        check(forbidden not in active and forbidden not in runner,
              "new owner PC-only build includes hardware operation "+forbidden)
    for key in (
        "m08_d3d2b_synaptic_gate.py",
        "m08_d3d2b_synaptic_build.tcl",
        "m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit",
        "mktemp -d", "sha256sum -c",
    ):
        check(key in runner, "new owner PC runner missing "+key)
    check(len(FIXTURES) == 2 and
          len({f.name for f in FIXTURES}) == 2,
          "independent M02 routed fixtures missing")
    for fixture in FIXTURES:
        check(len(format_fixture(fixture).split("|")) == FIELD_COUNT,
              "invalid M02 routed oracle dimensions")
    return {
        "status": "M08_D3D2B_ROUTED_SYNAPSES_SOURCE_ACCEPTED_PC_ONLY",
        "hardware_executed": False,
        "recurrent_synapse_physical_verified": False,
        "builder_sha256": sha256(builder.encode()).hexdigest(),
        "rtl_sha256": sha256(rtl.encode()).hexdigest(),
    }


def inspect_new_drc(report: str) -> dict:
    # New native source changes ROM/logic/routing; a prior debug-hub vendor
    # waiver MUST NOT be automatically inherited. First report needs review.
    counts = re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$", report)
    check(len(counts) == 1, "new route DRC missing/ambiguous finding count")
    if counts[0] != "0":
        raise Reject(
            "D3D2B_NEW_DRC_REVIEW_REQUIRED: first new four-neuron synaptic "
            f"candidate reported {counts[0]} findings; preserve original "
            "report, do not reprogram or silently waive")
    check(not re.search(r"(?m)^\|\s*[A-Z]+-\d+\s*\|", report) and
          not re.search(
              r"(?m)^[A-Z]+-\d+#\d+\s+(?:Warning|Critical Warning|Error)",
              report),
          "zero DRC summary contradicts nonzero warning rows")
    return {"drc_checks": 0, "drc_review_status": "ZERO_UNREVIEWED_FINDINGS"}


def native(folder: Path) -> dict:
    check(folder.is_dir() and not folder.is_symlink() and
          re.fullmatch(r"m08_d3d2b_synaptic_[A-Za-z0-9]+", folder.name) is not None
          and folder.parent.name == "M08",
          "not an original isolated D3.D.2B owner native run")
    receipt = read(folder/"99_evidence_sha256.txt",12000).decode().splitlines()
    check(len(receipt) == len(FILES), "expected exactly twelve original SHA rows")
    for name, line in zip(FILES,receipt):
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_./-]+)",line)
        check(match is not None and match.group(2) == name,
              "original native evidence SHA filename/order drift: "+name)
        obj = folder/name
        check(not obj.parent.is_symlink(), "symlinked native evidence parent")
        datum=read(obj,100000000 if name == BIT_REL else 12000000)
        check(sha256(datum).hexdigest()==match.group(1),
              "original native evidence SHA mismatch: "+name)
    check(read(folder/"02_vivado_exit.txt",80).decode().strip() ==
          "vivado_build_exit=0","native Vivado build exit nonzero")
    header = read(folder/"reports/30_native_result.txt",20000).decode().splitlines()
    parts = [line.split("=",1) for line in header]
    check(all(len(x)==2 for x in parts) and len(dict(parts))==len(parts),
          "native result metadata malformed")
    data=dict(parts)
    for key,value in {
        "schema":SCHEMA,
        "wrapper_top":"m08_d3d2b_synaptic_lif_jtag_wrapper",
        "neural_mode":"FOUR_NEURON_RECURRENT_POSITIVE_DELAY_SIGNED16",
        "part":"xck26-sfvc784-2LV-c",
        "bram_map_base":"0xA0000000",
        "lif_base":"0xA0001000",
        "ps_to_pl_hpm":"DISABLED",
        "bram_depth_words":"1024", "bram_width_bits":"32",
        "reset_mode":"FABRIC_POR_256_CYCLES",
        "ps_clock_dependency":"YES",
        "hardware_bitstream_programmed":"NO",
        "hardware_neural_execution_proven":"NO",
    }.items():
        check(data.get(key)==value,"native metadata mismatch: "+key)
    for key,obj in (
        ("builder_sha256",BUILDER),("lif_rtl_sha256",RTL),
        ("fabric_por_rtl_sha256",POR),
    ):
        check(data.get(key)==sha256(read(obj,120000)).hexdigest(),
              "builder/source native SHA not equal reviewed source: "+key)
    check(read(folder/"reports/11_fabric_por.v",25000)==read(POR,25000) and
          read(folder/"reports/12_synaptic_lif_axil.v",60000)==read(RTL,60000),
          "original native embedded RTL changed")
    check(data.get("vivado_version","").startswith("2025.2") and
          data.get("board_part","").startswith("xilinx.com:kv260_som:part0:"),
          "wrong native vendor tool/board")
    bit=read(folder/BIT_REL,100000000)
    digest=sha256(bit).hexdigest()
    check(len(bit)>100000 and data.get("bitstream_size_bytes")==str(len(bit)),
          "invalid new synapse image")
    check(digest not in (
        predecessor.ORIGINAL_OWNER_BIT_SHA, predecessor.OLD_BIT,
        d3c.OLD_FAILED, d3c.PREV_PASSIVE),
        "reused old standalone neuron image, not new synaptic FPGA engine")
    log=read(folder/"00_vivado.log").decode(errors="replace")
    check("M08_D3D2B_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d2b_synaptic_lif_jtag_wrapper" in log and
          "M08_D3D2B_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED" in log,
          "new native Vivado top/build acceptance marker missing")
    check(not any(re.match(r"^(ERROR:|CRITICAL WARNING:)",ln) for ln in log.splitlines()),
          "native Vivado build contains error/critical warning")
    drc=inspect_new_drc(read(
        folder/"reports/20_route_drc.rpt",3000000).decode(errors="replace"))
    try:
        timing=d3c.inspect_timing(read(
            folder/"reports/21_route_timing.rpt",3000000).decode(errors="replace"))
    except d3c.Reject as e:
        raise Reject("new native timing rejected: "+str(e)) from e
    return {
        "status":"M08_D3D2B_NATIVE_ROUTED_SYNAPSE_CANDIDATE_ACCEPTED_NO_BOARD",
        "candidate_path":str((folder/BIT_REL).resolve()),
        "candidate_sha256":digest,
        "candidate_bytes":len(bit),
        "hardware_programmed":False,"synaptic_routing_physical_verified":False,
        **drc,**timing,
    }


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    a=p.add_mutually_exclusive_group(required=True)
    a.add_argument("--source-only",action="store_true")
    a.add_argument("--run-dir",type=Path)
    args=p.parse_args()
    try:
        result=source()
        if args.run_dir is not None:
            result["native"]=native(args.run_dir)
    except (Reject,predecessor.Reject,d3c.Reject,ValueError,OSError,
            UnicodeError,KeyError) as e:
        print("M08_D3D2B_ROUTING_PC_REJECTED: "+str(e),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
