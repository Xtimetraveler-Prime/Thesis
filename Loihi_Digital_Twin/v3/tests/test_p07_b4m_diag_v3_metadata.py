"""P07-B.4m metadata repair: native C + RTL contract checks, NO board.
Uses synthetic P02 headers; never substitutes fake assets for genuine B2.4.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import p07_b4m_diagnose_physical_mailbox as decoder

ROOT=Path(__file__).resolve().parents[1]
C_SOURCE=ROOT/"software/p07/p07_b4m_dispatch_metadata.c"
HEADER=ROOT/"software/p07/include/p07_b4m_dispatch_metadata.h"

HARNESS=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "p07_b4m_dispatch_metadata.h"
static p03_hw_adapter hw;
static uint8_t h[27][0x38];
static const uint8_t *ptrs[27];

static void write32(uint8_t *p,uint32_t x){
    p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8);p[2]=(uint8_t)(x>>16);p[3]=(uint8_t)(x>>24);
}
static void setup(void){
    uint32_t c;
    memset(&hw,0,sizeof(hw));
    hw.backing_base=P03_HW_BACKING_BASE;
    for(c=0u;c<27u;c++){
        uint32_t n=c==0 ? 39u : (c==26 ? 10u : 40u);
        uint32_t syn=c==0 ? 30576u : (c==26 ? 10000u : 1000u);
        uint32_t route=c==0 ? 100u : (c==26 ? 0u : 100u);
        memcpy(h[c],"LTV3CTX1",8);
        write32(h[c]+8,1);write32(h[c]+12,0x1000);write32(h[c]+16,0x80000);
        write32(h[c]+20,c);write32(h[c]+24,0);write32(h[c]+28,0);
        write32(h[c]+32,n);write32(h[c]+36,syn);write32(h[c]+40,route);
        write32(h[c]+44,0);write32(h[c]+48,0);write32(h[c]+52,0);
        hw.configured[c]=1;
        hw.metadata[c]=((uint64_t)n << 7)|c;
        ptrs[c]=h[c];
    }
}
#define ASSERT(c) do{if(!(c)){fprintf(stderr,"FAILED %s line %d\n",#c,__LINE__);return 2;}}while(0)
int main(void){
    uint64_t baseline;
    setup();
    /* Actual HLS source semantics: a nonempty row is illegal with
     * the old zero synapse_count, legal after matching 30576 metadata. */
    ASSERT(((hw.metadata[0]>>18)&0xffffu)==0);
    ASSERT(12u+51u>((hw.metadata[0]>>18)&0xffffu));
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_OK);
    ASSERT(hw.metadata[0] == (((uint64_t)39u<<7)|
           ((uint64_t)30576u<<18)|((uint64_t)100u<<34)));
    ASSERT(hw.metadata[26] == (((uint64_t)26u)|((uint64_t)10u<<7)|
           ((uint64_t)10000u<<18)));
    ASSERT((hw.metadata[0]>>47)==0u);
    ASSERT(12u+51u<=((hw.metadata[0]>>18)&0xffffu));
    /* Simulate p03_hw_dispatch adding CURRENT 51 events without
     * clobbering the synapse or route count. */
    ASSERT((((hw.metadata[0]&~(UINT64_C(0x1fff)<<47))|
         (UINT64_C(51)<<47))>>47)==51u);
    setup();baseline=hw.metadata[0];write32(h[26]+36,32769u);
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    ASSERT(hw.metadata[0]==baseline); /* all-or-nothing */
    setup();write32(h[5]+40,4097u);
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    setup();write32(h[5]+20,4u);
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    setup();write32(h[5]+32,1u);
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    setup();write32(h[5]+48,2u);
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    setup();h[4][0]='X';
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    setup();hw.last_error=P03_HW_PROTOCOL;
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    setup();hw.metadata[0]|=UINT64_C(1)<<18;
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    setup();ptrs[25]=0;
    ASSERT(p07_b4m_apply_p02_counts(&hw,ptrs)==P07_B4M_METADATA_REJECT);
    puts("P07_B4M_DIAG_V3_METADATA_ATOMIC_NATIVE_PASS=1");
    return 0;
}
'''
def test_native_original_header_metadata_repair(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    if not cc:
        pytest.skip("native compiler not installed")
    harness=tmp_path/"metadata_harness.c"
    binary=tmp_path/"metadata_harness"
    harness.write_text(HARNESS)
    c=subprocess.run([cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
                      "-I",str(ROOT/"software/p07/include"),
                      "-I",str(ROOT/"software/p03/include"),
                      str(C_SOURCE),str(harness),"-o",str(binary)],
                     capture_output=True,text=True,timeout=60)
    assert c.returncode==0,c.stdout+c.stderr
    run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=20)
    assert run.returncode==0,run.stdout+run.stderr
    assert "P07_B4M_DIAG_V3_METADATA_ATOMIC_NATIVE_PASS=1" in run.stdout

def test_wired_rtl_metadata_and_original_header_contract():
    rtl=(ROOT/"rtl/p08_paged_dispatch_controller.v").read_text()
    bd=(ROOT/"vivado/create_p03_mmio_impl_project.tcl").read_text()
    adapter=(ROOT/"software/p03/p03_hw_adapter.c").read_text()
    freeze=(ROOT/"src/loihi_twin_v2/ddr_abi.py").read_text()
    source=C_SOURCE.read_text()
    assert "assign core_synapse_count = metadata_latched[33:18];" in rtl
    assert "assign core_route_count = metadata_latched[46:34];" in rtl
    assert "assign core_event_count = metadata_latched[59:47];" in rtl
    assert "p08_paged_dispatch_controller_0/core_synapse_count loihi_core_v2_tick_0/synapse_count" in bd
    assert "p08_paged_dispatch_controller_0/core_route_count loihi_core_v2_tick_0/route_count" in bd
    assert "metadata |= (uint64_t)hw->event_counts[id][current_bank] << 47;" in adapter
    assert "image.synapse_count," in freeze and "image.route_count," in freeze
    assert "le32(p+0x24u)" in source and "le32(p+0x28u)" in source
    assert "hw->metadata[c]=candidate[c];" in source

def test_historical_v2_and_original_descriptor_remain_untouched():
    v2=(ROOT/"software/p07/p07_b4m_full_board_diag.c").read_text()
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2" in v2
    assert "p07_b4m_apply_p02_counts" not in v2
    original=(ROOT/"software/p07/p07_b4l_b3_bindings.c").read_text()
    assert "metadata!=(((uint64_t)ncomp<<7u)|((uint64_t)core))" in original
    assert "p07_b4m_apply_p02_counts" not in original

def test_v3_failure_mailbox_metadata_fix_status_is_not_v2_debug_address():
    import struct
    words=[0]*64
    words[2]=0xDEAD0000
    words[3]=9
    words[47]=decoder.DIAG_V3_MAGIC
    words[49]=10
    words[53]=0x4
    words[62]=0
    words[63]=decoder.accepted.DONE
    decoded=decoder.diagnose(struct.pack("<64I",*words))
    assert decoded["diagnostic_v2_failure_payload_present"] is False
    assert decoded["diagnostic_v3_failure_payload_present"] is True
    assert decoded["failure_telemetry"]["v3_dispatch_metadata_fix_status"]["uint32"]==0
    assert decoded["failure_telemetry"]["p03_dispatch_core_status_raw"]["uint32"]==4
    words[62]=0xFFFFFFFF
    failure=decoder.diagnose(struct.pack("<64I",*words))
    assert failure["failure_telemetry"]["v3_dispatch_metadata_fix_status"]["uint32"]==0xFFFFFFFF
    assert failure["all_structural_inference_receipt_checks_pass"] is False
