#!/usr/bin/env python3
"""Independent 256-byte full B4m A53 physical mailbox verifier.

Only authentic JTAG mailbox captures from independently staged and owned
KV260 sessions may be called physical evidence. A native synthetic byte
fixture is never board proof. This gate does not prove neuron numerics;
real trained parity requires the original independent source oracle.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

MAGIC=0x42344D31
PASS=0x600D600D
DONE=0xC0DEF00D
FULL_MAGIC=0x464D3442
PER_PAGE_IN=438272
PER_MUTABLE_OUT=106496

class FullReceiptError(ValueError):
    pass

def verify(data:bytes,expected_class:int|None=None)->dict:
    if len(data)!=256:raise FullReceiptError("NO-GO: exact 256 physical mailbox bytes required")
    w=struct.unpack("<64I",data)
    if w[0]!=MAGIC or w[1]!=1 or w[2]!=PASS or w[63]!=DONE:
        raise FullReceiptError("NO-GO: genuine B4m terminal magic/schema/success/done mismatch")
    if any(w[i]!=0 for i in (3,4,5,6,7,8,9,10,11,42,43,44,45)):
        raise FullReceiptError("NO-GO: CPU/shell/route/pager/inference failure recorded")
    if w[12]!=FULL_MAGIC or w[13]!=26 or w[14]!=702 or w[15]!=702 or (
        w[16]!=699 or w[17]!=3 or w[23]!=21384 or w[24]!=1010):
        raise FullReceiptError("NO-GO: expected full 26-tick original 27core paging or original axon geometry missing")
    if not 0<w[18]<=25*784*27 or not 0<w[19]<=26*1010 or (
        w[20]!=w[21] or not 0<w[20]<=26*8192):
        raise FullReceiptError("NO-GO: missing external CURRENT/source spikes, NEXT route imbalance or overflow")
    if w[22]>=10 or (
        expected_class is not None and (expected_class not in range(10)
                                        or w[22]!=expected_class)):
        raise FullReceiptError("NO-GO: invalid/wrong frozen-reference predicted class")
    votes=list(w[32:42])
    if max(votes)==0 or w[22]!=votes.index(max(votes)) or sum(votes)>w[19]:
        raise FullReceiptError("NO-GO: readout spike counters/classification mismatch")
    if not 128<=w[31]<=0xE0000 or (
        w[46]<702 or any(w[i]!=0 for i in range(47,63))):
        raise FullReceiptError("NO-GO: staged ingress/PL completion/reserved mailbox invalid")
    read_bytes=w[27]|(w[28]<<32)
    write_bytes=w[29]|(w[30]<<32)
    if read_bytes!=w[15]*PER_PAGE_IN or (
        write_bytes!=(w[16]+w[17])*PER_MUTABLE_OUT):
        raise FullReceiptError("NO-GO: measured page-in/out byte receipt inconsistent with P03 transfer ABI")
    trace_hash=w[25]|(w[26]<<32)
    if not trace_hash:
        raise FullReceiptError("NO-GO: missing full per-compartment trace hash")
    return {
        "schema":"p07-b4m-real-physical-trained-inference-mailbox-v1",
        "raw_mailbox_sha256":hashlib.sha256(data).hexdigest(),
        "physical_dispatches":w[14],
        "physical_barriers_acked":w[13],
        "physical_page_ins":w[15],
        "physical_dirty_page_outs":w[16],
        "physical_final_page_outs":w[17],
        "physical_page_read_bytes":read_bytes,
        "physical_page_write_bytes":write_bytes,
        "external_current_events":w[18],
        "source_spikes_from_P03_trace_bank7":w[19],
        "P03_packet_words_captured":w[20],
        "NEXT_packets_physically_inserted":w[21],
        "trained_readout_prediction":w[22],
        "readout_spike_counts":votes,
        "original_registered_axons":w[23],
        "per_tick_compartments_traced":w[24],
        "all_26_tick_trace_hash":f"0x{trace_hash:016X}",
        "input_frame_bytes":w[31],
        "PS_PL_dispatch_counter_snapshot":w[46],
        "independent_full_neuron_numerical_parity":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mailbox",type=Path,required=True)
    p.add_argument("--expected-class",type=int)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        raw=a.mailbox.read_bytes()
        record=verify(raw,a.expected_class)
        if a.out:
            if a.out.exists() or a.out.is_symlink():
                raise FullReceiptError("NO-GO: independent receipt output must be NEW")
            a.out.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
        print(json.dumps(record,sort_keys=True,indent=2))
        print("P07_B4M_FULL_26_TICK_PHYSICAL_RECEIPT_STRUCTURALLY_VALID=1")
        print("P07_B4M_NUMERICAL_PARITY_INDEPENDENTLY_VERIFIED=0")
    except (OSError,ValueError,struct.error) as exc:
        print("P07_B4M_FULL_RECEIPT_NO_GO="+str(exc),file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
