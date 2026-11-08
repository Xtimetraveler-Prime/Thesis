"""P08-B4.4 read-only descriptive timing, 1023 selected scope, signed-source negative CI."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b4_4_single_run_timing_audit as b44
import test_p08_b2_4_numerical as old

def digest(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

@pytest.fixture
def physically_shaped_synthetic_evidence(tmp_path,monkeypatch):
    """1024 fake rows with REAL wire ABI and CRC, never physical evidence."""
    physical=tmp_path/"synthetic_capture"
    cap=physical/"full1024_capture"
    cap.mkdir(parents=True)
    timings=b"".join(old.timing(i) for i in range(1024))
    terminal=old.mailbox(count=1024)
    (cap/"timing1024_physical.bin").write_bytes(timings)
    (cap/"mailbox_terminal_physical.bin").write_bytes(terminal)
    report=tmp_path/"synthetic_independently_accepted.json"
    metadata={
        "schema":"p08-b4-2-original1024-independent-physical-jtag-numerical-v1",
        "original_full1024_scalar_sha256":b44.ORACLE_SHA,
        "single_session_full1024_numerical_parity_accepted":True,
        "real_1024_A53_terminal_PASS_observed":True,
        "all_1024_A53_complete_service_timers_structurally_valid":True,
        "all_1024_full_26tick_1010_neuron_FNV_fingerprints_equal_scalar":True,
        "full_multisession_TrackB_latency_benchmark_accepted":False,
        "boot_DDR_DMA_exclusive_owner_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "numerical_full1024_timing_sha256":digest(timings),
        "numerical_terminal_mailbox_sha256":digest(terminal),
    }
    report.write_text(json.dumps(metadata,sort_keys=True))
    monkeypatch.setattr(b44,"PIN",digest(report.read_bytes()))
    return report,physical,metadata

def test_1023_ordinary_timing_signed_source_and_true_phases(
        physically_shaped_synthetic_evidence,tmp_path):
    report,evidence,_=physically_shaped_synthetic_evidence
    outfile=tmp_path/"descriptive.json"
    result=b44.analyze(report,evidence,outfile)
    assert outfile.is_file()
    assert result["full_original_frame_count"]==1024
    assert result["ordinary_frame_count"]==1023
    assert result["recorded_actual_A53_CNTFRQ_EL0_hz"]==99999001
    assert result["ordinary_complete_service"]["median_ticks"]==8500
    assert result["ordinary_complete_service"]["p95_nearest_rank_ticks"]==8500
    assert result["selected_trace_1023"]["ordinal"]==1023
    assert result["selected_trace_1023"]["service_ticks"]==8500
    assert result["six_repeated_AB_BA_AB_physical_sessions_accepted"] is False
    assert result["cross_track_neural_complexity_matched"] is False
    assert result["physical_speedup_or_energy_proven"] is False
    assert len(result["ordinary_six_disjoint_service_phases"])==6
    phases=result["ordinary_six_disjoint_service_phases"]
    assert phases[b44.PHASES[3]]["median_ticks"]==7500
    assert sum(round(x["share_of_sum_complete_service_pct"],9)
               for x in phases.values())==pytest.approx(100)
    with pytest.raises(b44.TimingNoGo,match="no-overwrite"):
        b44.analyze(report,evidence,outfile)

@pytest.mark.parametrize("scenario",[
    "alter_raw_timing","alter_terminal","bad_report_hash",
    "forged_physical_acceptance","unsealed_test","fake_repeated_benchmark",
    "backward_timing_crc","different_hz","partial_capture",
])
def test_timing_audit_refuses_mutation_and_claims(
        physically_shaped_synthetic_evidence,tmp_path,monkeypatch,scenario):
    report,evidence,meta=physically_shaped_synthetic_evidence
    cap=evidence/"full1024_capture"
    if scenario=="alter_raw_timing":
        p=cap/"timing1024_physical.bin"
        x=bytearray(p.read_bytes());x[8000]^=1;p.write_bytes(x)
    elif scenario=="alter_terminal":
        p=cap/"mailbox_terminal_physical.bin"
        x=bytearray(p.read_bytes());x[5*4+1]=0;p.write_bytes(x)
    elif scenario=="bad_report_hash":
        report.write_text(report.read_text()+" ")
    elif scenario in ("forged_physical_acceptance","unsealed_test",
                      "fake_repeated_benchmark"):
        if scenario=="forged_physical_acceptance":
            meta["single_session_full1024_numerical_parity_accepted"]=False
        elif scenario=="unsealed_test":
            meta["official_MNIST_TEST"]="ACCESS_GRANTED"
        else:meta["full_multisession_TrackB_latency_benchmark_accepted"]=True
        report.write_text(json.dumps(meta,sort_keys=True))
        # Synthetic-only SHA substitution must not bypass structural gates.
        monkeypatch.setattr(b44,"PIN",digest(report.read_bytes()))
    elif scenario=="backward_timing_crc":
        p=cap/"timing1024_physical.bin"
        x=bytearray(p.read_bytes());x[8000]^=1;p.write_bytes(x)
        meta["numerical_full1024_timing_sha256"]=digest(x)
        report.write_text(json.dumps(meta,sort_keys=True))
        monkeypatch.setattr(b44,"PIN",digest(report.read_bytes()))
    elif scenario=="different_hz":
        p=cap/"timing1024_physical.bin"
        x=bytearray(p.read_bytes())
        # Change one row frequency, recompute exact original row CRC,
        # and rebind synthetic provenance (not actual operator report).
        import struct,zlib
        pos=500*256
        row=list(struct.unpack("<64I",x[pos:pos+256]))
        row[4]=123456789
        row[61]=zlib.crc32(struct.pack("<61I",*row[:61]))
        x[pos:pos+256]=struct.pack("<64I",*row)
        p.write_bytes(x)
        meta["numerical_full1024_timing_sha256"]=digest(x)
        report.write_text(json.dumps(meta,sort_keys=True))
        monkeypatch.setattr(b44,"PIN",digest(report.read_bytes()))
    elif scenario=="partial_capture":
        p=cap/"timing1024_physical.bin"
        p.write_bytes(p.read_bytes()[:-256])
    output=tmp_path/"must_not_create.json"
    with pytest.raises((b44.TimingNoGo,b44.original.RecordNoGo)):
        b44.analyze(report,evidence,output)
    assert not output.exists()

def test_real_operator_sha_pin_never_replaced_by_synthetic_fixture():
    # Mock patching only affects test runtime, not committed actual code.
    import ast
    source=(ROOT/"scripts/p08_b4_4_single_run_timing_audit.py").read_text()
    tree=ast.parse(source)
    accepted=[n.value.value for n in tree.body if isinstance(n,ast.Assign)
              and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)
              and n.targets[0].id=="PIN" and isinstance(n.value,ast.Constant)]
    assert accepted==[
        "297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032"
    ]
    assert "import subprocess" not in source
    assert "import socket" not in source
    assert "1023" in source
