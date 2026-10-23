#!/usr/bin/env python3
"""Strict independent 256-byte B4l PHYSICAL B3 one-epoch receipt verifier.

The new first-epoch firmware deliberately stops with an UNACKED global
B3 barrier. Packet counts may legitimately be zero for the pre-ingress
empty CURRENT banks. No 26-tick inference, no B2b routing or TEST access.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

RECEIPT_MAGIC=0x42334C34
ONE_EPOCH_MAGIC=0x31454233
PASS=0x600D600D
DONE=0xC0DEF00D
READ_PAGE_BYTES=0x6B000
DIRTY_PAGE_BYTES=0x1A000


def verify(data:bytes)->dict:
    if len(data)!=256:
        raise ValueError("NO-GO: B4l B3 independent receipt requires exactly 256 bytes")
    w=struct.unpack("<64I",data)
    checks={
        "receipt_magic":w[0]==RECEIPT_MAGIC,
        "version":w[1]==1,
        "board_status":w[2]==PASS,
        "first_fault":w[3]==0,
        "FPD128":w[4]==0,
        "adapter_initialized":w[5]==0,
        "shell_identity":w[6]==0,
        "original_B24_bindings":w[7]==0,
        "original_B3_LRU":w[8]==0,
        "original_B3c2_P03_adapter":w[9]==0,
        "one_epoch_rc":w[10]==0,
        "one_epoch_contract":w[11]==ONE_EPOCH_MAGIC,
        "original_27_logical_dispatches":w[12]==27,
        "original_27_full_page_ins":w[13]==27,
        "24_dirty_evictions":w[14]==24,
        "barrier_pending":w[15]==1,
        "barrier_NOT_acked":w[16]==0,
        "bounded_real_packet_bank_capture":w[17]<=8192,
        "27_source_views":w[18]==27,
        "packet_capture_fnv":(w[19]|w[20]<<32)!=0,
        "pager_not_faulted":w[21]==0,
        "scheduler_not_faulted":w[22]==0,
        "P03_not_faulted":w[23]==0,
        "P03_physical_page_completed":w[24]>=51,
        "P03_physical_dispatch_completed":w[25]>=27,
        "physical_FP_width_raw":w[26]==0xA00,
        "no_current_ingress":w[27]==0,
        "no_independent_source_spike_proof":w[28]==0,
        "no_next_event_bank_commit":w[29]==0,
        "no_B2b_barrier_ack":w[30]==0,
        "no_trained_numerical_parity":w[31]==0,
        "official_TEST_sealed":w[32]==0,
        "genuine_27_core_bindings":w[33]==27,
        "axon_bindings_not_empty":w[34]>0,
        "frozen_compartments_not_empty":0<w[35]<=27*1024,
        "original_P03_page_bytes":(w[36]|w[37]<<32)==27*READ_PAGE_BYTES+24*DIRTY_PAGE_BYTES,
        "pager_tick_never_advanced":w[38]==0,
        "barriers_completed_zero":w[39]==0,
        "ledger_dispatches":w[40]==27,
        "ledger_dirty_outs":w[41]==24,
        "ledger_page_ins":w[42]==27,
        "no_epoch_fault":w[43]==0,
        "core_bind_no_failure":w[44]==0xFFFFFFFF,
        "axon_bind_no_failure":w[45]==0xFFFFFFFF,
        "reserved_zero":all(x==0 for x in w[46:63]),
        "done":w[63]==DONE,
    }
    failed=[k for k,valid in checks.items() if not valid]
    if failed:
        raise ValueError("NO-GO: B4l true P03 27-dispatch receipt gate: "+",".join(failed))
    return {
        "physical_scheduler_dispatches":w[12],
        "physical_page_ins":w[13],
        "physical_dirty_page_outs":w[14],
        "first_epoch_pending_barrier":True,
        "barrier_acknowledged":False,
        "captured_P03_packet_words":w[17],
        "packet_capture_FNV64":f"0x{(w[19]|w[20]<<32):016X}",
        "genuine_frozen_axon_bindings":w[34],
        "genuine_frozen_compartments":w[35],
        "claimed_26_tick_inference":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mailbox",required=True,type=Path)
    a=p.parse_args()
    try:
        receipt=verify(a.mailbox.read_bytes())
    except (OSError,ValueError) as e:
        print("P07_B4L_B3_ONE_EPOCH_NO_GO="+str(e),file=sys.stderr)
        return 3
    print(json.dumps(receipt,indent=2,sort_keys=True))
    print("P07_B4L_B3_REAL_27_DISPATCH_BAR_PRE_ACK_PHYSICAL_RECEIPT_PASS=1")
    print("P07_B4L_B3_PHYSICAL_NEXT_ROUTING_ACCEPTED=0")
    print("P07_B4L_B3_TRAINED_26_TICK_INFERENCE_VERIFIED=0")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
