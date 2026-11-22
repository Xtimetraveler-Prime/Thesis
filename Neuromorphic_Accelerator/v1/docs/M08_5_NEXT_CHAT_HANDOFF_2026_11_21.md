# M08.5 — AUTHORITATIVE NEXT-CHAT HANDOFF (2026-11-21 America/Denver; 2026-11-22 UTC evidence)

> **START HERE.** This is the sole current next-instance handoff for **Neuromorphic_Accelerator/v1**, superseding the first-task instructions in `M08_5_NEXT_CHAT_HANDOFF_2026_11_20.md` and `M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md`. Those files remain readable **historical logs**; many earlier "not yet native-validated" statements are historical, not the present gate. Read `../roadmap.md` for milestone-wide status and the direct sources referenced below before making edits. This document reflects the owner's **independent read-only 22-file receipt review PASS** supplied in chat after the source increment.

## 0. Project identity and live Git workflow

- Repository: `Xtimetraveler-Prime/Thesis`. Project root within repo: `Neuromorphic_Accelerator/v1/`. Research target: FPGA virtualized signed16 recurrent LIF with controlled comparisons of sparse event work and neuron-state residency, **not** the separate `Loihi_Digital_Twin/v3` signed24 engine.
- **Current development branch:** `agent/neuromorphic-accelerator-v1-m08-matched-experiments`. **Draft PR #95**: https://github.com/Xtimetraveler-Prime/Thesis/pull/95 (stacked against `agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership` / draft #94). PRs #93/#94/#95 remain draft/unmerged. **Do not merge, rebase accepted history, rewrite originals, create branches or open a replacement PR** without a specific owner request. Continue this branch for the next self-contained M08.5 source increment.
- **Last source-and-test commit before handoff:** `3b56646fa3becd68256a25122776c52456e34d48`, with **18/18 GitHub Actions checks successful on that exact SHA** and genuine source-and-real-RTL CI reporting **617 Python tests PASS**; included 57 real compiled-host-C DMA boundary assertions and exact original Icarus neural regression. After writing this handoff, HEAD will change via documentation-only commits: **inspect actual current branch HEAD and its exact-sha CI**, never infer that an older check applies to newer code. Do not claim local owner tests for the latest source unless the owner supplies them.
- Owner environment: Ubuntu 24.04.5 workstation; repo `~/Git/Thesis`; Python env may be `(.venv-mnist)`; tools `python3`, `iverilog`, `vvp`, `tclsh`, `cc`; owner Vivado 2025.2 at `/home/dna/Vivado/2025.2/Vivado/settings64.sh`; physical board AMD/Xilinx KV260 K26. **Assistant has no access to the owner's board or private `~/Thesis_Evidence/M08` directory.** GitHub can be read/edited using an available GitHub connector; do not treat a repo link as editable without confirming tool access.

## 1. Milestone boundaries and accepted physical baseline

Do **not** proliferate gates: M01–M03 PC COMPLETE; M04–M06 offline COMPLETE; M07 PC COMPLETE; M08.4 **PHYSICALLY ACCEPTED/CLOSED**; **M08.5 ACTIVE** for real memory + matched neural execution; combined M08.6–M08.7 PLANNED measured reproducibility/resources/uncertainty; M09 PLANNED thesis closeout.

The research question is how off-chip state virtualization (N logical neural pages with K=1 physically resident page) interacts with sparse event-driven processing under matched signed16, input/recurrent workload, tick order, and actual physical cost. Golden correctness comes **only** from independent M02/M03 numerical references, used for comparison, never injected as neural output. Fixed baseline: **32 neurons × 4 ticks**, 5 positive-delay recurrent edges, 17 original external input events, 3/4 truncate-toward-zero LIF membrane leak, spike threshold/reset, 6 logical M6NF signed16 pages of 256B each (neuron counts 6+6+6+6+6+2) and separate 7th 256B M6EG five-edge configuration page. One **64-word × 32-bit** resident FPGA state bank.

