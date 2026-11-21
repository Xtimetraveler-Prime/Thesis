# M08.5 — Digital Twin PS/PL route reuse assessment and signed16 page admission

**Increment:** source-only work within the SAME M08.5 gate. M08.4 PHYSICALLY ACCEPTED; PRs #93–95 remain draft/unmerged. **No new Vivado build, JTAG, PS register access, DMA, DDR, or XMPU operation is authorized.**

## Exact first-party precedent: physical v3 DDR was real

Earlier Loihi Digital Twin v2 P08 performed physical host/JTAG-backed paging. More relevant, **Loihi Digital Twin v3** implemented a genuine PL-to-PS-DDR data path:

- Source: Loihi_Digital_Twin/v3/vivado/create_p02_ddr_impl_project.tcl, rtl/p02_context_page_bank_walker.v and rtl/p02_axi128_burst_adapter.v. Resident memory -> page walker -> fixed range guard -> AXI128 burst adapter -> SmartConnect -> PS S_AXI_HP0_FPD (SAXIGP2) -> physical DDR. The PS HP0 ingress was set to 128 bits using PSU__USE__S_AXI_GP2=1 and PSU__SAXIGP2__DATA_WIDTH=128.
- Loihi_Digital_Twin/v3/rtl/p02_ddr_backing_range_guard.v confines original transfers to **[0x40000000,0x44000000)** (64MiB), for **128 × 512KiB records**, not 256B M08 pages. The AXI adapter exposed a 128-bit AXI4 master, 256-byte coalescing and bounded outstanding requests. The P02 page arbiter excluded compute/debug ownership races.
- Loihi_Digital_Twin/v3/docs/P02_4B_ACCEPTANCE.md reports **real physically accepted DDR paging** on KV260: 5 logical contexts / 3 resident / 1 physical engine, 35 compute dispatches over seven ticks, 60 page-ins +60 page-outs and **32,686,080 original AXI bytes**, with final DDR records byte-exact. This was a **disposable/debug-halted Cortex-A53 operating boundary** with XSDB provisioning/readback and reboot, **not** a Linux DMA allocation service.
- Separately, Loihi_Digital_Twin/v3/vivado/create_p03_mmio_impl_project.tcl connected **PS M_AXI_HPM0_FPD -> SmartConnect -> 32-bit PL AXI-Lite control**, while HP0 remained the bulk DDR path. Per docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md, booted PS HPM0 actually selected 128-bit data width while early Vivado used 32-bit. The resulting offset read faults required a source-matched 128-to-32-bit SmartConnect, verified on physical board. Do not reconfigure the live Linux PS width speculatively.
- Crucially, Loihi_Digital_Twin/v3/docs/P08_B4_5_4_1_OPERATOR_STATIC_DDR_GAP_ACCEPTANCE_2026_11_05.md later recorded **unproven boot/firmware/Linux/XMPU owners despite passing static nonoverlap** in a separate experiment. Physical DDR success in one old debug environment is **not** sufficient permission for new M08/Linux memory writes.
- Accepted M08.4 source scripts/m08_paged_m06_lif_build.tcl deliberately disables PS HPM masters and uses JTAG AXI with one 256B resident neural bank; its own receipt says **physical_m06_ddr=NO** and **kernel_owned_dma_buffer=NO**. There is currently no connected M08 HP0 page master, and 24 physically accepted M08.4 page replacements were backed by the JTAG host.

## Reuse decision

**Reuse architecture and lessons, not the legacy memory image:** dual separated control and bulk-data paths; first-party range/transport checks; exclusive page/debug/compute arbitration; B/R completion fences; fail-closed errors; HPM0 PS width must match actual boot/AFI hardware; exact bit/route/source/raw-evidence review.

