"""Host-native P08-A2.1 wire ABI parity, corruption and isolation tests.

No board, no TEST partition, no Vitis required.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

from loihi_twin_v2.p08_a2_timing import (
    CAPACITY, HEADER_BYTES, RECORD_BYTES, parse_timing,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "software" / "p08"

HARNESS = r"""
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "p08_a2_timing.h"
static uint8_t bytes[P08_A2_CAPACITY];
int main(int argc, char **argv) {
    FILE *file;
    p08_a2_record r;
    if(argc!=2) return 5;
    if(p08_a2_pack_header(bytes, P08_A2_HEADER_BYTES, 2, 1, 2,
         P08_A2_OK_STATUS, 100000000u, 90u, 900u)!=0) return 6;
    memset(&r,0,sizeof(r));
    r.image_index=0;
    r.service_start=100; r.after_ingress=110;
    r.after_neural=300; r.after_commit=350;
    r.pl_dispatch_cycles=1110; r.pl_page_cycles=2500;
    r.ps_inference_ticks=170; r.ps_control_ticks=190;
    r.ps_route_ticks=30; r.ps_barrier_ticks=20;
    if(p08_a2_pack_record(bytes+256,96,&r)!=0) return 7;
    r.image_index=1; r.flags=1;
    r.service_start=400; r.after_ingress=430;
    r.after_neural=800; r.after_commit=830;
    r.pl_dispatch_cycles=3333; r.pl_page_cycles=2400;
    r.ps_inference_ticks=350; r.ps_control_ticks=360;
    if(p08_a2_pack_record(bytes+352,96,&r)!=0) return 8;
    file=fopen(argv[1],"wb");
    if(!file) return 9;
    if(fwrite(bytes,1,sizeof(bytes),file)!=sizeof(bytes)) return 10;
    if(fclose(file)) return 11;
    return 0;
}
"""


@pytest.fixture
def fixture_binary(tmp_path: Path) -> bytes:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.fail("cc compiler required for P08-A2 native C/Python parity gate")
    harness = tmp_path / "codec.c"
    binary = tmp_path / "codec"
    raw = tmp_path / "timing.bin"
    harness.write_text(HARNESS)
    subprocess.run([
        compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-I", str(SRC), str(SRC / "p08_a2_timing.c"),
        str(harness), "-o", str(binary),
    ], check=True, capture_output=True, text=True)
    subprocess.run([str(binary), str(raw)], check=True, capture_output=True)
    return raw.read_bytes()


def test_portable_c_to_python_decoder_parity(fixture_binary: bytes):
    run = parse_timing(fixture_binary, expected_count=2)
    assert run.count == 2
    assert run.trace_index == 1
    assert run.cntfrq_hz == 100000000
    assert run.dataset_start == 90 and run.dataset_stop == 900
    assert [r.index for r in run.records] == [0, 1]
    assert [r.service_ticks for r in run.records] == [250, 430]
    assert [r.selected_trace for r in run.records] == [False, True]
    assert [r.pl_dispatch_cycles for r in run.records] == [1110, 3333]
    assert run.throughput_frames_per_second == pytest.approx(2 * 100000000 / 810)


@pytest.mark.parametrize("change", [
    "length", "magic", "header_crc", "record_crc", "tail", "status",
    "count", "timer_order", "selected_trace", "record_index", "timer_freq",
])
def test_fail_closed_corrupt_timing(fixture_binary: bytes, change: str):
    raw = bytearray(fixture_binary)
    if change == "length":
        raw.pop()
    elif change == "magic":
        raw[0] ^= 1
    elif change == "header_crc":
        raw[252] ^= 1
    elif change == "record_crc":
        raw[256+88] ^= 1
    elif change == "tail":
        raw[-1] = 1
    else:
        if change == "status":
            struct.pack_into("<I", raw, 16, 0)
        elif change == "count":
            struct.pack_into("<I", raw, 24, 3)
        elif change == "timer_order":
            struct.pack_into("<Q", raw, 256+24, 50)
        elif change == "selected_trace":
            struct.pack_into("<I", raw, 256+4, 1)
        elif change == "record_index":
            struct.pack_into("<I", raw, 256, 17)
        elif change == "timer_freq":
            struct.pack_into("<Q", raw, 32, 0)
        if change in ("status", "count", "timer_freq"):
            struct.pack_into("<I", raw, 252, zlib.crc32(raw[:252]))
        else:
            struct.pack_into("<I", raw, 256+88, zlib.crc32(raw[256:256+88]))
    with pytest.raises(ValueError):
        parse_timing(bytes(raw), expected_count=2)


def test_no_changes_to_frozen_p07_and_safe_layout():
    original = (ROOT/"software/p07/p07_a4_board.c").read_text()
    candidate = (SRC/"p08_a2_board.c").read_text()
    assert "P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1" in original
    assert "P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1" not in candidate
    assert "P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1" in candidate
    assert "p07_a2_run_frame(ingress,sizeof(ingress),driver,&res)" in candidate
    assert "p07_a4_pack_result(&obj,buf,sizeof(buf))" in candidate
    assert "0x43000000" in (SRC/"p08_a2_timing.h").read_text()
    assert HEADER_BYTES+10000*RECORD_BYTES <= CAPACITY
    build = (ROOT/"scripts/build_p08_a2.sh").read_text()
    assert "P03_DIAG_REPORTS" in build
    assert "P08_A2_BUILD_DIR" in build
    assert "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f" in build
    assert "0x44000000" in build and "0x40000000" in build
    assert "run_p07_a4_official_physical" not in build


def test_new_shell_passes_static_parse():
    x = subprocess.run(["bash", "-n", str(ROOT/"scripts/build_p08_a2.sh")],
                       capture_output=True, text=True)
    assert x.returncode == 0, x.stderr
