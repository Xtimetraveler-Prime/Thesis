"""P08-B3 pilot16 new source, original 1024 raw auth, offline DDR plan."""
from __future__ import annotations
from pathlib import Path
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import struct

import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"software/p08"))
import build_p08_b3_pilot16 as pilot_builder
import build_p08_b2_3_image_only as original_builder
import p08_b3_pilot16_admission as gate
import p08_b3_pilot16_stage_host as staging
import p08_b2_3_elf_admission as elf_gate
import p08_b2_4_scalar_first16 as scalar
import p08_b2_2_prepare_reset_pins as pins


def test_pilot16_binary_source_distinct_from_1024_and_raw_sha_full():
    pilot=(ROOT/"software/p08/p08_b3_pilot16_a53.c").read_text()
    full=(ROOT/"software/p08/p08_b2_3_image_only_a53.c").read_text()
    assert pilot_builder.IDENTITY in pilot
    assert original_builder.IDENTITY in full
    assert original_builder.IDENTITY not in pilot
    assert "#define B23_FRAMES 16u" in pilot
    assert "#define B23_RAW_POOL_BYTES (1024u*784u)" in pilot
    assert "#define B23_RAW_POOL_BYTES (B23_FRAMES*784u)" in full
    assert "P08_B3_PILOT16_TERMINAL_DONE=1" in pilot
    assert "P08_B2_3_IMAGE_ONLY_1024_TERMINAL_DONE=1" in full
    assert "for(index=0u;index<B23_FRAMES;index++)" in pilot
    assert "sha_ok(raw,B23_RAW_POOL_BYTES,accepted_raw_pool_sha)" in pilot
    for stable in (
        "p08_b2_reset_image(", "p08_b2_encode_frame(",
        "p07_b4m_full_run(", "p08_b2_meter_start(",
        "P08_B2_AFTER_JOURNAL_COMMIT", "commit_timing(",
        "P07_B4M_ROUTE_IN_BASE", "P03_HW_BACKING_BASE"):
        assert stable in pilot
    assert pilot.count("p07_b4m_full_run(")==1


def test_pilot16_builder_distinct_source_and_dest():
    assert pilot_builder.APP != original_builder.APP
    assert pilot_builder.PLATFORM != original_builder.PLATFORM
    assert pilot_builder.SOURCES[0] == "p08_b3_pilot16_a53.c"
    assert pilot_builder.SOURCES[1:] == original_builder.SOURCES[1:]
    assert pilot_builder.HEADERS == original_builder.HEADERS
    assert "p07_b4m_full_board_diag_v3.c" not in pilot_builder.SOURCES
    script=ROOT/"scripts/build_p08_b3_pilot16.sh"
    s=script.read_text()
    assert "xsdb " not in s
    assert "vivado -mode batch" not in s
    assert "p08_b3_pilot16_admission.py" in s
    assert "p08_b3_pilot16_a53.c" in s
    assert "P08_B3_PILOT16_BUILD_DIR" in s
    assert "P08_B2_4_SCALAR_REPORT" in s
    subprocess.run(["bash","-n",str(script)],check=True,capture_output=True,text=True)


def test_pilot16_static_ddr_all_sources_six_write_targets_nonoverlap():
    rows=staging.plan_locations()
    assert len(rows)==6
    assert len({x["filename"] for x in rows})==5
    assert all(x["physical_write_authorized"] is False for x in rows)
    assert all(x["physical_readback_required"] is True for x in rows)
    by_start={x["DDR_destination_start"]:x for x in rows}
    assert by_start["0x43000000"]["bytes"]==27*512*1024
    assert by_start["0x40000000"]["source_sha256"]==by_start["0x43000000"]["source_sha256"]
    assert by_start["0x42100000"]["bytes"]==1024*784
    assert by_start["0x41000000"]["bytes"]==0xE0000


def test_reference_oracle_must_pin_operator_real_original_first16(tmp_path):
    fake=tmp_path/"untrusted-oracle.json"
    fake.write_text("{}")
    with pytest.raises(gate.PilotNoGo):
        gate.source_oracle(fake)
    assert gate.ORACLE_SHA=="13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271"
    assert gate.FULL_1024_SHA=="0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"


