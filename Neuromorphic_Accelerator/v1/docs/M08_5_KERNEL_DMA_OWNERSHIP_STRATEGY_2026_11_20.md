# M08.5 — Kernel-owned PS DDR strategy and source-only ownership fence

**Decision (2026-11-20): prefer a Linux platform-driver-owned coherent DMA allocation, runtime-bound to the first-party 7-slot signed16 page engine.** M08.5 ACTIVE, draft PR #95, M08.4 accepted owner physical image and evidence UNCHANGED. This document defines an architecture, **not** an authenticated kernel driver, actual DMA allocation, PS/PL integration, board permission or physical ownership receipt.

## 1. Specific decision; why this is not copied from Loihi Digital Twin v3

The old v3 Loihi route proved that a PL AXI4 128-bit master can access PS `S_AXI_HP0_FPD` through a SmartConnect on KV260, but its historical debug-stopped CPU, statically assumed `0x40000000` 64MiB range, signed24 512KiB context, firmware/XMPU provenance gaps and absent Linux driver binding are **not a license to reuse that DDR**. M08.3 explicitly distinguished accepted host/JTAG staging from actual kernel DMA ownership. M08.4 source has no connected PS HP0 datapath. We therefore choose a new **device-specific Linux platform driver**, not `/dev/mem`, user-supplied physical addresses, an unbound `/dev/uio`, guessed DTS `reserved-memory`, an arbitrary DMA heap, or a v3 debugger reservation.

### Proposed device data flow

```
authenticated owner/operator -> future bound Linux platform driver
  -> dma_set_mask_and_coherent() only after exact kernel/XSA/DT width review
  -> dma_alloc_coherent(&pdev->dev, PAGE_SIZE or a validated >=1792B size, ...)
       returns {kernel_cpu_pointer, dma_addr_t bus_address}
  -> CPU writes seven 256B pages into the allocated DMA-coherent buffer
  -> correct CPU-to-device memory ordering barrier before the control doorbell
  -> trusted platform-specific control (future PS HPM0 -> PL AXI-Lite)
  -> reviewed lease descriptor {generation, dma_addr, DMA allocation length}
  -> M08.5 source RTL runtime-window fence (not a kernel authenticator)
  -> M08.5 128-bit AXI4 page transfer, one resident 64x32-bit neuron bank
  -> eventually physically wired PS S_AXI_HP0_FPD -> PS DDR
  -> IRQ/poll completion with ordering, R/B response and full-page verification
  -> device quiesce + no outstanding AXI before release/free
```

The `dma_addr_t` device/bus address **is not necessarily a CPU physical address** (possible IOMMU/SMMU, `dma-ranges`, translations). Select **the actual platform device associated with the PL AXI master** and its live driver/DT; never use a random registered device just to obtain an address. Exact OS/kernel, bound device, PS AFI port widths, 49-bit address map, IOMMU mapping and boot XMPU protection **remain unverified**. A `DMA_BIT_MASK(49)` request is a *candidate* to be reviewed against actual hardware; if the real DMA mask or window excludes the returned `dma_addr_t`, reject. Even `dma_alloc_coherent` success alone does not prove that a PS-to-PL control path or routed AXI master exists.

**Why coherent allocation first:** the chosen HP0 path is not hardware snooping/coherent. The Linux DMA API's coherent allocation is a deliberately narrow early design that avoids a premature streaming-map/cache-sync protocol. Coherent allocation's CPU/device visibility guarantee and `dma_wmb`/necessary ordering barriers still require correct platform configuration and device behavior, and do **not** imply automatic ordering of a separate AXI-Lite doorbell versus payload writes. No user-space mapping or borrowed DMA-BUF in the first candidate. Later, if a credible resource or throughput study requires streaming DMA, design `dma_map_single` / `dma_sync_single_for_device` / `dma_sync_single_for_cpu`, direction, mapping-error, lifetime and IOMMU rules as a **separate reviewed variant**, never silently combine modes.

## 2. Exact M08 memory layout and dynamic bounds

The seven 256B records occupy the first **1792 bytes** of a device DMA allocation with a reviewed size **at least 1792**. Prefer an allocation of `PAGE_SIZE` (commonly 4096B, but use runtime kernel PAGE_SIZE, not a guessed physical K26 page). Do not expose the extra tail. To avoid a burst crossing a 4KiB AXI address boundary or aliasing another page, the trusted lease must be **256-byte aligned**, `base>=0`, `base+1792` calculated with an overflow-safe **65-bit** addition and inside the independently verified **49-bit PL master address aperture**. All 256-byte pages are aligned, 16 beats ×16B, no other burst shape permitted.

| Transport slot | Byte offset from allocation DMA address | Semantic bank ID | Header |
| --- | ---: | --- | --- |
| 0,1,2,3,4,5 | `slot*256` | `slot` (six neuron pages) | `M6NF` `0x4D364E46`, count 6 except slot5 count2, tick 0..3 |
| 6 | `1536` | `0xFFFFFFFF` (recurrent edge config) | `M6EG` `0x4D364547`, count5, tick0 |

