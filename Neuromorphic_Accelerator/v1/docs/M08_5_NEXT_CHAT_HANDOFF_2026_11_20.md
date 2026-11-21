
# M08.5 NEXT-CHAT HANDOFF — project context, source acceptance, Linux memory ownership, KV260 workflow
**Prepared 2026-11-20 America/Denver. This is the authoritative first file for the NEXT chat.** Earlier `M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md` contains chronological/interim advice and outdated first tasks. Use this file for the current development state and consult earlier handoffs only for history.

## 0. Current branch, PR and acceptance snapshot

- Repository **Xtimetraveler-Prime/Thesis**; working tree **Neuromorphic_Accelerator/v1/**. Different research from the separate Loihi Digital Twin v2/v3 code; borrow proven *ideas*, not signed24 neural HDL, 512KiB contexts or static DDR allocations.
- Continue source development on **agent/neuromorphic-accelerator-v1-m08-matched-experiments** in the existing **draft/unmerged PR #95**, based on **agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership** (draft #94; stacked drafts #93/#94 remain unmerged). Do not merge, rebase, change main, discard source history, or open a new PR per small fix without owner request.
- Last substantive code HEAD before this documentation-only handoff: **88e0de7cc43cfba30055908eb1df31b2410b8fb3**. User reported **all current local Python and genuine Icarus tests PASS**. A GitHub Actions check of that commit during handoff authoring showed **13/18 PASS, 5 in progress, 0 failures**; this is a point-in-time check, **not** a promise of eventual 18/18. Verify GitHub Actions on the NEW exact HEAD after this handoff commit as well.
- **M08.4 physically ACCEPTED/CLOSED; M08.5 ACTIVE; M08.6–7 combined PLANNED; M09 PLANNED**. No new physical test or PS DDR evidence was created in the M08.5 source-only series.
- Next work: **source/read-only Linux DMA / PS HPM/HP0 control-owner evidence**, trustworthy control-register and genuine bus-quiescence protocol, then offline resource/timing assessment. Do **not** start by rebuilding the already-tested comparator, AXI page master, seven-slot LIF shell or source-only DMA lease fence.

## 1. Read these actual repository files first (from the selected branch)

1. `roadmap.md` (authoritative status) and **this handoff**.
2. `docs/M08_5_PROGRESS_FORWARD_PATH_2026_11_20.md` (research state and forward path).
3. **`docs/M08_5_KERNEL_DMA_OWNERSHIP_STRATEGY_2026_11_20.md`** (selected concrete Linux driver/memory strategy; required reading).
4. `docs/M08_5_BANK_AXI_INTEGRATION_CONTRACT.md` and `docs/M08_5_MATCHED_EXPERIMENT_CONTRACT.md` (one-resident-bank, 256B AXI roundtrips, six experimental cells, unmatched controls).
5. `docs/M08_4_FIRST_OWNER_PAGED_NEURAL_PHYSICAL_2026_11_20.md` (accepted immutable owner experiment), `docs/M08_KV260_SUCCESSFUL_BITSTREAM_METHODS_2026_11_20.md` (actual four-stage physical verification workflow).
6. `docs/M08_3_DMA_READINESS_RUNBOOK.md`, `docs/M08_D3B_BOOT_PLATFORM_EVIDENCE_MATRIX_2026_11_12.md`, `docs/M08_5_DIGITAL_TWIN_PSPL_REUSE_AND_PAGE_GATE.md` (read-only PS Linux inventory, boot/AFI status, Loihi v3 PS route comparison).
7. Reopen exact RTL/test files listed in `3 below before editing. Source filenames or previous summaries are not a substitute for reading current bytes.

**Historical-conflict rule:** the older chronological handoff still says to start a matched comparator and an unconnected AXI page prototype. Both are already implemented and tested. The original accepted M08.4 method applies to historical JTAG-only hardware, **not** an already existing physical M08.5 DDR image.

## 2. Evidence levels (DO NOT COLLAPSE)

### A. Original M08.4 K26/JTAG hardware — physically accepted and immutable

- Owner's first physical Vivado 2025.2 run, 2026-11-20: **32 signed16 LIF neurons ×4 synchronous timesteps, 5 delayed recurrent synapses, 17 HOST-COALESCED external events**; **six distinct 256-byte M6NF neural pages and one M6EG edge config page**, with **ONE actual 256-byte FPGA resident bank**.
- **24 compute-bearing actual JTAG host-staged page dispatches**, six pages per tick with four barriers; each is loaded/64-word read back, computed, dirty-read, saved. Original independent M02/M03 numerical parity: **512/512** = **128 HOST input-current checks +384 actual PL neural outputs** (128 membrane, 128 spike, 128 recurrent current). Not 512 on-fabric calculations.
- Accepted original source/bitstream SHA256: **6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494**.
- Immutable owner-only native receipts: **~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW**, original 15/15 SHA; immutable physical receipts: **~/Thesis_Evidence/M08/m08_paged_m06_lif_HW_zhUx7lLJ**, original 13/13 SHA, one actual program, 24 page markers. Owner ran corrected independent auditor READ-ONLY and accepted result. **Do not rebuild, reprogram, delete, modify, overwrite, rehash original files, or mistake mocks for owner evidence.**
- Separate earlier D3.D.2E accepted FPGA used 17 **RAW on-fabric FIFO events** with 128 PL input-current +384 PL neural checks, but **all neurons still advanced each tick**; this is not the same ingress as the paged M08.4 design and proves no physical sparse-update skipping.
- JTAG host page staging **IS NOT PS DDR / Linux DMA**. No accepted performance speedup/power/energy claim, autonomous asynchrony or matched on-chip versus DDR hardware pair.

### B. M08.5 real source RTL and CPU-only simulation — user-local PASS, not physically deployed

- Research comparison: **timestep/event × onchip/JTAG-host-paged/PS-PL-DDR six-cell contract**, independent original signed16 M02/M03/M06 witness and fail-closed mismatched ingress/resources/time-boundaries. DDR cells are **BLOCKED** until physical allocation and master path are genuinely verified.
- AXI4: new first-party exact **256B =16×128-bit beats** PL AXI4 master, 49-bit candidate address, AW/W/B or AR/R, stalls/timeout, correct beat/ID/response/LAST ordering, poison on mismatch; default static permitted address window **[0,0)**.
- Original unchanged **64×32-bit neuron bank** plus AXI bridge: **64 full host writes AND 64 actual bank-word reads with comparison before LOAD COMMIT**; dirty SAVE requires **64 actual bank reads → 16-beat AXI write + successful B → a second full 256B AXI readback and comparison**, before clearing dirty state. One resident bank, never seven simultaneously resident.
- Optional **seventh** 256B backing slot 6 is separate **M6EG** recurrent edge configuration (M6EG magic, five edges, tick 0, semantic bank ID **0xFFFFFFFF**). Slots 0..5 remain M6NF six neural pages (6/6/6/6/6/2 neurons), tick 0..3. The source shell instantiates the **UNCHANGED actual recurrent LIF engine**, and real Icarus simulates all 24 original neural dispatches and **512 comparison-only oracle values**. Existing standalone tests also cover 18 admission, 25 AXI, 19 bank-integrated, and 11 neural/edge adverse cases.
- Memory owner **strategy**: future exact-device Linux platform driver uses `dma_alloc_coherent()` and the **device-visible** `dma_addr_t`, not an invented CPU physical address. At least 1,792B allocated (prefer platform-reviewed page-sized), but accelerator may access **only seven 256B slots [base, base+1792)**. Must independently validate DMA/coherent mask, PS 49-bit aperture, IOMMU/`dma-ranges`, kernel bind, firmware XMPU and buffer lifetime.
- Source RTL **`m08_m085_kernel_dma_lease_fence.v`** locks a 256B-aligned DMA handle, size and generation with 65-bit overflow/49-bit address check, live control and lease revalidation, pre-grant/post-release embargo, sticky poison on tamper/revoke, and independently asserted quiescence requirement for safe release. `USE_RUNTIME_WINDOW` is **opt-in** throughout admission/bridge/shell; static mode and empty default window remain unchanged. Composed `m08_m085_kernel_owned_neural_candidate.v` derives address only from latched lease base+slot×256, and gates **both page I/O and neural dispatch**. Icarus covers original 512 comparisons and **32 negative lease/neural cases** including 49-bit edge, owner change, stale generation, dirty/busy release, nonquiescent release and unleased dispatch.
- These are **real clocked RTL tests over synthetic seven-page DDR registers and FAKE “kernel lease valid” signals**; **NO** bound kernel driver, allocated `dma_addr_t`, real XSA/HP0 route, trusted control path, bus drain, routed timing, synthesized resource, real DDR bytes, measured latency or new FPGA image. Source-test transfer counts (e.g. 19,200 simulated bus bytes) are NOT physical bandwidth.

## 3. Source/test map for efficient next-chat work

| Area | Source files (all relative to `Neuromorphic_Accelerator/v1`) | Tests |
| --- | --- | --- |
| Numerical original M02/M03 and seven INPUT pages | `scripts/m08_paged_m06_lif_fixture.py`, unchanged M02/M03 source | `tests/test_m08_paged_m06_lif.py` and next lines |
| Accepted resident neural engine/bank | `rtl/m08/m08_paged_m06_lif_engine.v`, `rtl/m08/m08_host_staged_page_bank.sv` | `tests/test_m08_paged_m06_lif.py`, `tests/test_m08_paged_m06_lif_fail_closed.py`, `tests/test_m08_paged_m06_lif_physical_reaudit.py` |
| Page guard/master | `rtl/m08/m08_m085_ddr_page_admission.v`, `m08_m085_axi128_page_engine.v`, `m08_m085_axi128_page_candidate.v` | `tests/test_m08_m085_pspl_reuse.py` |
| 64-word verified load/save integration | `rtl/m08/m08_m085_axi_bank_bridge.v` | `tests/test_m08_m085_bank_axi_bridge.py` |
| Real recurring LIF over seven simulated DDR pages | `rtl/m08/m08_m085_axi_neural_shell.v` | `tests/test_m08_m085_axi_neural_closed_loop.py` |
| Runtime coherent DMA-owner lease source candidate | `rtl/m08/m08_m085_kernel_dma_lease_fence.v`, `m08_m085_kernel_owned_neural_candidate.v` | **`tests/test_m08_m085_kernel_dma_lease.py`** + `rtl/m08/tb_m08_m085_kernel_dma_neural.sv` |
| Matched six-cell/source lineage | `src/neuromorphic_accelerator_v1/m08_matched_experiments.py`, `scripts/m08_matched_contract.py`, `scripts/m08_m085_twin_pspl_audit.py` | `tests/test_m08_matched_experiments.py`, `tests/test_m08_m085_pspl_reuse.py` |

**Golden/oracle rule:** original **M02/M03-derived expected 512 values are comparison-only**; never write expected LIF output state into neural input page memory or replace actual LIF RTL with synthetic numerical values. Note which test uses synthetic compute only (the older bank+AXI test) vs original LIF (seven-slot and DMA lease tests).

## 4. Working / CI / local verification contract

1. Start by discovering connected GitHub repository/PR tools. Inspect **exact** current branch and PR #95 HEAD, source byte content and latest-HEAD CI. Do not infer a local assistant clone; GitHub connector source operations need correct branch + blob SHA and must be committed. No merges, no extra draft PRs per experiment.
2. Do a **coherent increment**: source-level design grounded in actual hardware/OS facts → real first-party Icarus + edge/fault tests → full M08/full Python regression → concise authoritative documentation/roadmap/handoff → exact-HEAD GitHub CI and local owner commands. No mock pass substituted for real Icarus; skip because simulator missing is not evidence.
3. Every response after development must contain: branch/commit, files changed, tests that **actually ran**, CI pass/failure/pending with URLs when available, factual limitations, and **copy/paste Linux VS Code commands** so owner can independently verify. If CI fails, inspect the exact raw job log; repair, don't wave it away.
4. Keep M08.4 and other accepted evidence immutable. Preserve failed historical route/DRC attempts too. Do not claim vendor board work from source tests, derived resource guesses, or source-only Windows/CI.
5. Research must respect six-cell comparison controls: identical precision/network/N/K/ingress and start/stop timing domain, actual event skipping vs dense update, physically measured page movement, stalls and honest UNAVAILABLE conditions. M08.6–7 later does repeated physical timing, uncertainty, resource and power qualification.

### Owner VS Code PC source-only commands (NO Vivado / NO board)

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
git branch --show-current

cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v python3
command -v iverilog
command -v vvp
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_lease.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axi_neural_closed_loop.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_bank_axi_bridge.py' -v
python3 scripts/m08_m085_twin_pspl_audit.py --source-only
python3 scripts/m08_matched_contract.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_reuse.py' -v
python3 -m unittest discover -s tests -p 'test_m08_matched_experiments.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
~~~

If `git status` is dirty, preserve/review local edits before switch/pull. `command -v iverilog` and `command -v vvp` must succeed for genuine RTL pass. User reported these source tests PASS in the preceding conversation.

## 5. KV260 hardware workflow: NEVER conflate levels or skip authorization

**No newly approved K26/Vivado/JTAG/PS-DDR physical experiment exists for M08.5.** The user's request to prepare a handoff is NOT authorization to touch a board, load a bitstream, read/write unknown PS MMIO or run kernel DMA. Distinguish:

**Level A (NOW, PC only):** read sources, review signed16 model and DMA-fence correctness, parse available PS HPM0/HP0 source and device-tree/driver/boot provenance, draft a **versioned trusted AXI-Lite lease/control ABI and independent bus-drain/fault isolation contract**. Source-only tests should fail closed on fake owner attestation, postrelease compute, stale generation, partial write/response and aliased page slots. Static/structural checks do **not** authenticate a real kernel driver or quiescent interconnect.

**Level B (only after owner explicitly authorizes read-only observation on a normally booted KV260 Linux shell):** the existing `scripts/m08_3_dma_readonly.py` gathers bounded allowlisted reads of `/proc` and `/sys`; its output always says **physical_dma_ready=false** and is NOT a kernel DMA ownership receipt. It writes only a **NEW** local immutable observation folder, never an existing artifact. Tested procedure from `docs/M08_3_DMA_READINESS_RUNBOOK.md`:

~~~bash
# Run ONLY on the owner-reviewed, normally booted KV260 Linux shell,
# after owner approves read-only inventory. NOT on development PC.
cd ~/Thesis/Neuromorphic_Accelerator/v1
mkdir -p "$HOME/Thesis_Evidence/M08"
D="$HOME/Thesis_Evidence/M08/m08_3_1_dma_observation_$(date -u +%Y%m%dT%H%M%SZ)_$$_$RANDOM"
python3 scripts/m08_3_dma_readonly.py --output-dir "$D"
python3 scripts/m08_3_dma_readonly.py --audit-only --output-dir "$D"
ls -lah "$D"
( cd "$D" && sha256sum -c m08_3_dma_readiness.sha256 )
~~~

No sudo, `/dev/mem`, `xmutil`, FPGA manager write, JTAG action, driver allocation, PS MMIO or DDR write is part of that read-only observation. Presence of a DMA-heap directory or platform device name never proves an owner. Any proposed expanded read-only command must be reviewed before execution.

**Level C (future, only after owner reviews new hardware/OS constraints):** separate **new** K26 offline Vivado 2025.2 source-pinned synthesis/route/bitgen in a fresh evidence folder, original SHA ledger, post-route device/clock/timing/WNS/WHS/resource and **every DRC warning** review. Consult `docs/M08_KV260_SUCCESSFUL_BITSTREAM_METHODS_2026_11_20.md`. The owner's historically used setup: Ubuntu 24.04.5, `source /home/dna/Vivado/2025.2/Vivado/settings64.sh`, exact K26 part `xck26-sfvc784-2LV-c`, nominal PS PL0 100MHz and fabric POR. The known JTAG-only block design had PS HPM masters **DISABLED**, a debug BRAM segment and neural AXI-Lite segment. Its accepted JTAG addresses and bitstream are **NOT** a DDR master or physical bus buffer. v3 HPM0 width mismatch is an explicit boot/AFI risk: independently verify PS HPM0 128/32-bit SmartConnect/AXI-Lite, HP0 128-bit PL master, clocks/resets, Linux DT and SMMU, XMPU protection, DMA mask and real **outstanding AXI drain/late-response** mechanism. Source-only “bus_quiescent” is fake until that physical path is proven.

**Level D (future, separately owner-armed physical run):** require new source/bit/hash/driver/DT-bound owner receipt, new image-specific read-only native reviewer, verified independent cooling (TTC fan pin A12 alone is NOT proof), UART console and stock rollback, unique K26 target/AXI port, exclusive Vivado Hardware Manager/JTAG, and explicit consent with two **new experiment-specific arming flags**. Use an approved one-shot runner that rechecks native identity then programs exactly once, no auto retries, no QSPI/SD, and creates a **NEW** immutable physical evidence folder with executed Tcl, logs/journal, exit, source/bit SHA, oracle, independent results. Historical JTAG server target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, `xck26_0`, `hw_axi_1` must always be revalidated; hardware identity may have changed. Do NOT reuse `run_m08_paged_m06_lif_physical_once.sh` to “run DDR tests” or reprogram accepted M08.4.

For any genuine future Linux DDR run, new exact-platform bound driver should perform `dma_set_mask_and_coherent()` only after live XSA/DT verification; `dma_alloc_coherent()` returns **device DMA handle** and CPU pointer. Buffer's 1,792B aperture, cache/coherence/CPU-visible ordering, lease generation and lifetime, protected register access, IRQ/poll, physical PS AXI drain after fault, safe reset/quarantine and `dma_free_coherent()` must be evidenced independently. A poisoned source master that reports `busy=0` does NOT prove it is safe to free or reuse its buffer.

## 6. Specific ordered next development tasks — still ONE M08.5 gate

1. **Read-only source and ownership/boot audit**: inspect concrete PS HP0/HPM0/AFI version/width evidence, existing M08.3 restricted Linux inventory, bound driver/DT/XSA clues and exact first-party source boundary. Keep all unavailable live evidence explicitly `UNKNOWN/BLOCKED`.
2. **Versioned trusted control / drain ABI**: design source-only control/status contract (cap/magic/version, DMA base + length + generation, owner identity and grant/revoke, M6EG config-first semantics, page/tick dispatch, completion/dirty-save, sticky poison, real AXI outstanding-transaction drain/reset acknowledgment). The present RTL fence does NOT authenticate a driver; add targeted real-RTL fault tests for owner forgery/control-loss/release races without pretending to operate PS.
3. **Resource/clock envelope**: quantify extra 2048-bit staging registers and M08 one-bank live state from source; only after review run new native Vivado 2025.2 offline implementation; preserve comparison-only numerical oracle. Do not inherit M08.4 WNS or resource totals for new architecture.
4. **Independent real-owner feasibility then measured comparisons**: after bound device/IOMMU/DMA mask/OS provenance and safely routed HP0 control, determine `AVAILABLE_VERIFIED` / `NOT_AVAILABLE` / `UNKNOWN`. Only then design and ask authorization for actual memory experiment. Keep the six-cell timestep/event × onchip/JTAG/DDR match; do not claim sparse neuron skipping or speedups from host-coalescing.

## 7. New-chat reporting template

At each development increment report exact branch/HEAD/draft PR status; what files changed; what **actually** passed (Python vs Icarus vs offline Vivado vs physical, all separately), CI on exact commit, any tests pending/failing, copy/paste owner terminal commands, source/evidence limitations, next safe step and whether owner physical permission is required. Preserve all original evidence and failed attempts. No background/asynchronous promises.

**STOP STATE:** Owner verified current M08.5 source increment locally. Hand off on this same branch; continue source/read-only ownership ABI development. This document creates no hardware authorization.
