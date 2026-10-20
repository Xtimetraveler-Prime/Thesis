#ifndef LOIHI_TWIN_P07_B4B_BOARD_ADMISSION_H
#define LOIHI_TWIN_P07_B4B_BOARD_ADMISSION_H
/* P07-B.4b: READ-ONLY live-shell probe + bounded B4a DDR read adapter.
 * No image reset, memory reservation, source-spike provenance, or inference.
 * This is NOT a go-for-hardware-dispatch authorization.
 */
#include <stdint.h>
#include <stddef.h>
#include "p03_hw_adapter.h"
#include "p07_b4a_current_ingress.h"
#define P07_B4B_PROBE_MAGIC UINT32_C(0x42344250) /* 'PB4B' */
#define P07_B4B_FPD_REG UINT64_C(0xFD615000)
#define P07_B4B_CORE_END (P03_HW_BACKING_BASE + 27u*P03_HW_RECORD_BYTES)
enum { P07_B4B_OK=0, P07_B4B_BAD_ARGUMENT=-1,
       P07_B4B_BAD_WIDTH=-2, P07_B4B_SHELL=-3,
       P07_B4B_RANGE=-4, P07_B4B_READ=-5 };
typedef int (*p07_b4b_read_phys32)(void *context,uint64_t addr,uint32_t *out);
typedef struct {
    uint32_t magic, fpd_register, shell_id, shell_version;
    uint32_t capabilities, global_status, page_pending;
    uint32_t read_only_shell_probe_pass;
    uint32_t inference_authorized; /* ALWAYS zero. Physical GO is separate. */
} p07_b4b_probe_receipt;
typedef struct {
    uint32_t magic;
    p07_b4b_read_phys32 read_physical;
    void *read_context;
    uint32_t accepted_reads;
    uint32_t failed_reads;
} p07_b4b_ddr_reader;
/* A caller-owned FPD register reader is required for host testing; Xilinx
 * concrete implementation must be bound at firmware startup. P03 adapter
 * shell is checked via ORIGINAL p03_hw_identify and p03_hw_quiescent.
 * Only reads, never write, dispatch, page or touch reserved DDR. */
int p07_b4b_probe(p03_hw_adapter *hw,p07_b4b_read_phys32 physical_reader,
                  void *reader_context,p07_b4b_probe_receipt *out);
/* Bind B4a's read_ddr32 callback only after a successful read-only shell
 * probe. This software receipt does NOT establish exclusive ownership of
 * the P02 window (boot mode/linker/OS/resource checks still required). */
int p07_b4b_reader_init(p07_b4b_ddr_reader *r,
                        const p07_b4b_probe_receipt *probe,
                        p07_b4b_read_phys32 read_physical,void *ctx);
/* Strictly event-bank-only 27-core [0x40000000, 0x40D80000) pointer.
 * B4a independently invalidates the destination DDR span prior to read;
 * never use this function for full P02 record, checkpoint or stage access.
 * On rejection *out is unchanged. */
int p07_b4b_current_event_read(void *context,uint64_t physical,
                               uint32_t *out);
#endif