For the accelerator, the only allowed transfer address is **`latched_dma_base + slot*256`**; it must not accept an address chosen by arbitrary user-space input. The runtime admitted interval is **`[latched_dma_base, latched_dma_base+1792)`**, regardless of actual allocation length. On release or any in-flight metadata change: **deny new transfers**, flag sticky poison, require interconnect quiescence/recovery before regrant. Static source-only M08 tests may still use fixed `WINDOW_BEGIN/END`; the new dynamic path is explicit opt-in, with default static window `[0,0)` (denies all).

## 3. Source-level runtime lease protocol (not a security proof)

The **future kernel driver** is the only authorized producer of a registered lease. It must bind to the *correct* platform device and first verify XSA/DT/PS port and IOMMU ownership. The first-party PL fence accepts a lease only if **all** of the following are true: explicit grant pulse, `kernel_dma_lease_valid`, `control_path_ready`, `bus_quiescent`, engine idle, bank clean/idle, `generation!=0`, DMA address aligned/within 49 bits, allocation size `>=1792`, and overflow-safe `base+allocation_size`/ `base+1792` within the aperture. The 7 pages are all backed by the *same frozen* lease. The fence stores the generation, address and size and exposes a **latched** runtime begin/end window. The owner-lease output is not asserted merely by an incoming Boolean; after successful grant it remains high only while every live owner/control/metadata signal matches the frozen record.

An **early revoke**, metadata/generation change or control-path loss during the lease must fail closed and quarantine. **No request may be issued on the cycle the lease becomes invalid**, even before the fault flop updates. Explicit release is permitted only after software has stopped new commands and positively verified **bus drained + engine idle + bank not dirty**; release goes to a stopped state that cannot regrant without independent reset and recovery. A sticky poison cannot be cleared by a new grant alone. Driving `kernel_dma_lease_valid=1` from a testbench is **not kernel ownership attestation** and the RTL cannot authenticate the driver's identity; that depends on the real PS/DT/control-interface integration.

**Critical quiescence gap:** `busy=0` or `poisoned=1` within the existing AXI master does **not** prove the PS/interconnect has drained outstanding AW/W/B/AR/R transactions after timeout. Before `dma_free_coherent()`, reset, buffer reuse or a new lease the driver must stop the master, isolate/recover the actual interconnect, observe real hardware drain/reset acknowledgments, and invalidate uncertain pages. No driver or current simulation implements that physical drain proof. Reboot/FPGA reset/AXI isolator may be required by the eventual platform—must be independently engineered.

## 4. Kernel implementation contract — future work, NOT code currently running on K26

1. **Probe:** require exact owner-approved XSA/bitstream/DT compatible string/physical control register mapping, bound platform driver and appropriate device DMA ranges/IOMMU domain; establish versioned CAP/identity MMIO. Reject unrecognized firmware/kernel/DT. Use `dma_set_mask_and_coherent(&pdev->dev, verified_mask)` only after those bindings are valid.
2. **Allocate:** `cpu_va = dma_alloc_coherent(&pdev->dev, allocation_len, &dma_handle, GFP_KERNEL)`. Reject NULL; record `dma_addr_t`, device pointer, exact length, alignment, generation and lifecycle in a private driver object. Check `dma_handle+1792` and `dma_handle+allocation_len` without overflow and against the verified HW address aperture. Never convert CPU virtual pointer or `virt_to_phys` into the PL DMA address; never invent `dma_addr_t` from a file.
3. **Initialize:** copy M6EG original five edges and six M6NF original signed16 input pages into the owned buffer; check 7×256B exact headers, no preloaded neural oracle outputs. Apply documented write ordering before grant/doorbell, with driver CPU access serialized against device writes. Capture source/hash/driver/kernel evidence for *future* operator review.
4. **Grant:** from reviewed **trusted** control registers (not user-writable UIO MMIO), set base, allocation length and fresh generation, verify readback, arm PL fence while bus and compute are idle. The 49-bit master drives exactly `base+slot*256` and never other addresses.
5. **Execute:** start M6EG then six M6NF per tick, IRQ/poll for completion and verify AXI R/B plus full 256B readback before bank dirty save. Enforce single-flight, model tick barriers, no concurrent CPU content edits and bounded watchdog. A timeout quarantines the whole session; do not retry on a potentially partially written buffer.
6. **Teardown:** deny new commands; wait for *real* quiescence/drain of PS/PL AXI before release; revoke lease, reset the accelerator/AXI path as required, and only then `dma_free_coherent(&pdev->dev, same_len, same_cpu_va, same_dma_handle)`. **Do not free/recycle while AXI can still access it**; driver removal or userspace death may require an unrecoverable 'allocated but quarantined' state until full system reset.

## 5. Required independent evidence before a driver or bitstream exists

