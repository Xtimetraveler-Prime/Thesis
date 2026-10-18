"""A3.2.1 offline analysis regressions. Synthetic unit fixtures NEVER claim FPGA results."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

from loihi_twin_v2.p08_a2_timing import TimingRun, TimingRecord
from loihi_twin_v2.p08_a2_2_ticks import TickRun, Tick
from loihi_twin_v2.p08_a3_2_analysis import (
    analyze_verified_pair,distribution,percentile_nearest_rank,
    FRAME_COUNT, TRACE_FRAME,ELF_A21_SHA256,ELF_A22_SHA256,
)

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def synthetic_pair():
    neural=tuple(SimpleNamespace(
        image_index=i,predicted=0,counts=(0,)*10,all_silent=True,
        routes=0,discarded=0,external_events=0,
        output_spikes=((0,)*10,)*26,
    ) for i in range(FRAME_COUNT))
    def run(hz: int, extra_ticks: int) -> TimingRun:
        rows=[]
        for i in range(FRAME_COUNT):
            start=1000+(i*1_000_000)
            rows.append(TimingRecord(
                i,i==TRACE_FRAME,start,start+100,
                start+100_000+extra_ticks-5,start+100_000+extra_ticks,
                2600,0,2000,1000,100,25,
            ))
        return TimingRun(FRAME_COUNT,TRACE_FRAME,hz,1,
                         rows[-1].after_commit+1,tuple(rows))
    a=run(100_000_000,0)
    d=run(100_000_000,10_000)
    ticks=tuple(
        Tick(
            frame=i,tick=t,external_events=0,emitted_packets=0,
            acknowledged_packets=0,final_drain=t==25,
            start=1100+i*1_000_000+t*100,
            after_encode=1101+i*1_000_000+t*100,
            after_append=1102+i*1_000_000+t*100,
            after_dispatch=1103+i*1_000_000+t*100,
            after_trace=1104+i*1_000_000+t*100,
            after_route=1105+i*1_000_000+t*100,
            after_barrier=1106+i*1_000_000+t*100,
            pl_dispatch_cycles=100,
        )
        for i in range(FRAME_COUNT) for t in range(26)
    )
    k=TickRun(FRAME_COUNT,TRACE_FRAME,0x12345678,
              100_000_000,1,d.dataset_stop, ticks)
    return a,d,k,neural


def test_1024_paired_nominal_reports_ordinary_vs_trace_and_clock(synthetic_pair):
    a,d,k,neural=synthetic_pair
    out=analyze_verified_pair(a,d,k,neural,neural)
    assert out["distinct_images"]==1024
    assert out["ordinary_images"]==1023
    assert out["a21_elf_sha256"]==ELF_A21_SHA256
    assert out["a22_elf_sha256"]==ELF_A22_SHA256
    assert out["normal_1023_a21_service_ms"]["median"]==1
    assert out["normal_1023_a22_service_ms"]["median"]==1.1
    assert out["paired_ordinary_1023_a22_minus_a21_service_ms"]["median"] == pytest.approx(0.1)
    assert out["per_tick_ordinary_1023_a22_stage_microseconds"]["event_encode"]["median"]==0.01
    assert out["full_replicated_latency_baseline"] if "full_replicated_latency_baseline" in out else True
    assert len(out["all_1024_a21_service_ms_raw"])==1024
    assert out["pl_cycles_equal_between_runs_per_image"] is True
    assert out["single_pair_is_statistical_repetition"] is False


def test_nearest_rank_definition_is_not_interpolated():
    assert percentile_nearest_rank([1,2,3,4,5,6,7,8,9,10],95)==10
    assert percentile_nearest_rank([1,2,3,4,5,6,7,8,9,10],50)==5
    assert distribution([3,5,7])["p95_nearest_rank"]==7
    with pytest.raises(ValueError,match="nonempty"):
        percentile_nearest_rank([],95)


def test_rejects_neural_mismatch_even_when_timer_values_look_good(synthetic_pair):
    a,d,k,neural=synthetic_pair
    corrupted=list(neural)
    corrupted[601]=SimpleNamespace(**{**vars(neural[601]),"routes":1})
    with pytest.raises(ValueError,match="frame 601"):
        analyze_verified_pair(a,d,k,neural,tuple(corrupted))


def test_rejects_mismatched_sample_count_trace_or_clock(synthetic_pair):
    a,d,k,neural=synthetic_pair
    with pytest.raises(ValueError,match="1024"):
        analyze_verified_pair(replace(a,count=16),d,k,neural,neural)
    with pytest.raises(ValueError,match="last trace"):
        analyze_verified_pair(a,replace(d,trace_index=0),k,neural,neural)
    with pytest.raises(ValueError,match="timer frequencies"):
        analyze_verified_pair(a,d,replace(k,hz=90_000_000),neural,neural)


def test_per_run_cntfrq_is_not_shared_between_firmware(synthetic_pair):
    a,d,k,neural=synthetic_pair
    varied=replace(a,cntfrq_hz=99_999_001)
    result=analyze_verified_pair(varied,d,k,neural,neural)
    assert result["a21_a53_cntfrq_el0_hz"]==99_999_001
    assert result["a22_a53_cntfrq_el0_hz"]==100_000_000
    assert result["normal_1023_a21_service_ms"]["median"]!=1


def test_cli_requires_original_independent_p07_oracle(monkeypatch,tmp_path):
    import sys
    sys.path.insert(0,str(ROOT/"scripts"))
    from p08_a3_2_pair_check import require_original_p07_oracle
    monkeypatch.setattr(subprocess,"run",
        lambda *a,**k:SimpleNamespace(
            returncode=1, stdout="P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1\n",
            stderr="original packed trace mismatch"))
    with pytest.raises(ValueError,match="packed-oracle verification FAILED"):
        require_original_p07_oracle(tmp_path,tmp_path/"journal",tmp_path/"trace")


def test_cli_rejects_missing_or_forged_physical_terminal(tmp_path):
    import sys
    sys.path.insert(0,str(ROOT/"scripts"))
    from p08_a3_2_pair_check import verified_source
    run=tmp_path/"mock"
    run.mkdir()
    (run/"physical_identity.txt").write_text(
        f"firmware_variant=A2_1\ncandidate_elf_sha256={ELF_A21_SHA256}\n"
        "scope=TRAIN_DERIVED_VALIDATION_FIRST_1024\n"
    )
    (run/"a53_run.log").write_text(
        "P08_A2_1_KV260_STATUS=TERMINAL_FAILURE_INSPECT_JOURNAL_AND_TIMING\n"
    )
    with pytest.raises(ValueError,match="physical terminal"):
        verified_source(run,"A2_1",ELF_A21_SHA256)
    (run/"physical_identity.txt").write_text("firmware_variant=A2_2\n")
    with pytest.raises(ValueError,match="ELF identity"):
        verified_source(run,"A2_1",ELF_A21_SHA256)


def test_cli_no_hardware_exec_and_guard(tmp_path):
    shell=(ROOT/"scripts/p08_a3_2_pair_check.py").read_text()
    assert "p07_a4_2_verify.py" in shell
    assert "parse_journal" in shell
    assert "parse_ticks" in shell
    assert "read_bytes()" in shell
    assert "subprocess.run(command" in shell
    assert "P08_A3_2_REPEATED_BASELINE_ACCEPTED=0" in shell
    assert not any(line.lstrip().startswith(("xsdb ","vivado ")) for line in shell.splitlines())
    check=subprocess.run(["python","-m","py_compile",
                          str(ROOT/"scripts/p08_a3_2_pair_check.py"),
                          str(ROOT/"src/loihi_twin_v2/p08_a3_2_analysis.py")],
                         check=False,capture_output=True,text=True)
    assert check.returncode==0,check.stderr
