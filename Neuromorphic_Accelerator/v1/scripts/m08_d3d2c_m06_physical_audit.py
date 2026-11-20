#!/usr/bin/env python3
"""Read-only independent D3.D.2C first owner-armed physical receipt checker.

No JTAG, PS MMIO, Vivado or board interactions. Recomputes original M06
32-neuron x 4-tick volts/masks/delivered-current reference against the genuine
receipt, and first revalidates exact immutable original owner native
bitstream+12-file SHA/DRC/timing gate. No board parity claim without receipts.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_vectors as oracle
import m08_d3d2c_m06_native_review as native_gate

TCL=ROOT/"scripts/m08_d3d2c_m06_readback_once.tcl"
FILES=(
    "00_executed_source.tcl","01_jtag_m06.log","02_jtag_m06.jou",
    "03_exit.txt","10_m06_32x4_golden.hex","80_m06_32x4_hw_parity.txt"
)
METADATA={
    "schema":"m08-d3d2c-m06-32-neuron-hardware-v1",
    "result":"ONE_ORIGINAL_M06_32X4_RECURRENT_HARDWARE_PARITY",
    "target":"localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
    "device":"xck26_0",
    "debug_axi":"hw_axi_1",
    "external_events_coalesced_on_host":"YES",
    "physical_ddr_m06_hls_verified":"NO",
}
class Reject(ValueError):
    pass
def require(ok,reason):
    if not ok:
        raise Reject(reason)
def read(p,limit=12000000):
    require(p.is_file() and not p.is_symlink(),"missing/symlinked evidence "+str(p))
    require(0<p.stat().st_size<=limit,"empty/oversized evidence "+str(p))
    return p.read_bytes()

def expected_lines():
    golden=oracle.words()
    ret=[]
    for n in range(32):
        idx=291+n*9
        ret.append(
            f"neuron={n} voltages={','.join(golden[idx:idx+4])} "
            f"mask={golden[idx+4]} "
            f"synaptic_currents={','.join(golden[idx+5:idx+9])}")
    return ret

def verify(native:Path,hw:Path)->dict:
    try:
        accepted=native_gate.inspect(native)
    except (native_gate.Reject,ValueError,OSError,KeyError) as exc:
        raise Reject("unaccepted original 32-neuron native image: "+str(exc)) from exc
    # Native ACCEPTED means the image is approved for owner-armed one-shot
    # JTAG. It never by itself proves any real physical computation.
    require(accepted.get("status")==
            "M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD",
            "native 32-neuron first-image DRC/image approval is PENDING")
    require(hw.is_dir() and not hw.is_symlink() and
            hw.parent==native.parent and hw.parent.name=="M08" and
            re.fullmatch(r"m08_d3d2c_m06_HW_[A-Za-z0-9]+",hw.name) is not None,
            "not a unique original M06 hardware receipt directory")
    receipt=read(hw/"99_evidence_sha256.txt",12000).decode("ascii").splitlines()
    require(len(receipt)==6,"six physical SHA rows required")
    for name,line in zip(FILES,receipt):
        m=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)",line)
        require(m is not None and m.group(2)==name,"physical evidence row drift: "+name)
        require(sha256(read(hw/name)).hexdigest()==m.group(1),
                "physical original byte mutation: "+name)
    require(read(hw/"03_exit.txt",80).decode().strip()=="vivado_physical_exit=0",
            "physical Vivado process nonzero")
    tcl=read(hw/"00_executed_source.tcl",30000)
    require(tcl==read(TCL,30000),"executed Tcl source changed")
    require(len(re.findall(rb"(?m)^\s*program_hw_devices \$fpga\s*$",tcl))==1,
            "must be exactly one programming statement")
    expected_golden="\n".join(oracle.words())+"\n"
    require(read(hw/"10_m06_32x4_golden.hex",9000).decode("ascii")==
            expected_golden,"M06 original dense/event/sparse input drift")
    lines=read(hw/"80_m06_32x4_hw_parity.txt",12000).decode("ascii").splitlines()
    require(len(lines)==len(METADATA)+1+32,
            "missing/extra actual 32-neuron hardware receipt rows")
    header=[x.split("=",1) for x in lines[:len(METADATA)+1]]
    require(all(len(x)==2 for x in header) and
            len(dict(header))==len(header),
            "invalid/duplicate physical metadata")
    expected=dict(METADATA)
    expected["candidate_sha256"]=accepted["candidate_sha256"]
    require(dict(header)==expected,"unexpected physical identity/target or false scope")
    require(lines[len(header):]==expected_lines(),
            "real hardware 128 voltage/mask/synaptic current words diverged")
    log=read(hw/"01_jtag_m06.log").decode(errors="replace")
    for marker in (
        "M08_D3D2C_ACCEPTED_IMAGE_HASH|"+accepted["candidate_sha256"],
        "M08_D3D2C_M06_TRIPLE_ORACLE_579_WORDS_VERIFIED",
        "M08_D3D2C_DEVICE|xck26_0|xck26",
        "M08_D3D2C_PROGRAM_START",
        "M08_D3D2C_PROGRAM_COMPLETED",
        "M08_D3D2C_AXI_MASTER|hw_axi_1",
        "M08_D3D2C_BRAM_TRANSPORT_PASS",
        "M08_D3D2C_M32N_V4_IDENTITY_PASS",
        "M08_D3D2C_PHYSICAL_M06_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS",
    ):
        require(marker in log,"actual board log missing: "+marker)
    # Vivado's journal echoes source lines containing marker strings.
    # Only count standalone stdout marker lines, not echoed Tcl commands.
    require(len(re.findall(r"(?m)^M08_D3D2C_PROGRAM_START$",log))==1 and
            len(re.findall(r"(?m)^M08_D3D2C_PROGRAM_COMPLETED$",log))==1,
            "physical record has ambiguous/multiple program markers")
    for n in range(32):
        require(log.count(f"M08_D3D2C_M06_REAL_NEURON_PARITY|{n}\n")==1,
                "missing/duplicated physical neuron parity marker "+str(n))
    require(not any(x.startswith(("ERROR:","CRITICAL WARNING:"))
                    for x in log.splitlines()),
            "physical Vivado error or critical warning")
    return dict(
        status="M08_D3D2C_PHYSICAL_M06_32X4_REAL_RECURRENT_M02_PARITY_ACCEPTED",
        hardware_voltages_verified=128,
        hardware_spike_decisions_verified=128,
        hardware_synaptic_currents_verified=128,
        four_ticks=True, physical_neurons=32, recurrent_edges=5,
        host_coalesced_external_events=17,
        m06_hls_physical=False, physical_ddr=False,
        candidate_sha256=accepted["candidate_sha256"])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    p.add_argument("--hw-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        print(json.dumps(verify(a.run_dir,a.hw_dir),indent=2,sort_keys=True))
        return 0
    except (Reject,ValueError,OSError,UnicodeError,KeyError) as exc:
        print("M08_D3D2C_PHYSICAL_REJECTED: "+str(exc),file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
