"""PC-only full1024 independent reviewer CLI contract regression.

Both original SHA-pinned pilot16 JSON receipts are REQUIRED by the physical
runner's admission and by the independent reviewer. This catches the actual
2026-11-05 argparse --pilot-* mismatch without reading real hardware.
"""
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b45_perf_full1024_independent_verify as independent

def argv(tmp_path:Path, with_pilots:bool=True)->list[str]:
    evidence=tmp_path/"failed_or_successful_physical_capture"
    evidence.mkdir()
    out=tmp_path/"report.json"
    args=["--experiment","once","--evidence",str(evidence),
          "--stage",str(tmp_path/"stage"),
          "--first16",str(tmp_path/"first16.json"),
          "--b3-report",str(tmp_path/"b3.json"),
          "--shards",str(tmp_path/"shards"),
          "--ingress",str(tmp_path/"ingress"),
          "--oracle",str(tmp_path/"oracle.json"),
          "--b4-independent-report",str(tmp_path/"b4.json"),
          "--b44-timing-report",str(tmp_path/"b44.json"),
          "--build",str(tmp_path/"build"),
          "--original-elf",str(tmp_path/"b2.elf"),
          "--reset-pins",str(tmp_path/"reset"),
          "--reports",str(tmp_path/"reports"),
          "--out",str(out)]
    if with_pilots:
        args += ["--pilot-once-report",str(tmp_path/"pilot_once.json"),
                 "--pilot-unchecked-report",str(tmp_path/"pilot_unchecked.json")]
    return args

@pytest.mark.parametrize("mode",["once","unchecked"])
def test_independent_cli_accepts_same_real_pilot_receipts_as_physical(tmp_path,monkeypatch,capsys,mode):
    args=argv(tmp_path)
    args[1]=mode
    captured=[]
    def fake_admission(parsed):
        captured.append(parsed)
        assert parsed.experiment==mode
        assert parsed.pilot_once_report==tmp_path/"pilot_once.json"
        assert parsed.pilot_unchecked_report==tmp_path/"pilot_unchecked.json"
        raise ValueError("HOST_TEST_STOP_BEFORE_ACTUAL_SOURCE_INPUTS")
    monkeypatch.setattr(independent.bench,"admission",fake_admission)
    result=independent.main(args)
    assert result==3 and len(captured)==1
    output=capsys.readouterr()
    assert "HOST_TEST_STOP_BEFORE_ACTUAL_SOURCE_INPUTS" in output.err
    assert "unrecognized arguments:" not in output.err
    assert not (tmp_path/"report.json").exists()

def test_independent_cli_missing_real_pilot_receipts_fails_closed(tmp_path):
    with pytest.raises(SystemExit) as exc:
        independent.main(argv(tmp_path,with_pilots=False))
    assert exc.value.code==2

def test_independent_cli_reuses_existing_SHA_pinned_source_admission():
    src=(ROOT/"scripts"/"p08_b45_perf_full1024_independent_verify.py").read_text()
    runner=(ROOT/"scripts"/"p08_b45_perf_full1024_physical_run.py").read_text()
    assert '"pilot_once_report"' in src and '"pilot_unchecked_report"' in src
    assert '"pilot_once_report"' in runner and '"pilot_unchecked_report"' in runner
    assert "verified=bench.admission(args)" in src
    assert "bench.check_post_backup(args.stage,cap)" in src
    assert "neural.verify(" in src
    assert "import subprocess" not in src
