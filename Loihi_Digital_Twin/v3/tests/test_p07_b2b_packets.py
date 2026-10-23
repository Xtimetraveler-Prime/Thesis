"""Native C11 P07-B.2b baseline, no FPGA/B2 official TEST."""
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def test_packet_native_26_epoch_fail_closed(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    assert cc, "C11 compiler required"
    binary=tmp_path/"p07_b2b"
    subprocess.run([cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p07/include"),
        str(ROOT/"software/p07/p07_b2_packet.c"),
        str(ROOT/"tests/native/p07_b2b_packet_harness.c"),
        "-o",str(binary)],check=True,capture_output=True,text=True)
    result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
    assert result.stdout.strip()=="P07_B2B_NATIVE_PACKET_EPOCH_PASS=1"


def test_packet_native_4096_vs_4097_source_and_destination(tmp_path):
    """Synthetic native C boundary; no B2 artifact, FPGA or official TEST."""
    cc=shutil.which("cc") or shutil.which("gcc")
    assert cc, "C11 compiler required"
    binary=tmp_path/"p07_b2b_capacity"
    subprocess.run([cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p07/include"),
        str(ROOT/"software/p07/p07_b2_packet.c"),
        str(ROOT/"tests/native/p07_b2b_capacity_harness.c"),
        "-o",str(binary)],check=True,capture_output=True,text=True)
    result=subprocess.run([str(binary)],check=True,capture_output=True,
                          text=True,timeout=90)
    assert result.stdout.strip()=="P07_B2B_NATIVE_PACKET_CAPACITY_PASS=1"
