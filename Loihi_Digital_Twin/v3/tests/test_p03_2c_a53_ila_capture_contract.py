"""Static regression for same-execution A53 mailbox and two ILA captures."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "scripts/run_p03_2c_a53_ila_capture.sh"


def test_correlated_a53_ila_capture_runs_with_both_analyzers_armed_first():
    s = SHELL.read_text(encoding="utf-8")
    assert "vivado/p03_2c_ila_capture.tcl" in s
    assert "vivado/p03_2c_xsdb_run.tcl" in s
    assert s.index('[[ -f "$ARMED_MARKER" ]]') < s.index('xsdb vivado/p03_2c_xsdb_run.tcl')
    assert "p03_2c_mmio_slave_capture.csv" in s
    assert "p03_2c_hpm0_capture.csv" in s
    assert "p03_2c_a53_readonly_mailbox.bin" in s


def test_correlated_capture_preserves_artifacts_and_candidate_identity():
    s = SHELL.read_text(encoding="utf-8")
    for item in (
        'if [[ -e "$OUT_DIR" ]]',
        'candidate_xsa_sha256=',
        'candidate_bit_sha256=',
        'candidate_ltx_sha256=',
        'a53_elf_sha256=',
        'a53_mmio_base=',
        '0x80000000|0xA4000000',
        'P03_2C_EXPECTED_XSA_SHA',
        'P03_2C_READONLY_MMIO_BASE',
        'P03_DIAG_REPORTS',
        'P03_2C_BUILD_DIR',
        'vivado/p03_2c_xsdb_prepare.tcl',
        'vivado/p03_2c_program_bitstream.tcl',
        'p03_2c_verify_readonly.py',
        'VERIFY_EXIT=',
        'P03_2C_A53_MAILBOX_VERIFY_EXIT=',
    ):
        assert item in s
    assert "xsdb_single_mmio_read.tcl" not in s
    assert "rm -rf" not in s


def test_correlated_capture_does_not_confuse_bad_mmio_data_with_failed_capture():
    s = SHELL.read_text(encoding="utf-8")
    assert "set +e" in s
    assert "VERIFY_EXIT=${PIPESTATUS[0]}" in s
    assert "PASS: P03.2c A53-originated dual-ILA capture artifacts collected (not MMIO acceptance)" in s
    assert "reboot KV260" in s
