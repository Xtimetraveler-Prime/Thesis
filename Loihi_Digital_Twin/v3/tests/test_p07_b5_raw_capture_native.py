"""B5.3.1: compile and test actual new 26x1010 P03 bank7 RAW C serializer.

HOST/NATIVE ONLY: synthetic trace words are **not** FPGA provenance.
Original signed frozen model, accepted V3 ELF/P03/HLS and official TEST untouched.
"""
from __future__ import annotations

import ctypes as ct
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
INC=ROOT/"software/p07/include"
SOURCE=ROOT/"software/p07/p07_b5_raw_capture.c"
CORES=27
NEURONS=1010
TICKS=26
WORD_CAP=210080
BYTES=840320
PASS=0
INVALID=-1
ORDER=-2
RESERVED=-3
INCOMPLETE=-4

class Recorder(ct.Structure):
    _fields_=[
        ("magic",ct.c_uint32),("active",ct.c_uint32),
        ("fault",ct.c_uint32),("finished",ct.c_uint32),
        ("word_capacity",ct.c_uint32),("next_record",ct.c_uint32),
        ("core_prefix",ct.c_uint32*CORES),
        ("core_compartments",ct.c_uint16*CORES),
        ("ddr_words",ct.POINTER(ct.c_uint32)),
    ]

@pytest.fixture(scope="module")
def c(tmp_path_factory):
    cc=shutil.which("cc")
    if not cc:
        pytest.skip("native C compiler unavailable: standalone C checks not run")
    tmp=tmp_path_factory.mktemp("b5_native_raw_capture")
    binary=tmp/"libp07_b5_raw_capture.so"
    subprocess.run([cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
                    "-shared","-fPIC","-I",str(INC),
                    str(SOURCE),"-o",str(binary)],check=True)
    lib=ct.CDLL(str(binary))
    lib.p07_b5_capture_begin.argtypes=[
        ct.POINTER(Recorder),ct.POINTER(ct.c_uint32),ct.c_size_t,
        ct.POINTER(ct.c_uint16)]
    lib.p07_b5_capture_begin.restype=ct.c_int
    lib.p07_b5_capture_record.argtypes=[
        ct.POINTER(Recorder),ct.c_uint32,ct.c_uint32,ct.c_uint32,
        ct.POINTER(ct.c_uint32)]
    lib.p07_b5_capture_record.restype=ct.c_int
    lib.p07_b5_capture_finalize.argtypes=[ct.POINTER(Recorder)]
    lib.p07_b5_capture_finalize.restype=ct.c_int
    return lib

@pytest.fixture()
def valid():
    # 25 original-sized hidden cores plus one remaining hidden core and
    # exactly 10 readout compartments. This is a synthetic ONLY geometry.
    counts=(ct.c_uint16*CORES)(*([38]*25+[50,10]))
    memory=(ct.c_uint32*(WORD_CAP+2))()
    memory[0]=0xBADC0FFE
    memory[-1]=0xFEE1DEAD
    pointer=ct.cast(ct.byref(memory,4),ct.POINTER(ct.c_uint32))
    return counts,memory,pointer

def sample_word(idx):
    return (ct.c_uint32*8)(
        idx&0xffffffff,0x3,
        0xFFFFFFFF,0xFFFFFFFF,
        (idx*3)&0xffffffff,0xAABBCCDD,
        idx&1,0,
    )

def test_native_full_26tick_1010_neuron_840320_exact_byte_abi(c,valid):
    counts,memory,ptr=valid
    recorder=Recorder()
    assert c.p07_b5_capture_begin(ct.byref(recorder),ptr,WORD_CAP,counts)==PASS
    assert recorder.magic==0x42354331
    assert recorder.word_capacity==WORD_CAP
    assert recorder.next_record==0
    assert memory[0]==0xBADC0FFE and memory[-1]==0xFEE1DEAD
    assert ptr[0]==0 and ptr[WORD_CAP-1]==0
    prefix=0
    expected=bytearray()
    for tick in range(TICKS):
        prefix=0
        for core in range(CORES):
            for compartment in range(counts[core]):
                idx=tick*NEURONS+prefix+compartment
                word=sample_word(idx)
                assert c.p07_b5_capture_record(
                    ct.byref(recorder),tick,core,compartment,word
                )==PASS
                expected.extend(struct.pack("<8I",*word))
            prefix+=counts[core]
    assert len(expected)==BYTES
    assert recorder.next_record==TICKS*NEURONS
    assert c.p07_b5_capture_finalize(ct.byref(recorder))==PASS
    assert recorder.finished==1 and recorder.active==0
    observed=ct.string_at(ct.addressof(memory)+4,BYTES)
    assert observed==bytes(expected)
    assert hashlib.sha256(observed).digest()==hashlib.sha256(expected).digest()
    assert memory[0]==0xBADC0FFE and memory[-1]==0xFEE1DEAD
    assert c.p07_b5_capture_record(
        ct.byref(recorder),25,26,9,sample_word(26259)
    )==INVALID

