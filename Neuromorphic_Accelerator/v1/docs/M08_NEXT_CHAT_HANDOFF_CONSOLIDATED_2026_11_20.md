# NEXT INSTANCE HANDOFF — M08.4 physical signed16 paging (consolidated, 2026-11-20)

> **IMMEDIATE INSTRUCTION FOR THE NEXT CHATGPT INSTANCE: DO NOT CREATE FURTHER MILESTONE OR SUB-MILESTONE DIVISIONS UNLESS ABSOLUTELY NECESSARY TO DEBUG A DISTINCT FAILURE BOUNDARY.** The user explicitly reviewed and approved a smaller roadmap. **M08.4 is ONE accepted-hardware deliverable**, M08.5 is ONE matched-memory-comparisons deliverable, and M08.6–7 is ONE physical measurement/owner-release deliverable. Do **not** invent D3.D.3B/C/D, M08.4.1/4.2/4.3, new branches per failing Icarus test, or a status-gate PR per Vivado warning. Tasks, regression tests, checkpoints and isolated evidence folders may exist *inside* the parent M08.4. A temporary named debugging experiment is allowed **only when essential to isolate a genuinely different hardware/software failure**, explicitly record the reason, and do **not** promote it to a separately accepted milestone.

**Read first:** [the concise authoritative roadmap](../roadmap.md), [the binding remaining-physical execution gates](M08_REMAINING_PHYSICAL_EXECUTION_PLAN_2026_11_20.md), [the last accepted physical M32Q run](M08_D3D2E_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md), [source-only real RTL host-page integration](M08_PAGED_SOURCE_RTL_CONFORMANCE_2026_11_20.md), and [the archival 171 KB troubleshooting/evidence history](archive/M08_ROADMAP_CHRONICLE_THROUGH_2026_11_20.md). Historical “not programmed” entries are dated history, not current status.

## Authoritative branch / PR / milestones

- Repository `Xtimetraveler-Prime/Thesis`; v1 work root `Neuromorphic_Accelerator/v1`.
- **Work on existing** `agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership` and **draft PR #94**, stacked on draft PR #93 (`agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue`). Both draft, unmerged; **do not merge without user's explicit approval**. Inherited code in PR #93 is physically accepted; later page code is source-only.
- **M01–M06 complete within PC/native offline bounds; M07 PC complete; M08 OPEN (M08.4 active); M08.5 and combined M08.6–7 planned; M09 planned.**
- The user independently ran the latest VS Code M08 page test instructions and reported **all passed**. Dedicated CI had **515 M08 tests OK**, real Icarus including real AXI host-page and original 32-neuron page replay [run 44843119050](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44843119050); CI on further changes must always be checked at the new exact HEAD before claiming success.

## Immutable owner-original physically accepted baseline

- Original Vivado 2025.2 native `~/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC`, accepted bit SHA256 `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc`, WNS **+1.844 ns**, WHS **+0.010 ns**, separately reviewed image-specific vendor DRC. First physical owner `~/Thesis_Evidence/M08/m08_d3d2e_queue_HW_4HQkm7rN`; six original SHA receipt checks OK on **read-only final audit**, `M08_D3D2E_PHYSICAL_M06_17_QUEUED_EVENT_128_BUCKET_384_NEURAL_ACCEPTED`.
- Real K26 JTAG `xck26_0` / `hw_axi_1`: 17 raw signed32 events FIFO accepted and serviced; four ordered clocked service barriers **5+5+4+3**, all **128 current buckets zero before service**, 128/128 fabric input current +128/128 membrane voltage +128/128 spike decisions +128/128 recurrent current = **512/512** original 32-neuron×4-tick, 5-edge M06 neural reference. Original M02 dense/event, M03 sparse numerical oracle.
- **Do not reprogram** this accepted bitstream or change/recreate/re-hash the accepted native/physical evidence. Real physical DDR/DMA, pageable M06 HLS neural state, async independent clock, power and throughput remain **NOT proved**.

