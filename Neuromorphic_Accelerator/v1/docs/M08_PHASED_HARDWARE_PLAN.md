# M08 — KV260 physical implementation and benchmarking plan
**Initial design:** 2026-11-10. **Status:** M08.1 PC/board read-only inventory under development; real hardware has not been contacted by this GitHub-side development session.

## Scope and research objectives

Build a genuinely deployable, independently correct KV260 SNN pipeline that includes a bounded PS/PL host interface and, when proven safe, real kernel-owned physical DDR behind an AXI page-service path. Then compare *fully matched hardware* on-chip versus virtualized, timestep versus event-driven work where actual source/resident capacity permits. Separate device-only, PS/DMA orchestration and end-to-end timing; measure area, clock and variation. Negative outcomes are valid.

Hardware work is authorized by the owner for M08, but **authorization is distinct from safe memory ownership, current board connectivity, a valid bitstream, or a verified operating system**. No arbitrary physical base addresses, /dev/mem writes, guessed mmap regions, automatic QSPI flashing, boot rewriting, or Linux-resident DDR ownership bypass is acceptable. Preserve failures in unique immutable evidence folders.

### Architectural starting point — critical non-equivalence

- **M05:** accepted signed32 HLS rolling event engine and simulated on-chip state/adjacency, full event stream control shell and standalone off-line simulation. No physical bitstream or live PS/DDR path is proven. Source reference: M05 acceptance.
- **M06:** accepted signed16 paged HLS neural engine with genuine AMD SmartConnect/width-converter RTL and a 64 KiB **simulated** canonical state image; exact 32-neuron/4-tick original vendor neural parity and G4 fail-closed/explicit rewrite. No physical DDR image, kernel-owned buffer, complete Linux/PS/PL BD, or automatic on-hardware recovery established. Source reference: M06 acceptance.
- **M07:** independently correct source-only policy models; M07.5 assumed cycles are **not** hardware timing. M07's activity-history candidate is NOT production RTL and is not approved as a resource-matched accelerator.
- **Important:** signed32 M05 and signed16 M06 are **not by definition fair four-way hardware comparators**. Select the same verified numeric contract, inputs, state layout, and achieved resource/clock configuration before any speedup ratio. An M05 signed32 on-chip smoke can prove connectivity independently, while the matched performance control may need additional engineering.

## Ordered development / acceptance gates

| Gate | Development and independent evidence | Stop condition |
| --- | --- | --- |
| **M08.1 — Hardware entry/read-only evidence** | Host toolchain/source SHA, original M06 five ZIP SHA audits, board UART/DT/Linux or boot-failure capture, firmware/version/device identity, clock/boot mode, JTAG USB presence; immutable collection tool and negative tests | Stop if boot or board identity cannot be confirmed; no destructive recovery/flash attempts inferred from a broken boot |
| **M08.2 — Real Vivado physical design construction** | From accepted HLS RTL+DAT and AMD vendor IP, build native K26 PS/PL BD including AXI-Lite kernel/shell controls, real DMA/HP interconnect, clock/reset, safe page-state datapath; independently check *all* interface widths, IDs, byte lanes, control base/range, reset polarity, stale warnings, BD validation, synthesis, full implementation/WNS and bitstream. Preserve exported XSA/handoff/bitstream SHA and Vivado log | Do not program a partially connected M05 PS shell and claim M06 state paging; don't ignore original M05.12d DDR/OCM and 63-warning history. No bitstream until genuine fully connected implementation passes |
| **M08.3 — Linux memory and driver ownership** | Record actual Linux image/DTB/boot firmware, kernel DMA mask/coherency and memory ranges; use **kernel-bound DMA API/attached DMA-BUF** with independent allocator lifetime and in-range DMA-visible address. Address 32/64-bit width must match real master. Driver shall quiesce/reset PL before free, and never reuse stale state after a poisoned run | Neither physically reachable DDR_LOW in BD nor a bare physical address from userspace is ownership. No /dev/mem DMA buffers, guessed addresses, or unbound memory before a verified driver |
| **M08.4 — First physical proof** | First harmless PL identification and static memory/control readback; then small M05 on-chip genuine signed32 smoke, independent oracle; then separate M06 signed16 32 neurons ×4 ticks with a **fresh, allocated** canonical state image, page fills/dirty writebacks, W-response-before-next-R, independent final state and trace. Quarantine faults and explicit reset/reinit as M06 dictates | If UART/Linux is lost, report outcome, power-cycle/known-boot recovery; no assumption of automatic crash-atomic rollback. Physical program != inference PASS |
| **M08.5 — Matched hardware comparators** | At same numeric LIF contract, workload, input/outputs, accuracy and feasible resource budgets: onchip timestep/event, virtual timestep/event. If onchip N state exceeds capacity mark comparator **UNAVAILABLE**, not 0-latency. Sweep N/K, active-role locality at fixed work, block/cache bytes, batching and memory placement. Preserve negative outcomes | Do not compare an oracle-guided source-only timestep model directly to actual event hardware, or treat cache bytes as full device timing |
| **M08.6 — Performance/evidence** | Report raw hardware counters and transactions, clock/DDR service histograms and B-before-AR waveform; sample-to-output device-only latency, PS setup/DMA latency, total service latency and steady-state throughput. Record cold/warm runs and repeats, each raw capture SHA, place-route LUT/FF/BRAM/URAM/DSP, routed timing. Power only with validated sensor/boundary and source of readings | Do not invent energy, clock or throughput without measurement. Repeated analysis of one capture is not independent trial replication |
| **M08.7 — Acceptance and M09 handoff** | Cross-signed full hardware evidence manifest, negative failure archives, repeatability analysis, uncertainty, source/bitstream/XSA/ELF/DT SHA, owner verification and prior-art configuration ledger; merge only after owner review | M08 cannot be accepted by PC-only source CI or a fabricated placeholder Vivado log |

