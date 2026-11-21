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

## Required next coding inside *M08.4* (no new milestone)

**Implement real signed16 LIF neural updates through the paged AXI/compute bank.** Use the accepted M32Q `rtl/m08/m08_d3d2e_tick_queue_lif_axil.v` as numerical/RTL reference, especially signed 3/4 truncation toward zero, signed34 input+recurrent accumulation, clamp to signed16, fired threshold and reset, real state/trace update; do **not** modify this physically accepted module or its exact owner source/bitstream.

One viable progression **inside M08.4**:
1. Choose a **true compute-facing 256B page ABI**, separate from M06 *expected* voltage/spike/current references. Fit signed16 parameters, persistent membrane voltage, per-tick external current, current tick, per-neuron spike history/state and recurrent-delivery model with explicit valid-count/logical ID. If the 15-neuron configuration page lacks space for dynamic state, **reduce neurons per resident page transparently**, proving N>K with more loads/replacements. Do not call a checksum a neuron.
2. Implement a **synthesizable page LIF compute-port engine** using already tested bank req/ack, full read/compute/write sequencing and fault watchdog; tick barriers/host page ownership enforce safe transitions. First test sign/threshold/decay/reset (including negatives) against **independently computed M02** values. Replays across eviction should reproduce same results, with complete readback/save before every replacement. Test fault/timeout and wrong-context isolation.
3. Extend to original full **32×4, 17 events, five positive-delay recurrent edges** with recurrent *fabric*-generated syn delivery. **Host furnishing precomputed reference recurrent currents is NOT a valid full 512/512 proof.** A staged intermediate current input model is okay if explicitly labeled partial scope.
4. Demand **real Icarus/vvp** functional tests, negative tests/mutations and full M08 regression on exact HEAD, plus owner VS Code commands. Once source and numerical comparisons are correct, propose **a NEW offline** Vivado 2025.2 K26 wrapper/build on this same M08.4 branch with fresh immutable source/timing/DRC report evidence. Never reuse old bit SHA or auto-program hardware. A new one-shot physical experiment requires original exact new-image/native acceptance, separately powered active cooling, UART capture, exclusive JTAG, stock recovery and owner preflight, followed by independent six-file physical SHA audit.

**Do not leap to M09 or a performance speedup claim.** The critical unproven feature is real neural computation using paged state beyond resident capacity.

## Local owner VS Code test commands (without changing board/evidence)

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
python3 -m unittest discover -s tests -p 'test_m08_page_compute_probe_shell.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m06_parameter_pages.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d3a_page_stage.py' -v
python3 scripts/m08_m06_parameter_pages.py --source-only
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

**FINAL HANDOFF RULE, REPEATED BECAUSE THE OWNER REQUESTED IT:** `M08.4` is the active deliverable. **DO NOT ADD ANY MORE MILESTONE SUBDIVISIONS UNLESS ABSOLUTELY NECESSARY FOR DEBUGGING**, and then only document the exception as an internal experiment. Preserve simple M08.4 → M08.5 → M08.6–7 → M09 structure in `roadmap.md`.
