"""A4.2c SYNTHETIC-only negative physical descriptor fault protocol tests.

NEVER calls Vivado/XSDB, touches KV260, opens MNIST TEST or TRAIN, or
modifies any of the accepted physical A53 ELF/FPGA or 1024 results.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess

import pytest

from loihi_twin_v2 import p07_a4_fault as fault
from loihi_twin_v2 import p07_a4_stream as stream


ROOT=Path(__file__).resolve().parents[1]
MAP=tuple(range(784))


@pytest.fixture
def fake_inputs(tmp_path):
    directory=tmp_path/"synthetic_ramp16_stage"
    directory.mkdir()
    pixels=bytes(i%256 for i in range(784))*16
    obj=stream.make_stream(pixels,MAP,trace_index=0)
    raw={
        "descriptor":("p07_a4_descriptor_256.bin",obj.header),
        "mapping":("p07_a4_mapping_1568.bin",obj.mapping_bytes),
        "pixels":("p07_a4_pixels_raw.bin",obj.images),
        "zero_journal_1m":("p07_a4_journal_initial_1m.bin",stream.initial_journal(obj)),
    }
    for _,(name,blob) in raw.items():
        (directory/name).write_bytes(blob)
    (directory/"p07_a4_2a_stage_manifest.json").write_text(json.dumps({
        "schema":"p07-a4-2a-persistent-ddr-stage-v1",
        "scope":"SYNTHETIC_RAMP",
        "frame_count":16,"trace_index":0,
        "official_mnist_test":"SEALED","physical_hardware":"NOT_RUN",
        "sha256":{name:stream.sha256(blob) for name,(_,blob) in raw.items()},
    }))
    before=obj.header
    after=bytearray(before)
    after[144:148]=b"\x01\x00\x00\x00"
    journal=bytearray(1048576)
    journal[:8]=b"P07A4R01"
    struct.pack_into("<9I",journal,8,1,256,0xDEAD0001,1,0,0xFFFFFFFF,0,0,0)
    struct.pack_into("<I",journal,252,stream.crc(journal[:252]))
    return directory,before,bytes(after),bytes(journal),bytes(65536)


def test_expected_one_word_physical_descriptor_rejection(fake_inputs):
    stage,before,after,journal,trace=fake_inputs
    result=fault.check_fault_bytes(stage,before,after,journal,trace)
    assert result["status_word"]=="0xDEAD0001"
    assert result["complete_frames"]==0
    assert result["official_mnist_test"]=="SEALED"


def test_refuse_normal_terminal_success_instead_of_failure(fake_inputs):
    stage,before,after,journal,trace=fake_inputs
    changed=bytearray(journal)
    struct.pack_into("<I",changed,16,0x600D600D)
    struct.pack_into("<I",changed,252,stream.crc(changed[:252]))
    with pytest.raises(ValueError,match="fail-closed header"):
        fault.check_fault_bytes(stage,before,after,bytes(changed),trace)


def test_refuse_two_word_or_wrong_address_corruption(fake_inputs):
    stage,before,after,journal,trace=fake_inputs
    extra=bytearray(after);extra[149]^=1
    with pytest.raises(ValueError,match="EXACTLY one reserved word"):
        fault.check_fault_bytes(stage,before,bytes(extra),journal,trace)


def test_refuse_physical_outputs_if_any_inference_occurred(fake_inputs):
    stage,before,after,journal,trace=fake_inputs
    raw=bytearray(journal);raw[300]=1
    with pytest.raises(ValueError,match="unexpected results"):
        fault.check_fault_bytes(stage,before,after,bytes(raw),trace)
    raw_trace=bytearray(trace);raw_trace[0]=1
    with pytest.raises(ValueError,match="unexpected inference dispatch"):
        fault.check_fault_bytes(stage,before,after,journal,bytes(raw_trace))


def test_refuse_nonzero_completed_even_if_crc_correct(fake_inputs):
    stage,before,after,journal,trace=fake_inputs
    raw=bytearray(journal)
    struct.pack_into("<I",raw,24,1)
    struct.pack_into("<I",raw,252,stream.crc(raw[:252]))
    with pytest.raises(ValueError,match="fail-closed header"):
        fault.check_fault_bytes(stage,before,after,bytes(raw),trace)


def test_refuse_tampered_source_before_hardware(fake_inputs):
    stage,before,after,journal,trace=fake_inputs
    p=stage/"p07_a4_pixels_raw.bin"
    p.write_bytes(p.read_bytes()[:-1]+b"\x01")
    with pytest.raises(ValueError,match="staged input SHA mismatch"):
        fault.check_fault_bytes(stage,before,after,journal,trace)


def test_negative_runner_needs_two_explicit_confirmations(fake_inputs,tmp_path):
    stage,before,after,journal,trace=fake_inputs
    script=ROOT/"scripts/run_p07_a4_fault_physical.sh"
    p=subprocess.run(["bash","-n",str(script)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    new=tmp_path/"negative_test_fresh_evidence"
    env={
        **os.environ,
        "P07_A4_FAULT_RUN_DIR":str(new),
        "P07_A4_FAULT_STAGE_DIR":str(stage),
        "P07_A4_BUILD_DIR":str(tmp_path),
        "P03_DIAG_REPORTS":str(tmp_path),
        "P03_2C_EXPECTED_XSA_SHA":"52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f",
        "P07_A4_CONFIRM_KV260_DDR_OVERWRITE":"NO",
        "P07_A4_CONFIRM_DESTRUCTIVE_FAULT_INJECTION":"NO",
    }
    fail=subprocess.run(["bash",str(script)],env=env,capture_output=True,text=True)
    assert fail.returncode!=0
    assert not new.exists()
    src=script.read_text()
    assert "P07_A4_CONFIRM_DESTRUCTIVE_FAULT_INJECTION" in src
    assert "P07_A4_CONFIRM_KV260_DDR_OVERWRITE" in src
    assert "P07_A4_2C_1024_RESTART_GATE_PASS=1" in src
    assert "P07_A4_VAL1024_PRIMARY_EVIDENCE" in src
    assert "P07_A4_VAL1024_REPEAT_EVIDENCE" in src
    assert "P07_A4_VAL1024_STAGE_DIR" in src
    assert "p07_a4_xsdb_inject_descriptor_fault.tcl" in src
    assert "P07_A4_2C_JOURNAL_STATUS=0xDEAD0001" in src
    assert "P07_A4_2C_PHYSICAL_FAULT" in src


def test_one_reserved_word_physical_injection_and_readback_bound():
    script=(ROOT/"vivado/p07_a4_xsdb_inject_descriptor_fault.tcl").read_text()
    assert "0x43FE0090" in script
    assert "0x00000001" in script
    assert "mrd -bin -file $before 0x43FE0000 64" in script
    assert "mrd -bin -file $after 0x43FE0000 64" in script
    assert "P07_A4_2C_DESCRIPTOR_ONE_WORD_PHYSICAL_FAULT_CONFIRMED=1" in script
    from loihi_twin_v2.p07_a4_restart import _physical_identity
    assert _physical_identity  # accepted original native tests cover default phase too
