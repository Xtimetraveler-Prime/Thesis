#!/usr/bin/env python3
"""Exact independent M06 32-neuron signed16 CONFIG → 3 host-page images.

Each 256B host-staged AXI bank is 64x32-bit little-endian:
  [0..59] 15 neurons x (initial_v, bias, threshold, reset_v), full signed16
  [60] M6PG magic; [61] logical page index; [62] resident valid neurons
  [63] reserved hardware compute-probe XOR output, initially zero.
Hence original 32 M06 neurons occupy 3 *logical* pages: 15,15,2 while the
RTL probe has ONE physical resident bank. This is genuinely neural SOURCE
DATA, unlike the earlier 4KiB *reference* page containing golden outputs.
The probe does NOT perform neural calculations: it scans 63 words and
writes a checksum to word63. No DDR, no DMA, no physical bitstream proof.
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
import m08_d3d2d_event_vectors as original

NEURONS=32
PAGE_NEURONS=15
PAGES=3
WORDS=64
BYTES=WORDS*4
MAGIC=0x4D365047  # M6PG
FIRST_METADATA_WORD=60
PROBE_RESULT_WORD=63

class Reject(ValueError):
    pass

def require(ok:bool,reason:str)->None:
    if not ok:
        raise Reject(reason)

def oracle():
    words=original.words()
    require(len(words)==630 and words[:3]==("D2C00001","00000003","00000005"),
            "original M06 32-neuron G3.3 reference changed")
    return tuple(int(x,16) for x in words)

def valid_neurons(page_index:int)->int:
    require(type(page_index) is int and 0<=page_index<PAGES,
            "invalid original M06 logical page ID")
    return min(PAGE_NEURONS,NEURONS-page_index*PAGE_NEURONS)

def parameter_words(page_index:int)->tuple[int,...]:
    count=valid_neurons(page_index)
    src=oracle()
    out=[0]*WORDS
    for local in range(count):
        n=page_index*PAGE_NEURONS+local
        for field in range(4):
            out[local*4+field]=src[3+n*8+field]
    out[60:63]=[MAGIC,page_index,count]
    return tuple(out)

def expected_probe_result(words:tuple[int,...])->int:
    require(len(words)==WORDS and all(type(x) is int and 0<=x<2**32 for x in words),
            "malformed 64-word parameter page")
    value=0
    for w in words[:63]:
        value ^= w
    return value

def image(page_index:int)->bytes:
    return struct.pack("<64I",*parameter_words(page_index))

def audit(image_bytes:bytes,page_index:int,*,post_compute:bool=False)->dict:
    expected=parameter_words(page_index)
    require(type(image_bytes) is bytes and len(image_bytes)==BYTES,
            "wrong type or size of neuron parameter page")
    actual=struct.unpack("<64I",image_bytes)
    require(actual[:63]==expected[:63],
            "neuron signed16 configuration, logical ID or reserved bytes differ")
    checksum=expected_probe_result(expected)
    if post_compute:
        require(actual[63]==checksum,
                "probe wrote wrong XOR readback or wrote no result")
    else:
        require(actual[63]==0,"nonzero uninitialized compute-probe result word")
    return {
        "logical_page":page_index,
        "valid_neurons":valid_neurons(page_index),
        "first_neuron":page_index*PAGE_NEURONS,
        "last_neuron_exclusive":min(NEURONS,(page_index+1)*PAGE_NEURONS),
        "page_sha256":sha256(image_bytes).hexdigest(),
        "expected_probe_xor":f"{checksum:08X}",
        "post_compute_probe_only":post_compute,
        "actual_neural_results_computed":False,
        "hardware_page_programmed":False,
        "physical_ddr_verified":False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only",action="store_true",required=True)
    args=parser.parse_args()
    receipts=[]
    for page in range(PAGES):
        b=image(page)
        receipts.append(audit(b,page))
    print(json.dumps({
        "status":"M08_PAGED_M06_SIGNED16_32_NEURONS_3_LOGICAL_1_RESIDENT_SOURCE_ONLY",
        "layout":"64x32 little-endian, 60 config, 3 metadata, 1 writeback",
        "logical_contexts":PAGES,
        "physical_rtl_resident_slots":1,
        "m06_total_neurons":sum(r["valid_neurons"] for r in receipts),
        "pages":receipts,
        "neural_execution_verified":False,
        "physical_ddr_verified":False,
    },indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