## Existing M08.4 source assets

- A **proposed 4 KiB reference-only page** in `scripts/m08_d3d3a_page_stage.py` contains the 630 original M06 input/output oracle words. It is **NOT compute-facing hardware memory**; cannot serve as compute input (would prepopulate expected outputs).
- A real first-party one-resident **256B AXI4-Lite host page** in `rtl/m08/m08_axil_page_control.sv` + `m08_host_staged_page_bank.sv`: full 64-word host load, explicit observed readback before COMMIT, exclusive host/computation dispatch, dirty full readback/SAVE, timeout quarantine. The earlier `m08_ps_page_safe_shell.v` remains safely `ENABLE_COMPUTE=0`; never change it to silently enable untested compute.
- New `m08_page_compute_probe_shell.v` (Verilog-2001 Vivado module-reference-compatible) connects all 19 AXI-Lite pins and `m08_page_compute_probe.v` (real 63-word sequential read/one reserved checksum write). The probe is **NOT a LIF neuron**. Real Icarus test `tests/test_m08_page_compute_probe_shell.py` checks safe handshakes, two page replacement, host/compute mutex, premature SAVE and stalled compute ACK faults. A real regression caught missing WVALID/WREADY and the wrapper was corrected; static gate checks all AXI pins.
- `scripts/m08_m06_parameter_pages.py` derives **real original M06 neural input parameters only** from 630-word M02/M03-backed oracle, 32 neurons in three logical **256B** pages (15,15,2), 1 RTL resident bank. Original signed16 `initial_v, bias, threshold, reset_v`; metadata M6PG, logical ID, valid neurons; reserved checksum word. Real Icarus `tests/test_m08_m06_parameter_pages.py` runs all three pages through AXI load/readback/dispatch/probe/writeback/dirty-save. **These pages do not currently include per-tick currents, dynamic membrane state or recurrent spike/edge state**; they CANNOT compute real M06 LIF and must be extended/replaced before a neural claim.

## ACTUAL new M08.4 work completed since this handoff was started

The initial next-code steps to replace the checksum probe with REAL paged LIF compute have now been **implemented and actually tested in Icarus**; do not start them a second time or claim only a checksum probe is current.

**New source:** `rtl/m08/m08_paged_m06_lif_engine.v` and the separate Verilog-2001/Vivado module-reference top `rtl/m08/m08_paged_m06_lif_shell.v`. The existing, previously tested one-resident **256B AXI4-Lite host page bank** and the safety-disabled legacy wrapper remain unchanged; accepted D3.D.2E M32Q RTL and bit remain unchanged. The new engine uses **six logical neuron pages (6+6+6+6+6+2) sharing ONE resident physical RTL bank**, with 10 words per neuron for signed16 state/bias/threshold/reset, four signed32 external current buckets, historical spike mask and last delivered synaptic current; metadata word60–63 for magic/ID/count/tick. One separate fully host-staged edge-configuration page initializes up to 8 recurrent edges, with exactly the original five used.

The engine actually reads and writes paged state, computes 3/4 signed decay **truncate toward zero**, saturating signed16 threshold/reset LIF, recurrent signed current from previously emitted **on-fabric** spike history and configured positive-delay weighted edges. An enforced **4-tick/6-page order** stops mixed-epoch computation; updated state and actual spike masks are saved from the physical-style RTL bank before host replacement/reload. A 256B page-lease and a small global 32×4 spike-history register remain resident; 32 full neuron state records are **not** retained alongside the page.