**Accepted M08.4 physical one-shot K26 JTAG/host-paged LIF:** Original native Vivado 2025.2 evidence at `~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW` (15/15 owner original SHA), exact bit SHA256 `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494`, routed 100MHz WNS +0.763ns, WHS +0.010ns; original one-shot K26 physical evidence `~/Thesis_Evidence/M08/m08_paged_m06_lif_HW_zhUx7lLJ` (13/13 original SHA, separately owner independently audited), 24 actual neural page operations over 4 ticks and **512/512 independent values** (128 host-coalesced input values plus 384 PL neural). **This was JTAG/host-staged, NOT real DDR; DO NOT rerun/reprogram this accepted image.** Earlier physically accepted 17-event FIFO source is another distinct physical baseline, not the DDR candidate. See `../roadmap.md` and original M08.4 acceptance docs.

## 2. NEWLY OWNER-VERIFIED native PS/PL source-BD evidence — scope is deliberately narrow

The owner reran the corrected **quarantined offline Vivado 2025.2 K26 block diagram** once in a **new original** directory:
```text
/home/dna/Thesis_Evidence/M08/m08_m085_pspl_bd_20261122T041029Z_PDYwZWvm
```
Owner-reported `vivado_exit_status=0`, successful `validate_bd_design -force`, **22/22 original SHA-256 records OK** (7 original log/journal/exit/builder/stdout/stderr/context, 2 native XDC/report records, 13 first-party source snapshots). Owner **subsequently independently ran the new read-only reviewer** `scripts/m08_m085_pspl_owner_receipt_review.py --original-evidence "$D"` and supplied its result:
```text
status=OWNER_RECEIPT_CONSISTENT_SOURCE_ONLY_NATIVE_BD_NOT_DMA_RELEASE
files_sha256_verified=22
snapshot_and_builder_match_current_source=true
declared_ps_hpm0_to_32_axil=true
declared_ps_hp0_128=true
four_trust_and_drain_signals_hardwired_zero=true
independent_vivado_replay_performed=false
rtl_synthesis_or_route_performed=false
board_access_performed=false
physical_dma_allowed=false
```
**Record BOTH the 22/22 SHA and the receipt reviewer as OWNER VERIFIED. Do not ask for them again unless new evidence is strictly needed.** The assistant did **not** open the original files or run Vivado; the read-only reviewer is an independent receipt/source consistency check, **not** an independent native Vivado replay.

The original K26 IPI validated PS `M_AXI_HPM0_FPD(128)` → SmartConnect → PL `S_AXI` AXI4-Lite(32), separate PL `M_AXI` AXI4(128) → SmartConnect → PS `S_AXI_HP0_FPD(128)`, nominal PS PL0 100MHz and source proposed `0xA4000000/0x1000` MMIO + HP0 low `[0,0x80000000)` route decoding. **All four inputs `csr_trusted`, `driver_bound_verified`, `control_route_verified`, `interconnect_drain_ack` are HARDWIRED ZERO** and cross-checked, so **GRANT is impossible**. Output says `OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY`; `native_synth=NOT_RUN`, `native_route=NOT_RUN`, `bitstream=NOT_CREATED`, `linux_dma_driver=NOT_PRESENT`, `board_programming=NOT_PERFORMED`.

The FIRST owner native attempt `m08_m085_pspl_bd_20261121T205920Z_E7OxxtTo` failed exit1 **before BD creation** because the Tcl guard missed shell-precreated stdout/stderr; 7/7 SHA original receipt preserved. Fixed Tcl allows exactly {log, journal, stdout, stderr} initially; new regression executes actual Tcl preflight, catches stale/symlink/extra files. **Preserve both original owner dirs untouched.**

**Do not conclude:** actual bitstream, AFI/PS runtime settings, applied DTB, real Linux platform device, true 128-bit AXI transaction to DDR, IOMMU/dma-ranges, kernel-exclusive MMIO, trusted physical ownership, hard independent drain, DDR reads/writes, latency, throughput, energy, sparse skipping, or full M08.5 acceptance. No new native Vivado run or board action is necessary to start the next **source-only** increment.

## 3. Existing RTL, Python, kernel and Vivado files to reopen

All paths below relative to `Neuromorphic_Accelerator/v1`.

