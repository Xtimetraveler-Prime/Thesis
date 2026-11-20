# M08 D3.D.2D → NEXT CHAT HANDOFF: accepted physical 512-value event-ingress test; next physical increment

**Prepared 2026-11-20. Authoritative current status.** The original D3.D.2D KV260 experiment is **PHYSICALLY ACCEPTED**, is complete for its bounded test, and should NOT be repeated. Earlier “pending” notes in the D3.D.2D development plan and older handoffs are historical; this document and the signed-off acceptance record supersede them. **M08 OPEN; M09 PLANNED.** Continue in a NEW chat and a NEW stacked Git branch, without merging the existing draft PRs.

## 0. Owner-original accepted results — DO NOT MODIFY

Owner supplied an original first real physical evidence folder:

```text
/home/dna/Thesis_Evidence/M08/m08_d3d2d_event_HW_h7RmZQui
  00_executed_source.tcl: OK
  01_jtag_m06.log: OK
  02_jtag_m06.jou: OK
  03_exit.txt: OK
  10_m06_raw17_golden.hex: OK
  80_m06_raw17_hw_parity.txt: OK
  03_exit.txt: vivado_physical_exit=0
Independent audit:
  M08_D3D2D_PHYSICAL_M06_17_RAW_EVENT_128_BUCKET_384_NEURAL_ACCEPTED
```

The genuine owner-run read-only auditor JSON gives 17 individually submitted signed32 raw events, **32 neurons × 4 logical ticks**, five signed delayed recurrent synapses and **128/128 FPGA-accumulated input current buckets, 128/128 voltages, 128/128 spike decisions, 128/128 recurrent currents**, **512 independent numerical checks**. It reports `external_event_ingestion_in_fabric=true`, `original_m05_hls_physical=false`, `physical_ddr=false` and `streaming_or_asynchronous_ingress_proven=false`. It verifies original native-image provenance and six original physical hashes. The assistant has not personally inspected the owner's private original hardware folder and was not provided separate full UART/temperature/energy logs; do not invent these.

Original first native candidate:

```text
/home/dna/Thesis_Evidence/M08/m08_d3d2d_event_DE6kQWvt
bitstream_candidate/m08_d3d2d_event_lif_jtag_UNRELEASED.bit
7,797,844 bytes
SHA256 f50a156342eaf1173a3869b5316e4edc1d59662d9f0d687bcec600f7b0efdeab
native 12/12 SHA receipts OK
full original DRC SHA256 f1cc7a7b72b7eeee85828a6c5f7cb75d56894a55a2143cfe4e0f1f6c8098ebee
Vivado 2025.2, K26 xck26-sfvc784-2LV-c, routed 100MHz
WNS +2.136ns; TNS 0; WHS +0.010ns; THS 0; no failing endpoints
exact seven reviewed XSDB/JTAG vendor warnings ONLY:
  PDCN-1569: A2/I1, A3/I0, A5/I0, exact cells/equations
  REQP-1857: jtag_axi rx_fifo_i BRAM18 WRITE_FIRST advisory
  REQP-1858: jtag_axi rd_cmd_fifo_i, wr_cmd_fifo_i BRAM36 advisories
  RTSTAT-10: 39 unroutable nets, 37 listed; only 15 actually printed
```

The independent **physical** auditor is distinct from CI, synthetic unit tests and the native read-only gate. It was run by the owner with `--run-dir "$RUN" --hw-dir "$HW"` and returned the success marker. This accepted image/physical folder and earlier original timing-failed folders are immutable. Never rebuild, overwrite, reprogram or mutate an already accepted original by default.

