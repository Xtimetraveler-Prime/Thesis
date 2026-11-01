"""PC-only Tcl interpreter smoke tests for NEW B5 physical capture launcher.

Never calls XSDB/Vivado/PSU nor changes anything on KV260. Verify that
missing/wrong arguments fail at initial gate, the address arithmetic and
atomic physical trace output mode are valid Tcl on the host.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
TCL=ROOT/"vivado/p07_b5_raw_trace_xsdb_run.tcl"
TOKEN="B5_RAW_A53_NEW_DDR_TRACE_AND_MAILBOX_EXPLICITLY_APPROVED"

@pytest.fixture(scope="module")
def tclsh():
    exe=shutil.which("tclsh")
    if not exe:
        pytest.skip("system Tcl interpreter missing; B5 Tcl smoke not run")
    return exe

def run_tcl(exe:str,script:str):
    return subprocess.run([exe],input=script,text=True,capture_output=True,
                          timeout=15)

def test_real_new_tcl_rejects_all_early_arg_mismatches_before_board(tclsh,tmp_path):
    source=str(TCL).replace("\\","\\\\").replace("}","\\}")
    for args in ("","NO_B5_APPROVAL fake.elf a b c localhost:3121",
                 "B5_RAW_A53_NEW_DDR_TRACE_AND_MAILBOX_EXPLICITLY_APPROVED"):
        program=(
            "set argv [list "+args+"]\n"
            "set argc [llength $argv]\n"
            "if {[catch {source {"+source+"}} why]} {puts \"EXPECTED_NO_GO=$why\"} "
            "else {puts \"UNSAFE_SUCCESS\"}\n"
        )
        p=run_tcl(tclsh,program)
        assert p.returncode==0,p.stderr
        assert "B5 RAW: require exact operator contract token" in p.stdout
        assert "UNSAFE_SUCCESS" not in p.stdout
        assert "P07_B5_RAW_NEW_A53_ELF_DOWNLOADED=1" not in p.stdout

def test_actual_tcl_atomic_trace_file_creation_and_4096_word_read_segments(tclsh,tmp_path):
    f=tmp_path/"one_new_trace.bin"
    script="""set output {"""+str(f)+"""}
set h [open $output {WRONLY CREAT EXCL}]
fconfigure $h -translation binary -encoding binary
puts -nonewline $h [binary format H* 00010203]
close $h
set total 210080
set count 0
for {set offset 0} {$offset<$total} {incr offset 4096} {
    set words [expr {min(4096,$total-$offset)}]
    set address [format {0x%08X} [expr {0x42000000+4*$offset}]]
    if {$words>4096 || $address eq ""} {error "invalid chunk"}
    incr count $words
}
puts "WORDS=$count"
if {![catch {open $output {WRONLY CREAT EXCL}} why]} {error "existing evidence clobbered"}
puts "NO_CLOBBER=1"
"""
    proc=run_tcl(tclsh,script)
    assert proc.returncode==0,proc.stderr+proc.stdout
    assert "WORDS=210080" in proc.stdout
    assert "NO_CLOBBER=1" in proc.stdout
    assert f.read_bytes()==bytes.fromhex("00010203")

def test_xsdb_capture_has_pinned_new_elf_no_old_V3_launcher_or_board_on_preflight():
    text=TCL.read_text()
    assert TOKEN in text
    assert "0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf" in text
    assert "0x42000000" in text and "0x420CD280" in text
    assert "0x43FF0100" in text
    assert "mrd -bin -file $chunk $address $words" in text
    assert "set destination [open $trace {WRONLY CREAT EXCL}]" in text
    assert "b5_ps_only" in text
    assert "P07_B5_RAW_840320_BYTE_PSU_PHYSICAL_TRACE_READBACK_CAPTURED=1" in text
    assert "P07_B5_RAW_A53_COLD_POWER_CYCLE_REQUIRED=1" in text
