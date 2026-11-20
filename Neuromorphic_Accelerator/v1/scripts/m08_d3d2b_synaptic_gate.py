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


# Pinned owner-original genuine Vivado 2025.2 routed candidate, 2026-11-20.
# These constants come from the FIRST immutable original native run, not a
# reimplementation. No other image, source or warning profile is released.
ORIGINAL_OWNER_NATIVE_DIR = "m08_d3d2b_synaptic_DakjdpCO"
ORIGINAL_OWNER_BIT_SHA = "dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14"
ORIGINAL_OWNER_BIT_BYTES = 7797847
OWNER_ORIGINAL_RTL_SHA = "2894f33a1c0054a0cf0231e1c4970e5eaea377bbe7524e4c57717c033b5ad88b"
OWNER_ORIGINAL_BUILDER_SHA = "82ba3b226e16ac579cfc2527216f8acb02f9b13d3f42c5574344fcc9ce49e1a8"
REVIEWED_NEW_JTAG_INSTANCE = "m08_d3d2b_synaptic_lif_jtag_i"
REVIEWED_RTSTAT_FIRST15 = tuple(
    item.replace("m08_d3d_lif_jtag_i", REVIEWED_NEW_JTAG_INSTANCE)
    for item in d3c.D3D_RTSTAT10_REVIEWED_FIRST15
)
REVIEWED_OWNER_DRC_PATH = (
    "/home/dna/Thesis_Evidence/M08/" + ORIGINAL_OWNER_NATIVE_DIR +
    "/reports/20_route_drc.rpt"
)
REVIEWED_DEBUG_PREFIX = (
    "dbg_hub/inst/BSCANID.u_xsdbm_id/SWITCH_N_EXT_BSCAN."
)


