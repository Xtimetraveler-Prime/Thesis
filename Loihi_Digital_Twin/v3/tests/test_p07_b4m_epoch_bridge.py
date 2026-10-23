"""P07-B.4m.1 strictly native integration, not a KV260 acceptance gate.

Reuses the *original* P03 adapter, B3a pager, B3c1 packet conversion,
B3c2 physical scheduler and B3c3 physical NEXT insertion on the accepted
fake-MMIO/DDRx event-bus harness. No frozen B2 official TEST or bitstream.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_original_p03_b3_multitick_provenance_next_barrier_bridge(tmp_path):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "A native C11 compiler is required"
    out = tmp_path / "p07_b4m_1_epoch_bridge"
    sources = (
        "software/p03/p03_hw_adapter.c",
        "software/p07/p07_b3_pager.c",
        "software/p07/p07_b2_packet.c",
        "software/p07/p07_b3c_packet_bridge.c",
        "software/p07/p07_b3c2_hw_scheduler.c",
        "software/p07/p07_b3c3_next_commit.c",
        "software/p07/p07_b4m_epoch_bridge.c",
        "tests/native/p07_b4m_epoch_bridge_harness.c",
    )
    command = [
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O1",
        "-I", str(ROOT / "software/p07/include"),
        "-I", str(ROOT / "software/p03/include"),
        "-I", str(ROOT / "software/p05/include"),
        "-I", str(ROOT / "tests/native"),
        *(str(ROOT / path) for path in sources),
        "-o", str(out),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert compiled.returncode == 0, (
        "Strict C11 compile failed:\n" + compiled.stdout + compiled.stderr
    )
    ran = subprocess.run(
        [str(out)], capture_output=True, text=True, timeout=120
    )
    assert ran.returncode == 0, (
        "Native original-P03 fake-bus harness failed:\n"
        + ran.stdout + ran.stderr
    )
    assert ran.stdout.splitlines() == [
        "P07_B4M_1_NATIVE_702_DISPATCH_26_ACK_ORIGINAL_P03_FAKE_BUS_PASS=1",
        "P07_B4M_1_NATIVE_SOURCE_PROVENANCE_AND_NEXT_FAULTS_FAIL_CLOSED=1",
        "P07_B4M_1_REAL_KV260_EXECUTED=0",
    ]


def test_bridge_never_accepts_synthetic_proof_as_board_evidence():
    header = (ROOT / "software/p07/include/p07_b4m_epoch_bridge.h").read_text()
    source = (ROOT / "software/p07/p07_b4m_epoch_bridge.c").read_text()
    assert "Production callers" in header
    assert "source_evidence_verified!=1u" in source
    assert "p07_b3c_encode_frame(" in source
    assert "p07_b3c3_prepare(" in source
    assert "p07_b3c3_commit(" in source
    assert "p07_b3c2_barrier_ack(" in source
    assert source.index("p07_b3c3_commit(") < source.index(
        "p07_b3c2_barrier_ack("
    )
    assert "P07_B4M_1_REAL_KV260_EXECUTED=0" in (
        ROOT / "tests/native/p07_b4m_epoch_bridge_harness.c"
    ).read_text()
