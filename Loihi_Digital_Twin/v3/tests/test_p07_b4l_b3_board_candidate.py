"""B4l standalone A53 first-epoch B3/P03 candidate contract: native ONLY."""
from __future__ import annotations

from pathlib import Path
import struct
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4l_verify_b3_epoch as v


def fixture():
    w=[0]*64
    w[0]=v.RECEIPT_MAGIC
    w[1]=1
    w[2]=v.PASS
    w[11]=v.ONE_EPOCH_MAGIC
    w[12],w[13],w[14]=27,27,24
    w[15],w[16]=1,0
    w[17],w[18]=0,27  # zero-input dispatches may generate 0 packets
    w[19],w[20]=1,2
    w[24],w[25],w[26]=51,27,0xA00
    w[33],w[34],w[35]=27,20384,1010
    expected=27*v.READ_PAGE_BYTES+24*v.DIRTY_PAGE_BYTES
    w[36],w[37]=expected&0xFFFFFFFF,expected>>32
    w[40],w[41],w[42]=27,24,27
    w[44]=w[45]=0xFFFFFFFF
    w[63]=v.DONE
    return w


def test_strict_non_26_tick_proof_accepts_zero_emission():
    expected=v.verify(struct.pack("<64I",*fixture()))
    assert expected["physical_scheduler_dispatches"]==27
    assert expected["barrier_acknowledged"] is False
    assert expected["captured_P03_packet_words"]==0
    assert expected["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"


@pytest.mark.parametrize(("idx","val"),[
    (0,0),(1,2),(2,0xDEAD0000),(3,1),
    (4,1),(5,1),(6,1),(7,1),(8,1),(9,1),(10,1),
    (11,0),(12,26),(13,26),(14,23),
    (15,0),(16,1),(17,8193),(18,26),
    (19,0),(21,1),(22,1),(23,1),(24,50),(25,26),
    (26,0x2560),(27,1),(28,1),(29,1),(30,1),(31,1),(32,1),
    (33,26),(34,0),(35,0),(36,0),(38,1),(39,1),
    (40,26),(41,25),(42,26),(43,1),(44,0),(45,0),
    (50,1),(63,0)
])
def test_any_false_packet_routing_barrier_or_dispatch_claim_fails(idx,val):
    w=fixture()
    w[idx]=val
    if idx==19:
        w[20]=0
    with pytest.raises(ValueError,match="NO-GO"):
        v.verify(struct.pack("<64I",*w))


def test_wrong_mailbox_length_rejected():
    full=struct.pack("<64I",*fixture())
    for data in [full[:-1],full+b"\x00",b""]:
        with pytest.raises(ValueError,match="256"):
            v.verify(data)


def test_new_elf_builder_includes_original_b3c2_p03_frozen_metadata_sources():
    from importlib.util import spec_from_file_location,module_from_spec
    builder=ROOT/"software/p07/build_p07_b4l_b3_epoch.py"
    spec=spec_from_file_location("b4l_b3_vitis_builder",builder)
    module=module_from_spec(spec)
    spec.loader.exec_module(module)
    source=set(module.SOURCES)
    headers=set(module.HEADERS)
    assert module.APP=="p07_b4l_b3_first_epoch"
    assert module.IDENTITY=="P07_B4L_A53_B3_ONE_EPOCH_V1"
    for p in ("p07_b4l_b3_epoch_board.c","p07_b4l_b3_epoch.c",
              "p07_b4l_b3_bindings.c","p07_b3c2_hw_scheduler.c",
              "p07_b3_pager.c","p07_b2_packet.c",
              "p07_b3c_packet_bridge.c","p07_b3c3_next_commit.c",
              "p03_hw_adapter.c","p03_hw_xilinx_io.c",
              "p07_a2_sha256.c"):
        assert p in source
    for p in ("p07_b3c2_hw_scheduler.h","p07_b4l_b3_bindings.h",
              "p07_b4l_b3_epoch.h","p03_hw_adapter.h",
              "p05_deployment.h","p07_a2_sha256.h"):
        assert p in headers
    wrapper=(ROOT/"scripts/build_p07_b4l_b3_epoch.sh").read_text()
    assert "P07_B4L_REAL_B3_ONE_EPOCH_VITIS_ELF_AND_MAP_BUILT=1" in wrapper
    assert "P07_B4L_B3_ONE_EPOCH_PHYSICAL_BOARD_RUN_AUTHORIZED=0" in wrapper
    assert "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f" in wrapper


def test_real_board_code_binds_original_metadata_before_scheduler_runs():
    c=(ROOT/"software/p07/p07_b4l_b3_epoch_board.c").read_text()
    assert c.index("b4l_bind_frozen(&hw")<c.index("p07_b3_init(&pager")
    assert c.index("p07_b3_init(&pager")<c.index("p07_b3c2_init(")
    assert c.index("p07_b3c2_init(")<c.index("p07_b4l_b3_one_epoch(")
    assert "Xil_DCacheInvalidateRange" in c
    assert "p03_hw_xilinx_fpd128_ready" in c
    assert "mailbox[30]=0u" in c
    assert "mailbox[31]=0u" in c
    assert "mailbox[32]=0u" in c
    assert "P07_B4L_A53_B3_ONE_EPOCH_V1" in c
    assert "p07_b3c2_barrier_ack" not in c
