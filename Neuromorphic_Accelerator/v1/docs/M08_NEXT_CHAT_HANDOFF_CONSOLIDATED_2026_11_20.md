# NEXT-CHAT HANDOFF — M08.5 matched real memory and execution experiments (2026-11-20)

> **FIRST INSTRUCTION TO THE NEXT CHATGPT INSTANCE:** M08.4 **IS PHYSICALLY ACCEPTED AND CLOSED**. The user supplied the **successful original, independent read-only hardware evidence audit** and explicitly asked that the result be recorded and the next milestone activated. **M08.5 IS NOW ACTIVE.** Do **not** ask the owner to reprogram, re-run or re-audit the original M08.4 image merely to resume work. Read this document and the current `roadmap.md`, then proceed with new **M08.5 source-first development** and give local terminal verification commands after every source change.

**Do not subdivide milestones:** M08.4 was one physical neural-paging acceptance gate; M08.5 is **one** matched-execution/memory-comparison gate; M08.6–M08.7 will be **one** repeatable measurement/owner-review gate; M09 is thesis/analysis. No additional D3.D.3B/C/D, M08.5.1/5.2/5.3, new PR or branch per failed Icarus test/AXI transfer/DDR check. Engineering tasks inside M08.5 may have descriptive tests/docs, not independently "complete" micro-milestones.

## M08.5 SOURCE-INCREMENT UPDATE (later on 2026-11-20; read before the earlier first-task advice)

The first **SOURCE ONLY** M08.5 matched comparison/provenance increment is now on `agent/neuromorphic-accelerator-v1-m08-matched-experiments`, draft **PR #95**, stacked on existing accepted-but-unmerged draft PR #94 (and #93). **Do not merge/rebase.** New contract `src/neuromorphic_accelerator_v1/m08_matched_experiments.py`, original-oracle-backed emitter `scripts/m08_matched_contract.py`, negative/positive tests `tests/test_m08_matched_experiments.py`, and [experiment/test explanation](M08_5_MATCHED_EXPERIMENT_CONTRACT.md) establish six explicitly separate onchip/JTAG-host-paged/PS-PL-DDR × timestep/event cells. D3.D.2C, D3.D.2E, and accepted M08.4 are historical physical **but not matched timing controls**; no DDR ownership or physically skipped sparse neuron updates are claimed. Earlier instructions below saying to *start* the comparator contract are now historical: next development within M08.5 is source-matched controls/RTL and read-only PS/PL memory-ownership feasibility review, followed only when warranted by separate offline native and explicitly owner-authorized physical work. **M08.4 ACCEPTED/CLOSED** and all original evidence are unchanged. Owner source-only commands are in the new contract document. GitHub CI for any future code change must be checked against its exact new HEAD; no prior CI implies a new hardware acceptance.

## M08.5 CONTINUATION: Digital Twin v3 physical DDR route review and first 256B source-only RTL gate

User independently reports all prior PR #95 M08.5 matched-contract VS Code verification commands **PASS**. Work remains on **the SAME M08.5 branch and draft PR #95**, stacked on accepted-but-unmerged draft PR #94 (and #93); no merge/rebase, no changed original owner evidence. The owner suggested consulting the Digital Twin before reinventing PS/PL memory. Source inspection confirmed that **Loihi Digital Twin v3 P02.4b really did physical DDR paging via PL page walker → range guard → AXI128 burst adapter → SmartConnect → PS S_AXI_HP0_FPD**, distinct from v3 P03 **PS M_AXI_HPM0_FPD → SmartConnect → PL AXI-Lite control**, with an independently documented PS HPM0 boot-width mismatch and substantial later OS/XMPU DDR ownership caveats. The accepted M08.4 K26 image retains disabled PS HPM, JTAG debug staging and no physical DDR. **Do not copy v3's 0x40000000 64MiB backing window, 512KiB Loihi/signed24 context records, bitstreams, ELFs or halted-Linux methods into new M08 signed16 memory access without new independent ownership/recovery authorization.**

