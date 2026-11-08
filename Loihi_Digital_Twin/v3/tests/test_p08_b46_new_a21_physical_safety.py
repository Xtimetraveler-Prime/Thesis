"""P08-B4.6 new SHA rebuilt A2.1 1024 original physical runner source safety.

HOST ONLY: inspect source and Python syntax, never interact with KV260.
Real physical acceptance requires separate operator approvals and 1024
independent ORIGINAL P07 packed neural verification on actual captures.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import subprocess
import sys
import ast

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/"scripts/run_p08_b46_rebuilt_a21_1024.sh"
HISTORICAL=ROOT/"scripts/run_p08_a3_2_1024.sh"
REVIEWER=ROOT/"scripts/p08_b46_a21_rebuilt_independent_physical_verify.py"

def read(path:Path)->str:
    return path.read_text()

def test_original_historical_A2_1_physical_runner_preserved_separate():
    old=read(HISTORICAL)
    new=read(RUNNER)
    assert "PINNED_ELF_SHA=fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0" in old
    assert "PINNED_ELF_SHA=fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793" in new
    assert "PINNED_ELF_SHA=fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0" not in new
    assert "scripts/p08_a3_2_single_check.py" in old
    assert "scripts/p08_b46_a21_rebuilt_independent_physical_verify.py" in new
    assert "scripts/p08_b46_a21_rebuilt_independent_physical_verify.py" not in old

def test_new_genuine_runner_sh_is_valid_bash_syntax():
    res=subprocess.run(["bash","-n",str(RUNNER)],capture_output=True,text=True)
    assert res.returncode==0,res.stderr

def test_original_KV260_fpd_ddr_jtag_sequence_preserved():
    s=read(RUNNER)
    operations=(
      "p03_2c_xsdb_ps_axi_width_diag.tcl",
      "p07_a4_xsdb_prepare.tcl",
      "p03_2c_program_bitstream.tcl",
      'xsdb "$XSDB_SCRIPT"',
      "P07_A4_2C_XSDB_PROVISION_PASS=1",
      "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
      "TERMINAL_BOTH_SUCCESS_UNVERIFIED_NUMERICS",
      "P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1",
    )
    for k in operations:
        assert k in s,k
    assert s.index("P03_2C_PS_FPD_HPM0_WIDTH_BITS=128")<s.index("xsdb vivado/p07_a4_xsdb_prepare.tcl")
    assert s.index("P07_A4_2C_XSDB_PROVISION_PASS=1")<s.index("vivado -mode batch -source vivado/p03_2c_program_bitstream.tcl")
    assert s.index("P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1")>s.index('xsdb "$XSDB_SCRIPT"')

def test_operator_approved_NEW_only_and_source_before_board():
    s=read(RUNNER)
    for gate in (
      "P08_B46_PREFLIGHT_ONLY",
      "P08_B46_SIGNED_SOURCE_REPORT",
      "P08_B46_SIGNED_A_ADMISSION",
      "P08_B46_CONFIRM_DISPOSABLE_LINUX_JTAG_ONLY",
      "P08_B46_CONFIRM_OVERWRITE_ORIGINAL_64M_DDR",
      "P08_B46_CONFIRM_ORIGINAL_TRAIN_ONLY",
      "P08_B46_CONFIRM_UNPROVEN_BOOT_DDR_DMA_RISK",
      "P08_B46_CONFIRM_PWR_CYCLE_AFTER_ANY_ATTEMPT",
      "P08_B46_CONFIRM_NEW_CANDIDATE_ELF",
      "ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56",
      "inspect_rebuild(build,xsa)",
      "source-report",
      "candidate-report",
      "P08_B46_SIX_REPEATED_A_B_SESSION_BENCHMARK_ACCEPTED=0",
    ):
        assert gate in s,gate
    assert s.index("inspect_rebuild(build,xsa)")<s.index('mkdir -p "$RUN/readback"')
    assert '[[ "$RUN" == /* && ! -e "$RUN" && ! -L "$RUN" ]]' in s
    assert '[[ "$ACTUAL_ELF_SHA" == "$PINNED_ELF_SHA" ]]' in s
    assert "TEST" in s and "TRAIN" in s

def test_reviewer_is_PC_only_original_replay_and_no_false_repeated_claim():
    text=read(REVIEWER)
    ast.parse(text)
    assert 'SOURCE_SHA="ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56"' in text
    assert "verified_source(run,\"A2_1\",candidate.NEW_A21_SHA)" in text
    assert "require_original_p07_oracle(stage,journal,trace)" in text
    assert "parse_journal(journal.read_bytes(),stream)" in text
    assert "parse_timing(timing.read_bytes(),expected_count=1024)" in text
    assert 'run/"readback"/"readback_43F00000.bin"' in text
    assert "old_original_historical_A21_ELF_reproduced" in text
    assert '"A_vs_B_auth_once_service_timer_boundaries_matched":False' in text
    assert '"B46_six_repeated_A_B_auth_once_sessions_accepted":False' in text
    assert '"hardware_DDR_owner_DMA_exclusivity_proven":False' in text
    assert "import subprocess" not in text
    assert "xsdb " not in text
    assert "devmem " not in text

def test_no_unplanned_benchmark_runner_for_six_sessions():
    # This PR admits exactly ONE rebuilt A2.1 physical revalidation,
    # NOT the historical 3-pair, six fresh-coldboot system benchmark.
    runner=read(RUNNER)
    assert 'MODE=A2_1' in runner
    assert "P08_B46_NEW_REBUILT_A21_ORIGINAL_1024_PHYSICAL_AND_INDEPENDENT_PASS=1" in runner
    assert "P08_B46_SIX_REPEATED_A_B_SESSION_BENCHMARK_ACCEPTED=0" in runner
    assert "P08_B45_PERF_FULL1024_SAME_SESSION_JTAG_SCALAR_FNV_AND_BACKUP_PASS=1" not in runner
