#!/usr/bin/env python3
"""M08 D3.D.3A software-only M32Q page geometry and host-lease conformance.

FIRST step after genuine D3.D.2E KV260 FIFO physical acceptance. Build a
candidate 4 KiB *software image* for all 32x4 original M06 configuration,
currents, edges, voltages, spikes, recurrent currents and 17 raw events.
Use pre-existing HostPagedOwnership to model 3 logical pages/2 resident
slots, exclusive host/compute leases and readback/dirty-save/barrier.
There is NO FPGA page bank here, no signed16 physical paged neural engine,
no Linux DMA API, no physical DDR, no clock/latency/power observation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
import m08_d3d2d_event_vectors as fixture
from neuromorphic_accelerator_v1.m08_host_page_ownership import HostPagedOwnership

WORDS=1024
BYTES=4*WORDS
MAGIC=0x4D335047  # M3PG, SOFTWARE CANDIDATE, NOT M32Q ON-DEVICE ABI
VERSION=0x00010000
HEADER=8
CONFIG=8            # 32 neurons x 4 config signed16 (sign-extended 32)
INPUTS=CONFIG+128    # 32 neurons x 4 signed32 bucket currents
EDGES=INPUTS+128     # 8 slots x 4 signed16/address/delay fields
VOLTAGES=EDGES+32    # 32 neurons x 4 sign-extended signed16 traces
SPIKES=VOLTAGES+128  # 32 per-neuron 4-bit time masks
RECURRENT=SPIKES+32  # 32 neurons x 4 signed32 delivered currents
EVENTS=RECURRENT+128 # 17 raw events x 3 words
END=EVENTS+51
assert END==635 and END<=WORDS

class PageReject(ValueError):
    pass

def require(ok:bool,message:str)->None:
    if not ok:
        raise PageReject(message)

def _u32(raw:tuple[str,...])->tuple[int,...]:
    require(len(raw)==630,"original independent M06 raw17 fixture length drift")
    require(all(len(s)==8 and all(ch in "0123456789ABCDEF" for ch in s)
                for s in raw),"original M06 oracle malformed")
    return tuple(int(x,16) for x in raw)

def _m06_words()->tuple[int,...]:
    data=_u32(fixture.words())
    require(data[0]==0xD2C00001 and data[1]==3 and data[2]==5,
            "original M06 signed16/recurrent/workload metadata drift")
    counts=[sum(data[580+3*e]==t for e in range(17)) for t in range(4)]
    require(counts==[5,5,4,3],"original 17 event tick ordering drift")
    return data

def _id(value:int,label:str)->None:
    require(type(value) is int and 0<=value<2**32,label+" must be unsigned32")

def _layout_words(original:tuple[int,...])->list[int]:
    output=[0]*WORDS
    # Full first-owner M06 oracle, rearranged for a proposed on-chip page
    # geometry. No source neural result is recomputed by this assembler.
    for n in range(32):
        source=3+n*8
        output[CONFIG+n*4:CONFIG+n*4+4]=original[source:source+4]
        output[INPUTS+n*4:INPUTS+n*4+4]=original[source+4:source+8]
        trace=291+n*9
        output[VOLTAGES+n*4:VOLTAGES+n*4+4]=original[trace:trace+4]
        output[SPIKES+n]=original[trace+4]
        output[RECURRENT+n*4:RECURRENT+n*4+4]=original[trace+5:trace+9]
    output[EDGES:EDGES+32]=original[259:291]
    output[EVENTS:END]=original[579:630]
    return output

def pack_page(logical_id:int,epoch:int=0)->bytes:
    """Pack original independent neural oracle into fixed 4 KiB software page."""
    _id(logical_id,"logical_id")
    _id(epoch,"epoch")
    original=_m06_words()
    output=_layout_words(original)
    output[:HEADER]=[MAGIC,VERSION,logical_id,epoch,
                     original[0],original[1],original[2],17]
    result=struct.pack("<1024I",*output)
    require(len(result)==BYTES,"candidate page length is not 4 KiB")
    return result

def audit_page(image:bytes,*,logical_id:int,epoch:int)->dict:
    """Validate exact *software* bytes against original M02/M03/M06 oracle."""
    _id(logical_id,"logical_id")
    _id(epoch,"epoch")
    require(type(image) is bytes and len(image)==BYTES,
            "not fixed-size immutable software page bytes")
    words=struct.unpack("<1024I",image)
    original=_m06_words()
    expected=_layout_words(original)
    expected[:HEADER]=[MAGIC,VERSION,logical_id,epoch,
                       original[0],original[1],original[2],17]
    require(words==tuple(expected),
            "page contains wrong logical ID, epoch, original neural data or nonzero padding")
    return {
        "logical_id":logical_id,
        "epoch":epoch,
        "page_bytes":BYTES,
        "source_m06_neurons":32,
        "source_m06_ticks":4,
        "source_m06_edges":5,
        "source_raw_events":17,
        "source_neural_and_input_comparisons":512,
        "software_page_sha256":sha256(image).hexdigest(),
        "hardware_page_verified":False,
        "physical_ddr":False,
    }

def with_epoch(image:bytes,*,logical_id:int,old_epoch:int,new_epoch:int)->bytes:
    """MODEL an epoch metadata update; NOT execution of any neuron."""
    audit_page(image,logical_id=logical_id,epoch=old_epoch)
    _id(new_epoch,"new_epoch")
    require(new_epoch==old_epoch+1,"source epoch must advance exactly once")
    raw=bytearray(image)
    struct.pack_into("<I",raw,3*4,new_epoch)
    result=bytes(raw)
    audit_page(result,logical_id=logical_id,epoch=new_epoch)
    return result

def demo()->dict:
    """Three software logical contexts share two modeled resident page slots.

    All three reference the SAME independently verified 32x4 M06 test
    fixture and differ only in logical page IDs. A modeled compute finish
    changes ONLY the software epoch tag; no neural inference occurs here.
    """
    owner="d3d3a-pc-software-only"
    starting={logical:pack_page(logical) for logical in range(3)}
    paging=HostPagedOwnership(starting,slots=2,owner=owner)
    def load(logical:int,slot:int):
        paging.begin_host(owner=owner)
        img=paging.stage_load(logical,slot,owner=owner)
        paging.verify_load(slot,observed_sha256=sha256(img).hexdigest(),owner=owner)
        paging.end_host(owner=owner)
    def execute_and_save(logical:int,slot:int):
        input_image=paging.dispatch(logical,slot,owner=owner)
        audit_page(input_image,logical_id=logical,epoch=0)
        modeled=with_epoch(input_image,logical_id=logical,old_epoch=0,new_epoch=1)
        paging.finish_compute(slot,observed_image=modeled,
                              packets_drained=True,owner=owner)
        paging.begin_host(owner=owner)
        paging.save_dirty(slot,observed_image=modeled,owner=owner)
        paging.end_host(owner=owner)
    load(0,0)
    load(1,1)
    execute_and_save(0,0)
    load(2,0)   # real logical replacement in SOFTWARE, after dirty save
    execute_and_save(1,1)
    execute_and_save(2,0)
    paging.advance_epoch(owner=owner)
    for logical in range(3):
        audit_page(paging.backing_snapshot(logical,owner=owner),
                   logical_id=logical,epoch=1)
    receipt=paging.receipt(owner=owner)
    require(receipt["page_loads"]==3 and receipt["page_saves"]==3
            and receipt["epoch"]==1 and
            receipt["slot_to_logical"]==[2,1],
            "source host-paged lifecycle not completed")
    return {
        "status":"M08_D3D3A_SOURCE_ONLY_M06_PAGE_GEOMETRY_AND_HOST_LEASE_PASS",
        "page_bytes":BYTES,
        "logical_contexts":3,
        "resident_slots":2,
        "original_32x4_m06_oracle_reused":True,
        "modeled_page_loads":receipt["page_loads"],
        "modeled_dirty_saves":receipt["page_saves"],
        "modeled_epoch":receipt["epoch"],
        "physical_ddr":False,
        "kernel_dma_buffer_owned":False,
        "hardware_page_swap_verified":False,
        "actual_neural_compute_performed":False,
        "directly_reuses_d3d2e_accepted_bitstream":False,
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-only",required=True,action="store_true")
    p.parse_args()
    try:
        print(json.dumps(demo(),indent=2,sort_keys=True))
        return 0
    except (PageReject,RuntimeError,AssertionError,ValueError) as exc:
        print("M08_D3D3A_SOURCE_PAGE_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
