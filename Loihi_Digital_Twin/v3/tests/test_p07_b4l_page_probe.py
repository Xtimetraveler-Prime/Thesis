"""Native C11 and strict mailbox tests for next P07-B.4l physical paging."""
from __future__ import annotations
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4l_verify_page_probe as verifier

def test_actual_paging_controller_c11_harness(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    if not cc: pytest.skip("host C11 compiler unavailable")
    obj=tmp_path/"b4l"
    args=[
        cc,"-std=c11","-O0","-g","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p07/include"),
        str(ROOT/"software/p07/p07_b4l_page_probe.c"),
        str(ROOT/"tests/native/p07_b4l_page_probe_harness.c"),
        "-o",str(obj)
    ]
    compile=subprocess.run(args,capture_output=True,text=True,timeout=60)
    assert compile.returncode==0,compile.stderr
    result=subprocess.run([str(obj)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    for line in (
        "P07_B4L_NATIVE_27_CORE_3_SLOT_DIRTY_DDR_ROUNDTRIP_PASS=1",
        "P07_B4L_NATIVE_DIRTY_PAGEOUT_FAIL_CLOSED_PASS=1",
        "P07_B4L_NATIVE_PAGEIN_FAIL_CLOSED_PASS=1",
    ):
        assert line in result.stdout


def physical_proof():
    w=[0]*64
    w[0]=verifier.MAGIC
    w[1]=1
    w[2]=verifier.PASS
    w[8],w[9],w[10]=27,28,1
    w[11]=0xABC00000
    w[12]=w[11]^verifier.DIRTY
    w[13]=w[12]
    w[14]=w[12]
    w[16]=0
    w[17]=900
    w[20]=1
    w[21]=0x00000A00
    w[22]=29
    w[24],w[25]=27,3
    w[26],w[27],w[28]=0x40000000,0x80000,verifier.DIRTY
    w[63]=verifier.DONE
    return w


def test_strict_independent_mailbox_positive_fixture():
    w=physical_proof()
    d=verifier.verify(struct.pack("<64I",*w))
    assert d["page_ins"]==28 and d["page_outs"]==1
    assert d["physical_inference_executed"] is False


@pytest.mark.parametrize(("index","value"),[
    (0,0),(2,0xDEAD0000),(3,1),(4,1),(5,0xFFFFFFFF),(6,1),
    (7,1),(8,26),(9,27),(10,0),(12,0),(13,0),(14,0),
    (15,3),(16,2),(17,0),(19,1),(20,0),(21,0x00002560),
    (22,28),(23,1),(24,26),(25,4),(26,0x43FF0000),
    (27,0x6B000),(28,0),(50,1),(63,0)
])
def test_mailbox_mutation_fails_closed(index,value):
    w=physical_proof()
    w[index]=value
    with pytest.raises(ValueError,match="NO-GO"):
        verifier.verify(struct.pack("<64I",*w))


def test_mailbox_short_or_trailing_bytes_rejected():
    raw=struct.pack("<64I",*physical_proof())
    for sample in (raw[:-1],raw+b"\x00"):
        with pytest.raises(ValueError,match="256"):
            verifier.verify(sample)


def test_board_firmware_uses_accepted_p03_live_page_debug():
    c=(ROOT/"software/p07/p07_b4l_paging_probe_board.c").read_text()
    h=(ROOT/"software/p07/include/p07_b4l_page_probe.h").read_text()
    worker=(ROOT/"software/p07/p07_b4l_page_probe.c").read_text()
    build=(ROOT/"software/p07/build_p07_b4l_page_probe.py").read_text()
    shell=(ROOT/"scripts/build_p07_b4l_page_probe.sh").read_text()
    assert "p03_hw_page(&hw" in c
    assert "p03_hw_debug_word(&hw" in c
    assert "Xil_DCacheInvalidateRange" in c
    assert "p03_hw_xilinx_fpd128_ready" in c
    assert "p03_hw_identify" in c
    assert "p03_hw_register_core" in c
    assert "p07_b4l_page_probe.c" in build and "p07_b4l_page_probe.c" in shell
    assert "P07_B4L_A53_27CORE_PAGING_PROBE_V1" in c
    assert "B4L_PROBE_PAGE_INS 28u" in h
    assert "B4L_PROBE_PAGE_OUTS 1u" in h
    assert "if (page(ops,ctx,r,0u,0u,1,1,101u))" in worker
    assert "if (saved!=r->state_dirty)" in worker
    assert "27" in worker
    assert "p07_b4i_xsdb_run" not in shell
