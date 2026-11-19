# M08 D3.2 — protected PS–PL AXI status and forward research work (2026-11-18)


## 2026-11-19 KV260 SSH public key added; stock read-only capture still incomplete

Owner reported adding a public SSH key to the KV260 `ubuntu` account. Noninteractive PC SSH `BatchMode=yes` and `StrictHostKeyChecking=yes` now returned `M08_SSH_AUTHENTICATION_OK`. The first owner stage-0 capture `m08_d3_2_stock_READONLY_rp2nq3it` failed SSH authentication (exit 255, permission denied). Owner reran the unmodified read-only baseline after key setup, producing `m08_d3_2_stock_READONLY_oyz3sts9`, which still reports `STOCK_BOARD_READONLY_CAPTURE_INCOMPLETE_STOP` but its individual error/probe evidence has **not yet been provided**. Do not conflate basic SSH auth success with probe acceptance; inspect existing second capture's `06_readonly_review.json`, exit, stdout and stderr before rerunning. No new image loaded; hardware release blocked. No public/private key bytes or fingerprint captured.


## 2026-11-19 new offline passive image accepted and physical stage-0 stock review

Owner's uploaded real native .bit receipt from `m08_d3_2_passive_synth_gKr8mQe6`: three evidence SHA ledgers accepted; image 7,797,839 bytes with exact SHA256 `07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547`. Independent auditor status `M08_D3_2_UNRELEASED_PASSIVE_BITSTREAM_SHA_ACCEPTED_NO_BOARD`, fan A12, HPM0/HPM1/LPD disabled, no .bit.bin/DTBO, no board activity or cooling/stock recovery approval. In response to owner request to resume physical experiments, prepared [new stage-0 nonprogramming stock-only read-only capture](M08_D3_2_PHYSICAL_STAGE0_STOCK_READONLY_2026_11_19.md). Owner must personally confirm independently powered backup cooling, UART monitoring, known stock boot/forced-power-cycle recovery and a nonstalled board before any SSH snapshot. New PC gate verifies pinned new image and 99/98/96 receipts first, collects stock manager/fan/overlay/temperature plus original stock image hashes with no board writes. Original prior RCU/timer stall and unknown root cause still make bitstream loading a separate blocked decision; old image remains quarantined, no ATB4/AIB13/AFI claim. Stage-0 hardware observation is PENDING owner local run.


## 2026-11-19 owner semantic route review accepted; offline-only bitgen candidate development

Owner independently verified both 99 synth and 98 route ledgers and ran scripts/m08_d3_2_passive_route_report_review.py against original /home/dna/Thesis_Evidence/M08/m08_d3_2_passive_synth_77Ols9zt: PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED, default DRC 0, one PS8+OBUF, no CLB logic, WNS/TNS NA, 68 unrelated board catalog and one no-critical-terminals warning. Owner has a backup fan and explicitly requested proceeding with bitstream **generation**; accepted permission **offline PC only**, not deployment. New [unreleased .bit owner-PC runbook](M08_D3_2_PASSIVE_UNRELEASED_BITSTREAM_PC_RUNBOOK_2026_11_19.md) creates a new route and one specifically marked UNRELEASED .bit plus 96 SHA receipt after all 99/98 source and native safety checks. No owner-native new bitstream has yet been generated; no bitstream deployment/FPGA manager/programming authorized, PS/boot/stock rollback and physical cooling remain unknown, original failed bit.bin quarantined. Separate physical approval remains required even with backup fan.


## 2026-11-19 owner routed passive checkpoint and follow-up

The owner uploaded the native routed report and SHA receipt checks for `m08_d3_2_passive_synth_77Ols9zt`: Vivado 2025.2 `route_design Complete!` 100%, default ruledeck DRC `Checks found: 0`, output A12, no exposed AXI, one PS8/OBUF/IOB and **zero LUTs/registers**. `WNS/TNS=NA`; the generic `All user specified timing constraints are met` phrase provides **no affirmative timing slack** with no clocked fabric paths. `clk_pl_0`/`clk_pl_1` nominal clock definitions do not establish enabled hardware clocks under Linux. New independent [route semantic receipt reviewer](M08_D3_2_PASSIVE_ROUTE_SEMANTIC_REVIEW_2026_11_19.md) verifies 98/99 ledgers, zero reported DRC findings, N/A-timing scope and resource/clock profile with fail-closed negatives; **owner execution of this new tool still pending**. Remain PC-only; independent fan cooling/stock rollback and PS boot protection are not proven and **new bitstream generation and hardware access remain forbidden**.


## Owner original passive synthesis acceptance and offline route work (2026-11-18)

