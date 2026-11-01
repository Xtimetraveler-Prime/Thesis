#ifndef LOIHI_TWIN_V3_P07_B4M_FROZEN_ROUTES_H
#define LOIHI_TWIN_V3_P07_B4M_FROZEN_ROUTES_H
/* Fixed read-only DDR image layout emitted by p07_b4m_frozen_inputs.py.
 * Original B2.4 B1.2 compiler SHA and capacity audit SHA hard-pinned.
 * Actual route-image bytes must also be independently checked against
 * host manifest/JTAG physical readbacks in the SAME dedicated run.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b2_packet.h"
#include "p03_hw_adapter.h"

#define P07_B4M_ROUTE_OUT_BASE UINT32_C(0x43FC4000)
#define P07_B4M_ROUTE_OUT_BYTES UINT32_C(0x00014000)
#define P07_B4M_ROUTE_IN_BASE UINT32_C(0x41000000)
#define P07_B4M_ROUTE_IN_BYTES UINT32_C(0x000E0000)
#define P07_B4M_FRAME_BASE UINT32_C(0x41100000)
#define P07_B4M_FRAME_MAX_BYTES UINT32_C(0x000E0000)
#define P07_B4M_ROUTE_HEAD 128u
#define P07_B4M_ROUTE_COMP_BYTES 64u
enum {P07_B4M_ROUTE_OK=0,P07_B4M_ROUTE_INVALID=-1,
      P07_B4M_ROUTE_SHA=-2,P07_B4M_ROUTE_TOPOLOGY=-3};
typedef struct {
    p07_b2_packet_binding packets;
    p07_b2_ingress_binding inputs;
    uint32_t emitted_route_count,input_route_count;
    uint32_t unique_registered_destinations;
} p07_b4m_frozen_binding;
/* Parse *independently physically verified* staged frozen two images.
 * Do NOT trust header payload SHA as a substitute for operator-pinned
 * image SHA; it is a structural tamper check only. Caller provides exact
 * 8192-entry output route buffer and 27-entry compartment buffer.
 * This function NEVER mutates the original P03 adapter.
 */
int p07_b4m_mount_frozen_routes(
    p07_b4m_frozen_binding *out,
    const uint8_t *original_output,size_t output_bytes,
    const uint8_t *original_input,size_t input_bytes,
    const p03_hw_adapter *original_hw,
    p07_b2_route *route_storage,size_t route_capacity,
    uint16_t *compartment_storage,size_t compartment_capacity);
#endif
