#ifndef LOIHI_TWIN_V3_P08_B2_SERVICE_METER_H
#define LOIHI_TWIN_V3_P08_B2_SERVICE_METER_H
/* P08-B2.2 software boundaries, portable C11.
 * The board adapter MUST use observed A53 CNTVCT_EL0/CNTFRQ_EL0.
 * These are NOT P03/PL accelerator cycles. No implicit inference speedup.
 */
#include <stdint.h>
#define P08_B2_METER_MAGIC UINT32_C(0x4D423832)
#define P08_B2_METER_BOUNDARIES 7u
#define P08_B2_METER_PHASES 6u
typedef enum {
    P08_B2_ENTRY=0,
    P08_B2_AFTER_STATE_RESTORE=1,
    P08_B2_AFTER_B13_INGRESS=2,
    P08_B2_AFTER_SCHEDULER_REINIT=3,
    P08_B2_AFTER_ALL_26_TICKS=4,
    P08_B2_AFTER_RECEIPT_VALIDATE=5,
    P08_B2_AFTER_JOURNAL_COMMIT=6
} p08_b2_boundary;
enum {P08_B2_METER_OK=0,P08_B2_METER_INVALID=-1,
      P08_B2_METER_NONMONOTONE=-2,P08_B2_METER_POISONED=-3};
typedef struct {
    uint32_t magic,frame_index,next_boundary,poisoned;
    uint64_t cntfrq_el0_hz;
    uint64_t cntvct[P08_B2_METER_BOUNDARIES];
} p08_b2_meter;
typedef struct {
    uint32_t frame_index,magic;
    uint64_t cntfrq_el0_hz,total_service_cycles;
    uint64_t phase_cycles[P08_B2_METER_PHASES];
    uint64_t service_entry_cntvct,service_commit_cntvct;
} p08_b2_image_timing;
/* start is called at the *very first* A53 image service instruction,
 * then mark each completed phase before any timing-sidecar I/O.
 * Oracle outside the A53 service is PC-only and NOT hidden in the timer.
 * P03-B trace hook is NESTED INSIDE the 27 dispatch operations each tick;
 * phase AFTER_ALL_26_TICKS includes ALL trace reads, paging, routing.
 */
int p08_b2_meter_start(p08_b2_meter *meter,uint32_t frame_index,
                       uint64_t observed_cntfrq,uint64_t t0);
int p08_b2_meter_mark(p08_b2_meter *meter,p08_b2_boundary boundary,
                      uint64_t observed_cntvct);
int p08_b2_meter_finish(const p08_b2_meter *meter,
                        p08_b2_image_timing *receipt);
#endif