Owner uploaded passive synth gate JSON and native report from original `m08_d3_2_passive_synth_z6PIsrwZ`, reporting `synth_design Complete!` at 100%, HPM masters disabled, no identity/page/SmartConnect, fan A12 and no bitstream. Warning scan included unrelated installed board definitions, unconstrained/unconnected PS clock/reset outputs and unused TTC slice input bits. This supports **advancing to offline passive implementation** but is NOT evidence of acceptable route/DRC/timing or physical cooling.

Added [M08 D3.2 fresh passive route-only PC runbook](M08_D3_2_PASSIVE_ROUTE_PC_RUNBOOK_2026_11_18.md) and fail-closed Tcl/runner/audit/negative tests. New owner route must be performed against a **freshly generated synthesis project** and produce a separate 98 SHA ledger; original successful `z6PIsrwZ` folder remains immutable. Even completed route report is **NOT** a bitstream/hardware authorization; protected HPM0 candidate additionally needs authentic PS boot ATB4/AIB13 clock/AFI and Linux driver proof.


## 2026-11-18 owner Icarus acceptance and next physical-design step

Owner's independently run full abstract AXI scoreboard printed all 11 expected markers and completed with $finish; owner also independently ran the new receipt reviewer against the 53-candidate PC inventory, obtaining SHA identity 5733da65c625ee25e98b7b3907e721a06b228b94a8301f2d866c5a17087de1ba, no original boot configuration evidence, one original M08 DTBO hash, one different-byte copy and absent stock DTBO. Four candidate classes: 1 BOOT_BUILD_RECIPE (conversion.bif), 3 DEVICE_TREE_BINARY, 4 DEVICE_TREE_SOURCE, 45 PLATFORM_LOG_OR_MANIFEST. **No original XSA, psu_init, genuine FSBL/PMUFW source in scanned candidates.** These are owner PC reports, not proof of which firmware executed.

**New offline hardware preparation:** [passive synthesis-only runbook](M08_D3_2_PASSIVE_SYNTHESIS_PC_RUNBOOK_2026_11_18.md) introduces a **fresh owner-PC Vivado 2025.2 synth_1-only** candidate based on D3.1 HPM0/HPM1/LPD-disabled fan-only BD, strict source and native reports, shell runner and negative tests. The tool chain cannot produce bitstream, run implementation or touch hardware. Source CI and future native synth remain separate. **Genuine new synthesis has NOT YET been owner-run or accepted**. A passive no-MMIO bitstream may be considered only after separate native route/DRC/timing, fan/rollback validation and explicit owner authorization. Protected HPM0 image continues to require firmware/ATB4/AIB13/clock/AFI proof.

