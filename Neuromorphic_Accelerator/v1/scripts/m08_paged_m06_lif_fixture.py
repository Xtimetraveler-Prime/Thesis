#!/usr/bin/env python3
"""M08.4 independently derived original M06 32x4 paged-LIF *input* fixtures.

Single real RTL resident bank = 64x32-bit (256B). Six logical neuron pages
carry 6+6+6+6+6+2 neurons; every 10-word neuron record:
  0 current signed16 membrane, 1 bias signed16, 2 threshold signed16,
  3 reset signed16, 4..7 four signed32 external input-current buckets,
  8 four-bit historical spike mask, 9 last signed32 hardware synaptic current.
Page words 60..63 = M6NF magic, page ID, count, current tick.
An extra source-only EDGE CONFIG page carries eight pre/post/weight/delay
slots and M6EG magic, id 0xFFFFFFFF, count=5, tick=0.
Original M02/M03-independent golden output words are stored ONLY in an
external comparison fixture, NEVER supplied to FPGA state pages.
External raw events are currently host-coalesced before staging, unlike
already physically accepted on-fabric M32Q raw event queue. This code does
NOT prove paged real K26, physical DDR or M06 original HLS execution.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import struct
import sys
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_vectors as m06
import m08_d3d2d_event_vectors as raw

NEURONS=32
TICKS=4
EDGES=5
EVENTS=17
PER_PAGE=6
PAGES=6
WORDS=64
BYTES=256
MAGIC_NEURAL=0x4D364E46 # M6NF
MAGIC_EDGES=0x4D364547 # M6EG
EDGE_ID=0xFFFFFFFF
WORD_STATE=0
WORD_BIAS=1
WORD_THRESHOLD=2
WORD_RESET=3
WORD_EXTERNAL=4
WORD_SPIKES=8
WORD_SYN_LAST=9
HEADER=60

class Reject(ValueError):
    pass

def require(ok:bool,reason:str):
    if not ok: raise Reject(reason)

def source():
    original=raw.words()
    require(len(original)==630 and original[:3]==("D2C00001","00000003","00000005"),
            "original signed16 independent M02/M03 M06 G3.3 fixture drift")
    network,events,external,voltages,masks,syn=m06.golden()
    require(len(network.neurons)==NEURONS and
            len(network.synapses)==EDGES and len(events)==EVENTS and
            network.decay_num==3 and network.decay_den==4 and
            network.state_bits==16,"original M06 original neural ABI changed")
    for t in range(TICKS):
        require(sum(ev.tick==t for ev in events)==(5,5,4,3)[t],
                "original raw input tick distribution changed")
    return tuple(int(w,16) for w in original),network,events,external,voltages,masks,syn

def neurons_in_page(page:int)->int:
    require(type(page) is int and 0<=page<PAGES,"invalid M06 logical neuron page")
    return min(PER_PAGE,NEURONS-page*PER_PAGE)

def neural_words(page:int,tick:int=0)->tuple[int,...]:
    count=neurons_in_page(page)
    require(type(tick) is int and 0<=tick<TICKS,"page tick invalid")
    src,*_=source()
    output=[0]*WORDS
    for local in range(count):
        n=page*PER_PAGE+local
        offset=3+n*8
        base=local*10
        output[base:base+4]=src[offset:offset+4]
        output[base+4:base+8]=src[offset+4:offset+8]
        # Spikes/current NOT preloaded from golden. Updated by real RTL.
        output[base+8]=0
        output[base+9]=0
    output[60:64]=[MAGIC_NEURAL,page,count,tick]
    return tuple(output)

def edge_words()->tuple[int,...]:
    src,*_=source()
    output=[0]*WORDS
    output[:32]=src[259:291]
    output[60:64]=[MAGIC_EDGES,EDGE_ID,EDGES,0]
    return tuple(output)

def golden_words()->tuple[int,...]:
    src,net,ev,external,volts,masks,syn=source()
    output=[]
    for tick in range(TICKS):
        for n in range(NEURONS):
            output.extend((
                m06.u32(external[n][tick]),
                m06.u32(volts[n][tick]),
                m06.u32((masks[n]>>tick)&1),
                m06.u32(syn[n][tick]),
            ))
    require(len(output)==512,"exact independent 512 numerical oracle geometry drift")
    return tuple(int(x,16) for x in output)

def audit_page(words:tuple[int,...],page:int,tick:int,*,post_compute:bool=False):
    count=neurons_in_page(page)
    require(type(words) is tuple and len(words)==WORDS and
            all(type(w) is int and 0<=w<2**32 for w in words),
            "neural page must be 64 unsigned32 words")
    original=neural_words(page,tick)
    require(words[60:64]==original[60:64],"neural logical ID, tick, count or magic mismatch")
    for local in range(count):
        base=local*10
        # Only state (0), spike history (8), delivered current (9) can
        # change on a compute update. ALL configuration and inputs frozen.
        for field in (1,2,3,4,5,6,7):
            require(words[base+field]==original[base+field],
                    "original M06 parameter/current input was changed")
        if not post_compute:
            for field in (0,8,9):
                require(words[base+field]==original[base+field],
                        "uncomputed page prefilled with expected neural outputs")
    require(words[count*10:60]==(0,)*(60-count*10),
            "inactive logical neuron slots must be zero")
    return True

def write_hex(out:Path,words:tuple[int,...]):
    # Used only from a unit test's exclusive temporary directory, not
    # immutable historical owner evidence.
    require(out.parent.is_dir() and not out.exists() and not out.is_symlink(),
            "new file in existing owned output directory required")
    with out.open("x",encoding="ascii") as handle:
        handle.write("".join(f"{w:08X}\n" for w in words))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-only",action="store_true",required=True)
    a=p.parse_args()
    _,net,events,ext,volts,masks,syn=source()
    pages=[neural_words(n) for n in range(PAGES)]
    golden=golden_words()
    print(json.dumps({
        "status":"M08_M06_SIGNED16_PAGED_LIF_FIXTURE_PC_ONLY_NOT_HARDWARE",
        "neuron_count":NEURONS,"ticks":TICKS,"recurrent_edges":EDGES,
        "original_raw_events":EVENTS,"logical_neuron_pages":PAGES,
        "resident_bank_pages_in_candidate_rtl":1,
        "neurons_per_page":[neurons_in_page(n) for n in range(PAGES)],
        "expected_total_numerical_comparisons":len(golden),
        "input_events_host_coalesced":True,
        "golden_trace_not_loaded_into_neuron_pages":True,
        "physical_paged_neural_execution_verified":False,
        "physical_ddr":False,
        "page_sha256":[sha256(struct.pack("<64I",*w)).hexdigest() for w in pages]
    },indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
