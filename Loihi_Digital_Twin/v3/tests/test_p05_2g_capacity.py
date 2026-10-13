"""P05.2g NATIVE full-bank/over-limit regression; synthetic mailboxes NEVER count as KV260 evidence."""
from __future__ import annotations
import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p05_2g_capacity_fixture as FIX
import p05_2g_capacity_verify as CHECK
RUN=ROOT/"scripts/run_p05_2g_capacity.sh"

@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    p=tmp_path_factory.mktemp("p05_2g")/"prepared"
    r=subprocess.run(["bash",str(RUN),"prepare",str(p)],
                     cwd=ROOT,capture_output=True,text=True,timeout=240)
    assert r.returncode==0,r.stdout+r.stderr
    assert "NO KV260 touched" in r.stdout
    return p

def full_mailbox(folder):
    w=[0]*64
    h=struct.unpack("<64I",(folder/"p05_artifacts/p05_header.bin").read_bytes())
    w[:20]=[0x52353050,1,0x600D600D,0,1,1,1,1,18,0,0,
            1,0,1,1,0,0,1,0,1]
    w[20]=400
    w[22]=800
    w[24]=1000
    w[26]=100
    w[28]=100
    w[30]=100
    w[32:42]=[99999001,0x4C543302,0x0001031F,1,2,106496,0,0,100,100]
    w[42:45]=[0,4096,3]
    w[50:52]=[h[23],h[22]]
    w[54:58]=[1,4096,3,1]
    return struct.pack("<64I",*w)

def overflow_mailbox(folder):
    w=[0]*64
    w[:4]=[0x52353050,1,0xDEAD0002,2]
    return struct.pack("<64I",*w)

@pytest.fixture
def staged(tmp_path,prepared):
    full=tmp_path/"full"
    over=tmp_path/"overflow"
    shutil.copytree(prepared/"full",full)
    shutil.copytree(prepared/"overflow",over)
    for p in (full,over):
        (p/"final_ddr").mkdir()
    shutil.copy2(full/"capacity_golden/core0_expected.bin",
                 full/"final_ddr/core0_after.bin")
    shutil.copy2(over/"capacity_golden/core0_initial.bin",
                 over/"final_ddr/core0_after.bin")
    (full/"p05_a53_result.bin").write_bytes(full_mailbox(full))
    (over/"p05_a53_result.bin").write_bytes(overflow_mailbox(over))
    return full,over

def test_exact_bank_4096_is_not_a_near_capacity_guess(prepared):
    p=prepared/"full"
    m=json.loads((p/"capacity_golden/manifest.json").read_text())
    g=json.loads((p/"p05_2g_full_gate.json").read_text())
    assert (g["max_event_bank_depth"],g["event_count"])==(4096,4096)
    assert g["status"]=="MODEL_ONLY_NOT_HARDWARE_ACCEPTED"
    assert m["event0_word0_crc"]==f"0x{zlib.crc32(struct.pack('<I',10)):08X}"
    initial=(p/"capacity_golden/core0_initial.bin").read_bytes()
    final=(p/"capacity_golden/core0_expected.bin").read_bytes()
    assert len(initial)==len(final)==0x80000
    assert final[0x54000:0x58000]==struct.pack("<I",10)*4096
    assert final[0x58000:0x5C000]==bytes(4096*4)
    assert final[0x5000:0x5008]!=initial[0x5000:0x5008]
    assert hashlib.sha256(final).hexdigest()==m["final_record_sha256"]

def test_host_builder_refuses_4097_even_if_extra_event_is_registered(prepared):
    p=prepared/"overflow"
    g=json.loads((p/"p05_2g_overflow_gate.json").read_text())
    assert g["event_count"]==4097
    h=struct.unpack("<64I",(p/"p05_artifacts/p05_header.bin").read_bytes())
    data=(p/"p05_artifacts/p05_payload.bin").read_bytes()
    assert h[13]==4097 and h[22]==zlib.crc32(data)
    assert h[23]==zlib.crc32(struct.pack("<64I",*(
        [*(h[:23]),0,*(h[24:])])))
    assert data[32:48]==data[32+4096*16:32+4097*16]
    assert (p/"p05_artifacts/core0_initial.bin").read_bytes()==(
        prepared/"full/p05_artifacts/core0_initial.bin").read_bytes()

def test_real_portable_C11_descriptor_validator_uses_event_overflow_not_checksum(prepared,tmp_path):
    cc=shutil.which("gcc") or shutil.which("cc")
    if not cc:pytest.skip("C compiler unavailable: native C gate not executed")
    source=ROOT/"software/p05/p05_deployment.c"
    lib=tmp_path/"libp05g_validator.so"
    comp=subprocess.run([cc,"-std=c11","-Wall","-Wextra","-Werror","-fPIC",
                         "-shared","-I",str(ROOT/"software/p05/include"),
                         str(source),"-o",str(lib)],
                        capture_output=True,text=True,timeout=60)
    assert comp.returncode==0,comp.stderr
    dll=ctypes.CDLL(str(lib))
    f=dll.p05_deployment_validate
    f.argtypes=[ctypes.c_void_p,ctypes.c_size_t,
                ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p]
    f.restype=ctypes.c_int
    for profile,expected in (("full",0),("overflow",-5)):
        p=prepared/profile/"p05_artifacts"
        header=(p/"p05_header.bin").read_bytes()
        payload=(p/"p05_payload.bin").read_bytes()
        info=ctypes.create_string_buffer(256)
        actual=f(ctypes.create_string_buffer(header),len(header),
                 ctypes.create_string_buffer(payload),len(payload),info)
        assert actual==expected,(profile,actual,expected)
    # Deliberately change payload without fixing its CRC: not a false "overflow pass".
    p=prepared/"overflow/p05_artifacts"
    bad=bytearray((p/"p05_payload.bin").read_bytes())
    bad[32]^=1
    header=(p/"p05_header.bin").read_bytes()
    info=ctypes.create_string_buffer(256)
    actual=f(ctypes.create_string_buffer(header),len(header),
             ctypes.create_string_buffer(bytes(bad)),len(bad),info)
    assert actual==-3  # P05_BAD_CHECKSUM, distinct from P05_BAD_EVENT