**Neural+AXI source:**
- `rtl/m08/m08_m085_axil_managed_neural_candidate.v`: **56 explicit Vivado IPI AXI signal annotations**, clock/reset association, ABI **v1.1**; genuine MMIO-only LOAD/DISPATCH/SAVE control (no external request/dispatch testbench pins), unchanged real signed16 recurrent LIF shell; one resident bank and a seven-page source-synthetic 128-bit AXI4 master.
- `rtl/m08/m08_m085_axil_control_candidate.v`, `rtl/m08/m08_m085_work_command_sequencer.v`, `rtl/m08/m08_m085_trusted_control_abi.v`, `rtl/m08/m08_m085_kernel_dma_lease_fence.v` are actual original first-party CSR/lease/work FSMs. ABI v1.0 default legacy, v1.1 opt-in managed endpoint. Byte offsets: `0x00 CAP 'M085'`, `0x04 VERSION`, `0x08 STATUS`, `0x0c DRAIN`, `0x10/14 DMA_BASE_LO/HI`, `0x18 ALLOCATION_BYTES`, `0x1c GENERATION`, `0x20 GRANT=1/STOP_AND_DRAIN=2`, `0x24 WORK_SLOT`, `0x28 WORK_TICK`, `0x2c WORK_COMMAND (1 LOAD, 2 DISPATCH, 3 SAVE)`, `0x30 WORK_STATUS` (busy/done/fault + last op in **bits 7:6**), `0x34 WORK_COMPLETIONS`. Full aligned 32-bit writes; no caller-supplied DMA transfer address. On malformed/untrusted/poison/timeout/STOP, quarantine. **Simulated** low→high drain ACK is not real isolation.
- `rtl/m08/m08_m085_axi_neural_shell.v`, `m08_m085_axi_bank_bridge.v`, `m08_m085_axi128_page_engine.v`, `m08_m085_ddr_page_admission.v`, `m08_host_staged_page_bank.sv`, `m08_paged_m06_lif_engine.v` implement original neural and seven-page semantics. `tests/test_m08_m085_axil_managed_neural.py` runs real Icarus 75 commands = 25 each LOAD/DISPATCH/SAVE, 24 neural dispatches + M6EG config, 512 independent checks, 19,200 bytes of **simulated AXI**, 4 tick barriers. Do not count these as physical DDR.
- `scripts/m08_m085_pspl_quarantine_bd.tcl` + `scripts/run_m08_m085_pspl_quarantine_bd_pc.sh`, `scripts/m08_m085_pspl_quarantine_source_check.py` and `tests/test_m08_m085_pspl_quarantine.py` form the **successful owner-verified offline source-BD candidate**; do not change the hard-zero trust/drain fixture to make a driver work. A future non-quarantined variant is a new separately reviewed design and release gate.

**New Linux source preflight, NOT deployed:**
- `kernel/m08_m085_dma_contract.h`: portable original RTL descriptor guard `base + allocation_size < 2^49` (strict upper-exclusive; byte field max 32 bits), alignment 256, 7×256=1792B used, valid nonzero 32-bit generation, slots 0..6 and epochs 0..3 (slot6 tick0 only). **Separate conservative source route** `m085_dma_candidate_hp0_low_valid` requires the **entire allocation** to fit the validated candidate PS HP0-low **[0,0x80000000)** decoder. A 49-bit-valid DMA handle alone is insufficient to reach the route; neither test proves live PS/IOMMU translation.
- `kernel/m08_m085_dma_preflight.c`: **source-only UNBUILT, no Kbuild/DT/binding/installation** Linux 6.8 API-shaped platform-driver preflight, unique nondeployed `thesis,m08-m085-preflight-quarantined` compatible. It would read-only check CAP/v1.1 MMIO, candidate `dma_set_mask_and_coherent`, `dma_alloc_coherent` on *that exact device*, validate actual `dma_addr_t` against both constraints, and free ONLY an allocation **never submitted/shared to PL**. It has **no writel/GRANT/IRQ/host MMIO**. This is an implementation sketch, NOT actual kernel compile/driver/board DMA verification.
- `tests/cases/m08_m085_dma_contract_host.c` and `tests/test_m08_m085_kernel_dma_preflight_source.py`: **genuine host C compilation**, 57 assertions (49 original/8 HP0-low), including a compiled weakened-boundary mutation; Python source restrictions. `scripts/m08_m085_pspl_owner_receipt_review.py` plus `tests/test_m08_m085_pspl_owner_receipt_review.py`: exact 22-file read-only owner receipt/source comparison + nine synthetic negative scenario tests. The owner has run the real reviewer on original evidence and it PASSED.

