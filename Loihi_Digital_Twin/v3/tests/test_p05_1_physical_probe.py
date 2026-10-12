"""P05.1 host-only rehearsal of strict physical verifier and board scripts.

These synthetic mailbox tests are NOT evidence of execution on the KV260.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import zlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts/p03_finish_fixture.py"
PRODUCER = ROOT / "scripts/p05_deployment.py"
VERIFY = ROOT / "scripts/p05_1_verify.py"
RUN = ROOT / "scripts/run_p05_1_probe.sh"
TCL = ROOT / "vivado/p05_1_xsdb_prepare.tcl"

spec = importlib.util.spec_from_file_location("p05_physical_verify", VERIFY)
assert spec is not None and spec.loader is not None
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


@pytest.fixture(scope="module")
def prepared_seed(tmp_path_factory):
    # P03 golden generation is expensive: only run once. Each test gets
    # independent copied evidence so deliberate corruption cannot leak.
    out = tmp_path_factory.mktemp("p05_1_physical") / "seed"
    proc = subprocess.run(
        ["bash", str(RUN), "prepare", str(out)],
        capture_output=True, text=True, timeout=120, cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "board has NOT been touched" in proc.stdout
    golden = json.loads((out/"p03_golden/p03_run_manifest.json").read_text())
    manifest = json.loads((out/"p05_artifacts/p05_manifest.json").read_text())
    assert golden["expected_packet_count_total"] == 30
    assert manifest["events"] == 35 and manifest["checkpoints"] == 35
    return out, golden, manifest


@pytest.fixture
def prepared(tmp_path, prepared_seed):
    seed, golden, manifest = prepared_seed
    out = tmp_path / "physical_evidence"
    shutil.copytree(seed, out)
    out_dir = out / "final_ddr"
    out_dir.mkdir()
    for k in range(5):
        shutil.copy2(out/"p03_golden"/f"core{k}_expected.bin",
                     out_dir/f"core{k}_after.bin")
    return out, golden, manifest


def good_mailbox(out: Path, golden: dict, manifest: dict) -> bytes:
    w = [0]*64
    w[0:20] = [
        0x52353050, 1, 0x600D600D, 0, 7, 7, 5, 3, 18, 0, 0,
        35, 30, 7, 3, golden["expected_replacement_page_ins"],
        golden["expected_runtime_page_outs"],
        golden["expected_final_flush_page_outs"],
        golden["expected_evictions"], golden["expected_page_hits"],
    ]
    w[20] = 100
    w[22] = 1000
    w[24] = 2000
    w[32:42] = [
        99999001, 0x4C543302, 0x0001031F, 35,
        golden["expected_page_operations"], 106496,
        0, 0, 200, 200,
    ]
    w[42] = 0
    w[43] = 35
    w[44] = 35
    w[50] = int(manifest["header_crc32"], 16)
    w[51] = int(manifest["payload_crc32"], 16)
    w[54:58] = [1, 35, 35, 35]
    return struct.pack("<64I", *w)


def run_verifier(out: Path, capsys):
    good = verifier.verify(
        out / "p05_a53_result.bin",
        out / "p03_golden",
        out / "p05_artifacts",
        out / "final_ddr",
    )
    captured = capsys.readouterr()
    return good, captured.out + captured.err


def test_strict_synthetic_mailbox_and_full_frozen_ddr(prepared, capsys):
    out, golden, manifest = prepared
    (out/"p05_a53_result.bin").write_bytes(
        good_mailbox(out, golden, manifest)
    )
    good, logs = run_verifier(out, capsys)
    assert good
    assert "PASS: P05.1 independent physical 35-checkpoint ring replay" in logs
    assert "five final 512KiB DDR records byte-exact" in logs
    assert "P05_RESULT_METADATA=" in logs
    assert "resident_deliveries=0" in logs


@pytest.mark.parametrize("word,bad_value,issue", [
    (0, 0, "magic"), (2, 0xDEAD0008, "result"),
    (9, 11, "fault"), (11, 34, "dispatches"),
    (12, 29, "packets"), (13, 6, "barriers"),
    (35, 34, "hw_dispatches"), (36, 2, "hw_pages"),
    (43, 34, "inputs_consumed"), (44, 34, "checkpoints_passed"),
    (50, 0, "header_crc"), (51, 0, "payload_crc"),
    (58, 1, "diag_flags"), (60, 1, "reserved"),
])
def test_mailbox_mutations_fail_closed(prepared, capsys, word, bad_value, issue):
    out, golden, manifest = prepared
    original = list(struct.unpack("<64I", good_mailbox(out, golden, manifest)))
    assert original[word] != bad_value
    original[word] = bad_value
    (out/"p05_a53_result.bin").write_bytes(struct.pack("<64I", *original))
    good, logs = run_verifier(out, capsys)
    assert not good
    assert issue in logs
    assert "P05_FINAL_DDR_COMPARISON=PASS" in logs


def test_first_checkpoint_mismatch_on_failed_mailbox(prepared, capsys):
    out, golden, manifest = prepared
    words = list(struct.unpack("<64I", good_mailbox(out, golden, manifest)))
    words[2], words[3], words[8], words[9], words[10] = (
        0xDEAD000A, 10, 19, 11, 13
    )
    words[44] = 17
    words[45:50] = [3, 2, 1, 0xDEADBEEF, 0xBADCAFE0]
    words[58] = 1
    (out/"p05_a53_result.bin").write_bytes(struct.pack("<64I", *words))
    good, logs = run_verifier(out, capsys)
    assert not good
    assert "P05_FIRST_DIAGNOSTIC=" in logs
    assert '"failed_core": 2' in logs
    assert '"failed_step": 3' in logs
    assert '"expected_crc": 3735928559' in logs


def test_corrupt_actual_ddr_fails_even_if_mailbox_says_pass(prepared, capsys):
    out, golden, manifest = prepared
    (out/"p05_a53_result.bin").write_bytes(good_mailbox(out,golden,manifest))
    bad = bytearray((out/"final_ddr/core4_after.bin").read_bytes())
    bad[0x5000] ^= 1
    (out/"final_ddr/core4_after.bin").write_bytes(bad)
    good, logs = run_verifier(out, capsys)
    assert not good
    assert "P05_FINAL_DDR_COMPARISON=FAIL" in logs
    assert "core 4 final record mismatch" in logs


def test_reject_missing_record_and_mutated_staged_manifest(prepared, capsys):
    out, golden, manifest = prepared
    (out/"p05_a53_result.bin").write_bytes(good_mailbox(out,golden,manifest))
    (out/"final_ddr/core2_after.bin").unlink()
    good, logs = run_verifier(out, capsys)
    assert not good
    assert "P05_FINAL_DDR_COMPARISON=FAIL" in logs
    (out/"p05_artifacts/p05_header.bin").write_bytes(bytes(256))
    good, logs = run_verifier(out, capsys)
    assert not good
    assert "evidence admission" in logs


def test_physical_scripts_are_explicitly_opt_in_and_preserve_p03():
    proc = subprocess.run(
        ["bash","-n",str(RUN)],
        capture_output=True,text=True,timeout=30,
    )
    assert proc.returncode==0,proc.stderr
    shell=RUN.read_text()
    tcl=TCL.read_text()
    assert "P05_1_CONFIRM_KV260_DDR_OVERWRITE" in shell
    assert "P05_CONFIGURABLE_A53_REGRESSION_V1" in shell
    assert "p05_1_xsdb_prepare.tcl" in shell
    assert "p03_finish_xsdb_run.tcl" in shell
    assert "p03_finish_xsdb_dump.tcl" in shell
    assert "p05_1_verify.py" in shell
    assert "0x43F00000" in tcl
    assert "0x43FE0000" in tcl
    assert "0x43FF0000" in tcl
    assert "0x40000000" in tcl
    assert "p05_equal" in tcl
    assert "mrd -bin -file" in tcl
    assert "dow -data" in tcl
    assert "Cortex-A53" in tcl
    assert "name =~" in tcl


def test_recomputed_matching_crc_sha_cannot_hide_wrong_oracle_checkpoint(
    prepared, capsys
):
    out,golden,manifest=prepared
    (out/"p05_a53_result.bin").write_bytes(good_mailbox(out,golden,manifest))
    artifact=out/"p05_artifacts"
    header=list(struct.unpack("<64I",(artifact/"p05_header.bin").read_bytes()))
    payload=bytearray((artifact/"p05_payload.bin").read_bytes())
    assert header[14]==35
    crc_location=header[18]+12
    original=struct.unpack_from("<I",payload,crc_location)[0]
    struct.pack_into("<I",payload,crc_location,original^1)
    assert struct.unpack_from("<I",payload,crc_location)[0]!=original
    header[22]=zlib.crc32(payload)
    header[23]=0
    header[23]=zlib.crc32(struct.pack("<64I",*header))
    modified_header=struct.pack("<64I",*header)
    (artifact/"p05_header.bin").write_bytes(modified_header)
    (artifact/"p05_payload.bin").write_bytes(payload)
    info=json.loads((artifact/"p05_manifest.json").read_text())
    info["header_crc32"]=f"0x{header[23]:08X}"
    info["payload_crc32"]=f"0x{header[22]:08X}"
    info["header_sha256"]=hashlib.sha256(modified_header).hexdigest()
    info["payload_sha256"]=hashlib.sha256(payload).hexdigest()
    (artifact/"p05_manifest.json").write_text(json.dumps(info))
    good,logs=run_verifier(out,capsys)
    assert not good
    assert "checkpoint 0 differs from frozen P02 oracle" in logs


def test_mutated_external_event_rejected_even_with_refreshed_crc_sha(
    prepared, capsys
):
    out,golden,manifest=prepared
    (out/"p05_a53_result.bin").write_bytes(good_mailbox(out,golden,manifest))
    artifact=out/"p05_artifacts"
    header=list(struct.unpack("<64I",(artifact/"p05_header.bin").read_bytes()))
    payload=bytearray((artifact/"p05_payload.bin").read_bytes())
    # Edit first input from correct axon 10 to incorrect 11, but
    # recompute CRC/SHA fields in both corresponding files.
    struct.pack_into("<I",payload,header[17]+8,11)
    header[22]=zlib.crc32(payload)
    header[23]=0
    header[23]=zlib.crc32(struct.pack("<64I",*header))
    raw=struct.pack("<64I",*header)
    (artifact/"p05_header.bin").write_bytes(raw)
    (artifact/"p05_payload.bin").write_bytes(payload)
    info=json.loads((artifact/"p05_manifest.json").read_text())
    info["header_crc32"]=f"0x{header[23]:08X}"
    info["payload_crc32"]=f"0x{header[22]:08X}"
    info["header_sha256"]=hashlib.sha256(raw).hexdigest()
    info["payload_sha256"]=hashlib.sha256(payload).hexdigest()
    (artifact/"p05_manifest.json").write_text(json.dumps(info))
    good,logs=run_verifier(out,capsys)
    assert not good
    assert "external input 0 does not match frozen P03" in logs