**Historical successful physical ladder:** D3.C JTAG AXI-to-BRAM actual PL communication; D3.D.1 one signed16 LIF×4; D3.D.2A four independent neurons×4/two workloads (owner original physical `m08_d3d2a_four_HW_UBi3VCax`); D3.D.2B four neurons with on-fabric recurrent synaptic routing (physical `m08_d3d2b_synaptic_HW_Pw3KKKXl`); D3.D.2C real original M06 32 neurons×4/five recurrent edges with 17 **host-coalesced** external events (physical `m08_d3d2c_m06_HW_BsHcfs4j`, bit SHA `244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932`, 384 checked); D3.D.2D adds individual signed raw input event PUSHes **summed in fabric** (512 checked). None yet establishes autonomous asynchronous event streams, M05 original HLS physical router, M06 HLS/real DDR/paging, physical sparse scheduling, Linux PS↔PL ownership, PL clock independence, performance or energy benefits.

## 1. New chat READ FIRST — actual project files and code

**Repo:** `Xtimetraveler-Prime/Thesis`; research source root `Neuromorphic_Accelerator/v1`. **Accepted source branch:** `agent/neuromorphic-accelerator-v1-m08-d3d2d-raw-event-ingress`, draft PR **#92**, stacked on D3.D.2C PR #91 and earlier draft PRs #87–#90. The user has not authorized merges; **leave all draft/unmerged**. Check live branch HEAD because documentation changes have advanced it.

Read these sources **before** deciding the next implementation:

1. This handoff `docs/M08_D3D2D_TO_NEXT_PHYSICAL_HANDOFF_2026_11_20.md`.
2. **Authoritative physical evidence** `docs/M08_D3D2D_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md` and `docs/M08_D3D2C_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md`.
3. **Known working procedure and failed timing recovery** `docs/M08_KV260_SUCCESSFUL_BITSTREAM_METHODS_2026_11_20.md`.
4. `roadmap.md`, `README.md`, `docs/M08_TESTS_EXPLAINED.md`. Read relevant M08 and M09 sections to align proposed next scope; historical “PENDING” text is superseded by the authoritative acceptance above.
5. `docs/M08_D3D2D_RAW_EVENT_INGRESS_PLAN_2026_11_20.md`, `docs/M08_D3D2C_M06_32_NEURON_PHYSICAL_PLAN_2026_11_20.md` for ABI, M06 oracle, 100 MHz failed timing route and successful sequential pipeline.
6. Real design/test/gates, not a prose substitute: `rtl/m08/m08_d3d2d_raw_event_lif_axil.v`, `rtl/m08/tb_m08_d3d2d_raw_event_lif_axil.sv`, `scripts/m08_d3d2d_event_vectors.py`, `scripts/m08_d3d2d_event_gate.py`, `scripts/m08_d3d2d_event_build.tcl`, `scripts/run_m08_d3d2d_event_pc.sh`, `scripts/m08_d3d2d_event_native_review.py`, `scripts/m08_d3d2d_event_readback_once.tcl`, `scripts/run_m08_d3d2d_event_physical_once.sh`, `scripts/m08_d3d2d_event_physical_audit.py`, and `tests/test_m08_d3d2d*.py`. Compare accepted earlier `rtl/m08/m08_d3d2c_m06_32_lif_axil.v`. The real M06 independent M02 dense/event + M03 sparse vectors originate in `scripts/m06_g3_3_m02_m03_owner_vectors.py`.
7. Prior hardware/safety record: `docs/M08_D3D2B_NEXT_CHAT_PHYSICAL_HANDOFF_2026_11_20.md` and physical recovery runbooks. If a broader roadmapped branch exists, read its actual source before conflating distinct research threads.

**Original evidence location:** `~/Thesis_Evidence/M08` exists on the owner's Linux PC, **not** inside GitHub/CI/assistant container. CI success cannot substantiate a new physical board result. Never claim to have viewed owner-local files not actually supplied.

## 2. NEXT physical increment proposal: D3.D.2E tick-aware fabric event queue (NOT YET DEVELOPED)

**Why this next step:** D3.D.2D already accumulates **17 individual host-delivered events inside fabric**, but JTAG AXI-Lite PUSHes are serialized/synchronous, and nothing yet proves event-arrival decoupling, a persistent FIFO, independent per-tick event service, sparse scheduling or asynchronous communication. Next high-value controlled physical test is to introduce a **bounded on-FPGA FIFO/queue and separate event-service/tick-consumption boundary**, without simultaneously adding DMA, real DDR, Linux PS MMIO or new neuron math.