**Essential documentation:** `../roadmap.md`, `docs/M08_5_OWNER_BD_RECEIPT_KERNEL_DMA_PREFLIGHT_2026_11_21.md`, `docs/M08_5_PSPL_QUARANTINED_BD_SOURCE_2026_11_21.md`, `docs/M08_5_MMIO_MANAGED_WORK_SEQUENCE_2026_11_21.md`, `docs/M08_5_KERNEL_DMA_OWNERSHIP_STRATEGY_2026_11_20.md`, `docs/M08_5_KV260_FIRST_SSH_OBSERVATION_REVIEW_2026_11_21.md`, `docs/M08_5_MATCHED_EXPERIMENT_CONTRACT.md`, `docs/M08_REMAINING_PHYSICAL_EXECUTION_PLAN_2026_11_20.md`.

## 4. Owner workstation and GitHub Actions development/testing/evidence workflow

**Every discrete increment**: (a) inspect exact source + docs on branch before editing; (b) implement one coherent change with negative tests and source safety checks; (c) run available real source/host-C/Icarus tests (or GitHub Actions that ACTUALLY runs them, inspect log); (d) verify **18/18 exact latest code-and-doc SHA** CI if jobs exist, distinguish pending/failure; (e) update authoritative `roadmap.md` and latest handoff, draft PR #95 body; (f) present copy/paste owner `~/Git/Thesis` VS Code commands and **stop for owner replay**. Do not promise or claim future asynchronous work. Do not say tests passed based only on created files or a mock wrapper. Never merge or overwrite original receipts on your own. Source-only GitHub Actions Icarus is **genuine simulation**, not board.

Owner PC baseline (same branch, new development may add more focused tests):
```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v python3 && command -v iverilog && command -v vvp && command -v cc
python3 -m compileall -q src scripts tests
python3 scripts/m08_m085_pspl_quarantine_source_check.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_owner_receipt_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_preflight_source.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_axil_managed_neural.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
```

Owner original native BD receipt ALREADY VERIFIED, retain for optional *read-only* future recheck:
```bash
D="$HOME/Thesis_Evidence/M08/m08_m085_pspl_bd_20261122T041029Z_PDYwZWvm"
( cd "$D" && sha256sum -c 99_evidence_sha256.txt )
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 scripts/m08_m085_pspl_owner_receipt_review.py --original-evidence "$D"
```
**Do not request another routine repetition of this accepted check; it was already completed.** If a *new* offline native Vivado build is expressly needed to verify different RTL, create a NEW unique `~/Thesis_Evidence/M08/m08_m085_*` directory, capture actual original log/exit/project/source/report/bit if applicable, run SHA + independent read-only audit; do not invent physical acceptance. All future Vivado scripts must be scoped to offline sources unless owner authorizes a distinct stage.

## 5. Hardware, driver and scientific acceptance boundaries