- Current *booted* Linux board kernel/DT/driver binding and actual device ID; PS S_AXI_HP0_FPD physically connected, AFI and HPM0 control-width (v3 demonstrated a real 128→32 mismatch) and clock/reset provenance.
- Kernel DMA mask + coherent mask; actual `dma-ranges`/IOMMU translation, address width/endianness; boot XMPU/firmware protection and no device/owner conflict.
- Explicit PL control registers/version, secure producer of grant, independence of user input vs DMA address; finite bus-drain/quiescence/timeout recovery protocol.
- Offline Icarus fault cases for invalid base/size/generation, attempts to change or revoke an active lease, request before grant, release while busy/dirty, and source-only 512-value parity with the new runtime window.
- New source-pinned Vivado synthesis/resource, routed DRC and achieved timing; then separate **owner-authorized** K26 physical read/write with original numerical oracle and real byte counts. Do not elevate static RTL, M08.3 read-only inventory or a local Linux `/sys` listing to live ownership.

## 6. Immediate PC-only deliverables in this M08.5 source increment

1. Add an **explicit runtime-window parameter** (off by default) to M08.5 admission/candidate/bank/neural shell. Inherited simulated `WINDOW_BEGIN/END` default-deny and six-slot tests must remain unchanged.
2. Add a **synthesizable fail-closed DMA lease fence** whose outputs are the latched runtime window and gated owner enable; test it in genuine Icarus with adversarial lease lifecycle and address cases, plus a composed seven-page neural trace against simulated DMA allocation.
3. Document exact API/ownership and recovery gap here, plus roadmap/handoff; update same draft PR #95. **No C kernel module, physical driver probe, XSA, bitstream, PL programming or PS DDR use** in this increment.

## 7. Development source added after this design decision

The above source deliverables were implemented **on the same M08.5 draft branch** (exact-HEAD CI and user local verification are separate release gates):

- `rtl/m08/m08_m085_kernel_dma_lease_fence.v`: synthesizable source-only FSM that freezes DMA base, length and nonzero generation on one validated grant; **65-bit no-wrap and exact 49-bit aperture checks**; exposes only `[base, base+1792)`; gates permission combinationally on live metadata/control failure; requires engine idle, bank clean, and independently asserted bus quiescence for release. Sticky faults quarantine until externally controlled full reset. **This module does not authenticate a Linux driver or detect true PS outstanding AXI responses.**
- `rtl/m08/m08_m085_ddr_page_admission.v`, `m08_m085_axi128_page_candidate.v`, `m08_m085_axi_bank_bridge.v`, `m08_m085_axi_neural_shell.v`: each now accepts an **opt-in** `USE_RUNTIME_WINDOW` parameter and pinned 64-bit runtime start/end wires. All existing tests continue to use the default **static parameter mode**; its empty default address window still denies all access.
- `rtl/m08/m08_m085_kernel_owned_neural_candidate.v`: combines the new lease fence with the **unchanged original recurrent signed16 LIF**, one actual 64-word bank and first-party AXI master. **The requesting interface has no caller-supplied DDR address.** All seven DMA addresses are computed as `latched_base + slot*256`; lease-poison is routed into original bank fail-closed behavior. External `bus_quiescent` is a *future evidence-bearing control*, not a real physical observation in this source candidate.
- `rtl/m08/tb_m08_m085_kernel_dma_neural.sv` and `tests/test_m08_m085_kernel_dma_lease.py`: genuine Icarus source model, seven exact original M02/M03 INPUT pages and unchanged 512-word read-only neural oracle, source-synthetic valid DMA lease plus **26 negative cases** (11 original neural/edge faults and 15 grant/owner/metadata/release/address failures). The positive case requires the original 24 recurrent neural dispatches and 512 comparisons through real RTL and all 7×256B simulated backing slots. No PS connection or board memory is accessed.

**New next gate, not part of this source pass:** owner must identify exact live kernel/driver/DT/XSA and approved PS HP0/HPM0 control clocks, physical quiesce/reset/late-response protocol, DMA API allocation identity, and 128→32 AXI-Lite width adaptation *before* an actual Linux driver/device-tree or Vivado PS connection can be reviewed. An offline unit test with `kernel_dma_lease_valid=1` is **never** a substitute for that evidence.

**PC-only local regression commands** (from `~/Git/Thesis/Neuromorphic_Accelerator/v1` on current M08.5 branch):

```bash
python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_lease.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axi_neural_closed_loop.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_bank_axi_bridge.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
```

## References

- Linux Kernel DMA API: https://www.kernel.org/doc/html/latest/core-api/dma-api.html
- Linux Kernel DMA-API HOWTO: https://docs.kernel.org/core-api/dma-api-howto.html
- AMD UG1085 Zynq UltraScale+ TRM, HP FPD non-coherent ports: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Functional-Description
- This repository: `docs/M08_3_DMA_READINESS_RUNBOOK.md`, `docs/M08_3_LOIHI_KV260_MEMORY_OWNERSHIP_REUSE_2026_11_11.md`, `docs/M08_5_PROGRESS_FORWARD_PATH_2026_11_20.md` and `rtl/m08/m08_m085_axi_neural_shell.v`.