New files **rtl/m08/m08_m085_ddr_page_admission.v**, **rtl/m08/tb_m08_m085_ddr_page_admission.sv**, **src/neuromorphic_accelerator_v1/m08_m085_pspl_lineage.py**, **scripts/m08_m085_twin_pspl_audit.py**, **tests/test_m08_m085_pspl_reuse.py**, and [single study + test/runbook](M08_5_DIGITAL_TWIN_PSPL_REUSE_AND_PAGE_GATE.md) implement source-level static route/provenance checking and a real RTL 256B request admission/timeout/quarantine simulator, **unconnected and default-denying**; the testbench is real Icarus with a positive read/write handshake and 18 failure cases. The old independent signed16 neural oracle and physically accepted bitstream/evidence remain unchanged. The source gate cannot demonstrate a live PS or kernel-owned DDR buffer; no new board run, AXI master connection, or physical release is authorized. Next work **within M08.5** is owner-reviewed read-only PS/PL/driver memory ownership, then an actual source-matched 256B AXI master/protocol/RTL integration if feasible; no gate proliferation. PC-only commands are in the new document. Full M08 source/RTL CI and owner local verification required for the new exact HEAD, not inherited from old PR #95 commit.

## M08.5 CONTINUATION: owner-verified previous tests PASS; first-party 256B real AXI4 master + original-page Icarus BFM

The owner reported all previous Digital Twin v3/256B guard and inherited tests **PASS**. Without new branch/PR or hardware authorization, SAME M08.5 branch/PR #95 now includes **rtl/m08/m08_m085_axi128_page_engine.v** (full AXI4 128-bit 16-beat INCR 256B AW/W/B and AR/R master with transaction IDs, bus attributes, full page staging, read-valid and B completion fences, stall timeout and sticky quarantine) and **rtl/m08/m08_m085_axi128_page_candidate.v** (connects the already source-tested zero-window-by-default signed16 page admission with this new AXI protocol master, propagating guard poison to in-flight transfer and masking read data until successful full page ACK). The real **rtl/m08/tb_m08_m085_axi128_page_candidate.sv** AXI bus functional model checks synthetic DDR 256B **write followed by same-address read**, 16 actual W and R handshakes, all 2048 payload bits, exact 512 simulated transferred bytes, stable AW/AR and W under backpressure, response and ID checks, and **25 independent fault scenarios**. Existing **tests/test_m08_m085_pspl_reuse.py** now also generates all **six original 256B independently derived M02/M03 signed16 neuron input pages** from existing m08_paged_m06_lif_fixture and sends each through the actual Icarus BFM roundtrip separately; **the 512 neural oracle outputs are never transferred as inputs**. New core source, testbench, and source docs in [M08.5 route/transport study](M08_5_DIGITAL_TWIN_PSPL_REUSE_AND_PAGE_GATE.md).

**Important separate boundaries:** these are real new RTL AXI4 protocol handshakes on a **simulated** memory slave, but the original accepted M08.4 single-page bank / neural compute are **not yet wired** to the 2048-bit snapshot ports. No PS S_AXI_HP0_FPD, SmartConnect, HPM0 control, XSA/bitstream, physical DDR, verified kernel DMA buffer or clock route exists for this M08.5 candidate. Do not assume the transmitted 256B is committed to the real bank just because a simulated B response returns OKAY. Next M08.5 engineering step: source-matched 64×32-bit bank-load/readback/commit and DIRTY-save interface for the existing **unchanged** 256B bank, with fresh Icarus tests; then independent read-only ownership admission/board-release review. Continue same PR, no acceptance/merge/physical authorization until explicit user approval. Operator Linux terminal commands are in the study doc. **Exact latest GitHub CI must be checked after all commits; owner local verification is still required.**

## M08.5 LATEST — owner verified prior AXI source increment, original 64-word bank connected via 256B AXI bridge

