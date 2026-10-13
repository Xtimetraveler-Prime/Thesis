#!/usr/bin/env python3
"""P05.2i final physical page-AXI counter provenance/Phase-5 closeout candidate.

Reuses accepted physical P05.2h 5-core/16-barrier oracle without changing
the neural model, ELF, RTL or bitstream. The counters are read from the
existing 128-bit HP0 DDR burst adapter, not estimated bus utilization.

PREPARE is an offline arithmetic audit; VERIFY requires the independent
original physical P05.2h mailbox + five complete DDR records AND a new,
read-only physical MMIO snapshot of PAGE_READ_BURSTS / PAGE_WRITE_BURSTS /
PAGE_AXI_BYTES_MOVED. Fail closed on absent/contradictory evidence.

This only meters PL page-engine AXI DDR payload traffic, not A53 cache/DDR,
PS-routed external events or end-to-end platform bandwidth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
SRC=str(ROOT/"src")
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)

import p05_2h_barrier_verify as BARRIER
import p05_2h_barrier_fixture as MODEL
from p05_2_composite_fixture import load

FIELDS=load("p05_2i_mailbox",ROOT/"scripts/p05_1_verify.py").FIELDS
PROFILE="p05-2i-pl-page-axi-burst-and-byte-register-provenance-v1"
OUTFILE="p05_2i_counter_expectations.json"
WITNESS="p05_2i_axi_witness.bin"
BURST_BYTES=16*16
FULL_IN=0x6B000
MUTABLE_OUT=0x1A000

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def calculation(root:Path)->dict:
    gate=json.loads((root/"p05_2h_barrier_gate.json").read_text())
    manifest=json.loads((root/"p05_artifacts/p05_manifest.json").read_text())
    if (gate["profile"]!=MODEL.PROFILE or
        gate["status"]!="MODEL_ONLY_NOT_HARDWARE_ACCEPTED" or
        (gate["steps"],gate["order"],gate["slots"],gate["cores"])!=(
            16,[4,1,3,0,2],3,[0,1,2,3,4]) or
        (gate["expected_packets"],gate["expected_dispatches"],
         gate["expected_events"],gate["expected_checkpoints"])!=(
            156,80,80,318)):
        raise ValueError("P05.2h accepted high-traffic model workload drift")
    s=gate["scheduler_model"]
    if (s["emitted_packets"],s["resident_deliveries"],
        s["nonresident_deliveries"],s["evictions"])!=(156,78,78,77):
        raise ValueError("16-step high-traffic routing/victim model drift")
    if (s["initial_ins"],s["replacement_ins"],
        s["runtime_outs"],s["final_outs"])!=(3,77,77,3):
        raise ValueError("full page-in/mutable-out counts drift")
    if (s["page_commands"]!=160 or
        s["programmed_page_in_payload_bytes"]!=80*FULL_IN or
        s["programmed_page_out_payload_bytes"]!=80*MUTABLE_OUT):
        raise ValueError("frozen programmed page payload bytes disagree")
    if (manifest["dispatches"],manifest["events"],
        manifest["checkpoints"])!=(80,80,318):
        raise ValueError("P05G descriptor not frozen P05.2h traffic oracle")
    read_commands=s["initial_ins"]+s["replacement_ins"]
    write_commands=s["runtime_outs"]+s["final_outs"]
    if (FULL_IN % BURST_BYTES)!=0 or (MUTABLE_OUT % BURST_BYTES)!=0:
        raise ValueError("AXI coalescer burst geometry not exact")
    rb=read_commands*(FULL_IN//BURST_BYTES)
    wb=write_commands*(MUTABLE_OUT//BURST_BYTES)
    tx=(rb+wb)*BURST_BYTES
    if (rb,wb,tx)!=(136960,33280,43581440):
        raise ValueError("expected 160 page operations did not yield frozen measured-burst targets")
    output={
        "schema":PROFILE,
        "status":"MODEL_ONLY_NOT_PHYSICAL_ACCEPTANCE",
        "hardware_source":{
            "read_burst_counter_mmio":"0xA4000044",
            "write_burst_counter_mmio":"0xA4000048",
            "axi_successful_bytes_lo_mmio":"0xA400004C",
            "axi_successful_bytes_hi_mmio":"0xA4000050",
            "hardware":"P03.2c accepted P02 128-bit AXI HP0 burst adapter",
            "axi_page_payload_only":True,
            "fixed_beats_per_burst":16,
            "fixed_bytes_per_beat":16,
            "read_burst_completion":"16-beat read returned without AXI error",
            "write_burst_completion":"final B response accepted without AXI error",
        },
        "separate_independent_reference":"P05.2h LogicalChip + P03 victim replay",
        "steps":16,"dispatches":80,"barriers":16,"checkpoints":318,
        "routed_packets":156,"resident_deliveries":78,
        "nonresident_deliveries":78,"evictions":77,
        "full_page_in_commands":read_commands,
        "mutable_page_out_commands":write_commands,
        "full_page_in_bytes_each":FULL_IN,
        "mutable_page_out_bytes_each":MUTABLE_OUT,
        "axi_burst_bytes":BURST_BYTES,
        "expect_axi_read_bursts":rb,
        "expect_axi_write_bursts":wb,
        "expect_axi_total_completed_bursts":rb+wb,
        "expect_axi_read_bytes":rb*BURST_BYTES,
        "expect_axi_write_bytes":wb*BURST_BYTES,
        "expect_axi_successful_bytes":tx,
        "expected_page_commands":s["page_commands"],
        "p05_2h_gate_sha256":sha(root/"p05_2h_barrier_gate.json"),
        "p05_2h_logical_manifest_sha256":sha(root/"barrier_logical_golden/manifest.json"),
        "p05_header_sha256":sha(root/"p05_artifacts/p05_header.bin"),
        "p05_payload_sha256":sha(root/"p05_artifacts/p05_payload.bin"),
        "independent_expected_full_ddr_sha256":gate["physical_final_record_sha256"],
        "limits":"PL page-engine HP0 AXI traffic only; not PS injected events/CPU cache DMA/total system; physical NEXT overflow/recovery is not covered",
    }
    return output

def prepare(root:Path)->int:
    try:
        if not root.is_dir():
            raise ValueError("P05.2h offline PREPARE must be completed first")
        target=root/OUTFILE
        if target.exists():
            raise ValueError("refuse to overwrite existing P05.2i counter ledger")
        got=calculation(root)
        target.write_text(json.dumps(got,indent=2,sort_keys=True)+"\n")
    except (OSError,ValueError,KeyError,TypeError,AssertionError) as e:
        print("FAIL: P05.2i offline counter model: "+str(e),file=sys.stderr)
        return 1
    print("PASS: P05.2i independent P03 page-AXI counter arithmetic frozen "
          f"read_bursts={got['expect_axi_read_bursts']} "
          f"write_bursts={got['expect_axi_write_bursts']} "
          f"successful_bytes={got['expect_axi_successful_bytes']}")
    print("P05_2I_PREPARE_MODEL_ONLY=1")
    return 0

def verify(root:Path,*,check_neural:bool=True)->bool:
    try:
        root=root.resolve()
        expected=calculation(root)
        saved=json.loads((root/OUTFILE).read_text())
        if saved!=expected:
            raise ValueError("P05.2i counter ledger differs from original 16-barrier model")
        wfile=root/WITNESS
        witness=wfile.read_bytes()
        if len(witness)!=16:raise ValueError("real read-only AXI MMIO witness must be exactly 16 bytes")
        rb,wb,lo,hi=struct.unpack("<4I",witness)
        moved=lo|(hi<<32)
        mailbox=root/"p05_a53_result.bin"
        original=mailbox.read_bytes()
        if len(original)!=256:raise ValueError("original device P05R mailbox must be 256 bytes")
        fields=dict(zip(FIELDS,struct.unpack("<64I",original)))
        expected_rb=expected["expect_axi_read_bursts"]
        expected_wb=expected["expect_axi_write_bursts"]
        expected_bytes=expected["expect_axi_successful_bytes"]
        if (rb,wb,moved)!=(expected_rb,expected_wb,expected_bytes):
            raise ValueError(
                "physical MMIO 128-bit AXI page counters mismatch: "
                f"read={rb} want={expected_rb}; write={wb} want={expected_wb}; "
                f"bytes={moved} want={expected_bytes}"
            )
        if (fields["hw_read_bursts"],fields["hw_write_bursts"])!=(rb,wb):
            raise ValueError("read-only halted PL MMIO counters disagree with independent A53 P05R terminal")
        if (fields["result"],fields["error"],fields["hw_pages"],
            fields["hw_dispatches"],fields["hw_pending_bytes"],
            fields["hw_status"],fields["hw_last_page_bytes"])!=(
            0x600D600D,0,160,80,0,0,MUTABLE_OUT):
            raise ValueError("hardware did not finish all 160 physical pages and 80 dispatches quiescent")
        if (fields["cntfrq_hz"]<=0 or
            fields["pl_page_lo"]|(fields["pl_page_hi"]<<32)==0 or
            fields["ps_infer_lo"]|(fields["ps_infer_hi"]<<32)==0):
            raise ValueError("no real PL page cycles / PS generic-timer witness")
        if (expected_rb+expected_wb)*BURST_BYTES!=moved:
            raise ValueError("physical bursts and hardware byte counter disagree on 256B transport geometry")
        if check_neural and not BARRIER.verify(mailbox,root):
            raise ValueError("original P05.2h real device neural/barrier/whole-DDR gate did not pass")
        for cid in MODEL.CORES:
            physical=(root/"final_ddr"/f"core{cid}_after.bin")
            if (physical.stat().st_size!=0x80000 or
                sha(physical)!=expected["independent_expected_full_ddr_sha256"][str(cid)]):
                raise ValueError(f"physical core{cid} 512KiB evidence not original independently derived route-ordered DDR")
    except (OSError,ValueError,KeyError,TypeError,AssertionError,struct.error) as e:
        print("FAIL: P05.2i physical PL page AXI byte/burst evidence: "+str(e),file=sys.stderr)
        print("P05_2I_VERIFY_EXIT=1",file=sys.stderr)
        return False
    print("PASS: P05.2i KV260 PL HP0 AXI successful 256-byte burst counters "
          f"read={rb} write={wb} and direct read-only hardware bytes={moved} "
          "exactly equal 80 complete full page-ins + 80 mutable-only page-outs")
    print("PASS: P05.2i independent A53 P05R page counters match halted-PL MMIO burst registers and directly measured page AXI byte register")
    print("PASS: P05.2i original 16-barrier/318-checkpoint neural and all five 512KiB physical DDR oracle preserved")
    ps_ticks=fields["ps_infer_lo"]|(fields["ps_infer_hi"]<<32)
    pl_cycles=fields["pl_page_lo"]|(fields["pl_page_hi"]<<32)
    print("P05_2I_MEASUREMENTS="+json.dumps({
        "axi_read_bursts":rb,"axi_write_bursts":wb,"axi_bytes_moved":moved,
        "pl_page_cycles_raw":pl_cycles,
        "ps_inference_ticks_raw":ps_ticks,
        "ps_timer_hz":fields["cntfrq_hz"],
        "ps_inference_seconds":ps_ticks/fields["cntfrq_hz"],
        "witness_sha256":sha(root/WITNESS),
        "p05r_sha256":sha(mailbox),
        "physical_full_ddr_sha256":expected["independent_expected_full_ddr_sha256"],
        "scope":"PL PAGE ENGINE ONLY; not total system DDR or runtime routed overflow recovery",
    },sort_keys=True))
    print("P05_2I_VERIFY_EXIT=0")
    return True

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("prepare","verify"))
    parser.add_argument("--directory",required=True,type=Path)
    args=parser.parse_args()
    return prepare(args.directory) if args.mode=="prepare" else (0 if verify(args.directory) else 1)

if __name__=="__main__":
    raise SystemExit(main())