@pytest.mark.parametrize("offset,override,expect",[
    (0,(0,0,1),ORDER),          # first expected compartment omitted
    (0,(1,0,0),ORDER),          # skipped full tick
    (0,(0,26,0),ORDER),         # skipped first 26 cores
    (1,(0,0,0),ORDER),          # repeated record 0
    (0,(26,0,0),ORDER),         # tick out of range
    (0,(0,27,0),ORDER),         # core out of range
    (0,(0,0,1024),ORDER),       # compartment out of range
])
def test_capture_refuses_skipped_duplicate_or_out_of_range(c,valid,offset,override,expect):
    counts,memory,ptr=valid
    r=Recorder()
    assert c.p07_b5_capture_begin(ct.byref(r),ptr,WORD_CAP,counts)==PASS
    if offset:
        assert c.p07_b5_capture_record(ct.byref(r),0,0,0,sample_word(0))==PASS
    before=(memory[0],memory[2],memory[-1])
    assert c.p07_b5_capture_record(
        ct.byref(r),*override,sample_word(22)
    )==expect
    assert r.fault !=0 and r.active==0
    assert c.p07_b5_capture_finalize(ct.byref(r))==INVALID
    assert (memory[0],memory[2],memory[-1])==before

@pytest.mark.parametrize("bad,expected",[
    ((0,0,0,0,0,0,2,0),RESERVED),
    ((0,0,0,0,0,0,0,1),RESERVED),
    ((0,0,0,0,0,0,0xffffffff,0),RESERVED),
])
def test_capture_rejects_trace_reserved_bit_corruption(c,valid,bad,expected):
    counts,memory,ptr=valid
    r=Recorder()
    assert c.p07_b5_capture_begin(ct.byref(r),ptr,WORD_CAP,counts)==PASS
    words=(ct.c_uint32*8)(*bad)
    assert c.p07_b5_capture_record(ct.byref(r),0,0,0,words)==expected
    assert r.active==0 and r.fault!=0
    assert ptr[0]==0 and ptr[7]==0

def test_capture_unfinished_failure_and_no_overread(c,valid):
    counts,memory,ptr=valid
    r=Recorder()
    assert c.p07_b5_capture_begin(ct.byref(r),ptr,WORD_CAP,counts)==PASS
    assert c.p07_b5_capture_record(ct.byref(r),0,0,0,sample_word(0))==PASS
    assert c.p07_b5_capture_finalize(ct.byref(r))==INCOMPLETE
    assert r.fault!=0 and r.finished==0
    assert memory[0]==0xBADC0FFE and memory[-1]==0xFEE1DEAD

@pytest.mark.parametrize("broken_counts",[
    [38]*25+[50,11],   # 1011 total / different readout core
    [38]*25+[49,10],   # 1009 total
    [38]*25+[50,0],    # invalid readout zero
    [0]+[38]*24+[50,10],
])
def test_capture_fails_closed_on_invalid_frozen_compartment_metadata(c,valid,broken_counts):
    _,memory,ptr=valid
    counts=(ct.c_uint16*CORES)(*broken_counts)
    r=Recorder()
    assert c.p07_b5_capture_begin(ct.byref(r),ptr,WORD_CAP,counts)==INVALID
    assert r.next_record==0
    assert memory[0]==0xBADC0FFE and memory[-1]==0xFEE1DEAD

def test_capture_requires_exact_capacity_and_aligned_buffer(c,valid):
    counts,memory,ptr=valid
    r=Recorder()
    assert c.p07_b5_capture_begin(ct.byref(r),ptr,WORD_CAP-1,counts)==INVALID
    wrong_align=ct.cast(ct.byref(memory,5),ct.POINTER(ct.c_uint32))
    assert c.p07_b5_capture_begin(
        ct.byref(r),wrong_align,WORD_CAP,counts
    )==INVALID

def test_capture_source_versioned_and_bounded_to_disjoint_candidate_ddr_region():
    header=(INC/"p07_b5_raw_capture.h").read_text()
    code=SOURCE.read_text()
    assert "0x42000000" in header
    assert "0x420CD280" in code
    assert "840320u" in code
    assert "P07_B5_CAPTURE_TICKS 26u" in header
    assert "P07_B5_CAPTURE_NEURONS 1010u" in header
    assert "P07_B5_CAPTURE_RECORDS" in code
    assert "P07_B5_CAPTURE_RESERVED" in code
    assert "P07_B5_CAPTURE_INCOMPLETE" in code
    assert "NOT physically executed" in header
    # Non-overlap is only for the accepted original P02/stage/route/mailbox
    # ranges; NOT an assertion of other boot owners or DDR exclusivity.
    ranges=[
        (0x40000000,0x40D80000), # 27 x original 512KiB P02 records
        (0x41000000,0x410E0000), # 896KiB input routes
        (0x41100000,0x411E0000), # maximally accepted original TRAIN frame
        (0x43FC0000,0x43FC4000), # 16KiB original binding descriptor
        (0x43FC4000,0x43FD8000), # 80KiB original output routing
        (0x43FF0000,0x43FF0100), # 256B original V3 mailbox
    ]
    candidate=(0x42000000,0x420CD280)
    assert candidate[1]-candidate[0]==BYTES
    assert all(candidate[1]<=start or candidate[0]>=end for start,end in ranges)