The owner ran all prior M08.5 local commands and reported **PASS** after the original six-page standalone AXI4 source test. The SAME draft PR #95 and branch `agent/neuromorphic-accelerator-v1-m08-matched-experiments` now contain a genuine source-level integrated **rtl/m08/m08_m085_axi_bank_bridge.v**, **rtl/m08/tb_m08_m085_axi_bank_bridge.sv**, **tests/test_m08_m085_bank_axi_bridge.py**, and [test, ownership and architectural explanation](M08_5_BANK_AXI_INTEGRATION_CONTRACT.md). They instantiate the unchanged original `m08_host_staged_page_bank.sv` and connect it to the independent 128-bit AXI4 16-beat page engine through the existing default-deny 256B page admission. A LOAD requires an exact M6NF page/tick/neuron-count header, all 64 host word writes, then 64 actual bank word readbacks and byte comparisons before committing READY. A DIRTY SAVE reads all 64 words from the actual bank, sends the 256B AXI write, waits for an OKAY B response, then does a *separate AXI readback of the same DDR page and compares all 256B* before asserting bank save_done. Fault means sticky system quarantine.

New **real Icarus** bus-functional test exercises **each of the six unchanged independently derived original M02/M03 signed16 M06 neural input pages** end to end across simulated six-page DDR, actual bank load, test-controlled (not neural LIF) compute state mutation, dirty save with second DDR readback, eviction to a different page and reload/state persistence, as well as **19 adversarial integrated bank/AXI failures, including rejected wrong-tick saves and page-to-DDR-slot aliases**. No neural golden 512-word trace is ever loaded as an input. No physical PS DDR, driver binding, bitstream or owner evidentiary artifact was touched. M08.4 accepted physical results and PR #93/#94 untouched. **Previous text below stating 2048-bit snapshot was not connected to the resident bank is now historic; this bridge connects it, but the separate M08.4 LIF compute engine is still NOT wired to the bridge and PS HP0/DDR remains absent.** Next within M08.5: connect verified original neural computation only after source-gated CPU/PL ownership details, continue independent tests, then controlled offline implementation and separately owner-approved physical acceptance. No new milestone gate, no merge, no hardware run.

## 1. Essential repository and source context

- GitHub: `Xtimetraveler-Prime/Thesis`; working root `Neuromorphic_Accelerator/v1`. Owner's VS Code/Linux repo is `~/Git/Thesis`. Genuine owner Vivado installation: `/home/dna/Vivado/2025.2/Vivado/settings64.sh`, KV260 K26 SOM, single real `xck26_0`, `hw_axi_1`, 100 MHz PS PL0 requested. Owner's physical evidence is on their **local PC**, not present in GitHub; do not invent file access.
- **Current accepted M08.4 source branch**: `agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership`; **draft PR #94**, stacked on the older accepted **draft PR #93**, branch `agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue`. Both PRs remain **DRAFT and UNMERGED**. **Never merge or rebase accepted history without explicit owner authorization.** Inspect Git state before deciding whether to continue on the accepted branch or create **one justified gate-level M08.5 branch** off its tip; absolutely no branch/PR per subtask.
- **Authoritative documentation**: `roadmap.md`; this one consolidated handoff; `docs/M08_REMAINING_PHYSICAL_EXECUTION_PLAN_2026_11_20.md`; `docs/M08_4_FIRST_OWNER_PAGED_NEURAL_PHYSICAL_2026_11_20.md` (official accepted owner result); `docs/M08_PAGED_SOURCE_RTL_CONFORMANCE_2026_11_20.md`; `docs/M08_D3D2E_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md`; `docs/M08_3_LOIHI_KV260_MEMORY_OWNERSHIP_REUSE_2026_11_11.md`; `docs/M08_PHASED_HARDWARE_PLAN.md`. Older `docs/archive/M08_ROADMAP_CHRONICLE_THROUGH_2026_11_20.md` is the preserved historical 171 KB chronicle, **not** current status. `docs/M08_4_PAGED_FIRST_OWNER_NATIVE_TRIAGE_AND_PHYSICAL_STAGE_2026_11_20.md` is a **historical one-shot pre-release runbook, NOT a new instruction to program**.
- Scientific question: with **identical** neuromorphic numerical semantics, network/synapses, original event workload and measurement boundaries, characterize how sparse event-driven execution interacts with **neuron-state virtualization** when logical resident capacity N exceeds available on-chip resident K. Distinguish source/software model predictions, real RTL simulations, measured real FPGA cycles/transfers, JTAG-host staging and genuine PS/PL DDR. **Never label one as another.**

## 2. M08.4 FINAL PHYSICAL ACCEPTANCE — DO NOT RERUN

