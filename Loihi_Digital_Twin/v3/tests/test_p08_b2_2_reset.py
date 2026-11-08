"""P08-B2.2 strict real 27x512KiB native fake-DDR reset and timer gates.

These tests deliberately do not import or invoke Vitis/XSDB or physical PL.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b2_2_prepare_reset_pins as pins


def test_native_27_full_record_restores_twice_and_fails_closed(tmp_path):
    compiler=shutil.which("cc")
    assert compiler, "strict native C11 compiler required"
    exe=tmp_path/"p08_b2_native_reset"
    subprocess.run([
        compiler,"-std=c11","-O2","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p08"),
        "-I",str(ROOT/"software/p07/include"),
        str(ROOT/"software/p08/p08_b2_context_reset.c"),
        str(ROOT/"software/p08/p08_b2_service_meter.c"),
        str(ROOT/"software/p07/p07_a2_sha256.c"),
        str(ROOT/"tests/native/p08_b2_reset_native.c"),
        "-o",str(exe),
    ],check=True,capture_output=True,text=True,timeout=60)
    out=subprocess.run([str(exe)],check=True,capture_output=True,
                       text=True,timeout=120).stdout
    for marker in (
        "P08_B2_2_NATIVE_27_RECORD_RESET_TWICE=PASS",
        "P08_B2_2_NATIVE_LAST_RECORD_SHA_PRESERVE_ALL=PASS",
        "P08_B2_2_NATIVE_CACHE_FAULT_POISON=PASS",
        "P08_B2_2_NATIVE_A53_TIMER_BOUNDARIES=PASS",
        "P08_B2_2_PHYSICAL_DDR_OWNER_VERIFIED=0",
        "P08_B2_2_KV260_EXECUTED=0",
    ):
        assert marker in out


def rows():
    return [{"logical_core_id":n,
             "sha256":hashlib.sha256(bytes([n])).hexdigest()} for n in range(27)]


def test_generated_pins_contain_all_27_unmodified_sha256():
    expected=rows()
    header=pins.generate_header(expected)
    assert header.startswith("#ifndef P08_B2_2_GENERATED_ORIGINAL_CONTEXT_SHA256_H")
    assert "p08_b2_original_context_sha256[27][32]" in header
    assert header.count("/* original logical core ")==27
    for r in expected:
        assert ",".join(f"0x{int(r['sha256'][i:i+2],16):02x}" for i in range(0,64,2)) in header


def test_reject_missing_or_wrong_order_core_pins():
    with pytest.raises(pins.ResetPinsNoGo):
        pins.generate_header(rows()[:-1])
    rotated=rows()
    rotated[0],rotated[1]=rotated[1],rotated[0]
    with pytest.raises(pins.ResetPinsNoGo):
        pins.generate_header(rotated)


@pytest.mark.parametrize("mutated",[
    None, "", "00"*32,"ff"*31,"ZZ"*32
])
def test_reject_bad_pinned_sha256(mutated):
    rs=rows()
    rs[18]["sha256"]=mutated
    with pytest.raises(pins.ResetPinsNoGo):
        pins.generate_header(rs)


def test_reset_source_does_not_reach_mmio_or_vitis():
    src=(ROOT/"software/p08/p08_b2_context_reset.c").read_text()
    assert "Xil_Out32(" not in src
    assert "Xil_In32(" not in src
    assert "p03_hw_dispatch(" not in src
    assert "memcpy(dest,src,P08_B2_CONTEXT_STRIDE)" in src


def test_meter_explicitly_marks_trace_as_inclusive():
    h=(ROOT/"software/p08/p08_b2_service_meter.h").read_text()
    assert "NESTED INSIDE" in h
    assert "CNTVCT_EL0/CNTFRQ_EL0" in h
    assert "P08_B2_AFTER_JOURNAL_COMMIT=6" in h
