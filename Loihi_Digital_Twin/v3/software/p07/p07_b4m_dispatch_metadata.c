#include "p07_b4m_dispatch_metadata.h"
#include <stddef.h>
#include <string.h>

_Static_assert(P07_B4M_METADATA_CORES <= P03_RT_MAX_CORES,
               "P07 model exceeds original P03 host metadata slots");

/* Read the ORIGINAL little-endian P02 v1 record header bytewise. The
 * caller invalidates the PS cache on each 0x1000-byte header before call.
 * No reinterpret-cast to struct and no writes to context backing.
 */
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8u) |
           ((uint32_t)p[2] << 16u) | ((uint32_t)p[3] << 24u);
}
int p07_b4m_apply_p02_counts(
    p03_hw_adapter *hw,
    const uint8_t *const headers[P07_B4M_METADATA_CORES]) {
    static const uint8_t magic[8]={'L','T','V','3','C','T','X','1'};
    uint64_t candidate[P07_B4M_METADATA_CORES];
    uint32_t c;
    if (!hw || !headers || hw->last_error != P03_HW_OK ||
        hw->backing_base != P03_HW_BACKING_BASE)
        return P07_B4M_METADATA_REJECT;
    /* PREVALIDATE EVERY original context before touching any registration.
     * Frozen P02 header fields: id@0x14, compartments@0x20,
     * synapses@0x24, output routes@0x28, initial event banks@0x2c/0x30.
     * P08 expects [17:7] compartments, [33:18] synapse count,
     * [46:34] route count, [59:47] CURRENT event count (added later by
     * unchanged p03_hw_dispatch). Reserved [63:60] must remain zero.
     */
    for (c=0u;c<P07_B4M_METADATA_CORES;c++) {
        const uint8_t *p=headers[c];
        uint32_t n,ns,nr;
        uint64_t prior;
        if (!p || !hw->configured[c])
            return P07_B4M_METADATA_REJECT;
        prior=hw->metadata[c];
        n=le32(p+0x20u);
        ns=le32(p+0x24u);
        nr=le32(p+0x28u);
        if (memcmp(p,magic,8u)!=0 ||
            le32(p+0x08u)!=1u ||
            le32(p+0x0cu)!=0x1000u ||
            le32(p+0x10u)!=P03_HW_RECORD_BYTES ||
            le32(p+0x14u)!=c || le32(p+0x18u)!=0u ||
            le32(p+0x1cu)!=0u ||
            n==0u || n>1024u ||
            ns==0u || ns>32768u || nr>4096u ||
            le32(p+0x2cu)!=0u || le32(p+0x30u)!=0u ||
            le32(p+0x34u)!=0u ||
            prior!=(((uint64_t)n<<7u)|(uint64_t)c))
            return P07_B4M_METADATA_REJECT;
        candidate[c] = prior | ((uint64_t)ns << 18u) |
                        ((uint64_t)nr << 34u);
    }
    for (c=0u;c<P07_B4M_METADATA_CORES;c++)
        hw->metadata[c]=candidate[c];
    return P07_B4M_METADATA_OK;
}