The user supplied the following **original post-fix** evidence and **subsequent** independently passing original-file audit, accepted 2026-11-20:

| Accepted original datum | Evidence |
| --- | --- |
| Owner-native Vivado 2025.2 first post-fix image | `~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW` |
| First-original bit SHA256 | `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494` |
| Bit file | `bitstream_candidate/m08_paged_m06_lif_jtag_UNRELEASED.bit` (the historical file name, **already programmed and accepted**) |
| First-original hardware directory | `~/Thesis_Evidence/M08/m08_paged_m06_lif_HW_zhUx7lLJ` |
| Immutable native source/route/bit SHA ledger | **15/15 verified**, includes exact new K26 source/bit/DRC/clocks/timing; native new-image-specific checker `ACCEPTED` |
| Immutable original physical evidence SHA ledger | **13/13 verified** by owner's `sha256sum -c`, including original executed Tcl, JTAG Vivado log/jou, exit receipt, original host input pages, oracle and first 128-row neural trace |
| Original JTAG programming | **Exactly one** first-original K26 program marker, accepted after independent log marker-order audit |
| One-resident signed16 neural paging | **One** 64×32-bit = 256B on-chip resident host/compute bank, **six** 256B logical pages containing 6+6+6+6+6+2 neurons, plus an **independent** host-loaded five-edge configuration page |
| Physical dynamic work | **24 real page LOAD/64-word readback/COMMIT/DISPATCH/64-word DIRTY readback/SAVE/replacement cycles** through four ordered tick barriers |
| Independent numerical parity | **128 HOST-coalesced input-current values** + **128 truly PL-computed voltages** + **128 PL-computed spike decisions** + **128 PL-computed recurrent currents** = **512/512** exact original M02/M03/M06 comparisons |
| Native route | AMD K26, routed Vivado 2025.2, 100 MHz PS PL0, WNS **+0.763 ns**, WHS **+0.010 ns**, seven individually reviewed vendor debug/JTAG DRC warnings, zero setup/hold/pulse-width violating endpoints |
| Accepted residual caveat | Five `LUTAR-1` async-reset methodology advisories **untraced**; owner expressly accepted limited first JTAG-test risk. Do not retroactively claim their cell paths were verified. |

The first physical run (Nov 20, 2026 **18:40:35–18:41:37 America/Denver**) finished the hardware test, printed `M08_4_PHYSICAL_128_HOST_CURRENTS_384_FABRIC_COMPUTED_24_PAGES_ONE_BANK_PASS`, and verified all 13 SHA receipts. The **first** independent Python auditor subsequently *falsely* rejected a programming marker: Vivado echoes `# puts "M08_4_NEW_IMAGE_PROGRAM_ONCE_START"` and also emits the actual standalone runtime line. The auditor had wrongly counted both via substring. `scripts/m08_paged_m06_lif_physical_audit.py` was corrected to count **only exact standalone marker lines in globally expected chronological order**, while continuing strict 13 SHA/executed-source/128 physical-row/oracle comparison. Six new synthetic full-receipt/adversarial tests `tests/test_m08_paged_m06_lif_physical_reaudit.py` passed; **548 M08 source/real Icarus tests** passed [GitHub Actions 44851903415](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44851903415). **No second hardware program or original evidence rewrite occurred.**

**Critically: the owner has NOW rerun this corrected independent auditor READ-ONLY on the first immutable physical folder and posted actual SUCCESS output**:

```text
00_executed_source.tcl: OK
01_jtag_paged_m06.log: OK
02_jtag_paged_m06.jou: OK
03_exit.txt: OK
10_edge_config_input.hex: OK
11_neural_page_0_input.hex: OK
11_neural_page_1_input.hex: OK
11_neural_page_2_input.hex: OK
11_neural_page_3_input.hex: OK
11_neural_page_4_input.hex: OK
11_neural_page_5_input.hex: OK
20_independent_512_oracle_ONLY.hex: OK
80_physical_paged_neural_parity.txt: OK
original_native_15_SHA_files_checked: true
original_physical_sha_files_checked: 13
original_single_JTAG_program_marker: true
ordered_tick_barriers: 4
physical_256_byte_page_dispatches_saved: 24
independent_host_coalesced_input_checks: 128
independent_physical_pl_computed_checks: 384
total_exact_numerical_comparisons: 512
physical_ddr: false
```

