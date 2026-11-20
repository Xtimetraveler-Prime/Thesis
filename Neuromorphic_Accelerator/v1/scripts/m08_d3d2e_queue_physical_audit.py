#!/usr/bin/env python3
"""Independent read-only D3.D.2E raw 17-event 32-neuron JTAG receipt auditor.

Requires the independently approved exact original M32Q native DRC/timing/
source/bit SHA gate BEFORE accepting ANY physical receipts. No Vivado/JTAG/PS/DDR/board operations.
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
import m08_d3d2d_event_vectors as oracle
import m08_d3d2e_queue_exact_native_accept as native

TCL=ROOT/"scripts/m08_d3d2e_queue_readback_once.tcl"
FILES=("00_executed_source.tcl","01_jtag_m06.log","02_jtag_m06.jou",
       "03_exit.txt","10_m06_tickqueue_golden.hex","80_m06_tickqueue_hw_parity.txt")
METADATA={
    "schema":"m08-d3d2e-m06-32-neuron-17-queued-event-hardware-v1",
    "result":"ONE_ORIGINAL_M06_32X4_QUEUED_EVENT_SERVICE_AND_RECURRENT_HARDWARE_PARITY",
    "target":"localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
    "device":"xck26_0",
    "debug_axi":"hw_axi_1",
    "external_events_coalesced_on_host":"NO",
    "event_ingress_transport":"JTAG_AXI_LITE_FIFO_MAILBOX",
    "event_push_count":"17",
    "hardware_event_bucket_sums_verified":"128",
    "physical_ddr_m06_hls_verified":"NO",
    "live_buckets_zero_before_service_verified":"128",
    "fifo_event_accept_count":"17",
    "fifo_event_serviced_count":"17",
    "fifo_depth_after_all_services":"0",
    "fifo_high_watermark":"17",
    "tick_completion_mask":"0000000F",
}

class Reject(ValueError):
    pass

def require(ok,msg):
    if not ok:
        raise Reject(msg)

def read(p,limit=12_000_000):
    require(p.is_file() and not p.is_symlink(),"missing/symlink physical file "+str(p))
    require(0<p.stat().st_size<=limit,"empty/oversize physical evidence "+str(p))
    return p.read_bytes()

def expected_lines():
    words=oracle.words()
    lines=[]
    for n in range(32):
        idx=3+n*8
        output=291+n*9
        lines.append(
            f"neuron={n} external_currents={','.join(words[idx+4:idx+8])} "
            f"voltages={','.join(words[output:output+4])} "
            f"mask={words[output+4]} "
            f"synaptic_currents={','.join(words[output+5:output+9])}")
    return lines

def verify(owner:Path,hw:Path):
    try:
        first=native.inspect(owner)
    except (native.Reject,ValueError,KeyError,OSError) as exc:
        raise Reject("new original raw-event native image not accepted: "+str(exc)) from exc
    # An owner arming flag or old D3.D.2D image can never bypass an exact
    # new D3.D.2E DRC/timing/source/bit SHA release.
    require(first.get("status")==
            "M08_D3D2E_EXACT_OWNER_NATIVE_TICKQUEUE_IMAGE_ACCEPTED_NO_BOARD"
            and first.get("image_specific_gate") == "ACCEPTED",
            "new M32Q first image DRC/pins/equations/timing NOT accepted")
    require(hw.is_dir() and not hw.is_symlink() and hw.parent==owner.parent and
            hw.parent.name=="M08" and
            re.fullmatch(r"m08_d3d2e_queue_HW_[A-Za-z0-9]+",hw.name) is not None,
            "not unique original first-owner hardware experiment folder")
    ledger=read(hw/"99_evidence_sha256.txt",12000).decode("ascii").splitlines()
    require(len(ledger)==6,"six original physical receipt SHA rows required")
    for name,row in zip(FILES,ledger):
        m=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)",row)
        require(m is not None and m.group(2)==name,"wrong physical SHA ledger name/order "+name)
        require(sha256(read(hw/name)).hexdigest()==m.group(1),
                "mutated physical evidence "+name)
    require(read(hw/"03_exit.txt",80).decode().strip()=="vivado_physical_exit=0",
            "Vivado physical exit failed")
    src=read(hw/"00_executed_source.tcl",30000)
    require(src==read(TCL,30000),"executed JTAG source altered")
    require(len(re.findall(rb"(?m)^\s*program_hw_devices \$fpga\s*$",src))==1,
            "JTAG source must contain exactly one program_hw_devices")
    require(read(hw/"10_m06_tickqueue_golden.hex",10000).decode("ascii")==
            "\n".join(oracle.words())+"\n",
            "original M06 independent 630-word raw-event reference changed")
    contents=read(hw/"80_m06_tickqueue_hw_parity.txt",18000).decode("ascii").splitlines()
    golden=oracle.words()
    per_tick=[sum(int(golden[580+3*k],16)==t for k in range(17)) for t in range(4)]
    require(sum(per_tick)==17,"original raw event tick grouping drift")
    meta_tick={f"per_tick_serviced_{t}":str(per_tick[t]) for t in range(4)}
    header_rows=len(METADATA)+len(meta_tick)+1
    require(len(contents)==header_rows+32,
            "missing/extra complete 32-neuron raw event physical receipt rows")
    pairs=[s.split("=",1) for s in contents[:header_rows]]
    require(all(len(x)==2 for x in pairs) and len(dict(pairs))==len(pairs),
            "invalid/duplicate physical result metadata")
    meta=dict(METADATA)
    meta["candidate_sha256"]=first["candidate_sha256"]
    meta.update(meta_tick)
    require(dict(pairs)==meta,"physical target, image, event-ingress claims wrong")
    require(contents[header_rows:]==expected_lines(),
            "raw-event 128 bucket/384 neural physical trace differs")
    log=read(hw/"01_jtag_m06.log",12_000_000).decode(errors="replace")
    for marker in (
        "M08_D3D2E_ACCEPTED_IMAGE_HASH|"+first["candidate_sha256"],
        "M08_D3D2E_M06_TRIPLE_ORACLE_630_WORDS_VERIFIED",
        "M08_D3D2E_DEVICE|xck26_0|xck26",
        "M08_D3D2E_PROGRAM_START",
        "M08_D3D2E_PROGRAM_COMPLETED",
        "M08_D3D2E_AXI_MASTER|hw_axi_1",
        "M08_D3D2E_BRAM_TRANSPORT_PASS",
        "M08_D3D2E_M32Q_V6_IDENTITY_PASS",
        "M08_D3D2E_PHYSICAL_RAW_17_EVENT_PUSH_ACCEPTED",
        "M08_D3D2E_ALL_128_LIVE_BUCKETS_ZERO_BEFORE_SERVICE",
        "M08_D3D2E_QUEUE_17_ACCEPTED_17_SERVICED_ALL_FOUR_TICKS_PASS",
        "M08_D3D2E_PHYSICAL_ALL_128_FPGA_EVENT_BUCKET_SUMS_PASS",
        "M08_D3D2E_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS",
    ):
        require(marker in log,"physical original event/JTAG log marker absent "+marker)
    for marker in ("M08_D3D2E_PROGRAM_START","M08_D3D2E_PROGRAM_COMPLETED"):
        require(len(re.findall(r"(?m)^"+marker+r"$",log))==1,
                "ambiguous or duplicated JTAG program marker")
    for t in range(4):
        require(log.count(f"M08_D3D2E_TICK_SERVICE_PARITY|{t}|{per_tick[t]}\\n")==1,
                "missing/duplicated physical per-tick SERVICE receipt")
    for n in range(32):
        for marker in (f"M08_D3D2E_EVENT_BUCKET_PARITY|{n}\n",
                       f"M08_D3D2E_M06_REAL_NEURON_PARITY|{n}\n"):
            require(log.count(marker)==1,"missing/duplicate true hardware bucket/neural parity "+marker.strip())
    require(not any(line.startswith(("ERROR:","CRITICAL WARNING:"))
                    for line in log.splitlines()),
            "physical Vivado log contains errors/critical warnings")
    return dict(
        status="M08_D3D2E_PHYSICAL_M06_17_RAW_EVENT_128_BUCKET_384_NEURAL_ACCEPTED",
        first_original_image_sha256=first["candidate_sha256"],
        external_event_ingestion_in_fabric=True,
        hardware_input_buckets_verified=128,
        physical_events_accepted=17, physical_events_serviced=17,
        fifo_live_buckets_zero_before_service=128,
        fifo_high_watermark=17, four_service_tick_barriers=True,
        hardware_voltages_verified=128,
        hardware_spike_decisions_verified=128,
        hardware_recurrent_currents_verified=128,
        physical_neurons=32, logical_ticks=4, external_raw_events=17,
        recurrent_synapses=5,
        original_m05_hls_physical=False, physical_ddr=False,
        streaming_or_asynchronous_ingress_proven=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir",type=Path,required=True)
    p.add_argument("--hw-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        print(json.dumps(verify(a.run_dir,a.hw_dir),indent=2,sort_keys=True))
        return 0
    except (Reject,ValueError,OSError,UnicodeError,KeyError) as exc:
        print("M08_D3D2E_PHYSICAL_RECEIPT_REJECTED: "+str(exc),file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
