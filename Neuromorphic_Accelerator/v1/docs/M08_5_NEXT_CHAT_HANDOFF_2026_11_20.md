> **SUPERSEDED FOR NEXT-CHAT STARTUP (2026-11-21 America/Denver):** Start with [the CURRENT owner-accepted M08.5 next-chat handoff](M08_5_NEXT_CHAT_HANDOFF_2026_11_21.md), not this chronological document's older first-task instructions. Owner has confirmed genuine quarantined Vivado 2025.2 offline PS/PL BD exit0, 22/22 original SHA and independent read-only `OWNER_RECEIPT_CONSISTENT_SOURCE_ONLY_NATIVE_BD_NOT_DMA_RELEASE` PASS; 18/18 source-code CI on `3b56646fa3becd68256a25122776c52456e34d48`. No DDR/DMA or physical drain acceptance. This older document remains intact as historical history; its original "authoritative" claim was true when written but is no longer current.\n\n# M08.5 NEXT-CHAT HANDOFF — project context, source acceptance, Linux memory ownership, KV260 workflow
**Prepared 2026-11-20 America/Denver. This is the authoritative first file for the NEXT chat.** Earlier `M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md` contains chronological/interim advice and outdated first tasks. Use this file for the current development state and consult earlier handoffs only for history.

## 0. Current branch, PR and acceptance snapshot