**Historical auditor output caveat**: the JSON still includes `"owner_final_M08_4_acceptance_review_pending": true` and `"status": "...NUMERICAL_PASS_REVIEW_REQUIRED"`. These are deliberately conservative labels emitted by the generic **pre-human-review** Python tool; every programmed numerical check passed, and the owner **subsequently reviewed and directed formal acceptance**. Do **not** edit original JSON or re-run JTAG to change a status string. **M08.4 is PHYSICALLY ACCEPTED in `roadmap.md` and its owner acceptance document.**

**Hard scope limitations**: original 17 external events were **HOST-coalesced** for this new paged-neural design; they did **not** enter an on-fabric raw-event FIFO. No actual PS DDR/DMA, cache coherency, autonomous asynchronous clock/event execution, matched timing/throughput or power/energy was measured. This result **does** establish physical compute-bearing, resource-bounded neural-state page replacement on FPGA with exact signed16 reference parity.

### Separate earlier physically accepted on-chip FIFO baseline (DO NOT EQUATE THE IMAGES)

Prior D3.D.2E M32Q physical run: native `~/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC`, bit SHA `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc`, physical `~/Thesis_Evidence/M08/m08_d3d2e_queue_HW_4HQkm7rN`, **6/6** immutable physical receipts, **17 actual raw FIFO events** queued and serviced with 5/5/4/3 ordering and 128 initial buckets proven zero; **512/512 physical** neural parity. WNS +1.844 ns, WHS +0.010 ns. It is a **different topology and image**, not automatically apples-to-apples with new 6-page hardware. No accepted source, first owner evidence or bit should be copied over or reprogrammed.

## 3. M08.5 — ACTIVE NEXT ACCEPTANCE GATE

**Goal:** rigorously match **same signed16 neuron semantics, same 32-neuron/five-edge/17-event workload, same event order and synchronization boundaries, same N/K geometry when applicable**, and compare feasible memory/execute strategies:
1. **Timestep-driven on-chip** (actual proven M32Q and/or a source-matched RTL control).
2. **Event-driven on-chip** (actual FIFO/event-service baseline with explicit differences documented and/or truly equivalent control).
3. **Timestep-driven host-paged** (the newly accepted six-page JTAG-host-backed execution).
4. **Event-driven host-paged** where feasible, then **genuine memory-backed DDR timestep/event** only when a safe, verified PS/PL memory owner and route exist.

Do **not** claim these are already matched just because two older physical runs both have 512 outputs. Define exactly matched workload, memory residency K/N, queue service semantics, control strategy and **measurement windows** before comparisons. Report honest unmapped or unavailable cells in the comparator matrix.

**Mandatory M08.5 deliverables to progress** (one broad gate, not four new milestones):
- A **single provenance-aware comparator contract/matrix**: image/source SHA, native route/clocks, input M02/M03 golden version, N/K and page bytes, exact numerical outcome per configuration; host-staging vs PL compute time, raw events vs host-coalesced events, on-chip vs host-paged vs actual DDR and its proof, number of actual page transfers, dirty-save bytes, tick/event barriers, stalls, and measurement origin. Explicit **not comparable yet** flags for dissimilar original baselines.
- First source-only/RTL reproducible matched controls and negative tests for manipulated event order, incorrect off-chip ownership, wrong page state, wrong arithmetic or wrong timing-domain assumptions. Reuse available M07 policy/traffic and original M02/M03 oracle fixtures; **don't introduce another easier neural reference**.
- Read-only owner-side **M08.3 PS/PL/DDR/DMA readiness inventory** and available runtime/kernel/devicetree/device binding evidence, without programming hardware or writing OS/DDR/MMIO. Ask for only genuinely missing owner data. A device-tree name, `/dev/mem`, a guessed CPU→PL address such as `0xA0000000`, or a simulated backing buffer are **NOT** proof of safe DDR.
- If true DDR is technically possible, independently validate connected PS→PL route, driver ownership and safe buffer lifetime, physical/DMA mask/IOMMU window, cache coherence, clock/reset and quiesce/recovery, before constructing a separate SHA-pinned **new** offline K26 candidate and separately approved one-shot physical test. **Never** infer DDR ownership from the existing JTAG AXI scratch-BRAM map.
- Measured/stated costs only when evidence exists; distinguish **simulated cycle/service predictions**, original JTAG **host-end-to-end** timing, **actual on-fabric** cycle counters where available and **true DDR transactions**. Report transfer counts, bandwidth, page locality and stall distributions with their measurement method. Collect repeats/uncertainty at combined M08.6–7; no invented throughput/power/energy.

