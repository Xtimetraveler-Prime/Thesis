#include "p07_b4b_board_admission.h"
#include "p03_mmio.h"
#include <string.h>
_Static_assert(P07_B4B_CORE_END == UINT64_C(0x40D80000),
               "frozen 27 P02 records do not fit expected physical range");
_Static_assert(P03_HW_EVENT1_OFFSET - P03_HW_EVENT0_OFFSET ==
               P03_HW_EVENT_DEPTH*sizeof(uint32_t),
               "event-bank record geometry drift");
static int checked_event(uint64_t addr){
    uint64_t relative;uint32_t offset;
    if(addr<P03_HW_BACKING_BASE||addr>P07_B4B_CORE_END-4u||
       (addr&UINT64_C(3))!=0u)return 0;
    relative=addr-P03_HW_BACKING_BASE;
    offset=(uint32_t)(relative%P03_HW_RECORD_BYTES);
    return (offset>=P03_HW_EVENT0_OFFSET &&
            offset<P03_HW_EVENT0_OFFSET+P03_HW_EVENT_DEPTH*4u) ||
           (offset>=P03_HW_EVENT1_OFFSET &&
            offset<P03_HW_EVENT1_OFFSET+P03_HW_EVENT_DEPTH*4u);
}
int p07_b4b_probe(p03_hw_adapter *hw,p07_b4b_read_phys32 read_phys,
                  void *ctx,p07_b4b_probe_receipt *out){
    uint32_t width=0u;
    p07_b4b_probe_receipt proposed={0};
    if(!hw||!read_phys||!ctx||!out||
       hw->backing_base!=P03_HW_BACKING_BASE||
       hw->last_error!=P03_HW_OK)return P07_B4B_BAD_ARGUMENT;
    if(read_phys(ctx,P07_B4B_FPD_REG,&width)!=0)return P07_B4B_READ;
    if(((width>>8u)&3u)!=2u)return P07_B4B_BAD_WIDTH;
    /* P03's original adapter performs the exact ID/version/caps check and
     * a fresh global-idle / zero-DMA-pending check; no writable commands. */
    if(p03_hw_identify(hw)!=P03_HW_OK ||
       p03_hw_quiescent(hw)!=P03_HW_OK)return P07_B4B_SHELL;
    proposed.magic=P07_B4B_PROBE_MAGIC;
    proposed.fpd_register=width;
    proposed.shell_id=P03_MMIO_ID_VALUE;
    proposed.shell_version=P03_MMIO_VERSION_VALUE;
    proposed.capabilities=UINT32_C(0x0001031F);
    proposed.global_status=0u;proposed.page_pending=0u;
    proposed.read_only_shell_probe_pass=1u;
    proposed.inference_authorized=0u;
    *out=proposed;
    return P07_B4B_OK;
}
int p07_b4b_reader_init(p07_b4b_ddr_reader *r,
                        const p07_b4b_probe_receipt *proof,
                        p07_b4b_read_phys32 callback,void *ctx){
    p07_b4b_ddr_reader candidate={0};
    if(!r||!proof||!callback||!ctx||
       proof->magic!=P07_B4B_PROBE_MAGIC ||
       !proof->read_only_shell_probe_pass ||
       proof->inference_authorized!=0u ||
       ((proof->fpd_register>>8u)&3u)!=2u ||
       proof->shell_id!=P03_MMIO_ID_VALUE ||
       proof->shell_version!=P03_MMIO_VERSION_VALUE ||
       proof->capabilities!=UINT32_C(0x0001031F) ||
       proof->global_status!=0u||proof->page_pending!=0u)
        return P07_B4B_BAD_ARGUMENT;
    candidate.magic=P07_B4B_PROBE_MAGIC;
    candidate.read_physical=callback;candidate.read_context=ctx;
    *r=candidate;
    return P07_B4B_OK;
}
int p07_b4b_current_event_read(void *context,uint64_t address,
                               uint32_t *value){
    p07_b4b_ddr_reader *r=(p07_b4b_ddr_reader *)context;
    uint32_t word=0u;
    if(!r||!value||r->magic!=P07_B4B_PROBE_MAGIC ||
       !r->read_physical||!r->read_context)
        return P07_B4B_BAD_ARGUMENT;
    if(!checked_event(address))return P07_B4B_RANGE;
    if(r->read_physical(r->read_context,address,&word)!=0){
        ++r->failed_reads;
        return P07_B4B_READ;
    }
    *value=word;++r->accepted_reads;
    return P07_B4B_OK;
}
