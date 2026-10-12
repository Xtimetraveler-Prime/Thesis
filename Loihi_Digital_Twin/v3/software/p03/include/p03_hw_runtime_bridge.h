#ifndef LOIHI_TWIN_V3_P03_HW_RUNTIME_BRIDGE_H
#define LOIHI_TWIN_V3_P03_HW_RUNTIME_BRIDGE_H
#include "p03_hw_adapter.h"

/* P03.3b1: policy-to-MMIO binding. Deployment validation, P02 digest
 * verification, initial input injection and result recording remain
 * supplied by the board boot/application layer (P03.3c).
 *
 * The user callbacks MUST be real board-local implementations; a
 * placeholder that reports success without the work is not acceptable
 * for physical autonomy or P03.4 acceptance.
 */
typedef struct {
    p03_hw_adapter *hw;
    p03_rt *runtime;
    void *app_cookie;
    int (*validate_deployment)(void *app_cookie);
    int (*validate_backing)(void *app_cookie);
    int (*load_input)(void *app_cookie);
    int (*write_result)(void *app_cookie, const p03_rt *rt);
    uint64_t (*read_ticks)(void *app_cookie);
    void (*on_error)(void *app_cookie, const p03_rt *rt);
} p03_hw_runtime_bridge;

/* Populates a real set of page/dispatch/drain/barrier callbacks. A53
 * application owns the startup validation, result persistence and input
 * bootstrap callbacks. No host-initiated algorithmic action is required.
 */
int p03_hw_bind_runtime(p03_hw_runtime_bridge *bridge, p03_rt_ops *out_ops);
#endif