def test_native_C_route_next_bank_last_slot_and_no_4097th_store(tmp_path):
    cc=shutil.which("gcc") or shutil.which("cc")
    if not cc:pytest.skip("C compiler unavailable: portable route guard not executed")
    exe=tmp_path/"p05_2g_route_guard"
    build=subprocess.run([
        cc,"-std=c11","-Wall","-Wextra","-Werror",
        "-I",str(ROOT/"software/p03/include"),
        str(ROOT/"tests/p05_2g_route_guard.c"),
        str(ROOT/"software/p03/p03_hw_adapter.c"),
        "-o",str(exe)
    ],capture_output=True,text=True,timeout=60)
    assert build.returncode==0,build.stderr
    run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
    assert run.returncode==0,f"guard return {run.returncode}: {run.stderr}"

def test_4096_synthetic_P05R_and_entire_original_ddr_verifier(staged,capsys):
    full,_=staged
    assert CHECK.verify_full(full)
    result=capsys.readouterr().out
    assert "P05_2G_FULL_VERIFY_EXIT=0" in result
    assert "complete 512KiB" in result

def test_4097_synthetic_P05R_precise_early_reject(staged,capsys):
    _,over=staged
    assert CHECK.verify_overflow(over)
    assert "P05_2G_OVERFLOW_VERIFY_EXIT=0" in capsys.readouterr().out

@pytest.mark.parametrize("path,offset",[
    ("final_ddr/core0_after.bin",0x5000),
    ("final_ddr/core0_after.bin",0x54000),
    ("final_ddr/core0_after.bin",0x57FFC),
    ("final_ddr/core0_after.bin",0x5C000),
    ("p05_artifacts/p05_header.bin",52),
    ("p05_artifacts/p05_payload.bin",32),
])
def test_full_bank_rogue_ddr_or_deployment_byte_fails(staged,capsys,path,offset):
    full,_=staged
    file=full/path
    raw=bytearray(file.read_bytes());raw[offset]^=1
    file.write_bytes(raw)
    assert not CHECK.verify_full(full)
    assert "FAIL: P05.2g" in capsys.readouterr().err

@pytest.mark.parametrize("field,value",[(2,0xDEAD0002),(11,0),(36,0),(43,4095),(44,2),(50,0),(54,0),(60,1)])
def test_full_bank_forged_mailbox_fails(staged,capsys,field,value):
    full,_=staged
    file=full/"p05_a53_result.bin"
    raw=list(struct.unpack("<64I",file.read_bytes()))
    assert raw[field]!=value
    raw[field]=value
    file.write_bytes(struct.pack("<64I",*raw))
    assert not CHECK.verify_full(full)
    assert "FAIL: P05.2g" in capsys.readouterr().err

@pytest.mark.parametrize("field,value",[(2,0x600D600D),(3,3),(11,1),(36,1),(43,4097),(60,1)])
def test_overlimit_rejects_unrelated_error_or_any_runtime_activity(staged,capsys,field,value):
    _,over=staged
    file=over/"p05_a53_result.bin"
    w=list(struct.unpack("<64I",file.read_bytes()))
    assert w[field]!=value
    w[field]=value
    file.write_bytes(struct.pack("<64I",*w))
    assert not CHECK.verify_overflow(over)
    assert "FAIL: P05.2g" in capsys.readouterr().err

def test_overflow_cannot_mutate_single_byte_of_reserved_ddr(staged,capsys):
    _,over=staged
    file=over/"final_ddr/core0_after.bin"
    b=bytearray(file.read_bytes());b[0x54000]^=1;file.write_bytes(b)
    assert not CHECK.verify_overflow(over)
    assert "FAIL: P05.2g" in capsys.readouterr().err

def test_physical_runner_guard_and_no_C_or_fpga_build_changes():
    content=RUN.read_text()
    assert "P05_2G_CONFIRM_KV260_DDR_OVERWRITE" in content
    assert "p05_2g_capacity_verify.py" in content
    assert "p05_2g_capacity_prepare.tcl" in content
    assert "P03_2C_EXPECTED_XSA_SHA" in content
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in content
    assert "P05_1_BUILD_DIR" in content
    assert "P03_DIAG_REPORTS" in content
    assert "preflight_identity.txt" in content
    assert "physical-full" in content and "physical-overflow" in content
    assert subprocess.run(["bash","-n",str(RUN)],capture_output=True).returncode==0