**Independent real Icarus positive result:** `scripts/m08_paged_m06_lif_fixture.py` derives original input-only pages from the unchanged M02 dense/event + M03 sparse exact M06 oracle. `tb_m08_paged_m06_lif.sv` performs one real recurrent setup plus **24 real neuron-page dispatches**, 4 tick barriers, full AXI4-Lite 64-word load/readback, real neuron compute, full dirty readback/save, one-bank replacement. Independently verifies **128 input-current + 128 computed voltages +128 spike decisions +128 fabric-generated recurrent currents =512/512**. On commit `4ef8994e` the [genuine full M08 CI](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44844692979) passed **519 tests** with the new neural integration test. The external original **17 signed events are host-coalesced into input buckets for this NEW paged shell**—the earlier accepted D3.D.2E raw-event FIFO is NOT yet present in this image. The comparison therefore proves on-fabric LIF and recurrent math, not on-fabric 17-event ingress in this paged shell.

**Independent real Icarus negatives:** `tb_m08_paged_m06_lif_fail_closed.sv` and `tests/test_m08_paged_m06_lif_fail_closed.py` require **six** sticky fault/quarantine scenarios: missing recurrent configuration, wrong logical page, wrong tick, invalid signed16 threshold, withheld compute ACK timeout, invalid recurrent delay. Source CI [run 44845066819](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44845066819) passed **521 M08 tests** including actual negative RTL.

**NEW OFFLINE owner-PC native prep (NO board):** `scripts/m08_paged_m06_lif_source_gate.py`, `m08_paged_m06_lif_build.tcl`, `run_m08_paged_m06_lif_pc.sh`, `m08_paged_m06_lif_native_review.py`, `tests/test_m08_paged_m06_lif_native_candidate.py` implement an **independent first-new-image Vivado 2025.2 K26** project generator based on the proven independent fan/PL0/fabric-POR/JTAG AXI topology, with exact separate FPGA RTL, 15 original SHA receipt rows, routed timing, DRC and original .bit candidate in a *fresh* owner directory. The first-image reviewer **ALWAYS exits 2/BLOCKED** until original *new* owner DRC warning instances, achieved timing, source/bit hash and clocks are reviewed and a new-image-specific release gate is written; the FIRST owner-local Vivado attempt on 2026-11-20 FAILED in `lif_0_synth_1` at `m08_paged_m06_lif_engine.v:226` (`Synth 8-10871`), with following cascading Verilog syntax errors. The problem was the decimal literal `3'd5?` adjoining a ternary `?`; the existing branch now changes it to `3'd5 ?` and adds lexer/Verilog-2001 regression coverage. Preserve immutable failed run `~/Thesis_Evidence/M08/m08_paged_m06_lif_gkft3TOX`; do NOT rerun into it. The owner then supplied **15/15 OK first-original offline-native SHA receipt verification** for NEW owner folder `~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW` and bit SHA256 `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494`. The owner subsequently uploaded the **original DRC/timing/clock/metadata** reports; the exact new-image native acceptance validator `scripts/m08_paged_m06_lif_exact_native_accept.py` now SHA-pins those original reports + bit, all 15 receipt/source rows, and the seven vendor-debug-only DRC warning instances and +0.763 ns WNS/+0.010 ns WHS/100-MHz clocks. The standalone methodology/CDC check was **not required for the earlier accepted D3.D.2E JTAG run**, and the owner explicitly chose to proceed after accepting residual five unlocalized `LUTAR-1` async-reset methodology warnings. The optional methodology runner's previous `-tclargs` ordering bug was repaired without rewriting its failed original output. The SHA-pinned first-image gate now **exists**; the original is still **not programmed**. New `m08_paged_m06_lif_physical_readiness.py` read-only triage and one-shot `m08_paged_m06_lif_physical_vectors.py`, `m08_paged_m06_lif_physical_once.tcl`, `run_m08_paged_m06_lif_physical_once.sh`, `m08_paged_m06_lif_physical_audit.py`, source-only negative tests and [runbook](M08_4_PAGED_FIRST_OWNER_NATIVE_TRIAGE_AND_PHYSICAL_STAGE_2026_11_20.md) are ready. NEXT: owner pulls exact HEAD, runs local exact native gate (MUST print ACCEPTED), confirms independent active cooling/UART/stock rollback/exclusive single-owner JTAG, then executes ONE separately consented physical run. The physical runner is fail-closed and must NOT be bypassed; preserve every original failure/run folder. The KV260 has **not** been programmed with the paged candidate. Do not borrow older M32Q image hashes or DRC waivers. The owner has previously requested to verify local commands before moving to physical changes.