## Implementation order and deliberate stage boundaries

1. **Now:** M08.1 host-only inventory code, SHA-pinned accepted original ZIP audit, read-only board-local Linux command capture, no-mem-ownership guards, tests/CI, plus the exact operator runbook.
2. **Next (real local PC required):** audit current 2025.2 Vivado, installed AMD IP/board files, locally retained original M05/M06 generated HLS RTL and DAT, existing .bd/.xpr/.xsa; obtain truthful **originals-present** and actual K26 IP connection reports. A new **standalone read-only AXI4-Lite PL identity slave** (M08.2 preliminary RTL) is already source-created and Icarus-verifiable; it is NOT attached to a real BD, and its default build tag is zero. Do not resynthesize accepted original cores just for an inventory.
3. **Then (physical KV260 or local Vivado required):** advance M08.2 actual BD and routed implementation from the observed original artifacts; build/verify Linux allocation mechanism. Never substitute M06 bytearray for hardware DDR.
4. **Once the actual board boots, **run M08.1 board-local read-only inventory and bring host/board receipts back for a verified next-step integration decision. A halted or unavailable Linux is a *measured entry blocker*; capture UART/boot logs rather than assuming pre-existing image is repairable.

## First hardware session checklist

- Confirm actual KV260/K26 model, power supply, J4 UART at **115200 8N1, no flow control**, USB JTAG enumeration and exact boot mode. Do not confuse a UART attach or an HLS config with a programmed PL.
- Distinguish OS images: board can boot a Linux/PetaLinux/Ubuntu release with version-specific firmware requirements. Firmware mismatch is an engineering finding, not a mandate for automatic QSPI update. Record read-only `/proc/device-tree/model`, `/proc/cmdline`, `/etc/os-release`, `/proc/meminfo`.
- Check known safe boot/recovery, source/bitstream signatures, independently mapped PS control register readback and board power cycle after invasive debug. For an already stalled boot, power-cycle under operator control and capture serial; do not resume a halted Linux image.
- Keep `~/Thesis_Evidence/M08/` immutable and outside checkout; folders are unique per run and never overwritten; README and scripts must not insert accepted owner-original ZIPs into Git.

## Preliminary M08.2 deliverable — safe identity-first RTL

New first-party `rtl/m08/m08_axil_readonly_identity.v` implements only a **32-bit AXI4-Lite slave** with fixed magic/version/capability/build-tag words. It has **no memory master**, no DMA, no state writer and no neural processing. Every write returns SLVERR after correctly pairing decoupled AW and W, stable under BREADY backpressure; reads hold RDATA/RRESP under RREADY stalls, unmatched addresses DECERR, and reset drops stale partial transactions. Its dedicated first-party Icarus testbench covers all protocol edges. A separate host `m08_identity_client.py` requires a caller-supplied `read32(offset)`, reads twice for consistency, and **never constructs `/dev/mem` or infers a real bus address**. Zero default build-tag is explicitly *unprovisioned*. The identity register tells us that a future *actual* PS→PL register path works if wired and measured, not that any physical DDR interface works.