### Recommended first development task in the new chat (NO board action)

1. Read `roadmap.md`, this handoff, M08.5 execution-plan gate, M08.3 readiness notes, M07 matched-ablation foundations and original accepted signed16 fixture/oracle. Inspect relevant current source/tests and the existing draft PR state.
2. Create **one M08.5 comparator/provenance contract** as source + tests. Enumerate which comparator rows are actually **physical**, merely **Icarus**, merely **PC model**, or **not yet available**. Make mismatched raw-event vs host-coalesced input a **fail-closed** comparator condition rather than quietly treating them as identical. Distinguish 128 host checks from 384 PL-computed checks and respect one resident bank in the accepted paged design. Design controls to eventually isolate the contribution of event sparsity from that of page movement.
3. Add deterministic positive and adversarial source/RTL tests to enforce strategy equivalence before any new physical work; preserve existing M08 tests and original numerical oracle; run CI. Source-only confidence is necessary, **not** hardware authorization.
4. Design a strictly **read-only** owner PC + KV260 PS/PL memory inventory (do not access unknown MMIO or DDR addresses, no `sudo devmem`, no assumed kernel DMA buffer) and request the owner's outputs only after the software deliverables pass. Make a clean PS/PL DDR gate: `AVAILABLE_VERIFIED`, `NOT_AVAILABLE`, `UNKNOWN`; no guesses or silent fallback labeled as DDR.
5. Develop in larger coherent increments within M08.5, not a new branch for every missing ready bit. Include reproducible tests, evidence and local VS Code terminal commands in **every development response**; wait for user local verification before requesting a new offline Vivado build or JTAG action.

## 4. Current source/test files worth reopening

- **First-party signed16 paged neural RTL:** `rtl/m08/m08_paged_m06_lif_engine.v`, `rtl/m08/m08_paged_m06_lif_shell.v`. Real RTL host-owned 256B AXI4-Lite bank in `rtl/m08/m08_host_staged_page_bank.sv`, `rtl/m08/m08_axil_page_control.sv`.
- **Physical exact-image and immutable auditors:** `scripts/m08_paged_m06_lif_exact_native_accept.py`, `scripts/m08_paged_m06_lif_native_review.py`, `scripts/m08_paged_m06_lif_physical_audit.py`, `scripts/m08_paged_m06_lif_source_gate.py`. Read-only native records are **historical**; no need to run/program for new task.
- **Unchanged independent oracle:** `scripts/m08_paged_m06_lif_fixture.py`, `scripts/m08_d3d2c_m06_vectors.py`, `scripts/m08_d3d2d_event_vectors.py`; original M02 dense/event and M03 sparse fixtures, signed16 leak 3/4 truncate-toward-zero, saturation and positive-delay recurrent edges. The goldens are **comparison-only**, never preload expected voltages/spikes into neural input pages.
- **Actual positive/negative HDL tests:** `tests/test_m08_paged_m06_lif.py`, `tests/test_m08_paged_m06_lif_fail_closed.py`, `tests/test_m08_paged_m06_lif_physical_reaudit.py`, `tb_m08_paged_m06_lif.sv`, `tb_m08_paged_m06_lif_fail_closed.sv` (locate exact TB paths before issuing simulator commands). Tests for missing edge setup, wrong page/tick, invalid threshold, compute-ACK timeout and bad recurrent delays deliberately fail closed.
- **Older foundations with narrower claims:** `scripts/m08_d3d3a_page_stage.py` is a **software-only proposed 4KiB M06 reference image**, NOT the new real on-fabric neural ABI. `rtl/m08/m08_page_compute_probe_shell.v` and `m08_page_compute_probe.v` provide an earlier checksum-only first-party host/compute probe, not LIF. `scripts/m08_m06_parameter_pages.py` derives earlier input-only (15+15+2) neuron parameters; they are **not** the accepted six-page dynamic neural-state geometry. Do not regress to one of these earlier probes as a replacement for accepted M08.4.
- **Separate old physically accepted 17-event FIFO**: M32Q D3.D.2E original source/fixture; review its owner accepted file before making a physically matched comparator. Do not assert original source’s 17 raw FIFO events enter the new paged shell.
- **Documentation:** `docs/M08_3_LOIHI_KV260_MEMORY_OWNERSHIP_REUSE_2026_11_11.md` informs PS/PL ownership; older accepted Loihi-v2 P08 experiments are **different project/neural precision** and cannot validate M08 signed16 DDR safety.

