"""Synthetic-only tests for A4.2c physical 128 cold reboot evidence checker.

NEVER access real FPGA, canonical TEST, or external MNIST archives.
The fixtures are in-memory artificial output records and fake physical
logs/readback to verify strict fail-closed evidence structure.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import struct
import sys

import pytest

from loihi_twin_v2.p07_a4_stream import sha256
from loihi_twin_v2 import p07_a4_restart as restart
from test_p07_a4_crosscheck import evidence

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def accepted(evidence,tmp_path,monkeypatch):
    # The imported A3.3+new-format fixture contains synthetic 128 image
    # records and emulates prior physical mailboxes, not actual evidence.
    identity=tmp_path/"fake_acceptance_sources"
    identity.mkdir()
    sources={
        "p07_a4_board.elf":b"synthetic A53 ELF fake",
        "p03_2_ps_mmio.xsa":b"synthetic XSA fake",
        "p03_2_ps_mmio.bit":b"synthetic bitstream fake",
        "p03_2_ps_mmio.ltx":b"synthetic LTX fake",
        "core0_initial_p02_ddr_512k.bin":bytes(524288),
    }
    for name,data in sources.items():
        (identity/name).write_bytes(data)
    monkeypatch.setattr(restart,"ELF_SHA256",sha256(sources["p07_a4_board.elf"]))
    monkeypatch.setattr(restart,"XSA_SHA256",sha256(sources["p03_2_ps_mmio.xsa"]))
    monkeypatch.setattr(restart,"MASTER_SHA256",
                        sha256(sources["core0_initial_p02_ddr_512k.bin"]))
    run_dirs=[]
    for kind in ("primary","repeat"):
        run=tmp_path/("synthetic_"+kind)
        run.mkdir()
        run_dirs.append(run)
        shutil.copyfile(evidence["a4_journal"],run/"p07_a4_journal_1m.bin")
        shutil.copyfile(evidence["a4_trace"],run/"p07_a4_trace_64k.bin")
        (run/"trace_zero_64k.bin").write_bytes(bytes(65536))
        provenance=[
            "phase=P07-A4.2c persistent A53 TRAIN-derived validation physical gate",
            "status=BOARD_NOT_YET_RUN","git_commit=SYNTHETIC_FAKE_EVIDENCE",
        ]
        for name,data in sources.items():
            provenance.append(f"{sha256(data)}  {identity/name}")
        for name in restart.STAGE_FILES:
            file=evidence["a4_stage"]/name
            provenance.append(f"{sha256(file.read_bytes())}  {file}")
        (run/"physical_identity.txt").write_text("\n".join(provenance)+"\n")
        for logfile,markers in restart.LOG_MARKERS.items():
            (run/logfile).write_text("fake A4 native fixture\n"+
                                     "\n".join(markers)+"\n")
        rb=run/"readback"
        rb.mkdir()
        readback={
            0x43F00000:sources["core0_initial_p02_ddr_512k.bin"],
            0x41000000:(evidence["a4_stage"]/"p07_a4_pixels_raw.bin").read_bytes(),
            0x43FE0000:(evidence["a4_stage"]/"p07_a4_descriptor_256.bin").read_bytes(),
            0x43FE0100:(evidence["a4_stage"]/"p07_a4_mapping_1568.bin").read_bytes(),
            0x42000000:(evidence["a4_stage"]/"p07_a4_journal_initial_1m.bin").read_bytes(),
            0x43FF0000:bytes(65536),
        }
        for addr,data in readback.items():
            (rb/f"readback_{addr:08X}.bin").write_bytes(data)
    return {**evidence,
            "stage":evidence["a4_stage"],
            "primary":run_dirs[0],"repeat":run_dirs[1],
            "fake_sources":identity}


def _args(x, repeat=True):
    return {
        "stage":x["stage"],
        "primary":x["primary"],
        "a3_protocol":x["a3_protocol"],
        "a3_evidence":x["a3_evidence"],
        "repeat":x["repeat"] if repeat else None,
    }


def test_primary_host_preflight_accepts_exact_original_gate_logs(accepted):
    report=restart.verify_cold_repeat(**_args(accepted,False))
    assert report["status"]=="PRIMARY_ACCEPTED_REPEAT_PENDING"
    assert report["primary"]["complete_frames"]==128
    assert "repeat" not in report


def test_synthetic_cold_repeat_checks_every_byte_and_old_evidence(accepted):
    report=restart.verify_cold_repeat(**_args(accepted))
    assert report["physical_launches"]==2
    assert report["total_hardware_image_executions"]==256
    assert report["unique_train_validation_frames"]==128
    assert report["status"]=="PRIMARY_AND_COLD_REPEAT_VERIFIED_PENDING_LARGER_VALIDATION"
    assert report["full_journal_1m_byte_exact"]
    assert report["selected_trace_64k_byte_exact"]
    assert report["primary"]["journal_sha256"]==report["repeat"]["journal_sha256"]


def test_reject_same_directory_not_independent_launch(accepted):
    with pytest.raises(ValueError,match="distinct evidence"):
        restart.verify_cold_repeat(
            **{**_args(accepted),"repeat":accepted["primary"]}
        )


def test_reject_divergent_repeat_raw_journal_even_with_valid_recomputed_crc(accepted):
    file=accepted["repeat"]/"p07_a4_journal_1m.bin"
    raw=bytearray(file.read_bytes())
    start=256+77*96
    struct.pack_into("<I",raw,start+88,9)   # optional cycles field
    import zlib
    struct.pack_into("<I",raw,start+92,zlib.crc32(raw[start:start+92]))
    file.write_bytes(raw)
    with pytest.raises(AssertionError,match="1MiB physical journal differs"):
        restart.verify_cold_repeat(**_args(accepted))


def test_reject_changed_full_selected_trace(accepted):
    file=accepted["repeat"]/"p07_a4_trace_64k.bin"
    raw=bytearray(file.read_bytes())
    raw[53]=0x80
    file.write_bytes(raw)
    with pytest.raises(AssertionError,match="64KiB selected physical trace differs"):
        restart.verify_cold_repeat(**_args(accepted))


def test_reject_missing_or_failed_original_hardware_oracle_log(accepted):
    file=accepted["primary"]/"verify.log"
    file.write_text("P07_A4_2C_PHYSICAL_FRAMES=128\n")
    with pytest.raises(ValueError,match="missing physical gate marker"):
        restart.verify_cold_repeat(**_args(accepted,False))


def test_reject_wrong_or_modified_physical_elf(accepted):
    file=accepted["fake_sources"]/"p07_a4_board.elf"
    file.write_bytes(b"different ELF")
    with pytest.raises(ValueError,match="source hash changed"):
        restart.verify_cold_repeat(**_args(accepted,False))


def test_reject_missing_staging_xsdb_readback_even_with_pass_log(accepted):
    file=accepted["primary"]/"readback"/"readback_41000000.bin"
    raw=bytearray(file.read_bytes())
    raw[11]^=1
    file.write_bytes(raw)
    with pytest.raises(ValueError,match="DDR readback mismatch"):
        restart.verify_cold_repeat(**_args(accepted,False))


def test_reject_distinct_unaccepted_bitstream_identity(accepted):
    # Different unproven bitstream at reboot cannot be called same-run
    # equivalence, even when fake result bytes happen to match.
    f=accepted["fake_sources"]/"p03_2_ps_mmio.bit"
    data=b"new fake bitstream"
    f.write_bytes(data)
    # Changes fake original physical primary and repeat identities too;
    # the immutable original hash MUST trigger first.
    with pytest.raises(ValueError,match="source hash changed"):
        restart.verify_cold_repeat(**_args(accepted))


def test_reject_non128_staged_corpus(accepted):
    file=accepted["stage"]/"p07_a4_descriptor_256.bin"
    raw=bytearray(file.read_bytes())
    struct.pack_into("<I",raw,16,127)
    import zlib
    struct.pack_into("<I",raw,252,zlib.crc32(raw[:252]))
    file.write_bytes(raw)
    with pytest.raises(ValueError):
        restart.verify_cold_repeat(**_args(accepted))


def test_cli_is_read_only_and_refuses_overwrite(accepted,tmp_path):
    # CLI constants must use the immutable, physically accepted identities;
    # only test the pure CLI guard here, independent from mock patch.
    script=ROOT/"scripts/p07_a4_2_restart_verify.py"
    exist=tmp_path/"original_report.json"
    exist.write_text("{}")
    import os
    env={**os.environ,"PYTHONPATH":str(ROOT/"src")}
    command=[sys.executable,str(script),
             "--stage-dir",str(accepted["stage"]),
             "--primary-dir",str(accepted["primary"]),
             "--a3-protocol-dir",str(accepted["a3_protocol"]),
             "--a3-evidence-dir",str(accepted["a3_evidence"]),
             "--report",str(exist)]
    result=subprocess.run(command,env=env,text=True,capture_output=True)
    assert result.returncode != 0
    assert "refuse to overwrite" in result.stderr
    assert exist.read_text()=="{}"