- Actual KV260 stock Linux owner inventory previously observed kernel `6.8.0-1036-xilinx`, stock-named `k26-starter-kits_image_1` overlay, `cma=800M`, no bound M08 PL platform driver. Existing owner read-only SSH receipt `~/Thesis_Evidence/M08/m08_m085_ssh_readonly_20261121T181457Z_Cu9fFaJN` was owner SHA 5/5; it does NOT prove selected device `struct device`, applied DTB, `dma-ranges`, SMMU, AFI, PS address protections or live HP0 DMA. **Never run SSH/modify live Linux/PL automatically:** separate explicit owner approval for each physical stage, and distinguish read-only audits from writes.
- Future actual DMA requires **exact enabled/bound custom platform device**, verified trusted PS HPM0 kernel-only MMIO, real DT/XSA/firmware/boot applied PS width + translation/isolation, independently verified DMA API `dma_addr_t` + mask + actual PS HP0 memory segment, CPU/device ordering and 7×256B layout. The 49-bit RTL bound is wider than the candidate 2GiB HP0 decoder.
- **Most critical safety gate:** genuinely independent physical PS/PL AXI outstanding drain/isolation across AW, W, B, AR and R. A PL-local idle/busy counter is not sufficient if SmartConnect/PS still holds an accepted request or response; a fabric reset, fake `interconnect_drain_ack`, the lease SEALED bit and Linux cleanup are **not** proof that no late B/R can touch DDR. Once a buffer was ever granted or seen by PL, **never call `dma_free_coherent` without an independently proved no-late-transaction recovery**; keep/quarantine the allocation even through driver remove, timeout or owner disconnect; plan reset/rollback/exclusive owner lifecycle.
- Only after these physical and firmware gates: separate non-quarantined K26 source, native exact 2025.2 synthesis/place/route/timing/DRC + original SHA/bit, stock image/rollback/UART/fan/board preflight, explicit owner permission for one physical program and bounded tests; no live DDR writes absent verified ownership, no automatic retries. **Do NOT turn current hard-zero trust/drain input pins high** as a shortcut.

## 6. The next ordered source-only development increment (start immediately, no repeated confirmation)

Continue M08.5 on the existing branch; no additional milestone sublabel or new PR. The next instance should:

1. **Audit exact current source first** (`kernel/m08_m085_dma_preflight.c`, `kernel/m08_m085_dma_contract.h`, `rtl/m08/m08_m085_trusted_control_abi.v`, `rtl/m08/m08_m085_axi128_page_engine.v`, `rtl/m08/m08_m085_axi_neural_shell.v`, `scripts/m08_m085_pspl_quarantine_bd.tcl`, and relevant tests/docs). Confirm last code SHA and latest CI, owner-reported original BD receipt PASS; do not ask the owner to revalidate that receipt or rerun accepted M08.4.
2. **Implement a PC/source-only physical-drain design contract and verification model**: distinguish source engine quiescence from end-to-end SmartConnect/PS completion, track independently observable accepted AW/W/B and AR/R outstanding obligations (including backpressure, W-before-AW where permitted, delayed B/R, cancellation/STOP, timeouts, reset with outstanding state and false/stale ACK). Explicitly identify which drain assumptions cannot be proven from the PL endpoint alone and require physical hardware/PS owner isolation or downstream monitor. Keep the existing grant-disabled quarantine. Add adversarial genuine Icarus and/or host C/Python tests; never replace real RTL computation with a mocked neural engine for integration claims.
3. **Strengthen nondeployed Linux 6.8 preflight/lifecycle source** only as justified by the reviewed contract: choose immutable first-party device-tree binding proposal + read-only `reg`/address map + DMA mask/range/IOMMU review checklist; do **not** compile/install on the owner's kernel, create an enabled DT node, use `/dev/mem`, expose UIO, or permit GRANT. If an actual Linux 6.8 kernel-header build or new read-only board inventory becomes necessary, first document exact source/evidence script and obtain owner stage approval.
4. Run genuine tests and exact-HEAD CI; update the single roadmap/handoff/PR; provide full local owner commands. **Pause for owner verification at end of increment.** No new Vivado hardware build, bitstream, JTAG, live driver, board writes or physical DDR operations are authorized in this handoff.

**Remember the scientific deliverable:** source RTL correctness and a validated PS/PL BD are prerequisites only. M08.5 still needs genuinely memory-backed, independently owner-accepted **matched physical** neural/sparse-residency runs with measured transfer/stall/throughput and consistent event accounting. Keep unavailable cells visibly blocked rather than fabricating speed/energy. M08.6–7 then covers repeated measurements/resources/uncertainty, and M09 thesis analysis.

## 7. End-of-increment reporting

Give the owner: exact branch/HEAD/PR draft state; files and architecture changed; genuine tests and count, exact CI state (not cached earlier SHA); what was simulated/source-audited vs **owner-native** vs physically tested; any warnings and open ownership/drain/DTIOMMU blockers; **copy/paste-ready full VS Code `git fetch/switch/pull` + targeted/full Python/Icarus/host C commands**; what the owner should verify next; explicit statement no board work/merge performed. Preserve all original evidence.