## Actual next task inside M08.4 (no new milestone or branch)

1. Recheck **latest exact-HEAD CI** and owner VS Code real Icarus suites including the 512 positive and six sticky-fault cases. Correct real failures without abandoning M02/M03 values or declaring weaker success.
2. Check offline-only build Tcl/shell and source/new-image review blocker; produce first **separate** genuine owner-local Vivado 2025.2 bitstream candidate **only after all new PC tests pass** and the owner agrees to that offline build. The offline builder is NOT a JTAG or DDR program and preserves older evidence.
3. Collect/report original routed DRC (including every new vendor debug/JTAG pin/equation), true slack/clock/source/bit SHA for this new image. Create a NEW exact original-image native acceptance validator as was done for D3.D.2E. Never blanket-waive old warning instances.
4. Only after accepted first new native image and cooling/UART/exclusive JTAG/stock recovery, prepare one **new** owner-run physical experiment proving 32×4 signed16 state swapped through the same 256-byte on-chip bank with independent **512** comparisons and full original SHA evidence. The JTAG test must explicitly account for input-current host coalescing in this image; do not claim 17 separate raw events were pushed unless a real new FIFO source/physical test proves it.
5. Once genuinely physically paged M08.4 is independently audited, progress to consolidated M08.5 matched on-chip vs safe memory-backed strategies. Actual DDR requires new kernel/device ownership and coherency proof; `/dev/mem` or assumed `0xA0000000` are never sufficient.

**Absolute no-sprawl rule repeated for the next instance:** these are **engineering tasks inside M08.4**, not new milestones. Do **not** invent D3.D.3B/C/D, M08.4.1, a new PR per timing warning, or a new phase for each failed first owner image. New named debugging experiments are allowed only when genuinely necessary to isolate a distinct failure mechanism; they remain subordinate to M08.4.

## Owner VS Code verification and next FRESH OFFLINE native rerun

**SOURCE-ONLY / NO VIVADO / NO BOARD.** The user passed the earlier 3-page checksum stage locally; the **NEW** neural/negative/native-source tests below are a *different* updated HEAD and must be run separately before any new owner native evidence:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v iverilog
command -v vvp
python3 scripts/m08_paged_m06_lif_fixture.py --source-only
python3 scripts/m08_paged_m06_lif_source_gate.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif.py' -v
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_fail_closed.py' -v
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_native_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

**Separate next option: ONE NEW OWNER PC OFFLINE Vivado rerun in a FRESH evidence directory (never JTAG):** Only after source tests pass and the owner wishes to create a fresh original Vivado bitstream candidate, source the owner's known installed toolchain:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_paged_m06_lif_pc.sh
```

The offline runner creates a **new**, non-overwriting `~/Thesis_Evidence/M08/m08_paged_m06_lif_XXXXXXXX` original folder, runs true Vivado once, saves full first-image DRC/clocks/timing/bitstream source SHA evidence and intentionally returns **exit code 2/BLOCKED** on success until a separate real image-specific review authorizes hardware. A genuine routed **timing failure** or new Vivado error also stops; diagnose from the *first original* error, preserving the owner folder and avoiding automatic retries. **NEVER run `program_hw_devices` or any DDR write as part of this step.** The next instance must collect/inspect actual original DRC and timing, not waive the previous M32Q warning profile.


**FINAL HANDOFF RULE, REPEATED BECAUSE THE OWNER REQUESTED IT:** `M08.4` is the active deliverable. **DO NOT ADD ANY MORE MILESTONE SUBDIVISIONS UNLESS ABSOLUTELY NECESSARY FOR DEBUGGING**, and then only document the exception as an internal experiment. Preserve simple M08.4 → M08.5 → M08.6–7 → M09 structure in `roadmap.md`.
