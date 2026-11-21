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

## Continuing development — first-party **real AXI4 handshake** 256B page engine (source-only)

With the original 18-fault page-admission tests locally verified by the owner, the SAME M08.5 branch and draft PR #95 now contain a **new, accelerator-specific AXI4 burst master**, not copied Loihi page logic:

- **rtl/m08/m08_m085_axi128_page_engine.v**: synthesizable AXI4 read/write master, exactly one 256B **INCR burst = 16 × 128-bit beats**, 49-bit address, 1-bit transaction ID 0, no narrow bursts, full 16-byte WSTRB, WLAST only on beat 15. AW/AR ID/cache/protection/QOS/lock signals explicitly bound, modeled after the *interface shape* of the physically proven v3 adapter, not its 512KiB backing image. No AXI clock bridge, SmartConnect, Vivado block design, PS endpoint, driver or DDR address was attached.
- The engine accepts a single **2048-bit write snapshot** and exposes a **2048-bit read snapshot only after all sixteen accepted R handshakes**, OKAY responses, matching RID=0 and correct RLAST. Writes become successful **only after the B handshake** with OKAY and matching BID=0. AXI VALID remains stable under backpressure. No full-page ACK on AW, W, AR or intermediate R alone.
- **rtl/m08/m08_m085_axi128_page_candidate.v** composes the previously developed 256B guard **with the actual new AXI master**. It defaults to empty [0,0) address window. It latches the producer snapshot at accepted request, preserving all 256B across bus stalls, and propagates guard poison into the transport engine (an unsafe second request quarantines the already-active AXI burst). The accepted logical page, tick and direction are reported only after the successful complete AXI handshake. Lower-level read snapshot is **masked to zero** except on the one-cycle promoted successful read-ACK.
- The **2048-bit staging interface is intentional for this offline handshake proof**, not a new claimed physical resident bank. It currently requires separate candidate buffers and has **not** been connected to the M08.4 bank's 64-word **readback-verified LOAD / readback-before-DIRTY-SAVE** protocol. Connecting it safely, minimizing staging resources, independently checking placement, and integrating with the original signed16 LIF engine are still open tasks. Neither the original neural RTL nor accepted M08.4 JTAG bitstream changed.
- **rtl/m08/tb_m08_m085_axi128_page_candidate.sv** is a genuine Icarus AXI bus-functional model with synthetic 256B DDR backing. The positive test writes **all 16 W beats** into simulated backing memory, waits for the B response, then reads **the same address** over **16 R beats**, compares all 2048 bits, verifies byte/burst counters (one write + one read = **512 simulated AXI bytes**) and owner-facing page/tick IDs. With stalls it actively checks every WDATA/WSTRB/WLAST, AW/AR shapes and stable addresses. **25 separately executed negative cases** include illegal page/tick/window/alignment, missing/malformed R/B, early/missing RLAST, wrong RID/BID, wrong read response, orphan channels, stalled AW/W/B/AR/R, owner revocation, compute/bank conflict and a second command. A fault is sticky until reset and disallows any additional AXI request. The test model cannot prove electrical AXI operation on the K26.
- **tests/test_m08_m085_pspl_reuse.py** compiles these real modules with Icarus and requires the full directed positive/negative traces. A *second* real-RTL regression derives and writes **all six original** 64-word signed16 M06 input pages from scripts/m08_paged_m06_lif_fixture.py, whose state/config/17 input events and 512-word comparison oracle originate from the independently accepted M02/M03 workload. Each original page is transferred into **testbench-only simulated DDR** and back byte-for-byte under a distinct page ID. The golden 512 neural output words are **NEVER** written to the page bus or used as fake compute data. This checks 6 × 256B input transport fidelity, not on-FPGA recurrence, neural computation, real DDR or measured throughput.

**Important accounting:** the 512 model AXI bytes in the two-operation test are **16 write beats × 16B + 16 read beats × 16B** and are counts of successful **Icarus bus-functional-model handshakes**, not bytes actually transferred on physical PS DDR. The original M08.4 accepted 24 page dispatches and 512/512 neural comparisons remain separate hardware evidence. A timed-out burst may already have issued partial writes into a real device; the design **requires full transport quiesce/reset and memory invalidation** before any recovery, not software retry on the same buffer.

### Current engineering limits

No physically mapped or Linux/standalone-owned buffer; no connected SmartConnect / S_AXI_HP0_FPD or PS HPM0 AXI-Lite control; no PS clock/reset/boot width admission; no byte-persistency proof for a real R/B slave; no OS kernel DMA mask/IOMMU/cache sync; no current-period resource/route/timing metrics; no validated overlap-free load/save bank controller; no actual DDR measurements. **M08.5 physical cell stays BLOCKED / NOT MEASURED.** Do not interpret original Dual AXI source path as authorization to modify boot-time PS registers or program the KV260.

### Later continuation on the SAME M08.5 gate — original bank is now connected in source RTL

The paragraph above describing the 2048-bit page staging ports as *not yet wired to a bank* is **historical to the preceding AXI-only increment**. New [M08.5 integrated AXI/64-word neuron bank lifecycle and test runbook](M08_5_BANK_AXI_INTEGRATION_CONTRACT.md) describes the later first-party `m08_m085_axi_bank_bridge.v`. It now connects the existing M08 bank to the 16-beat AXI source engine, requiring **64 actual bank readbacks before LOAD commit and a second full DDR readback before DIRTY save acknowledgement**. Genuine six-original-page Icarus positive tests and 15 negative faults are in `tests/test_m08_m085_bank_axi_bridge.py`. The bridge still has **no connected LIF engine or physical PS HP0/DDR route**, and preserves the original M08.4 accepted image untouched. The actual next work is source-matched neural-compute integration and owner-bound memory admission, not to reinvent this already implemented bridge.

## Architecture safety gate before any actual DDR wire or new image

1. Run existing read-only M08.3 Linux/driver inventory and inspect current booted PS width, XSA memory routes, real device binding, DMA mask/IOMMU/cache ownership. No /dev/mem, guessed address, DMA heap listing or candidate Vivado address is proof of safe buffer ownership.
2. Explicitly choose either **kernel-owned Linux DMA / PS-managed page service** with bound driver, pinned lifetime, buffer coherency, outstanding-drain and reset/quiesce, **or** a separately preflighted disposable standalone-A53/debug-halted reserved address/boot-owner-exclusion scheme. The v3 debug experiment does NOT automatically authorize M08's use of its physical window.
3. **AXI4 256B handshake engine now exists source-only** and has genuine Icarus tests. Next, still PC-only, build a 64×32-bit host-page adapter that respects the accepted M08.4 bank's complete write/readback/commit/dirty-save protocol, then connect the streaming endpoint to the new AXI engine with independent B/R tests and the actual M02/M03 neural input pages. No host readback coverage or durable save claim is established by an AXI B response alone. Separately require source-matched timing/DRC/resource evidence before any candidate native release. Do not modify or silently replace the physically accepted M08.4 image.
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