This small read-only peripheral is the first hardware candidate we can honestly develop without local AMD Vivado/board. **Next milestone step requires the operator's actual Vivado IP/BD project and device evidence** before connecting the PS master, assigning a physical MMIO aperture, generating a real bitstream or programming the board.

## 2026-11-10 owner evidence update and first native Vivado trial

The owner's original PC report was independently inspected: **5/5 accepted M06 ZIP SHA matches**, FTDI 0403:6011 present, source checkout at the prior M08 head, original Loihi evidence and Vivado logs untracked and preserved, and Vivado/Vitis 2025.2 **not on that shell's PATH**. Separately, owner confirms normal KV260 Linux boot and standard post-boot `sudo xmutil unloadapp`. This replaces the original tentative boot-failure concern: UART recovery remains a fallback, not the default path. The Loihi v2 acceptance sources establish a real prior routed P08 K26 physical host-paged result and state/trace conformance, but their bitstreams and signed24 Loihi model are **not** reusable as accepted M08 signed16 HLS/DDRx accelerators. [Exact receipt digest and scope crosswalk](M08_1_OWNER_EVIDENCE_AND_LOIHI_REUSE_2026_11_10.md).

**M08.1b source extension:** board-local readonly `xmutil listapps/boardid/bootfw_status/platformstats` are now allowed and independently audited as local **observations only**. `xmutil unloadapp`, `loadapp`, `bootfw_update` remain disallowed **in the inventory tool**, but the operator may use their previously established `sudo xmutil unloadapp` procedure outside the tool while archiving app state before/after.

**M08.2 PS→PL identity integration trial is source-complete, vendor validation OPEN:** local genuine-Vivado `scripts/m08_identity_ps_bd_candidate.tcl` and `scripts/run_m08_identity_bd.sh` attempt a new K26/Zynq PS HPM0 FPD/SmartConnect/read-only-PL-identity block design, with explicitly checked reset polarity, auto-assigned reportable AXI address aperture, real `validate_bd_design`, exported `.tcl` and no routed implementation or bitstream. `m08_identity_bd_audit.py` gates immutable original source SHA before/after, genuine local Vivado status and first-party report with **null physical claims**. A synthetically constructed auditor test demonstrates report validation only; real Vivado success remains **NOT ESTABLISHED** until the owner runs it on their PC and shares the original evidence folder. [Exact commands](M08_FIRST_PC_KV260_RUNBOOK.md).

## Current explicit M08 blockers (before physical work)

1. No connected live KV260 accessible from GitHub Actions or this research runtime. **Physical status unknown**, not PASS/FAIL.
2. Original M06 archive hashes known and accepted in prior milestone but **actual local files must be reauthenticated**; GitHub does not have their raw ZIPs.
3. Full K26 combined original HLS pager + PS DMA/HP, kernel driver, clock/reset, G4 supervisors and complete routed on-chip/DDR comparators are **not present as accepted physical hardware outputs** in Git.
4. No verified kernel-owned PS DDR buffer, DMA mask/IOMMU/FPGA address reachability, current Linux image, real XSA or measured timing/resource data.
5. Final M05 signed32 and M06 signed16 paths differ in precision and architecture. No shortcut hardware speedup claim.

## Documentation and upstream references

Project originals: [M05 acceptance](M05_ACCEPTANCE_REVIEW_2026_11_09.md), [M06 acceptance](M06_ACCEPTANCE_REVIEW_2026_11_10.md), [M07 acceptance](M07_ACCEPTANCE_REVIEW_2026_11_10.md), [M07 prior-art comparability](M07_PRIOR_ART_CONFIGURATION_COMPARISON.md).

AMD developer resources (read-only research references): [Kria SOM starter-kit software/boot matrix](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/1641152513/Kria+SOMs+Starter+Kits), [Zynq UltraScale+ PL masters, DMA addressing and Linux reserved memory caveats](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18842169/PL+Masters), [KV260 official starter kit guide UG1089](https://www.xilinx.com/support/documents/boards_and_kits/kv260/ug1089-kv260-starter-kit.pdf). Always select the correct firmware/image for the *observed* board before changing boot software.
