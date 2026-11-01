"""P07-B.4g incident regression: observed FPD 0x2560 must skip ALL PL MMIO.

Runs fake Tcl XSDB *only*, never connects to board. Optional separate
PS-only script must read exactly two SLCR registers and no 0xA4000000.
"""
from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest

ROOT=Path(__file__).resolve().parents[1]
STRICT=ROOT/"vivado/p07_b4g_readonly_shell.tcl"
PS_ONLY=ROOT/"vivado/p07_b4g_ps_width_only.tcl"
PS_FPD="0xFD615000"
PS_LPD="0xFF419000"
PL_BASE="0xA4000000"
DATA={
    PS_FPD:"0x00000A00",
    PS_LPD:"0x00000200",
    PL_BASE:"0x4C543302",
    "0xA4000004":"0x00010000",
    "0xA4000008":"0x0001031F",
    "0xA400000C":"0x00000000",
    "0xA4000054":"0x00000000",
}


def fake_xsdb(tmp_path,script,fpd="0x00002560",missing_ps=None):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable; CI tclsh required")
    values=DATA | {PS_FPD:fpd}
    if missing_ps:
        del values[missing_ps]
    pairs=" ".join(f"{k} {v}" for k,v in values.items())
    test=textwrap.dedent("""
        set argc 1
        set argv [list READ_ONLY_OPERATOR_APPROVED]
        proc connect {args} {puts "FAKE_CONNECT=1"}
        proc targets {args} {return PSU}
        proc disconnect {} {puts "FAKE_DISCONNECT=1"}
        proc stop {args} {error "ILLEGAL CPU STOP"}
        proc rst {args} {error "ILLEGAL RESET"}
        proc con {args} {error "ILLEGAL CPU RESUME"}
        proc mwr {args} {error "ILLEGAL REGISTER WRITE"}
        proc dow {args} {error "ILLEGAL MEMORY DOWNLOAD"}
        proc fpga {args} {error "ILLEGAL PL PROGRAM"}
    """)
    test+=f"set words [dict create {pairs}]\n"
    test+=textwrap.dedent("""
        proc mrd {args} {
            global words
            if {[lrange $args 0 3] ne {-force -value -size w}} {
                error "ILLEGAL NONSTANDARD XSDB READ"
            }
            if {[lindex $args end] ne "1"} {
                error "ILLEGAL READ BURST SIZE"
            }
            set addr [lindex $args end-1]
            puts "FAKE_MRD_ADDR=$addr"
            if {![dict exists $words $addr]} {
                error "FAKE REGISTER READ FAILURE $addr"
            }
            return [list [dict get $words $addr]]
        }
    """)
    test+=f"source {{{script}}}\n"
    path=tmp_path/"fake.tcl"
    path.write_text(test)
    return subprocess.run(["tclsh",str(path)],text=True,
                          capture_output=True,timeout=12)


def test_actual_fpd_0x2560_declares_64_and_skips_all_pl_reads(tmp_path):
    run=fake_xsdb(tmp_path,STRICT,fpd="0x00002560")
    assert run.returncode!=0
    assert "P07_B4G_FPD_RAW=0x00002560" in run.stdout
    assert "P07_B4G_FPD_HPM0_WIDTH_BITS=64" in run.stdout
    assert "P07_B4G_PS_WIDTH_MISMATCH_FPD=1" in run.stdout
    assert "SKIPPED ALL P03 MMIO READS" in run.stderr
    assert run.stdout.count("FAKE_MRD_ADDR=")==1
    assert "FAKE_MRD_ADDR="+PL_BASE not in run.stdout
    assert run.stdout.count("FAKE_DISCONNECT=1")==1
    assert "P07_B4G_READONLY_PS_PL_SNAPSHOT_FAIL=1" in run.stdout
    assert "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0" in run.stdout


def test_accepted_fpd128_still_reaches_exactly_six_reads(tmp_path):
    run=fake_xsdb(tmp_path,STRICT,fpd="0x00000A00")
    assert run.returncode==0,run.stderr
    assert "P07_B4G_FPD_HPM0_WIDTH_BITS=128" in run.stdout
    assert run.stdout.count("FAKE_MRD_ADDR=")==6
    assert "P07_B4G_READONLY_PS_PL_SNAPSHOT_PASS=1" in run.stdout
    assert "P07_B4G_PS_WIDTH_MISMATCH_FPD=1" not in run.stdout


def test_ps_only_diagnostic_can_read_64_fpd_without_any_pl_access(tmp_path):
    run=fake_xsdb(tmp_path,PS_ONLY,fpd="0x00002560")
    assert run.returncode==0,run.stderr
    assert "P07_B4G_PS_ONLY_FPD_HPM0_RAW=0x00002560" in run.stdout
    assert "P07_B4G_PS_ONLY_FPD_HPM0_WIDTH_BITS=64" in run.stdout
    assert "P07_B4G_PS_ONLY_LPD_HPM0_WIDTH_BITS=128" in run.stdout
    assert "P07_B4G_PS_ONLY_FPD128_MISMATCH=1" in run.stdout
    assert "P07_B4G_PS_ONLY_DONE_NO_PL_READ=1" in run.stdout
    assert "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0" in run.stdout
    assert run.stdout.count("FAKE_MRD_ADDR=")==2
    assert "FAKE_MRD_ADDR="+PL_BASE not in run.stdout
    assert run.stdout.count("FAKE_DISCONNECT=1")==1


def test_ps_only_fails_closed_and_disconnects_on_register_error(tmp_path):
    run=fake_xsdb(tmp_path,PS_ONLY,missing_ps=PS_LPD)
    assert run.returncode!=0
    assert "P07_B4G_PS_ONLY_FAIL=1" in run.stdout
    assert "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0" in run.stdout
    assert "FAKE_DISCONNECT=1" in run.stdout
    assert "FAKE_MRD_ADDR="+PL_BASE not in run.stdout


def test_ps_only_tcl_allowlist_no_p03_mmio_text():
    s=PS_ONLY.read_text()
    assert "0xA4000000" not in s
    assert s.count("p07_b4g_psread ")==3
    for bad in ("mwr","dow","rst","stop","con","fpga"):
        import re
        assert not re.search(r"(?m)^\s*"+bad+r"\s+",s),bad