**Suggested new work label/ABI:** D3.D.2E, a new `M32Q` version/magic (suggestion only; confirm roadmap and address-space constraints first). Keep exactly **32 neurons, 4 logical ticks, 5 signed positive-delay recurrent edges, 3/4 truncate-toward-zero LIF decay and original 17 signed current input events**, against the independently reconciled M02 dense/event + M03 sparse golden. Separate (1) enqueue acceptance, (2) on-fabric dequeue/service and signed bucket accumulation, and (3) compute/tick commit after the defined input events are serviced. Provide observer registers for accepted count, FIFO depth/high watermark, serviced count and tick-specific service completion, rather than asserting behavior from host writes alone.

**Design decisions to explicitly settle before RTL:** finite FIFO depth, event ordering, behavior on a late/prior/future tick, atomic signed overflow handling without silently losing an event, empty-service behavior, full FIFO/SLVERR or backpressure, BUSY vs enqueue/clear/reset semantics, spike history and prohibition on same-tick recurrent propagation, replay/nonce isolation, preservation of signed saturation and 3/4 truncation. Add independent tests for malformed tuples, 0 and max values, duplicate/coincident events, ordering, queue full/empty, under/overservice, reset during safe phase, and signed overflow. Don't claim asynchronous physical operation from an ordinary synchronous FIFO behind JTAG.

**Minimum new RTL/physical oracle:** all **128** reconstructed external signed32 buckets **plus** **128 voltages, 128 spike decisions, 128 on-FPGA recurrent currents**, exactly the original **512** numerical comparisons, and additional independently meaningful FIFO-service counters/ordering. Simulate actual new clocked Verilog through Icarus (no skip-as-pass); test queue service and all negative paths. If integrated queue+32 neurons is too complex, split a smaller *first* queue-control physical submilestone and state its bounded coverage before integrating the full M06 workload.

**What NOT to imply:** physical M05 HLS, M06 DDR/paged HLS, DMA/AXI-Stream, event-driven sparse skipping, clock independent of PS, sustained throughput, power/energy, Loihi 1/2 equivalence, an independently clocked or asynchronous hardware fabric. These should become later **separate** physical tests only after the appropriate evidence.

## 3. Work sequence — start developing, not just describing

1. **Inspect live GitHub branch/PR and real files**, read roadmap/handoff/methods/acceptance. Summarize bounded scientific hypothesis/expected physical result and remaining claims.
2. **Create NEW stacked development branch** from accepted current D3.D.2D head, e.g. `agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue`; open a **draft PR** stacked on PR #92 branch; **DO NOT MERGE**. Preserve accepted prior source, bitstream and evidence folders.
3. Develop actual source-only RTL/ABI + deterministic FIFO/tick-service contract + M06 original independent oracle adapters; actual clocked AXI-Lite Icarus simulation of enqueue/dequeue/service, 512 neural/current outputs, negative cases, source-only fail-closed gate, tests, and initial new phase plan. Avoid one-cycle deeply combinational recurrence.
4. Develop a **separate offline Vivado 2025.2 owner-PC builder**, new first-original 12-file SHA ledger and PC launcher **without any JTAG**. Use a **brand-new** independent folder. First-image new DRC/timing/bit SHA review defaults to **exit 2 / REVIEW REQUIRED**, not auto-approval.
5. **Stage, but hard block** a new one-shot JTAG Tcl/shell and independent 6-file physical auditor, with mock evidence/mutation tests. **DO NOT release/program** the new candidate until the user supplies genuine first native DRC/timing/bit SHA and a separate exact-image acceptance gate passes on the owner's PC.
6. Run real Icarus and CI; fix actual regressions; update roadmap, README, M08 tests explained, phase plan and PR with **precise completed vs pending status**. Provide owner-local VS Code terminal verification commands after each change, and if source passes, the **offline-only** native Vivado candidate commands. On later owner board data, preserve original evidence and audit independently; only then assert new physical PASS.

