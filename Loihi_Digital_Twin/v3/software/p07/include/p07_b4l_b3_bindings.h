#ifndef P07_B4L_B3_BINDINGS_H
#define P07_B4L_B3_BINDINGS_H
/* Immutable host-verified original B2.4 27-core P03 registrations.
 * 16KiB descriptor at standalone [0x43FC0000,0x43FC4000),
 * outside 27x512KiB backing; NEVER substitute hardcoded fake axons.
 */
#include <stdint.h>
#include <stddef.h>
#include "p03_hw_adapter.h"
#define B4L_BIND_BASE UINT32_C(0x43FC0000)
#define B4L_BIND_SIZE 0x4000u
#define B4L_BIND_HEADER 128u
#define B4L_BIND_ENTRY 528u
#define B4L_BIND_CORES 27u
#define B4L_BIND_BITMAP 512u
#define B4L_BIND_BYTES (B4L_BIND_ENTRY * B4L_BIND_CORES)
enum { B4L_BIND_OK=0,B4L_BIND_INVALID=-1,B4L_BIND_SHA=-2,
       B4L_BIND_ADAPTER=-3 };
typedef struct {
    uint32_t core_count,registered_axons,registered_compartments;
    uint32_t first_bad_core,first_bad_axon;
} b4l_binding_receipt;
/* Verify independently pinned accepted B2.4 source fingerprints,
 * 27 ordered metadata/compartment IDs, full 4096-axon bitmaps,
 * table SHA256 (accepted existing P07 SHA implementation) and zero padding.
 * Mutating hw registrations is an ALL-OR-ABORT operation: no partial
 * failure may be followed by a scheduler launch.
 */
int b4l_bind_frozen(p03_hw_adapter *hw,const uint8_t *bytes,size_t n,
                   b4l_binding_receipt *receipt);
#endif