def test_prohibit_original_1024_elf_in_pilot_admission(tmp_path,monkeypatch):
    # Fake oracle bytes are test-only; even with an oracle helper stub,
    # the full 1024 ELF must be denied before any PT_LOAD inspection.
    monkeypatch.setattr(gate,"source_oracle",lambda path: {"frames":[{"TRAIN_source_index":i} for i in range(16)]})
    monkeypatch.setattr(gate,"sha",lambda path: (
        elf_gate.EXPECTED_XSA_SHA if path.name=="accepted.xsa" else
        elf_gate.EXPECTED_PINS_SHA if path.name=="original.h" else
        "d"*64))
    elf=tmp_path/"full1024.elf";elf.write_bytes(
        gate.FULL_1024_ID+b"no bounded pilot marker")
    m=tmp_path/"pilot.map";m.write_text("Linker script and memory map")
    x=tmp_path/"accepted.xsa";x.write_bytes(b"XSA")
    h=tmp_path/"original.h";h.write_text("27")
    with pytest.raises(gate.PilotNoGo):
        gate.analyse(elf,m,x,h,tmp_path/"nooracle",tmp_path/"new.json")


def test_pilot16_staging_sha_source_sentinels():
    assert staging.EXPECTED_SHA[staging.FILES[0][0]]==(
        "3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e")
    assert staging.EXPECTED_SHA[staging.FILES[4][0]]==scalar.RAW_POOL_SHA
    assert staging.EXPECTED_SHA[staging.FILES[2][0]]==(
        "380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8")
    assert staging.PLAN_FILE.endswith(".json")


def test_pilot16_source_strict_native_syntax_with_stub_xilinx(tmp_path):
    compiler=shutil.which("cc")
    assert compiler,"native C11 compiler required"
    source=(ROOT/"software/p08/p08_b3_pilot16_a53.c")
    include=tmp_path/"isolated_staged_headers"
    include.mkdir()
    for name in pilot_builder.HEADERS:
        if name=="p08_b2_2_original_context_sha256.h":
            rows=[{"logical_core_id":n,
                   "sha256":hashlib.sha256(bytes([n])).hexdigest()}
                  for n in range(27)]
            data=pins.generate_header(rows)
        elif (ROOT/"software/p08"/name).is_file():
            data=(ROOT/"software/p08"/name).read_text()
        elif (ROOT/"software/p07/include"/name).is_file():
            data=(ROOT/"software/p07/include"/name).read_text()
        elif (ROOT/"software/p03/include"/name).is_file():
            data=(ROOT/"software/p03/include"/name).read_text()
        else:
            data=(ROOT/"software/p05/include"/name).read_text()
        if name=="p07_b2_packet.h":
            assert "#define P07_B2_MAX_ROUTE_BINDINGS 8192u" in data
            data=data.replace("#define P07_B2_MAX_ROUTE_BINDINGS 8192u",
                              "#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        (include/name).write_text(data)
    (include/"xil_cache.h").write_text(
        "#ifndef FAKE_XIL_CACHE_H\n#define FAKE_XIL_CACHE_H\n"
        "#include <stdint.h>\n#include <stddef.h>\n"
        "typedef uintptr_t INTPTR;\n"
        "void Xil_DCacheInvalidateRange(INTPTR,uint32_t);\n"
        "void Xil_DCacheFlushRange(INTPTR,uint32_t);\n"
        "#endif\n")
    (include/"xil_io.h").write_text(
        "#ifndef FAKE_XIL_IO_H\n#define FAKE_XIL_IO_H\n"
        "#include <stdint.h>\ntypedef uintptr_t UINTPTR;\n"
        "uint32_t Xil_In32(UINTPTR);\nvoid Xil_Out32(UINTPTR,uint32_t);\n"
        "#endif\n")
    (include/"xil_printf.h").write_text(
        "#ifndef FAKE_XIL_PRINTF_H\n#define FAKE_XIL_PRINTF_H\n"
        "int xil_printf(const char *,...);\n#endif\n")
    subprocess.run([
        compiler,"-std=c11","-fsyntax-only","-Wall","-Wextra",
        "-Werror","-pedantic","-I",str(include),str(source),
    ],check=True,capture_output=True,text=True,timeout=30)

