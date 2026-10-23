"""Native C acceptance for the packed original B2.4 route table wire layout.

The fixed-layout fixture is synthetic and uses only original P03 adapter,
B2b decoder structs and original SHA256 algorithm. NOT a real KV260 result.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("dense",[False,True])
def test_original_frozen_c_route_parser_and_strict_sha(tmp_path,dense):
    cc=shutil.which("cc") or shutil.which("gcc")
    assert cc
    exe=tmp_path/("route_loader_dense" if dense else "route_loader")
    sources=[
        "software/p03/p03_hw_adapter.c",
        "software/p07/p07_b3_pager.c",
        "software/p07/p07_b2_packet.c",
        "software/p07/p07_b3c_packet_bridge.c",
        "software/p07/p07_b3c2_hw_scheduler.c",
        "software/p07/p07_b3c3_next_commit.c",
        "software/p07/p07_b4m_frozen_routes.c",
        "software/p07/p07_a2_sha256.c",
        "tests/native/p07_b4m_frozen_routes_harness.c",
    ]
    built=subprocess.run([
        cc,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
        "-O1",
        *(["-DP07_B2_MAX_ROUTE_BINDINGS=10000u", "-DP07_B4M_DENSE_ROUTES=1"] if dense else []),
        "-I",str(ROOT/"software/p07/include"),
        "-I",str(ROOT/"software/p03/include"),
        "-I",str(ROOT/"software/p05/include"),
        *(str(ROOT/p) for p in sources),"-o",str(exe)
    ],capture_output=True,text=True,timeout=120)
    assert built.returncode==0,built.stdout+built.stderr
    ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
    assert ran.returncode==0,ran.stdout+ran.stderr
    assert ran.stdout.splitlines()==[
        ("P07_B4M_FROZEN_10000_DENSE_ROUTES_C11_NATIVE_PASS=1"
         if dense else "P07_B4M_FROZEN_ROUTES_C11_NATIVE_MOUNT_PASS=1"),
        "P07_B4M_FROZEN_ROUTES_SHA_AND_TOPOLOGY_FAIL_CLOSED=1",
        "P07_B4M_FROZEN_ROUTES_REAL_BOARD_STAGED=0",
    ]


def test_packing_contract_matches_host_fixed_layout():
    host=(ROOT/"scripts/p07_b4m_frozen_inputs.py").read_text()
    header=(ROOT/"software/p07/include/p07_b4m_frozen_routes.h").read_text()
    assert 'OUT_BYTES=0x14000' in host
    assert 'IN_BYTES=0xE0000' in host
    assert 'IN_BASE=0x41000000' in host
    assert 'OUT_BASE=0x43FC4000' in host
    assert "P07_B4M_ROUTE_OUT_BASE UINT32_C(0x43FC4000)" in header
    assert "P07_B4M_ROUTE_IN_BASE UINT32_C(0x41000000)" in header
