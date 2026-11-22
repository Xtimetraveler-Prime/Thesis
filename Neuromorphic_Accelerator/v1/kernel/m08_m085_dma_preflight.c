// SPDX-License-Identifier: GPL-2.0-only
/*
 * M08.5 SOURCE-ONLY Linux platform preflight CANDIDATE (6.8 API shape).
 *
 * NOT WIRED into Kbuild / DKMS / device tree, NOT deployed or compiled
 * against owner KV260 kernel. Unique compatible string has no currently
 * approved enabled DTS node. Do NOT install or modprobe this source.
 *
 * This PROBE-ONLY candidate demonstrates strictly-owned coherent allocation
 * on the SAME platform device used for control/MMIO and PL DMA, with exact
 * CAP v1.1 and 49-bit bounds. It NEVER writes a single control register,
 * grants a lease, sets trust bits, dispatches, or starts AXI traffic.
 * Probe/cleanup may free the allocation ONLY because it is never shared
 * with the PL. If any future work issues GRANT, this cleanup MUST be removed
 * and replaced with an independently proved physical drain/isolator and
 * quarantine lifecycle; neither a PL reset nor BUSY=0 suffices.
 *
 * The owner must independently verify booted XSA/AFI, Linux DTB, dma-ranges,
 * IOMMU domain, cache/coherent translation and upstream protected MMIO before
 * enabling a future driver. A 49-bit mask is only the RTL's source aperture,
 * NOT evidence that the live PS can access a returned dma_addr_t.
 */
#include <linux/device.h>
#include <linux/dma-mapping.h>
#include <linux/err.h>
#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/slab.h>

#include "m08_m085_dma_contract.h"

#define M085_CAP_OFF       0x00
#define M085_VERSION_OFF   0x04
#define M085_CAP_MAGIC     0x4d303835U
#define M085_ABI_V11       0x00010001U
#define M085_CSR_MIN_BYTES 0x1000U

struct m085_preflight {
    struct device *dma_dev;
    void __iomem *csr;
    void *cpu_virt;
    dma_addr_t dma_handle;
    size_t bytes;
    bool never_shared_with_pl;
};

/*
 * This is the ONLY cleanup possible in a source preflight whose allocation
 * has never been made visible to the accelerator. NEVER reuse it in a live
 * granted driver: that must retain the DMA buffer on timeout, reset and
 * uncertain outstanding B/R until independently proven bus isolation.
 */
static void m085_free_never_shared(void *data)
{
    struct m085_preflight *s = data;

    if (WARN_ON_ONCE(!s->never_shared_with_pl))
        return; /* intentional leak rather than unsafe free */
    if (s->cpu_virt)
        dma_free_coherent(s->dma_dev, s->bytes, s->cpu_virt,
                          s->dma_handle);
}

static int m085_probe(struct platform_device *pdev)
{
    struct device *dev = &pdev->dev;
    struct m085_preflight *state;
    struct resource *res;
    u32 cap, version;
    int ret;

    /*
     * Require explicit custom platform binding; NO stock /dev/uio,
     * reserved-memory physical guess or user selected addresses.
     */
    if (!dev->of_node)
        return -ENODEV;
    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    if (!res || resource_size(res) != M085_CSR_MIN_BYTES)
        return -ENODEV;

    state = devm_kzalloc(dev, sizeof(*state), GFP_KERNEL);
    if (!state)
        return -ENOMEM;
    state->csr = devm_platform_ioremap_resource(pdev, 0);
    if (IS_ERR(state->csr))
        return PTR_ERR(state->csr);

    /* READ ONLY. Identical source v1.1 CAP/ABI checks used by MMIO tests. */
    cap = readl(state->csr + M085_CAP_OFF);
    version = readl(state->csr + M085_VERSION_OFF);
    if (cap != M085_CAP_MAGIC || version != M085_ABI_V11)
        return -ENODEV;

    /*
     * Owner review MUST precede ever binding this candidate: the kernel DMA
     * API mask alone cannot attest physical PS HP0 aperture or IOMMU setup.
     * This allocation is NEVER submitted to PL, so it can be safely freed.
     */
    ret = dma_set_mask_and_coherent(dev, DMA_BIT_MASK(49));
    if (ret)
        return ret;
    if (PAGE_SIZE < M085_DMA_USED_BYTES ||
        PAGE_SIZE > M085_DMA_ALLOC_FIELD_MAX)
        return -EINVAL;

    state->dma_dev = dev;
    state->bytes = PAGE_SIZE;
    state->never_shared_with_pl = true;
    state->cpu_virt = dma_alloc_coherent(dev, state->bytes,
                                         &state->dma_handle, GFP_KERNEL);
    if (!state->cpu_virt)
        return -ENOMEM;

    /* Revalidate the ACTUAL device bus address from DMA API, not
     * virt_to_phys / an assumed CPU address / a userspace pointer.
     */
    if (!m085_dma_descriptor_valid((u64)state->dma_handle,
                                   state->bytes, 1ULL)) {
        ret = -ERANGE;
        goto free_never_shared;
    }
    /*
     * devres cleanup is allowed ONLY while the descriptor has NEVER
     * reached any AXI/CSR control: no possible outstanding PL access.
     */
    ret = devm_add_action_or_reset(dev, m085_free_never_shared, state);
    if (ret)
        return ret; /* action already freed unshared allocation */
    platform_set_drvdata(pdev, state);
    dev_info(dev, "M08.5 source preflight: ABI v1.1, coherent handle checked; no GRANT or PL DMA enabled\n");
    return 0;

free_never_shared:
    m085_free_never_shared(state);
    return ret;
}

static const struct of_device_id m085_of_match[] = {
    { .compatible = "thesis,m08-m085-preflight-quarantined" },
    { }
};
MODULE_DEVICE_TABLE(of, m085_of_match);

static struct platform_driver m085_driver = {
    .probe = m085_probe,
    .driver = {
        .name = "m08-m085-preflight-quarantined",
        .of_match_table = m085_of_match,
    },
};
module_platform_driver(m085_driver);

MODULE_AUTHOR("M08.5 research source candidate");
MODULE_DESCRIPTION("M08.5 read-only coherent DMA allocation preflight; no PL grant");
MODULE_LICENSE("GPL");