This is **suggested next research scope**, not a pre-existing proven implementation. First confirm live roadmap priorities; if another immediately-needed hardware boundary is more faithful to the approved roadmap, document the choice and keep it equally bounded. Never do a wide redesign of previously physically accepted stages.

## 4. Repeat exactly the successful safety, Vivado and evidence method

See `docs/M08_KV260_SUCCESSFUL_BITSTREAM_METHODS_2026_11_20.md` for technical details. Essential invariants:

- Linux Ubuntu 24.04.5, genuine **Vivado 2025.2**, K26 `xck26-sfvc784-2LV-c`, 100 MHz **PS-requested PL0** clock (**PS-clock dependency still exists**), **fabric POR 256 cycles** in PL without using PS `pl_resetn0` for JTAG AXI data-path reset, PS HPM masters **DISABLED**.
- Safe JTAG AXI→SmartConnect→4KiB BRAM `0xA0000000` and standalone AXI-Lite neural window `0xA0001000`; validate all bus pins, controller-derived BRAM geometry and clock/reset/address nets, generated wrapper and source hash. PS TTC0 WAVEOUT2 EMIO to fan output A12/LVCMOS33 is an existing route, **not independent cooling proof**. Physical operator checks separately powered active fan/cooling and UART capture.
- Earlier D3.D.2C first owner route reached routing but **FAILED timing**: WNS −0.188ns, TNS −18.168ns, 277 failing setup endpoints. Fix was to iterate one signed recurrent edge/clock and register neuron update in stages, preserving M06 semantics. D3.D.2C re-routed WNS +2.675ns; D3.D.2D WNS +2.136ns. Retain the working pipeline unless tests justify another change.
- Original PC-only builder creates unique fresh Vivado project, routes, checks full DRC, setup/hold constraints and clocks, writes bitstream, records **12 original SHA receipts**. `Routing Is Done` does not mean timing pass; `OFFLINE_BUILD_EXIT=2` can mean a **successful bitgen but first image review required**. Do NOT rebuild an accepted image to clear a review gate.
- Original *new-image* native read-only gate first reviews **this image's** exact 7/other warning details (XSDB LUT pins, FIFO hierarchy, RTSTAT first-15 displayed names), original full DRC SHA, RTL/builder/POR SHA, bit SHA+size, clock/timing and 12 receipts. **Never reuse D3.D.2D A2/A3/A5 warning approval on a new routed image.** Fail closed and mutation-test. GitHub CI lacks owner's original native evidence.
- After new native image approved, user independently confirms active cooling/UART capture, known stock boot recovery, exclusive stable JTAG, exact target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`/device `xck26_0`/`hw_axi_1`, and explicit experiment-specific consent flags. Only **ONE** Tcl `program_hw_devices`, no retries, no flash/SD writes, no PS DDR/Linux MMIO. Verify BRAM `55AA22DD` and distinct new peripheral magic before neural readback. Create a new six-file SHA physical receipt and independent read-only audit; mock tests are not physical evidence.

## 5. Owner Linux VS Code source-only first commands

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2d-raw-event-ingress
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2d-raw-event-ingress
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_m08_d3d2d_raw_events_source.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2d_owner_native_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2d_event_physical_audit.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

These commands do NOT program hardware. Use updated branch/test commands when creating the NEW source submilestone. The accepted physical D3.D.2D board run is completed and should not be repeated by default. For **read-only** evidence replication, see `docs/M08_D3D2D_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md`.

## 6. Next-chat completion contract

Return actual code/document/PR progress, regression outcomes, specific unmet risks and copy-ready Linux owner commands. Clearly separate **source simulated**, **offline Vivado routed+bitgen**, **exact new original-image accepted**, and **real board programmed+independently audited**. The next chat may finish one or more stages, but it must never invent or skip owner physical evidence. No merge without user instruction. M08 remains OPEN and M09 PLANNED until their own agreed full scopes are completed.

**This handoff itself is DOCUMENTATION ONLY. D3.D.2E is not yet developed or physically tested.**
