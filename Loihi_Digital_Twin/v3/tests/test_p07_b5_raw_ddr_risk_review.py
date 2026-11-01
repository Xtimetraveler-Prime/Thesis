"""B5.3 standalone B5 DDR aperture and boot-ownership risk (PC ONLY)."""
from __future__ import annotations
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b5_raw_ddr_risk_review as review

def test_actual_P03_64MiB_broad_aperture_contains_new_B5_allocation():
    checks=review.check_source_memory_contract()
    assert checks and all(checks.values())
    assert review.BASE==0x40000000
    assert review.APERTURE_END==0x44000000
    assert review.RECORD_END==0x40D80000
    assert review.TRACE==(0x42000000,0x420CD280)
    assert review.MAILBOX==(0x43FF0100,0x43FF0200)
    assert review.OLD_MAILBOX==(0x43FF0000,0x43FF0100)
    assert review.LOW_DDR==(0,0x00107BC0)
    assert review.LOW_DDR[1]-review.V3_LOW_DDR[1]==4288
    assert review.TRACE[1]-review.TRACE[0]==840320
    assert review.BASE<review.TRACE[0]<review.TRACE[1]<review.APERTURE_END
    assert review.BASE<review.MAILBOX[0]<review.MAILBOX[1]<review.APERTURE_END
    assert review.TRACE[0]>=review.RECORD_END
    assert review.MAILBOX[0]>=review.RECORD_END

def test_host_review_requires_real_frozen_signed_elf_and_offline_report(tmp_path):
    with pytest.raises((ValueError,OSError)):
        review.review(
            offline=tmp_path/"fake.json",
            build=tmp_path/"not_a_real_build",
            reports=tmp_path/"not_real_xsa",
            frozen=tmp_path/"no_real_frozen_train",
            routes=tmp_path/"not_real_signed_routes",
        )

def test_static_PC_review_inherently_cannot_be_a_DDR_ownership_proof():
    source=(ROOT/"scripts/p07_b5_raw_ddr_risk_review.py").read_text()
    assert '"trace_and_new_mailbox_are_WITHIN_broad_P03_64MiB_aperture":True' in source
    assert '"trace_sidecar_exclusively_owned_by_new_A53":False' in source
    assert '"mailbox_exclusively_owned_by_new_A53":False' in source
    assert '"low_DDR_free_of_boot_firmware_independently_proven":False' in source
    assert '"other_APU_RPU_or_DMA_masters_quiescent_proven":False' in source
    assert '"destructive_board_execution_authorized":False' in source
    assert '"actual_KV260_accessed":False' in source
    assert "xsdb" not in source and "program_hw_devices" not in source
    assert "P07_B5_RAW_BOARD_CONTACT=0" in source
