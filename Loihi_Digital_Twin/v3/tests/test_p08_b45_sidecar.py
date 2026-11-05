"""P08-B4.5 synthetic reset sidecar parser positive and negative tests."""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b45_sidecar as audit


def frame(mode: str, i: int, guard: int = 1) -> bytes:
    w=[0]*64
    w[0]=audit.MAGIC[mode]
    w[1]=1
    w[2]=i
    w[3]=audit.PASS
    w[4]=audit.MODE[mode]
    w[5]=i+1
    w[6]=27
    w[7]=audit.COPY_BYTES
    n=27 if mode=="once" else 0
    for index in (8,9,10,11):
        w[index]=n
    w[12]=0
    w[13]=99999001
    w[14]=0
    w[15]=900000+i*17
    w[16]=0
    w[17]=30000000 if mode=="once" else 1800
    w[18]=0
    w[19]=guard
    w[20]=26
    w[21]=702
    w[63]=audit.DONE
    w[61]=zlib.crc32(struct.pack("<61I",*w[:61]))
    return struct.pack("<64I",*w)


@pytest.mark.parametrize("mode",("once","unchecked"))
def test_16_image_structural_pilot_parity_scope_remains_unverified(mode):
    blob=b"".join(frame(mode,i) for i in range(16))
    result=audit.audit(blob,mode=mode,expected_rows=16,observed_hz=99999001)
    assert result["frames_structurally_verified"]==16
    assert result["ordinary_frames"]==16
    assert result["actual_KV260_neural_FNV_oracle_parity_proven"] is False
    assert result["physical_memory_ownership_independently_proven"] is False
    assert result["backing_backup_guard_provisioned_flag"]==1
    assert result["physical_JTAG_launch_authorized"] is False


@pytest.mark.parametrize("mode",("once","unchecked"))
def test_1024_image_trace_isolation(mode):
    blob=b"".join(frame(mode,i) for i in range(1024))
    result=audit.audit(blob,mode=mode,expected_rows=1024)
    assert result["frames_structurally_verified"]==1024
    assert result["ordinary_frames"]==1023
    assert result["isolated_trace_ordinal"]==1023


@pytest.mark.parametrize("mode",("once","unchecked"))
def test_unprovisioned_guard_must_fail_strict_physical_candidate(mode):
    blob=b"".join(frame(mode,i,guard=0) for i in range(16))
    with pytest.raises(audit.SidecarNoGo,match="NOT provisioned"):
        audit.audit(blob,mode=mode,expected_rows=16)
    structural=audit.audit(blob,mode=mode,expected_rows=16,
                           require_protection=False)
    assert structural["backing_backup_guard_provisioned_flag"]==0
    assert structural["physical_JTAG_launch_authorized"] is False


@pytest.mark.parametrize("mode",("once","unchecked"))
@pytest.mark.parametrize("change",(
    "bad_crc","bad_magic","bad_mode","bad_count","bad_generation",
    "bad_zero_reserved","wrong_tick_count","wrong_dispatch_count",
    "wrong_session_clock","bad_copy_bytes","bad_sha_count","short_blob",
    "mixed_guard","zero_ticks","wrong_hz",
))
def test_sidecar_negative_structural_rejections(mode,change):
    frames=[frame(mode,i) for i in range(16)]
    rows=[list(struct.unpack("<64I",raw)) for raw in frames]
    k=5
    if change=="bad_crc":
        rows[k][61] ^= 1
    elif change=="bad_magic":
        rows[k][0] ^= 1
    elif change=="bad_mode":
        rows[k][4] = 2 if mode=="once" else 1
    elif change=="bad_count":
        rows[k][6] = 26
    elif change=="bad_generation":
        rows[k][5] = 300
    elif change=="bad_zero_reserved":
        rows[k][22] = 1
    elif change=="wrong_tick_count":
        rows[k][20] = 25
    elif change=="wrong_dispatch_count":
        rows[k][21] = 700
    elif change=="wrong_session_clock":
        rows[k][13] = 100000000
    elif change=="bad_copy_bytes":
        rows[k][7] = 0
    elif change=="bad_sha_count":
        rows[k][8] = 5
    elif change=="mixed_guard":
        rows[k][19] = 0
    elif change=="zero_ticks":
        rows[k][15] = 0
    elif change=="wrong_hz":
        rows[k][13] = 88888888
    if change not in ("bad_crc","short_blob"):
        rows[k][61]=zlib.crc32(struct.pack("<61I",*rows[k][:61]))
    frames=[struct.pack("<64I",*row) for row in rows]
    blob=b"".join(frames)
    if change=="short_blob":
        blob=blob[:-1]
    with pytest.raises(audit.SidecarNoGo):
        audit.audit(blob,mode=mode,expected_rows=16,observed_hz=99999001)


def test_sidecar_new_report_no_overwrite_and_not_hardware_acceptance(tmp_path):
    captured=tmp_path/"synthetic.bin"
    report=tmp_path/"synthetic_report.json"
    captured.write_bytes(b"".join(frame("once",i) for i in range(16)))
    assert audit.main(["--capture",str(captured),"--mode","once",
                       "--rows","16","--hz","99999001","--out",str(report)])==0
    assert report.exists()
    assert audit.main(["--capture",str(captured),"--mode","once",
                       "--rows","16","--out",str(report)])==3