def inspect_new_drc(report: str) -> dict:
    """Precisely bound 7 owner-reviewed vendor/debug warning details.

    This is NOT a blanket waiver for warning classes or DRC count. Check
    owner-original native provenance, exact severity/count/description, all
    seven detailed instances/pins, and the 15 RTSTAT paths actually printed.
    Vivado reported 39 unroutable nets / 37 listed but printed ONLY 15; the
    remaining paths are not asserted as reviewed.
    """
    from collections import Counter

    review = "D3D2B_NEW_DRC_REVIEW_REQUIRED: "
    found = re.findall(r"(?m)^\s*Checks found:\s*(\d+)\s*$", report)
    check(len(found) == 1, "new route DRC missing/ambiguous finding count")
    if found[0] == "0":
        check(not re.search(r"(?m)^\|\s*[A-Z]+-\d+\s*\|", report)
              and not re.search(
                  r"(?m)^[A-Z]+-\d+#\d+\s+(?:Warning|Critical Warning|Error)",
                  report),
              "zero DRC summary contradicts nonzero warning rows")
        return {"drc_checks": 0, "drc_review_status": "ZERO_UNREVIEWED_FINDINGS"}
    check(found[0] == "7", review + "wrong total DRC finding count")
    for fragment in (
        "Vivado v.2025.2 (lin64)",
        "Date         : Fri Nov 20 00:49:59 2026",
        "Command      : report_drc -file " + REVIEWED_OWNER_DRC_PATH,
        "Design       : m08_d3d2b_synaptic_lif_jtag_wrapper",
        "Device       : xck26-sfvc784-2LV-c",
        "Design State : Fully Routed",
    ):
        check(fragment in report, review + "original routed report provenance drift")
    rows = re.findall(
        r"(?m)^\|\s*([A-Z]+-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*$",
        report)
    check(len(rows) == 4 and len({row[0] for row in rows}) == 4,
          review + "warning summary row count/uniqueness drift")
    parsed = {code: (int(qty), desc.strip()) for code, severity, desc, qty in rows
              if severity.strip() == "Warning"}
    check(parsed == d3c.VENDOR_DRC_PROFILE and
          sum(int(row[3]) for row in rows) == 7,
          review + "warning rule/severity/count/description drift")
    details = list(re.finditer(
        r"(?m)^([A-Z]+-\d+)#(\d+)\s+(Warning|Critical Warning|Error)\s*$",
        report))
    check(len(details) == 7, review + "seven original details not all present")
    per_rule, seen = Counter(), set()
    for index, match in enumerate(details):
        code, ordinal, severity = match.group(1), int(match.group(2)), match.group(3)
        check(severity == "Warning" and code in parsed and
              (code, ordinal) not in seen,
              review + "unknown/critical/duplicate DRC detail")
        seen.add((code, ordinal))
        per_rule[code] += 1
        end = details[index + 1].start() if index + 1 < len(details) else len(report)
        body = report[match.end():end]
        check(body.count("Related violations: <none>") == 1 and
              d3c.VENDOR_DRC_PROFILE[code][1] in body,
              review + "vendor warning body/related violations changed")
        if code == "PDCN-1569":
            pins = {
                1: ("'A1'", "bscan_switch/temp_curid[31]_i_1", "I0"),
                2: ("'A3'", "bscan_switch/temp_curid[31]_i_1", "I1"),
                3: ("'A4'", "id_state[0]_i_1", "I0"),
            }
            check(ordinal in pins, review + "unreviewed LUT warning ordinal")
            physical_pin, suffix, endpoint = pins[ordinal]
            complete_cell = REVIEWED_DEBUG_PREFIX + suffix
            # The owner-original #3 warning uses no bscan_switch subtree
            # and prints "notincluded" (no space). Match that exact report;
            # do not widen the accepted warning hierarchy or message.
            equation_term = ("is notincluded in the LUT equation" if ordinal == 3
                             else "is not included in the LUT equation")
            fragment = (f"Used physical LUT pin {physical_pin} of cell "
                        f"{complete_cell} (pin {complete_cell}/{endpoint}) "
                        f"{equation_term}")
            check(fragment in body and body.count("of cell ") == 1 and
                  body.count("(pin ") == 1,
                  review + "LUT advisory is not the exact XSDB debug cell/pin")
        elif code in ("REQP-1857", "REQP-1858"):
            names = {
                ("REQP-1857", 1): "rx_fifo_i",
                ("REQP-1858", 1): "rd_cmd_fifo_i",
                ("REQP-1858", 2): "wr_cmd_fifo_i",
            }
            fifo = names.get((code, ordinal))
            prefix = ("BRAM (" + REVIEWED_NEW_JTAG_INSTANCE +
                      "/jtag_axi/inst/jtag_axi_engine_u/")
            check(fifo is not None and
                  body.count("BRAM (") == 1 and
                  body.count(prefix + fifo + "/") == 1 and
                  "SDP mode with WRITE_FIRST write-mode" in body and
                  "address collisions" in body,
                  review + "non-JTAG or changed vendor command FIFO advisory")
        elif code == "RTSTAT-10":
            check(ordinal == 1 and re.search(
                r"(?m)^\s*39 net\(s\) have no routable loads\.", body) is not None
                and "(the first 15 of 37 listed)" in body,
                review + "RTSTAT count/sample size changed")
            m = re.search(
                r"problem bus\(es\) and/or net\(s\) are (.*?)\s*"
                r"\(the first 15 of 37 listed\)", body, re.S)
            check(m is not None, review + "RTSTAT sample missing")
            paths = tuple(x.strip() for x in m.group(1).split(",") if x.strip())
            check(paths == REVIEWED_RTSTAT_FIRST15,
                  review + "RTSTAT sample includes unreviewed routing path")
    for code, (count, _) in d3c.VENDOR_DRC_PROFILE.items():
        check(per_rule[code] == count and
              {num for rule, num in seen if rule == code} ==
              set(range(1, count + 1)),
              review + "missing/renumbered vendor warning")
    return {
        "drc_checks": 7,
        "vendor_drc_warnings": 7,
        "drc_review_status": "EXACT_OWNER_D3D2B_VENDOR_DEBUG_SEVEN_FIRST15_RTSTAT",
        "rtstat_total_unroutable": 39,
        "rtstat_listed_count": 37,
        "rtstat_sampled_paths": 15,
    }


def native(folder: Path) -> dict:
    check(folder.is_dir() and not folder.is_symlink() and
          folder.name == ORIGINAL_OWNER_NATIVE_DIR and
          folder.parent.name == "M08",
          "not the immutable owner-original D3.D.2B native run")
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
    check(data.get("builder_sha256") == OWNER_ORIGINAL_BUILDER_SHA and
          data.get("lif_rtl_sha256") == OWNER_ORIGINAL_RTL_SHA,
          "original owner Vivado builder/RTL provenance not the routed candidate")
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
    check(len(bit) == ORIGINAL_OWNER_BIT_BYTES and
          digest == ORIGINAL_OWNER_BIT_SHA,
          "bitstream digest/bytes differ from reviewed original owner candidate")
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
    check(drc["drc_checks"] == 7,
          "native DRC profile not the exact seven owner-reviewed warnings")
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
