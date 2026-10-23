"""B4m new Vitis candidate provenance and mailbox verifier. HOST ONLY."""
from pathlib import Path
import importlib.util
import shutil
import struct
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "b4m_verify",ROOT/"scripts/p07_b4m_verify_full_receipt.py"
)
verify=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(verify)


def mailbox():
    w=[0]*64
    w[0]=verify.MAGIC
    w[1]=1
    w[2]=verify.PASS
    w[12]=verify.FULL_MAGIC
    w[13]=26
    w[14]=702
    w[15]=702
    w[16]=699
    w[17]=3
    w[18]=784*25
    w[19]=1000
    w[20]=800
    w[21]=800
    w[22]=3
    w[23]=21384
    w[24]=1010
    w[25]=0xAABBCCDD
    w[26]=0x11223344
    read_bytes=702*438272
    write_bytes=702*106496
    w[27]=read_bytes&0xffffffff
    w[28]=read_bytes>>32
    w[29]=write_bytes&0xffffffff
    w[30]=write_bytes>>32
    w[31]=5616
    w[35]=42   # readout neuron3 emitted 42 verified spikes
    w[46]=702
    w[63]=verify.DONE
    return w


def test_complete_physical_mailbox_synthetic_shape_without_claiming_parity():
    result=verify.verify(struct.pack("<64I",*mailbox()),expected_class=3)
    assert result["physical_dispatches"]==702
    assert result["physical_barriers_acked"]==26
    assert result["physical_page_ins"]==702
    assert result["physical_dirty_page_outs"]==699
    assert result["physical_final_page_outs"]==3
    assert result["trained_readout_prediction"]==3
    assert result["P03_packet_words_captured"]==800
    assert result["NEXT_packets_physically_inserted"]==800
    assert result["independent_full_neuron_numerical_parity"] is False
    assert result["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"


@pytest.mark.parametrize("index,new",[
    (0,0),(1,2),(2,0),(3,42),
    (11,1),(12,0),(13,25),(14,701),(15,701),
    (16,700),(17,2),(18,0),(19,0),(20,801),
    (22,11),(23,0),(24,1009),(25,0),(26,0),
    (31,0),(32,99),(42,1),(43,1),(44,1),(45,1),
    (46,0),(47,1),(63,0),
])
def test_false_physical_acceptance_markers_rejected(index,new):
    w=mailbox()
    w[index]=new
    with pytest.raises(verify.FullReceiptError):
        verify.verify(struct.pack("<64I",*w),expected_class=3)


def test_wrong_class_rejected_even_with_valid_counters():
    with pytest.raises(verify.FullReceiptError):
        verify.verify(struct.pack("<64I",*mailbox()),expected_class=9)


def test_real_vitis_stage_source_set_and_no_board_execution(tmp_path):
    sh=ROOT/"scripts/build_p07_b4m_full.sh"
    code=(ROOT/"software/p07/build_p07_b4m_full.py").read_text()
    board=(ROOT/"software/p07/p07_b4m_full_board.c").read_text()
    script=sh.read_text()
    if shutil.which("bash"):
        subprocess.run(["bash","-n",str(sh)],check=True,capture_output=True)
    assert 'APP="p07_b4m_full_26tick"' in code
    assert 'IDENTITY="P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1"' in code
    for module in (
        "p07_b4m_full_board.c",
        "p07_b4m_full_inference.c",
        "p07_b4m_spike_trace.c",
        "p07_b4m_frozen_routes.c",
        "p07_b4m_epoch_bridge.c",
    ):
        assert module in code
        assert module in script
    assert 'P07_B4M_REAL_BOARD_RUN_AUTHORIZED=0' in script
    assert 'P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1' in board
    assert "p07_b4m_full_run(" in board
    assert "p07_b4m_mount_frozen_routes(" in board
    assert "B4L_BIND_BASE" in board
    assert "P07_B4M_FRAME_BASE" in board
    assert "P07_B4M_FRAME_MAX_BYTES" in board
    assert "mailbox[63]=B4M_MAILBOX_DONE" in board
