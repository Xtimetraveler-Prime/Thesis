#!/usr/bin/env python3
"""Read-only original physical D3.D.2B recurrent synaptic routing auditor.

No board/JTAG hardware access, file writes or runtime state changes. Requires
accepted original NEW native candidate and complete immutable six-file physical
ledger, genuine JTAG markers and exact M02 voltage/spike/synaptic-current data.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import m08_d3d2b_synaptic_gate as gate
from m08_d3d2b_synaptic_vectors import FIXTURES, format_fixture

ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT/"scripts/m08_d3d2b_synaptic_readback_once.tcl"
FILES = (
    "00_executed_source.tcl", "01_jtag_synaptic.log", "02_jtag_synaptic.jou",
    "03_exit.txt", "10_m02_golden.txt", "80_synaptic_parity_readback.txt",
)
METADATA = {
    "schema": "m08-d3d2b-hw-recurrent-four-neurons-v1",
    "result": "TWO_FOUR_NEURON_RECURRENT_SYNAPSE_FIXTURES_MATCHED_M02",
    "target": "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
    "device": "xck26_0",
    "debug_axi": "hw_axi_1",
    "synaptic_execution_tested": "YES_8_EDGES_4_NEURONS_4_TICKS",
    "no_ps_axi_ddr_ssh_used": "YES",
    "reset_mode": "FABRIC_POR_256_CYCLES",
    "ps_clock_dependency": "YES",
    "full_m06_paging_tested": "NO",
}


class Reject(ValueError):
    pass


def check(ok: bool, msg: str):
    if not ok:
        raise Reject(msg)


def read(file: Path, limit: int=12000000) -> bytes:
    check(file.is_file() and not file.is_symlink(),
          "missing/symlinked physical receipt "+str(file))
    check(0 < file.stat().st_size <= limit,
          "empty/oversized physical receipt "+str(file))
    return file.read_bytes()


def expected_golden():
    return ("# schema=m08-d3d2b-m02-routed-four-neuron-v1\n"
            "# independent_dense_vs_queued=PASS\n"
            + "\n".join(format_fixture(f) for f in FIXTURES) + "\n")


def expected_lines():
    result=[]
    for f in FIXTURES:
        fields=format_fixture(f).split("|")
        v_groups,masks,s_groups=[],[],[]
        for n in range(4):
            idx=68+n*9
            v_groups.append(",".join(fields[idx:idx+4]))
            masks.append(fields[idx+4])
            s_groups.append(",".join(fields[idx+5:idx+9]))
        result.append(
            f"fixture={f.name} nonce={fields[1]} decay={fields[2]} "
            f"voltages={';'.join(v_groups)} spike_masks={','.join(masks)} "
            f"synaptic_currents={';'.join(s_groups)} hardware=PASS")
    return result


def verify(native: Path, hw: Path) -> dict:
    try:
        accepted=gate.native(native)
    except (gate.Reject,ValueError,OSError,KeyError) as exc:
        raise Reject("unaccepted original D3.D.2B native image: "+str(exc)) from exc
    check(hw.is_dir() and not hw.is_symlink() and
          hw.parent == native.parent and hw.parent.name=="M08" and
          re.fullmatch(r"m08_d3d2b_synaptic_HW_[A-Za-z0-9]+",hw.name) is not None,
          "invalid physical four-neuron synaptic original evidence folder")
    entries=read(hw/"99_evidence_sha256.txt",12000).decode().splitlines()
    check(len(entries)==len(FILES),"expected exactly six physical ledger rows")
    for name,line in zip(FILES,entries):
        m=re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_./-]+)",line)
        check(m is not None and m.group(2)==name,
              "physical ledger member missing/reordered: "+name)
        check(sha256(read(hw/name)).hexdigest()==m.group(1),
              "physical original receipt SHA changed: "+name)
    check(read(hw/"03_exit.txt",80).decode().strip()=="vivado_physical_exit=0",
          "original physical Vivado execution nonzero")
    tcl=read(hw/"00_executed_source.tcl",30000)
    check(tcl==read(TCL,30000),"executed physical Tcl != reviewed original")
    check(len(re.findall(rb"(?m)^\s*program_hw_devices \$fpga\s*$",tcl))==1,
          "physical script does not contain exactly one programming command")
    check(read(hw/"10_m02_golden.txt",12000).decode("ascii")==expected_golden(),
          "original synaptic current golden changed from independent M02")
    lines=read(hw/"80_synaptic_parity_readback.txt",12000).decode("ascii").splitlines()
    head_count=len(METADATA)+1  # plus bitstream SHA256
    check(len(lines)==head_count+len(FIXTURES),
          "wrong number of physical results/header rows")
    pairs=[x.split("=",1) for x in lines[:head_count]]
    check(all(len(p)==2 for p in pairs) and len(dict(pairs))==len(pairs),
          "duplicate/invalid physical metadata")
    expected=dict(METADATA)
    expected["candidate_sha256"]=accepted["candidate_sha256"]
    check(dict(pairs)==expected,"unexpected physical source/target/status/header")
    check(lines[head_count:]==expected_lines(),
          "physical synaptic/voltage/spike trace does NOT match M02 oracle")
    log=read(hw/"01_jtag_synaptic.log").decode(errors="replace")
    for token in (
        "M08_D3D2B_IMAGE_HASH_VERIFIED|"+accepted["candidate_sha256"],
        "M08_D3D2B_M02_ROUTING_FIXTURES_VERIFIED|2",
        "M08_D3D2B_DEVICE|xck26_0|xck26",
        "M08_D3D2B_PROGRAM_COMPLETED",
        "M08_D3D2B_AXI_MASTER|hw_axi_1",
        "M08_D3D2B_BRAM_TRANSPORT_PASS",
        "M08_D3D2B_ROUTED_SYNAPSE_IDENTITY_PASS",
        "M08_D3D2B_PHYSICAL_ROUTED_RESULT_PC_RECEIPT=",
    ):
        check(token in log,"JTAG original log missing "+token)
    for f in FIXTURES:
        marker="M08_D3D2B_HW_M02_RECURRENT_SYNAPSE_PARITY_PASS|"+f.name+"|"
        check(log.count(marker)==1,"missing or repeated on-device synaptic case")
    check(not any(re.match(r"^(ERROR:|CRITICAL WARNING:)",x)
                  for x in log.splitlines()),
          "physical Vivado log contains fatal diagnostics")
    return {
        "status": "M08_D3D2B_PHYSICAL_RECURRENT_SYNAPTIC_ROUTING_M02_PARITY_ACCEPTED",
        "candidate_sha256":accepted["candidate_sha256"],
        "fixtures":2,
        "neurons_per_fixture":4,
        "ticks_per_fixture":4,
        "synapses_per_fixture":8,
        "hardware_membrane_voltages_verified":32,
        "hardware_spike_decisions_verified":32,
        "hardware_delivered_synapse_current_words_verified":32,
        "recurrent_synapse_routing_physically_verified":True,
        "full_m06_accelerator_verified":False,
        "physical_ddr_verified":False,
        "ps_clock_independence_verified":False,
        "scope":"4 signed16 LIF neurons, 4 ticks, eight positive-delay edges x two cases",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    p.add_argument("--hw-dir",type=Path,required=True)
    args=p.parse_args()
    try:
        result=verify(args.run_dir,args.hw_dir)
    except (Reject,ValueError,OSError,KeyError,UnicodeError) as e:
        print("M08_D3D2B_HARDWARE_AUDIT_REJECTED: "+str(e),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
