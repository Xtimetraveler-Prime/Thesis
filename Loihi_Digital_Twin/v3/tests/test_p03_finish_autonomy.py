"""P03 closure preflight: frozen P02 ring, 7/100 profiles, A53 C syntax.

Offline PASS does not mean standalone Vitis or physical acceptance.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib
import pytest

ROOT=Path(__file__).resolve().parents[1]
GEN=ROOT/"scripts/p03_finish_fixture.py"
VERIFY=ROOT/"scripts/p03_finish_verify.py"
SOFTWARE=ROOT/"software/p03"
RUN=SOFTWARE/"p03_finish_run.c"
BUILD=ROOT/"scripts/build_p03_finish.sh"
PHYSICAL=ROOT/"scripts/run_p03_finish.sh"
VITIS=SOFTWARE/"build_p03_finish.py"
PREP=ROOT/"vivado/p03_finish_xsdb_prepare.tcl"
EXEC=ROOT/"vivado/p03_finish_xsdb_run.tcl"
DUMP=ROOT/"vivado/p03_finish_xsdb_dump.tcl"


def fixture(tmp_path:Path,steps:int):
    target=tmp_path/f"golden{steps}"
    proc=subprocess.run(
        [sys.executable,str(GEN),"--output-dir",str(target),
         "--timesteps",str(steps)],
        capture_output=True,text=True,timeout=90,
    )
    assert proc.returncode==0,proc.stdout+proc.stderr
    return target,json.loads((target/"p03_run_manifest.json").read_text())


@pytest.mark.parametrize("steps,packets,dispatches,ins,outs,hits",[
    (7,30,35,32,32,3),
    (100,None,500,497,497,3),
])
def test_frozen_golden_and_manifest_crc(tmp_path,steps,packets,dispatches,ins,outs,hits):
    target,manifest=fixture(tmp_path,steps)
    assert manifest["dispatch_count"]==dispatches
    if packets is not None:
        assert manifest["expected_packet_count_total"]==packets
        assert manifest["trace_fingerprint"]==(
            "9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac"
        )
    assert manifest["p03_timesteps"]==steps
    assert manifest["expected_replacement_page_ins"]==ins
    assert manifest["expected_runtime_page_outs"]==outs
    assert manifest["expected_evictions"]==ins
    assert manifest["expected_page_hits"]==hits
    assert manifest["expected_final_flush_page_outs"]==3
    raw=(target/"p03_run_config.bin").read_bytes()
    assert len(raw)==256
    words=struct.unpack("<64I",raw)
    assert words[:10]==(0x50334346,1,steps,5,3,10,
                         0x40000000,0x80000,0x43FF0000,1)
    assert words[63]==zlib.crc32(raw[:252])
    assert words[45]==manifest["expected_packet_count_total"]
    assert words[46]==dispatches
    assert words[47]==steps
    assert words[48]==steps&1
    assert len((target/"mailbox_zero.bin").read_bytes())==256
    for core in range(5):
        record=(target/f"core{core}_initial.bin").read_bytes()
        assert len(record)==0x80000
        assert words[40+core]==zlib.crc32(record)
        assert struct.unpack_from("<I",record,0x14)[0]==core
        assert words[30+core]==10+core
        assert (target/f"core{core}_expected.bin").stat().st_size==0x80000


def good_mailbox(manifest:dict)->bytes:
    steps=manifest["p03_timesteps"]
    words=[0]*64
    fields={
        0:0x50335253,1:1,2:0x600D600D,3:0,
        4:steps,5:steps,6:steps&1,7:0,8:0,9:18,
        10:0x4C543302,11:0x0001031F,12:5,13:3,
        14:5*steps,15:manifest["expected_packet_count_total"],
        16:steps,17:steps,18:3,
        19:manifest["expected_replacement_page_ins"],
        20:manifest["expected_runtime_page_outs"],
        21:3,22:manifest["expected_evictions"],
        23:manifest["expected_page_hits"],
        24:12345,26:23456,32:34567,
        36:100000000,37:1,38:manifest["expected_page_operations"],
        39:5*steps,40:106496,41:0,42:0,43:1712,44:416,
        60:int(manifest["p03_run_config_crc32"],16),
        63:manifest["expected_packet_count_total"],
    }
    for index,value in fields.items():words[index]=value
    for core in range(5):
        state=int(manifest["final_state_words"][str(core)],16)
        words[45+2*core]=state&0xFFFFFFFF
        words[46+2*core]=(state>>32)&0xFFFFFFFF
        words[55+core]=len(manifest["final_next_events"][str(core)])
    return struct.pack("<64I",*words)


def check(tmp:Path,profile:Path,blob:bytes)->subprocess.CompletedProcess:
    mbox=tmp/"result.bin"
    mbox.write_bytes(blob)
    return subprocess.run(
        [sys.executable,str(VERIFY),"--mailbox",str(mbox),
         "--fixture-dir",str(profile),
         "--dump-dir",str(tmp/"after")],
        capture_output=True,text=True,timeout=60,
    )


def test_strict_mailbox_pass_and_full_ddr_golden_and_fail_closed(tmp_path):
    golden,manifest=fixture(tmp_path,7)
    dumps=tmp_path/"after"
    dumps.mkdir()
    for core in range(5):
        (dumps/f"core{core}_after.bin").write_bytes(
            (golden/f"core{core}_expected.bin").read_bytes()
        )
    original=good_mailbox(manifest)
    good=check(tmp_path,golden,original)
    assert good.returncode==0,good.stdout+good.stderr
    assert "byte-exact" in good.stdout
    for index,value in [(2,0xDEAD0002),(7,6),(14,34),(15,29),
                        (16,6),(19,31),(21,2),(37,0xFFFFFFFF),(38,0),(45,0)]:
        data=list(struct.unpack("<64I",original))
        data[index]=value
        failed=check(tmp_path,golden,struct.pack("<64I",*data))
        assert failed.returncode != 0,(index,failed.stdout,failed.stderr)
    # Exact 512 KiB check: one modified byte must be rejected even if the
    # mailbox/counters and all five returned state words are valid.
    altered=bytearray((dumps/"core3_after.bin").read_bytes())
    altered[0x5000]^=0x01
    (dumps/"core3_after.bin").write_bytes(altered)
    failed=check(tmp_path,golden,original)
    assert failed.returncode!=0
    assert "core 3 final record mismatch" in failed.stderr


def test_100_step_synthetic_mailbox_and_full_record_conformance(tmp_path):
    profile,manifest=fixture(tmp_path,100)
    records=tmp_path/"after"
    records.mkdir()
    for core in range(5):
        (records/f"core{core}_after.bin").write_bytes(
            (profile/f"core{core}_expected.bin").read_bytes()
        )
    result=check(tmp_path,profile,good_mailbox(manifest))
    assert result.returncode==0,result.stdout+result.stderr
    assert "timesteps=100 dispatches=500" in result.stdout
    assert "byte-exact" in result.stdout


def test_vitis_and_board_single_launch_guards():
    b=BUILD.read_text()
    r=PHYSICAL.read_text()
    c=RUN.read_text()
    vitis=VITIS.read_text()
    for source in (
        "p03_finish_run.c","p03_runtime.c",
        "p03_hw_adapter.c","p03_hw_runtime_bridge.c",
        "p03_hw_xilinx_io.c",
    ):
        assert source in b
        assert source in vitis
        assert source in r
    assert "p03_finish_fixture.py" in b
    assert "P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V1" in b
    assert "P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V1" in c
    assert "P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V1" in r
    assert "p03_hpm0_data_width_bits=128" in r
    assert "p03_finish_xsdb_prepare.tcl" in r
    assert "p03_finish_xsdb_run.tcl" in r
    assert "p03_finish_xsdb_dump.tcl" in r
    assert "p03_finish_verify.py" in r
    assert "cmp -s" in r
    assert r.index('grep -aFq "$STAMP" "$ELF"') < r.index(
        'xsdb vivado/p03_finish_xsdb_prepare.tcl'
    )
    assert "RUN_RECORD_BYTES 0x80000u" in c
    assert "p03_rt_execute(&runtime,&ops,&bridge)" in c
    assert "ops.dispatch=inject_external_and_dispatch" in c
    assert "ops.drain_route=observe_and_drain" in c
    assert "++resident_routes;" in c
    assert "M_RESIDENT_ROUTES" in c
    assert "p03_hw_page(adapter" in c
    assert "p03_hw_quiescent(adapter)" in c
    assert "if(runtime.phase!=P03_RT_DONE" in c
    assert c.count("result[M_RESULT]=RUN_PASS;")==1
    assert c.index("if(runtime.phase!=P03_RT_DONE") < c.index("result[M_RESULT]=RUN_PASS;")
    assert "if(validate_manifest()!=0)" in c
    assert "if(check_records(NULL)!=0)" in c
    assert "CNTFRQ" not in c or "cntfrq_el0" in c
    assert "cntvct_el0" in c
    assert "core%d_initial.bin" in PREP.read_text()
    assert "131072" in DUMP.read_text()
    assert "binary scan $raw @8i result_word" in EXEC.read_text()
    for shell in (BUILD,PHYSICAL):
        proc=subprocess.run(["bash","-n",str(shell)],capture_output=True,text=True)
        assert proc.returncode==0,proc.stderr


def test_a53_sources_c11_strict_host_syntax(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    if cc is None: pytest.skip("no host C compiler")
    (tmp_path/"xil_io.h").write_text(
        "#ifndef TEST_XIL_IO_H\n#define TEST_XIL_IO_H\n"
        "#include <stdint.h>\n"
        "typedef uintptr_t UINTPTR;\ntypedef intptr_t INTPTR;\n"
        "typedef unsigned int u32;\n"
        "static inline uint32_t Xil_In32(UINTPTR a){(void)a;return 0;}\n"
        "static inline void Xil_Out32(UINTPTR a,uint32_t v){(void)a;(void)v;}\n"
        "#endif\n"
    )
    (tmp_path/"xil_cache.h").write_text(
        "#ifndef TEST_XIL_CACHE_H\n#define TEST_XIL_CACHE_H\n"
        '#include "xil_io.h"\n'
        "static inline void Xil_DCacheFlushRange(INTPTR a,u32 n)"
        "{(void)a;(void)n;}\n"
        "static inline void Xil_DCacheInvalidateRange(INTPTR a,u32 n)"
        "{(void)a;(void)n;}\n#endif\n"
    )
    for name in (
        "p03_finish_run.c","p03_runtime.c","p03_hw_adapter.c",
        "p03_hw_runtime_bridge.c","p03_hw_xilinx_io.c",
    ):
        proc=subprocess.run([
            cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
            "-fsyntax-only","-I",str(tmp_path),
            "-I",str(SOFTWARE/"include"),
            str(SOFTWARE/name)],
            capture_output=True,text=True,timeout=30,
        )
        assert proc.returncode==0,name+"\n"+proc.stderr