## 5. Working method, GitHub integration, local verification

**Use connected GitHub tools to read/update repository content.** The cloud/container here may not contain a clone and may not access GitHub via raw shell network; do not assume `~/Git/Thesis` exists in the assistant sandbox. Discover live GitHub plugin actions through tools, fetch exact file contents before changing them, use each original blob SHA for updates on the correct branch, and check CI for every substantive new HEAD. If user attaches local files, inspect those exact attachments rather than inferring their contents. Never mutate `~/Thesis_Evidence/M08` through code or invent owner hardware pass results.

**Owner's usual local verification commands (VS Code terminal, PC source-only):**

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1

command -v python3
command -v iverilog
command -v vvp
python3 scripts/m08_paged_m06_lif_fixture.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif.py' -v
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_fail_closed.py' -v
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_physical_reaudit.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

Adjust the `git switch`/pull branch when the new instance deliberately selects **one proper M08.5 feature branch**; fetch first and **never merge draft #93/#94 by accident**. Do not run `vivado`, `program_hw_devices`, hardware manager or board actions as part of initial source tests. The prior source CI run [44851903415](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44851903415) passed 548 M08 tests, **at that historical source commit**. New tests/commits require **new exact-HEAD** CI and owner verification; never claim previous CI proves future code.

**When hardware becomes warranted (not yet authorized for M08.5)** use this sequence: owner review of comparator/ABI and negative tests → real Icarus integration and source CI → fresh unique PC `~/Thesis_Evidence/M08/` **offline** Vivado 2025.2 project/bitstream → original 15-or-redefined SHA ledger → image-specific routed DRC warning/pin, timing, clocks and source/bit SHA acceptance → independent cooling/fan, UART, stock rollback and exclusive JTAG preflight → **explicit owner authorization for one narrowly bounded program** → new unique immutable physical evidence folder → read-only independent audit → owner acceptance/documentation. **No automatic reprogramming, no overwriting original evidence, no unrestricted PS/DDR writes.**

### Proof/evidence and reporting expectations

At the end of every development increment give: what files changed, what real tests executed (source vs genuine HDL vs offline Vivado vs physically run, clearly separated), CI run URL/conclusion when verified, any bounded failures or assumptions, and **copy/paste-ready exact owner `~/Git/Thesis` VS Code commands**. Keep the authoritative `roadmap.md` concise and statuses honest. Do not promise asynchronous work.

## 6. Roadmap state / next handoff decision

- **M01–M03**: complete PC neural/traffic/oracle foundations.
- **M04–M06**: complete within offline/RTL/HLS-conformance bounds; no claim of physical DDR or original HLS neural page execution.
- **M07**: complete PC caching/scheduling/matched ablation foundations.
- **M08.4**: **PHYSICALLY ACCEPTED/CLOSED**, immutable first owner 24-page JTAG run, owner independent 13/13 and 512/512 original audit.
- **M08.5**: **ACTIVE**, matched execution/placement control strategies, documented provenance and safe DDR feasibility inventory.
- **M08.6–M08.7 (one combined gate)**: PLANNED repeatable hardware measurement, variance/resource reporting and owner release.
- **M09**: PLANNED thesis analysis/plots/limitations/closeout.

**NOW START M08.5** by inspecting exact current branch/files and implementing a source-only comparator contract + adversarial tests. Do not seek owner reconfirmation of already accepted M08.4 or repeat its hardware run.