**Branch:** agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit (stacked draft PR #86 over #85, #84, #83). **Work class:** OFFLINE ONLY. The original M08 image remains QUARANTINED; no board operations, new deployable HPM0 design, firmware writes or register accesses are authorized.

## Current milestones

M01–M04: completed, within separately documented PC-only architecture/numerical/workload/engine-audit scope. M05: accepted genuine offline HLS/RTL event-engine integration. M06: accepted genuine offline connected HLS/AMD RTL paging, fault/restore and M02/M03 parity (NOT physical DDR). M07: accepted PC/source scheduling, locality, cache and service-model experiments (NOT device measurements).

**M08: IN PROGRESS.** The original M08 image was physically loaded, but Linux stalled around its first identity access. A forced power cycle restored stock; no register result or proven root cause was captured. The old image SHA256 is a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b and it remains QUARANTINED. The D3.1 passive-fan/no-AXI candidate passed native owner Vivado 2025.2 BD validation only. Current work is **M08 → D3 → D3.2**, offline protection and integration. Do not create new milestones for individual verification checks.

**M09: PLANNED**, after reproducible M08 physical results, to analyze virtualization/sparsity, matched resource/traffic/service comparisons, negative results, prior art and thesis plots.

## Owner inventory verification reported on 2026-11-18

Owner successfully ran corrected v2 PC-only inventory: status M08_D3_2_PC_INVENTORY_RECORDED_HARDWARE_BLOCKED; **53 candidate files**; SHA receipt check for 00_boot_platform_inventory.json reported OK. Owner's summary: **one byte-exact original M08 overlay match**, one same-name different-byte review-only overlay candidate, original stock k26_starter_kits.dtbo absent in bounded roots, hardware authorization FALSE.

Those are owner-reported console outcomes, NOT independent byte review of the 53 entries. The actual original XSA/PS init, installed firmware versions, base/applied Linux DT, ATB4/AIB13 enable/error/ACK, HPM0 AFI and PL0 ownership are still UNKNOWN from the supplied summary. An overlay filename and SHA match do NOT prove boot use.

New read-only offline **receipt reviewer** scripts/m08_d3b_boot_platform_receipt_review.py independently checks full JSON/SHA receipt and cross-validates every reported candidate against historical reference summaries; it outputs only a safe class/name/hash triage and explicitly refuses all boot/physical readiness claims. The companion synthetic negative tests reject rehashed forged evidence, mismatched reference summaries, symlinked receipts, inconsistent runtime flags and duplicate candidates. The owner's genuine saved receipt has NOT YET been independently reviewed by this new tool; its owner PC execution is the next evidence step.

## Completed software-only D3.2 changes

New testbench rtl/m08/tb_m08_d3b_axi_fault_scoreboard.sv and companion tests/test_m08_d3b_axi_fault_scoreboard.py provide an **ABSTRACT** event-driven, PS-clocked AR/R + AW/W/B scoreboard and negative fault probes, not a real PS ATB or AIB simulator. It distinguishes accepted downstream obligations from synthetic upstream SLVERR, rejects falsely safe isolation with outstanding AR/AW/W, covers late R/B, split AW and W, B missing, unsolicited responses, concurrent read and write traffic, bounded tracking, response backpressure instability, stopped PL0 and stopped PS clock. A stopped PS clock cannot advance the monitor. A local zero-outstanding counter is NOT actual AIB13 isolation ACK or proof of quiescence in silicon. It must NEVER enter a Vivado candidate or authorize MMIO.

Latest new-source GitHub M08 workflow passed real Icarus compilation/execution, **261 targeted M08 tests**, **40 M07 tests**, **1,147 full Python tests**. Final-HEAD all-eight-workflow results must be checked again after documentation updates. Any simulation is **NOT** real vendor PS/Vivado validation or live KV260 evidence.

## D3.2 remaining workstreams — no extra milestone numbering

1. **Boot/PS ownership:** identify exact boot/XSA/PS-init/FSBL/PMUFW/ATF/U-Boot/kernel artifacts and their original provenance; derive ATB4 response/timebase/error, AIB13 quiescence/ACK, HPM0 128-bit AFI and PL0/reset boot owners from actual source. If absent, leave unproven and do NOT write guessed register sequences.
2. **AXI containment verification:** extend and independently compare AR/R and AW/W/B with real AMD AXI/PS-ATB/SmartConnect models **only if such a model is verifiably available**. The abstract scoreboard may close offline coverage, but never proves actual stopped-clock recovery or late-response isolation.
3. **Linux/FPGA-region integration:** inspect versioned stock/kernel/dfx-manager source for bridge ordering, clock consumers/AFI, driver binding, no unguarded raw generic-UIO mappings, independent fan continuity and stock rollback. Write review-only, non-deployable contracts pending authentic sources.
4. **Conditional new Vivado-only PS HPM0 candidate:** require independently supported ATB4/AIB13/clock/AFI/driver/fan and outstanding-transaction protocol first; then create a **new** candidate with disabled compute and owner-original offline Vivado source/native evidence, not bitstream or DTBO deployment.

**Later within M08, contingent on independent safety and explicit owner authorization:** physical one-register diagnostic; Linux kernel-owned DDR/DMA/page transfer; hardware M02/M03 neural correctness; genuine repeatable resource-matched event/timestep, cache/DDR and end-to-end measurements. These correspond to existing M08.3–M08.7 work packages; do not promote them to new global milestones. M09 follows only with rigorously labeled PC-model vs physical-device evidence.

## Nonnegotiable prohibition

No board interrogation, JTAG, PS registers, clock/fan/firmware changes, Linux MMIO (/dev/uio or /dev/mem), xmutil, FPGA programming, old image reload, new bitstream/DTBO deployment, or false claims of ATB4/AIB13 runtime protection. Old failure root cause remains UNKNOWN.

## Owner Linux VS Code commands — PC only

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3b_boot_platform_receipt_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3b_axi_fault_scoreboard.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
RUN="$HOME/Thesis_Evidence/M08/m08_d3b_b1_inventory_Kcn9mCdA"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_d3b_boot_platform_receipt_review.py --run-dir "$RUN"
command -v iverilog
command -v vvp
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_d3b_axi_fault_scoreboard \
  -o "$TMP/d3b_axi.vvp" rtl/m08/tb_m08_d3b_axi_fault_scoreboard.sv
vvp "$TMP/d3b_axi.vvp"
# LAST marker: M08_D3_2_AXI_ABSTRACT_BFM_ALL_PASS_NOT_VENDOR_ATB_AIB_OR_BOARD
# Only the newly allocated TMP is disposable. Preserve original evidence folders.
~~~