**Do not carry over** Loihi signed24 arithmetic, 512KiB records, ten Loihi banks, static 0x40000000 backing window, three-resident design, original bitstreams/ELFs, old VIO readback Tcl, or any presumed kernel-owned DDR buffer. M08 is signed16, 6 logical pages ×256B, 1 resident page, 32 neurons ×4 ticks, 5 recurrent edges and 17 events. No measured physical sparse-update skipping or resource-matched latency exists yet.

## Implemented this increment: inert-by-default 256B RTL transfer-admission boundary

New **rtl/m08/m08_m085_ddr_page_admission.v** is a synthesizable, **UNCONNECTED** request boundary before a *future* AXI page mover. It does not read/write payload data. Its default empty window [0,0) **rejects every request**, even if a synthetic owner signal is asserted. The testbench uses a fake 0x1000 address region **only within simulator**, never a board DDR address.

- Accepts an exact 256-byte aligned transfer with 65-bit no-overflow bounds, 49-bit address guard consistent with v3 HP0 adapter metadata, explicit window bounds, compute and page-bank idle, and the **future** owner-active interlock (which by itself **does not authenticate DMA ownership**).
- Latches page ID/tick/address/read-write for downstream matching. Allows only one outstanding request; waits for a synthetic downstream complete with valid read-data indication for a read or write-response completion for a write. The future actual AXI bridge must independently prove R/B response semantics; this test supplies a simplified abstract completion.
- Sticky poison and response embargo on premature/replayed request, stale orphan completion, wrong size/alignment/range/page ID/tick, downstream error, malformed read/write completion, busy compute, owner revocation and timeout. The completed transaction counter is **SIMULATED handshake accounting**, **NOT physical DDR bytes/cycles**.
- New genuine **Icarus RTL** testbench includes a positive ordered read then dirty-save acknowledgement (with deliberately held request) and **18 separate failure conditions**, including a default empty-window denial.
- New source checker and CLI, src/neuromorphic_accelerator_v1/m08_m085_pspl_lineage.py and scripts/m08_m085_twin_pspl_audit.py, inspect only eight original repository files and emit source SHA witnesses/precise v3 versus M08 limitations. New tests mutate v3 HP0 route, control width, range guard, original acceptance, M08 HPM0 disable and owner gap; they cannot be misinterpreted as physical K26 device observations.

## Architecture safety gate before any actual DDR wire or new image

1. Run existing read-only M08.3 Linux/driver inventory and inspect current booted PS width, XSA memory routes, real device binding, DMA mask/IOMMU/cache ownership. No /dev/mem, guessed address, DMA heap listing or candidate Vivado address is proof of safe buffer ownership.
2. Explicitly choose either **kernel-owned Linux DMA / PS-managed page service** with bound driver, pinned lifetime, buffer coherency, outstanding-drain and reset/quiesce, **or** a separately preflighted disposable standalone-A53/debug-halted reserved address/boot-owner-exclusion scheme. The v3 debug experiment does NOT automatically authorize M08's use of its physical window.
3. Only after ownership design review, implement a new actual M08 256B page mover with AXI4 128-bit transport and new timing/DRC/resource evidence, full M02/M03 neural RTL parity and tests covering dropped R/B/timeout/stale dirty page; then separately seek original offline K26 build and new image/board preflight authorization. Do not connect this source-only guard to the M08.4 accepted bitstream automatically.
4. If ownership cannot be verified, keep real DDR mode **BLOCKED** in the existing six-cell matched contract; no fabricated DDR bytes, bandwidth, timing or speedups.

## Owner VS Code terminal verification (NO BOARD)

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git log -1 --format='%h %s'
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v iverilog
command -v vvp
python3 scripts/m08_m085_twin_pspl_audit.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_reuse.py' -v
python3 -m unittest discover -s tests -p 'test_m08_matched_experiments.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
~~~

All commands read original source, compile real standalone Icarus RTL and run source regressions only. None calls Vivado/Vitis, XSDB, Linux MMIO, DMA, DDR, the board or immutable original physical owner evidence. Combined repeatable physical measurement remains M08.6–7.