- Repository **Xtimetraveler-Prime/Thesis**; working tree **Neuromorphic_Accelerator/v1/**. Different research from the separate Loihi Digital Twin v2/v3 code; borrow proven *ideas*, not signed24 neural HDL, 512KiB contexts or static DDR allocations.
- Continue source development on **agent/neuromorphic-accelerator-v1-m08-matched-experiments** in the existing **draft/unmerged PR #95**, based on **agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership** (draft #94; stacked drafts #93/#94 remain unmerged). Do not merge, rebase, change main, discard source history, or open a new PR per small fix without owner request.
- Last substantive code HEAD before this documentation-only handoff: **88e0de7cc43cfba30055908eb1df31b2410b8fb3**. User reported **all current local Python and genuine Icarus tests PASS**. GitHub Actions for that **exact code-bearing commit** subsequently completed **18/18 SUCCESS (push + PR), 0 failures**; the owner also reported the same source branch's full local tests PASS. The documentation-only handoff commit creates a *new* HEAD whose own CI must still be checked separately.
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

## 8. Subsequent same-branch source-only continuation (after this original handoff)

The branch now includes an additional **M08.5 candidate**, documented in `docs/M08_5_TRUSTED_CONTROL_AND_DRAIN_ABI_2026_11_20.md`: `rtl/m08/m08_m085_trusted_control_abi.v`, `rtl/m08/tb_m08_m085_trusted_control_abi.sv`, and `tests/test_m08_m085_trusted_control_abi.py`. This is a **non-AXI-Lite, source-only 32-bit versioned CSR decoder + original DMA fence** with complete descriptor/full-strobe checks, trusted-write input, same-cycle stop embargo, a low-then-high fresh external drain ACK, bounded drain timeout, and negative cases. The initial CI uncovered a same-cycle held-VALID decode race; the decoder now consumes each valid write only once until deassert/rearm. It is still NOT kernel owner authentication, actual PS HPM0/HP0 connection, a physical drain or M08.5 hardware acceptance. Do **not** treat the original 18/18 at `dbb0db6b` as evidence for later source commits; inspect the exact latest HEAD CI and replay below. No new hardware permission or merging is implied.

```bash
cd ~/Git/Thesis
 git status --short
 git fetch origin
 git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
 git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
 git rev-parse HEAD
 cd Neuromorphic_Accelerator/v1
 export PYTHONDONTWRITEBYTECODE=1
 command -v iverilog && command -v vvp
 python3 -m unittest discover -s tests -p 'test_m08_m085_trusted_control_abi.py' -v
 python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_lease.py' -v
 python3 -m unittest discover -s tests -p 'test_m08*.py' -v
 python3 -m unittest discover -s tests -v
```

**Next:** independently review read-only applied-DT/XSA/firmware/Linux provenance under owner authorization, secure PS HPM0 width and kernel-only AXI-Lite bridge, true late-response drain/isolation/recovery, then controlled integration into the existing recurrent candidate. No physical testing before separate consent.

## 9. Further continuation: SSH-only KV260 platform inventory prepared, NOT EXECUTED

The owner now explicitly requested collecting KV260 operating-system/driver information **through SSH only**. The assistant environment could not establish a private-network SSH connection; it **did not collect a live board observation**. The same M08.5 branch/PR #95 now includes `scripts/m08_m085_ssh_linux_probe.sh` (read-only streamed board shell), `scripts/run_m08_m085_ssh_readonly_pc.sh` (strict-key PC-side SSH capture, unique PC-only original SHA evidence directory, historically recorded target `ubuntu@10.42.0.135`), `tests/test_m08_m085_ssh_readonly.py` (source and MOCK-SSH tests), and the authoritative owner command runbook `docs/M08_5_SSH_READONLY_KV260_INVENTORY_2026_11_20.md`. It observes only bounded Linux/DT/driver/IOMMU/sensor metadata with **NO remote files, sudo, /dev/mem, DMA allocation, manager changes, MMIO, JTAG, Vivado or programming**. Do not confuse a mock SSH test or existing historical address with actual current connectivity, firmware identity, driver ownership, AXI drain, or DDR acceptance.

Next: owner reviews `git status --short`, pulls the same branch, runs `python3 -m unittest discover -s tests -p 'test_m08_m085_ssh_readonly.py' -v`, then from the PC runs `bash scripts/run_m08_m085_ssh_readonly_pc.sh ubuntu@10.42.0.135` following the new runbook. Preserve original evidence and SHA receipt, submit bounded observations for classification before any expanded live commands. Check **exact latest HEAD** CI (not previous commits); local owner source and live SSH verification remain separate. Any invalid SSH host key/board model must STOP. Real M08.5 DDR and device ownership remain **UNKNOWN/BLOCKED**.

## 10. 2026-11-21 — owner-submitted KV260 SSH stdout reviewed, actual M08.5 DDR still blocked

Original owner submitted `99_evidence_sha256.txt`, `04_ssh_exit_status.txt`, and `02_original_stdout.log` from the SSH-only capture. The latter two bytes independently SHA-match the owner ledger; exit=0, both boundary markers and section completion, model `ZynqMP KV260 revB`, kernel `6.8.0-1036-xilinx`, boot `cma=800M`, stock-named `k26-starter-kits_image_1`, system/reserved DMA heap listings, bound *PS* DMA providers and no IOMMU-group listings were observed. The complete five-file folder was **not** supplied, and full SHA receipt integrity is NOT attested. OS distro release was not collected due symlink refusal. See the exact [owner SSH evidence review](M08_5_KV260_FIRST_SSH_OBSERVATION_REVIEW_2026_11_21.md) for distinctions and unclosed gates.

Do **NOT** interpret PS DMA drivers, Linux CMA, empty IOMMU groups, stock overlay or programmed FPGA-manager state as a valid bound M08 DMA owner, unique `dma_addr_t`, live `dma-ranges` translation, secure PS HPM0/PL AXI-Lite route, physically connected HP0 master or bus drainage. This environment could not SSH to the board and conducted NO hardware operation; the owner did. Next meaningful work is source-only protected AXI-Lite/dispatch integration, physical drain isolation protocol and new reviewed K26 PS+PL Vivado/XSA/driver/DT implementation; then offline route and separately authorized one-shot hardware verification. Optional narrowly-scoped second SSH pass for OS release, relevant live DT child nodes and memory reservation metadata will not solve absent hardware/driver. No release/programming approval has been implied. Preserve draft PR #95, branch and accepted original evidence; check current head CI and report owner replay commands.

## 11. 2026-11-21 — actual AXI4-Lite CSR protocol and source-level 512-oracle neural composition

The owner independently audited the **original** five-file SSH evidence directory on their PC and reported `00_remote_source.sh: OK`, `01_context.txt: OK`, `02_original_stdout.log: OK`, `03_original_stderr.log: OK`, `04_ssh_exit_status.txt: OK`; owner-local full receipt **5/5 SHA PASS**. Original owner path: `/home/dna/Thesis_Evidence/M08/m08_m085_ssh_readonly_20261121T181457Z_Cu9fFaJN`. Assistant independently verified the two previously uploaded output files against the ledger, but **did not receive** the other three original files. No second board SSH scan is needed to achieve that receipt.

The M08.5 branch now contains `rtl/m08/m08_m085_axil_control_candidate.v` (synthesizable **five-channel** 32-bit AXI4-Lite AW/W/B+AR/R candidate with independent AW/W, held B/R, aligned/full-WSTRB CSR decoding, 4KiB no-alias register guard, immediate page/compute embargo on orphan/held/accepted write beats) and `rtl/m08/m08_m085_axil_neural_candidate.v` (direct CSR/lease-front-end composition with unchanged original 7-page AXI4 signed16 recurrent LIF and one physical source bank). Genuine real Icarus dedicated tests `tests/test_m08_m085_axil_control_candidate.py` run positive +19 fault/handshake scenarios; `tests/test_m08_m085_axil_neural_candidate.py` runs the integrated 7-slot / 24 signed16 neural dispatch / 512 independent M02/M03 check golden over **synthetic DDR**. Also new TBs `rtl/m08/tb_m08_m085_axil_control_candidate.sv`, `rtl/m08/tb_m08_m085_axil_neural_candidate.sv`, and [full source/hardware limitation document](M08_5_AXIL_CONTROL_NEURAL_SOURCE_INTEGRATION_2026_11_21.md). Initial CI exposed a mistaken **W-only orphan write test expectation**, corrected without changing source RTL; check **exact final HEAD** CI and obtain owner local verification before continuing.

**Physical status stays blocked:** actual PS HPM0 128→32 conversion and kernel exclusivity unverified; PS HP0 connection / XSA / Linux bound DMA driver/DT/IOMMU/mask/coherency absent; external `csr_trusted`, driver/route and drain are synthetic, no real outstanding transaction monitor or safe DDR-buffer release; the composite retains TESTBENCH-DIRECT page/dispatch request pins instead of reviewed kernel MMIO page/dispatch/IRQ sequence. No K26 bitstream or true physical DDR transfer created; no M08.4 acceptance or original evidence modified. Next source-only development: kernel-authorized page/dispatch/control/status command transport and fault/drain isolation, then new reviewed exact-K26 Vivado 2025.2 PS HPM0/HP0 BD and independent kernel/DT/XSA owner, later separate owner-armed physical test. Do not merge PR #95 or program KV260 without approval.

## 12. 2026-11-21 — MMIO-only 75-command full recurrent neural source top

The user reported **all owner PC local tests PASS** for the previous real 32-bit AXI-Lite + recurrent neural source increment. This continuation preserves the branch/PR #95 and accepted M08.4 physical evidence. Added `rtl/m08/m08_m085_work_command_sequencer.v` as an **opt-in** register interface to the previous `m08_m085_axil_control_candidate.v` (`ENABLE_WORK_COMMANDS=0` default), with **managed ABI v1.1 `0x00010001`** (legacy disabled v1.0 unchanged) and `0x24 WORK_SLOT`, `0x28 WORK_TICK`, `0x2c WORK_COMMAND (1 LOAD,2 DISPATCH,3 SAVE)`, `0x30 WORK_STATUS` (busy/done/fault/last op), `0x34 completed commands`. Invalid, untrusted, busy, bad strobe/slot/epoch/phase, stopped lease, timeout or mismatch quarantines work; a partial AXI-Lite AW/W request or pending response gates new work. No caller-provided DMA address enters work ABI. Full detailed contract: [MMIO managed work source increment](M08_5_MMIO_MANAGED_WORK_SEQUENCE_2026_11_21.md).

New `rtl/m08/m08_m085_axil_managed_neural_candidate.v` uses MMIO-only **actual** LOAD/COMPUTE/SAVE request wires through the unchanged original signed16 LIF neural shell, seven synthetic 256B DDR pages, and one 64-word FPGA resident bank. Its AXI4 page master's actual PS HP0 route remains **unconnected**, but the externally exposed page/compute request pins are **removed from this new candidate**. `tb_m08_m085_axil_managed_neural_candidate.sv` and `tests/test_m08_m085_axil_managed_neural.py` drive 25 source-page triplets = **75 AXI-Lite work commands**, original five M6EG edges, 24 neural dispatches, four tick barriers, 512 independent M02/M03 checks, 25 independent dirty save AXI readbacks and 19,200 *simulated* AXI bytes, followed by **fake** low→high drain ack and seal. `tb_m08_m085_work_command_sequencer.sv` and `tests/test_m08_m085_work_command_sequencer.py` add 19 adverse/source-simulated neural-status scenarios to the full real neural positive. Check exact current branch HEAD CI, not earlier intermediate commit, and collect owner local replay using the doc commands before further source/hardware expansion.

**Remaining physical gates unchanged:** actual authenticated kernel driver and device-tree binding, DMA API `dma_addr_t` mask/IOMMU/driver lifetime, PS HPM0 128→32 protected AXI-Lite, PS HP0 128-bit DDR route/XSA/boot AFI ownership, clocks/resets, real outstanding-transaction drain/isolation and buffer quarantine, new independent K26 Vivado 2025.2 resource/DRC/timing and separate explicit owner one-shot physical authorization. Never equate synthetic driver/route/drain input pins or `WORK_COMPLETIONS` with physical DMA acceptance. Do not modify original M08.4 evidence or merge draft #95. Owner's original SSH evidence was separately 5/5 SHA checked locally and its receipt history is preserved.

## 13. 2026-11-21 — QUARANTINED PS/PL native BD readiness, not native verification

Owner independently reported all local tests for the preceding ABI v1.1 MMIO-controlled 75-work-command signed16 neural increment PASS. The existing M08.5 branch and draft/unmerged PR #95 continue. This source increment **does not contact, SSH, JTAG, program, reset or write DDR on KV260**, does not modify accepted M08.4 physical/source evidence and did not run Vivado 2025.2 natively in the assistant's environment. The source proposed a **new quarantine-only** PS/PL topology, not production DMA readiness. Full method and owner copy/paste commands: [M08.5 quarantined KV260 PSPL BD source candidate](M08_5_PSPL_QUARANTINED_BD_SOURCE_2026_11_21.md).

New 56 actual annotated `X_INTERFACE_INFO` AXI signals and S_AXI/M_AXI clock associations in the unchanged `rtl/m08/m08_m085_axil_managed_neural_candidate.v`: 19 AXI4-Lite 32-bit slave, 37 AXI4 128-bit/49-bit master. `scripts/m08_m085_pspl_quarantine_bd.tcl` proposes **exact 2025.2/K26** PS `M_AXI_HPM0_FPD(128)` → SmartConnect → `accel/S_AXI(32)`, and `accel/M_AXI(128)` → SmartConnect → PS `S_AXI_HP0_FPD(128)`. It requests PL0 nominal 100MHz, source-only 256-cycle fabric POR, TTC0 EMIO → fan PWM A12, a proposed 4KiB `0xA4000000` control map and source-only HP0 `0..0x7fffffff` route. **CRITICAL:** it hardwires `csr_trusted`, `driver_bound_verified`, `control_route_verified` AND `interconnect_drain_ack` to **the same literal 1-bit zero constant**, and audits that net after Vivado `validate_bd_design`. NO trusted GRANT or DDR access can be authorized. Source snapshot includes 12 unchanged first-party neural RTL files and fabric POR, no golden output injection.

New owner PC shell `scripts/run_m08_m085_pspl_quarantine_bd_pc.sh` requires real Vivado 2025.2; uses NEW exclusive PC evidence dir and original log/journal/stdout/stderr/exit/BD receipt and SHA-256 manifest, fail closed if native receipt absent/bitstream generated, **no** synthesis/route/bitgen/XSA deployment. New pure-source guard `scripts/m08_m085_pspl_quarantine_source_check.py --source-only` plus `tests/test_m08_m085_pspl_quarantine.py` check Tcl balanced syntax via `tclsh` when present, exact 56 named AXI signals, PS width/map/clock/reset/fan, zeroed trust/ACK, forbid dangerous hardware/synth commands, and mock Vivado false-positive/incorrect-version failure retention. Initial CI found audit mutation-test blindspots (two occurrences of clock names and count-preserving renamed AXI RDATA); **source auditor was strengthened to require exact AXI4/AXI-Lite signal sets and tests now remove all duplicate witnesses**. Recheck **latest exact HEAD CI** before any PASS claim, and owner run local source-only Python and new tests.

Optional later owner native offline BD command after source tests, as documented:
```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
mkdir -p "$HOME/Thesis_Evidence/M08"
bash scripts/run_m08_m085_pspl_quarantine_bd_pc.sh
```
This action creates only an OFFLINE native BD receipt; it is not owner permission for a *non-quarantined* PS/PL route, kernel driver deployment, FPGA programming, DDR access, firmware mutation or real drain. If Vivado rejects bus inference/port widths/IP pins, preserve original evidence and correct code in a **new** source candidate, never silently tie trust high or bypass validation. No native BD run has yet occurred. Remaining blockers: kernel-bound actual device DMA API/mask and DT/XSA/AFI boot provenance, authentic protected PS MMIO and privilege enforcement, actual independent outstanding AW/W/B/AR/R drain/isolation before freeing buffer, offline resource/timing/DRC/bitstream and owner-armed new physical evidence; matched six-cell and sparse-skipping remain unverified.

## 14. 2026-11-21 — corrected first native offline Vivado preflight: redirection files

Owner's actual first 2025.2 **offline** K26 BD attempt original folder `/home/dna/Thesis_Evidence/M08/m08_m085_pspl_bd_20261121T205920Z_E7OxxtTo` exited **1 before create_project** with `Evidence directory not fresh or unexpected content: 04_stdout.txt`. The PC runner was correctly creating `04_stdout.txt` and `05_stderr.txt` as shell redirection targets **before** the Tcl guard ran, but the Tcl precreation allowlist had omitted both. The owner independently reported **7/7 original SHA256 ledger entries OK** (no original files altered). That historical failed attempt is evidence of correct fail-closed rejection, **NOT** a native PS HPM0/HP0 BD result.

Fixed `scripts/m08_m085_pspl_quarantine_bd.tcl` to allow only **four pre-Vivado regular, non-symlink files**: `00_vivado.log`, `01_vivado.jou`, `04_stdout.txt`, `05_stderr.txt`. Any stale result/manifest/`project/`/hidden file/symlink still rejects; no permission or logic changes to the exact hard-zero four trust/driver/route/drain input pins, PS HPM0/HP0 route, source RTL, or board policy. Strengthened `scripts/m08_m085_pspl_quarantine_source_check.py` to require exact Tcl+shell startup contract and `tests/test_m08_m085_pspl_quarantine.py` with **actual Tcl interpreter preflight** (stub `create_project`; no Vivado) reproducing both the previously failing valid four-file startup and malformed/stale/symlink cases. Check exact latest HEAD GitHub Actions and owner PC tests, then repeat **only** with `bash scripts/run_m08_m085_pspl_quarantine_bd_pc.sh` in **a newly-created** evidence dir; never reuse `...E7OxxtTo`. Follow [the original evidence root-cause addendum](M08_5_PSPL_QUARANTINED_BD_SOURCE_2026_11_21.md) and retain original stdout/stderr/log/exit SHA for any next Vivado IP error. This corrected startup does not mean the BD is natively validated. K26 SSH, JTAG, kernel DMA, physical DDR, Vivado synthesis/route/bit and prior accepted M08.4 remain untouched.

## 15. 2026-11-21 — owner original quarantined BD success and kernel DMA source preflight

Owner provided original terminal evidence of **successful genuine offline native Vivado 2025.2 K26 PS/PL quarantine block diagram** on `/home/dna/Thesis_Evidence/M08/m08_m085_pspl_bd_20261122T041029Z_PDYwZWvm`: `vivado_exit_status=0`, **22/22 original SHA-256 checks reported OK**, `OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY` native record, PS `M_AXI_HPM0_FPD` 128→32 control, separate PL AXI4 128→PS `S_AXI_HP0_FPD`, 100MHz nominal PL0, four trust/driver/route/drain net flags all HARDWIRED_ZERO, no synthesis/route/bitstream/Linux driver/programming. This is owner-native SOURCE TOPOLOGY validation, not authenticated DDR or physical safety. Previous first failed `m08_m085_pspl_bd_20261121T205920Z_E7OxxtTo` 7/7 receipt remains immutable. The assistant did NOT independently open the owner's original 22 files or run native Vivado itself. The source contract never programs the board.

New `scripts/m08_m085_pspl_owner_receipt_review.py` is a **read-only owner-local** independent 22-file source SHA ledger/report/builder/snapshot checker; runner CLI requires the precise original owner evidence root. It rejects drift even after rehashed reports, altered trust/drain, incorrect source snapshot, wrong native version/exit/completion, source XDC fan, bit/bin/symlink and extra/duplicate manifest items. Synthetic negative tests in `tests/test_m08_m085_pspl_owner_receipt_review.py` are not owner-native or physical evidence. Owner should now run it on the exact original path, retain the original evidence folder unchanged and provide status; a source reviewer PASS is **receipt consistency only**, not actual PS boot/DDR ownership.

New `kernel/m08_m085_dma_contract.h` **C source** matches the existing RTL 49-bit strict upper-exclusive aperture/256B alignment/7×256B boundary, generation and slot/tick checks. Genuine host `cc` compilation tests `tests/cases/m08_m085_dma_contract_host.c` execute **57 boundary cases**: 49 original RTL 49-bit/slot tests + 8 additional first-owner native PS HP0 DDR_LOW `[0,0x80000000)` checks, and the Python test recompiles a deliberately weakened strict-limit version to demonstrate a real detected failure. New `kernel/m08_m085_dma_preflight.c` contains Linux **6.8 API-shaped**, but **not compiled against real kernel headers**, not registered in any Kbuild/DT, never installed/bound on KV260, NO CSR writes/GRANT/IRQ/user MMIO, a future exact CAP+ABI v1.1 readonly probe, a candidate `dma_set_mask_and_coherent(DMA_BIT_MASK(49))`, `dma_alloc_coherent(&pdev->dev,...)`, runtime-bus-address check of BOTH the original 49-bit RTL lease and narrower native-quarantined candidate PS HP0 low 2GiB route; devres cleanup only of **never shared with PL** allocation. Driver compatible string is a new quarantine-only placeholder `thesis,m08-m085-preflight-quarantined`; no approved DT binding exists. A physical driver must replace cleanup with proven drain/quarantine and match actual live XSA/DT/IOMMU/AFI and kernel device identity. Do not deploy or treat platform-driver source as a measured Linux test.

Read [full owner evidence and kernel preflight report](M08_5_OWNER_BD_RECEIPT_KERNEL_DMA_PREFLIGHT_2026_11_21.md) for exact owner PC read-only commands, `cc` host tests, all M08 regressions and remaining hardware gates. Verify **exact latest HEAD CI success**, maintain original M08.4 evidence, and keep draft PR #95 unmerged. No SSH, JTAG, hardware manager, write of board Linux kernel or physical DDR permitted by this increment.
