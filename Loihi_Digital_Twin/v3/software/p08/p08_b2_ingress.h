#ifndef LOIHI_TWIN_V3_P08_B2_INGRESS_H
#define LOIHI_TWIN_V3_P08_B2_INGRESS_H
/* Original B2.4 -> B1.3 on-board ingress builder, PC-only candidate.
 * Must admit SHA-pinned ORIGINAL 896KiB B4MING01 once before any encoding.
 * This component NEVER resets physical neural state and NEVER launches PL.
 */
#include <stddef.h>
#include <stdint.h>
#define P08_B2_RAW_IMAGE_BYTES 784u
#define P08_B2_EXPECTED_INPUT_ROUTES 20384u
#define P08_B2_ROUTE_IMAGE_BYTES 0xE0000u
#define P08_B2_ROUTE_HEADER_BYTES 128u
#define P08_B2_WIRE_HEADER_BYTES 128u
#define P08_B2_WIRE_BYTES (P08_B2_WIRE_HEADER_BYTES + 6u*P08_B2_EXPECTED_INPUT_ROUTES + P08_B2_RAW_IMAGE_BYTES)
#define P08_B2_ADMITTED_TAG UINT32_C(0xB2001D24)
typedef struct {
    const uint8_t *original_route_image; /* Borrowed authenticated immutable DDR bytes */
    const uint8_t *routes;              /* Offset 128, original route order */
    uint32_t route_count;
    uint32_t admitted_tag;
} p08_b2_route_binding;
enum { P08_B2_OK=0, P08_B2_INVALID=-1, P08_B2_SOURCE_SHA=-2,
       P08_B2_CAPACITY=-3 };
/* Fail closed and leave output unmodified on rejection. The whole 896KiB
 * route input image must exactly match original B4M source SHA256.
 */
int p08_b2_admit_routes(const uint8_t *source,size_t source_len,
                        p08_b2_route_binding *out);
/* Caller ensures source route image remains pinned/immutable after admission.
 * No overlap between caller raw pixels, route image, and output frame.
 * Output must have capacity >= P08_B2_WIRE_BYTES; writes only that length.
 */
int p08_b2_encode_frame(const p08_b2_route_binding *binding,
                        const uint8_t pixels[P08_B2_RAW_IMAGE_BYTES],
                        uint8_t *output,size_t capacity,size_t *out_length);
#endif
