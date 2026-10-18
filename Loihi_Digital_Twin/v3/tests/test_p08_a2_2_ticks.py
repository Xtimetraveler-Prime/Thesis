"""A2.2 host native C wire parity, corruption, cross-clock and scope guards.

Nothing here executes A53/KV260; passing != physical timing acceptance.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import re
import struct
import subprocess
import zlib

import pytest

from loihi_twin_v2.p08_a2_timing import parse_timing
from loihi_twin_v2.p08_a2_2_ticks import parse_ticks, CAPACITY, HEADER, RECORD, TICKS

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "software" / "p08"
C_SAMPLE = r"""
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "p08_a2_timing.h"
#include "p08_a2_2_ticks.h"
static uint8_t images[P08_A2_CAPACITY];
static uint8_t ticks[P08_A2_2_TICK_CAPACITY];
int main(int argc,char**argv)
{
    p08_a2_record image;
    p08_a2_2_tick tick;
    FILE *f;
    uint32_t frame,t;
    if(argc!=3)return 1;
    if(p08_a2_pack_header(images,256,2,1,2,P08_A2_OK_STATUS,
                          100000000u,90u,1100u))return 2;
    if(p08_a2_2_pack_header(ticks,256,2,1,2,
                           P08_A2_2_TICK_SUCCESS,
                           UINT32_C(0x12345678),
                           100000000u,90u,1105u))return 3;
    for(frame=0;frame<2u;++frame) {
        uint64_t base=frame==0u?100u:600u;
        memset(&image,0,sizeof(image));
        image.image_index=frame; image.flags=frame==1u?1u:0u;
        image.service_start=base; image.after_ingress=base+10u;
        image.after_neural=base+400u; image.after_commit=base+410u;
        image.pl_dispatch_cycles=2925u;
        image.ps_inference_ticks=200u; image.ps_control_ticks=240u;
        if(p08_a2_pack_record(images+256u+96u*frame,96u,&image))return 4;
        for(t=0u;t<26u;++t) {
            uint64_t start=base+12u+(uint64_t)t*9u;
            memset(&tick,0,sizeof(tick));
            tick.frame=frame;tick.tick=t;tick.external_events=t==25u?0u:10u;
            tick.emitted_packets=4u;tick.acknowledged_packets=4u;
            tick.flags=t==25u?1u:0u;
            tick.start=start;tick.after_encode=start+1u;
            tick.after_append=start+2u;tick.after_dispatch=start+3u;
            tick.after_trace=start+4u;tick.after_route=start+5u;
            tick.after_barrier=start+6u;
            tick.pl_dispatch_cycles=100u+t;
            if(p08_a2_2_pack_tick(ticks+256u+(frame*26u+t)*96u,96u,&tick))
                return 5;
        }
    }
    f=fopen(argv[1],"wb");if(!f)return 6;
    if(fwrite(images,1,sizeof(images),f)!=sizeof(images) || fclose(f))return 7;
    f=fopen(argv[2],"wb");if(!f)return 8;
    if(fwrite(ticks,1,sizeof(ticks),f)!=sizeof(ticks) || fclose(f))return 9;
    return 0;
}
"""


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory) -> tuple[bytes, bytes]:
    tmp_path = tmp_path_factory.mktemp("p08_a2_2_native")
    cc = shutil.which("cc")
    assert cc, "A2.2 native C test requires cc; installing C compiler is a gate"
    c = tmp_path / "test.c"
    executable = tmp_path / "test"
    images = tmp_path / "images.bin"
    ticks = tmp_path / "ticks.bin"
    c.write_text(C_SAMPLE)
    subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-I", str(SRC),
                    str(SRC/"p08_a2_timing.c"),
                    str(SRC/"p08_a2_2_ticks.c"),
                    str(c), "-o", str(executable)],
                   check=True, capture_output=True, text=True)
    subprocess.run([str(executable), str(images), str(ticks)],
                   check=True, capture_output=True, text=True)
    return images.read_bytes(), ticks.read_bytes()


def test_native_c_python_tick_parity_and_image_cycle_correlation(synthetic):
    image_bytes, tick_bytes = synthetic
    image = parse_timing(image_bytes, expected_count=2)
    run = parse_ticks(tick_bytes, image, expected_descriptor_crc32=0x12345678)
    assert run.count == 2 and run.trace_index == 1
    assert len(run.ticks) == 52 and run.hz == 100000000
    assert run.ticks[0].external_events == 10
    assert run.ticks[25].final_drain and run.ticks[25].external_events == 0
    assert run.ticks[26].frame == 1
    assert run.ticks[0].source_ticks == 1
    assert run.ticks[0].dispatch_wrapper_ticks == 1
    assert sum(t.pl_dispatch_cycles for t in run.ticks[:26]) == 2925


@pytest.mark.parametrize("mutation", [
    "truncated", "wrong_magic", "header_crc", "record_crc",
    "status", "count", "frequency", "descriptor", "wrong_trace",
    "record_frame", "record_tick", "event_overflow", "drain_events",
    "drain_flag", "timer_order", "cycles", "tail", "wrong_a2_1_clock",
])
def test_tick_corruption_and_cross_source_mismatch_fail_closed(synthetic, mutation):
    image_bytes, tick_bytes = synthetic
    ticks = bytearray(tick_bytes)
    if mutation == "truncated":
        ticks.pop()
    elif mutation == "wrong_magic":
        ticks[0] ^= 1
    elif mutation == "header_crc":
        ticks[252] ^= 1
    elif mutation == "record_crc":
        ticks[256+88] ^= 1
    elif mutation == "tail":
        ticks[-1] = 1
    else:
        if mutation == "status":
            struct.pack_into("<I", ticks, 16, 0)
        elif mutation == "count":
            struct.pack_into("<I", ticks, 24, 3)
        elif mutation == "frequency":
            struct.pack_into("<Q", ticks, 32, 99999001)
        elif mutation == "descriptor":
            struct.pack_into("<I", ticks, 52, 0xDEADBEEF)
        elif mutation == "wrong_trace":
            struct.pack_into("<I", ticks, 56, 0)
        elif mutation == "record_frame":
            struct.pack_into("<I", ticks, 256, 1)
        elif mutation == "record_tick":
            struct.pack_into("<I", ticks, 256+4, 2)
        elif mutation == "event_overflow":
            struct.pack_into("<I", ticks, 256+8, 785)
        elif mutation == "drain_events":
            struct.pack_into("<I", ticks, 256+25*96+8, 1)
        elif mutation == "drain_flag":
            struct.pack_into("<I", ticks, 256+25*96+20, 0)
        elif mutation == "timer_order":
            struct.pack_into("<Q", ticks, 256+40, 12)
        elif mutation == "cycles":
            struct.pack_into("<Q", ticks, 256+80, 9000)
        elif mutation == "wrong_a2_1_clock":
            image_bytes = bytearray(image_bytes)
            struct.pack_into("<Q", image_bytes, 32, 100000001)
            struct.pack_into("<I", image_bytes, 252,
                             zlib.crc32(image_bytes[:252]))
        if mutation in ("status", "count", "frequency", "descriptor", "wrong_trace"):
            struct.pack_into("<I", ticks, 252, zlib.crc32(ticks[:252]))
        elif mutation not in ("wrong_a2_1_clock",):
            off=256 + (25*96 if mutation in ("drain_events","drain_flag") else 0)
            struct.pack_into("<I", ticks, off+88, zlib.crc32(ticks[off:off+88]))
    image=parse_timing(bytes(image_bytes), expected_count=2)
    with pytest.raises(ValueError):
        parse_ticks(bytes(ticks),image,expected_descriptor_crc32=0x12345678)


def test_unchanged_accepted_runtime_and_32bit_reserved_ddr():
    p07=(ROOT/"software/p07/p07_a2_runtime.c").read_text()
    p08=(SRC/"p08_a2_2_runtime.c").read_text()
    assert "int p07_a2_run_frame" in p07
    assert "int p08_a2_2_run_frame" in p08
    assert "p07_a1_tick_events" in p07 and "p07_a1_tick_events" in p08
    assert "underlying.dispatch" in p07 and "underlying.dispatch" in p08
    assert "P08_A2_2_PER_TICK_KV260_A53_CANDIDATE_V1" in (SRC/"p08_a2_2_board.c").read_text()
    assert "p08_a2_2_run_frame" in (SRC/"p08_a2_2_board.c").read_text()
    assert "p07_a2_run_frame" not in (SRC/"p08_a2_2_board.c").read_text()
    assert HEADER + RECORD*TICKS*1024 <= CAPACITY
    assert 0x43100000+CAPACITY <= 0x43F00000
    builder=(ROOT/"scripts/build_p08_a2_2.sh").read_text()
    assert "P08_A2_2_BUILD_DIR" in builder
    assert "P03_DIAG_REPORTS" in builder
    assert "P08_A2_2_PER_TICK_KV260_A53_CANDIDATE_V1" in builder


def test_a2_2_build_shell_syntax_and_collector_consent():
    script=ROOT/"scripts/build_p08_a2_2.sh"
    out=subprocess.run(["bash","-n",str(script)],text=True,
                       capture_output=True)
    assert out.returncode == 0,out.stderr
    xsdb=(ROOT/"vivado/p08_a2_2_xsdb_run.tcl").read_text()
    assert "P08_A2_CONFIRM_KV260_JTAG_ONLY" in xsdb
    assert "P08_A2_CONFIRM_VALIDATION_ONLY" in xsdb
    assert "0x43100000 786432" in xsdb
    assert "TERMINAL_ALL_THREE_SUCCESS_UNVERIFIED_NUMERICS" in xsdb
