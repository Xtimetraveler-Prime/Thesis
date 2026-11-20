# M08 D3.D.2B — NEXT CHAT HANDOFF: accept ORIGINAL synapse image, then one-shot KV260 JTAG test

## COMPLETED OWNER D3.D.2B PHYSICAL TEST — historical handoff retained

**2026-11-20 10:36–10:37 MST — OWNER ORIGINAL D3.D.2B PHYSICAL RECURRENT SYNAPSE PARITY PASS.** The owner supplied the genuine Linux PC / Vivado 2025.2 one-shot terminal transcript (not a direct assistant read of owner filesystem). The original read-only native gate returned exit **0** with 12/12 original SHA ledger entries OK and nested `M08_D3D2B_NATIVE_ROUTED_SYNAPSE_CANDIDATE_ACCEPTED_NO_BOARD`. The original bitstream was **not rebuilt**: SHA256 `dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14`, 7,797,847 bytes, owner native `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO`, original reviewed 7 vendor/debug warnings (only first 15 displayed RTSTAT paths individually reviewed), WNS **+0.136 ns**, WHS **+0.012 ns**, TNS/THS 0. The original third PDCN-1569 LUT warning used the exact `SWITCH_N_EXT_BSCAN.id_state[0]_i_1/I0` path and `is not included` text; narrowly corrected synthetic-gate assumptions were accepted without changing RTL, builder or image.

**Genuine board observation:** `xck26_0` on `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, configuration startup HIGH, `M08_D3D2B_PROGRAM_COMPLETED`, `hw_axi_1` 32-bit JTAG AXI, BRAM echo `55AA22DD`, and new synaptic engine ID `M4SN` / `0x00030000`. Both real on-device recurrent networks passed: `chain_recurrent` spike masks `[1,2,4,8]` and `inhibition_half_decay` spike masks `[1,10,4,8]`. **32/32 voltages, 32/32 per-tick spike decisions, and 32/32 hardware-delivered synaptic currents** matched independently generated M02 dense/event reference. The first one-shot physical folder is **immutable**: `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_HW_Pw3KKKXl`. Its original **6/6** physical SHA ledger entries checked `OK`, independent physical audit returned `M08_D3D2B_PHYSICAL_RECURRENT_SYNAPTIC_ROUTING_M02_PARITY_ACCEPTED`, runner printed `M08_D3D2B_HARDWARE_RECURRENT_SYNAPSE_M02_PARITY_SUCCEEDED`, and `M08_D3D2B_PHYSICAL_RUN_EXIT=0`. This report establishes *bounded* recurrent routed synaptic computation on fabric; it does **not** prove physical 32-neuron M06, physical DDR/paging, Linux/PS compatibility, PS-clock independence, sustained cooling, performance, or energy. **D3.D.2B PHYSICAL COMPLETE; M08 OPEN, M09 PLANNED. D3.D.2C next: distinct 32-neuron ×4-tick RTL/ABI/synapse-capacity design with independent M02/M06 oracle, Icarus, then separate genuine native+owner physical gates.** Earlier "pending" entries below remain historical and are superseded by this owner-supplied original pass. Draft PR stack remains unmerged.

**Do not rerun the one-shot D3.D.2B program command in section 5**. That procedure is a completed historical test, not current deployment authorization. Continue only on a NEW D3.D.2C branch after separate validation; leave original owner folders untouched.


**Updated November 20, 2026; based on docs/M08_D3D_1_PHYSICAL_LIF_NEXT_CHAT_HANDOFF_2026_11_19.md and the established D3.C/D3.D.2A owner hardware workflow.**

**AUTHORITATIVE NEXT GATE: Run the newly reviewed source/native gate against the original D3.D.2B bitstream; do NOT rebuild it. If owner-local original evidence acceptance passes, do fresh physical readiness/identity preflight, then ONE owner-controlled JTAG recurrent-synaptic neural parity test.** Native image acceptance is not the same as physical acceptance.

## 0. Current factual status (no false physical claim)

| Work | Status |
|---|---|
| D3.C JTAG AXI→BRAM physical communication | Owner original physical PASS; limited JTAG transport only. |
| D3.D.1 physical one signed16 LIF ×4 | Owner original four-tick M02 PASS. |
| D3.D.2A physical FOUR independent LIF ×4, two cases | Owner original physical PASS: 32/32 voltages and 32/32 spike decisions, independent auditor; immutable physical m08_d3d2a_four_HW_UBi3VCax. |
| D3.D.2B four LIF + EIGHT positive-delay weighted recurrent synapses | Real Icarus/dual M02 reference and physical harness tests passed PC/CI. **Genuine owner Vivado 2025.2 routed bitstream exists** with all original 12/12 SHA evidence OK. |
| D3.D.2B original DRC | **REVIEWED.** Seven vendor XSDB/JTAG debug warnings, not synaptic RTL logic. A source gate narrowly allows these exact warning paths and pins, exact original source/digest. **Owner post-patch rerun of the native gate is still PENDING.** |
| D3.D.2B real FPGA recurrent synapse routing | **NOT YET PROGRAMMED OR TESTED.** |
| D3.D.2C M06 32 neurons ×4 ticks | Not developed/physical; new state/synapse address/scheduler architecture required. |
| Physical DDR/paging, PS clock independence, Linux ownership, performance/energy | Not proven. Original HPM0/PS DDR hazards remain quarantined. M08 OPEN; M09 PLANNED. |

**Why no rebuild?** The owner-original D3.D.2B Vivado run on 2026-11-20 00:49:59 MST reached FULLY ROUTED and successfully wrote its bitstream; original 12/12 evidence members matched SHA256, WNS +0.136 ns, WHS +0.012 ns, TNS/THS zero with no failed endpoints, all specified timing constraints met. The first gate exit code 2 came from the intentional *NEW_DRC_REVIEW_REQUIRED* policy on seven yet-unreviewed findings. After looking at the complete report the seven are exactly: PDCN-1569 three XSDB debug-hub LUT pin advisories (A1/I0, A3/I1, A4/I0), REQP-1857 one JTAG rx_fifo BRAM warning, REQP-1858 two JTAG rd_cmd/wr_cmd BRAM warnings, RTSTAT-10 one unused-load advisory (39 nets, 37 listed, first **15** actually printed). The printed first 15 paths all belong to XSDB/debug/JTAG FIFOs and are explicitly allowlisted; **the other 22 names are not individually reviewed**. A BRAM-collision *advisory* is not proof collisions cannot occur; use bounded hardware test only. WNS +0.136 ns is a narrow routed 100 MHz margin and not a robustness/throughput claim.

## 1. Repository/PR and immutable owner native evidence

Repository: Xtimetraveler-Prime/Thesis; project Neuromorphic_Accelerator/v1.
Working branch: agent/neuromorphic-accelerator-v1-m08-d3d2b-synaptic-routing.
Draft PR **#90**, stacked onto D3.D.2A draft PR **#89**, then D3.D.1 draft #88 and D3.C draft #87; **DO NOT MERGE** without owner approval. Check git rev-parse HEAD or the live PR after the handoff, since a documentation commit advances the branch.

~~~text
Original owner native directory, DO NOT MODIFY:
  /home/dna/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO

Exact first native bitstream:
  /home/dna/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO/bitstream_candidate/m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit

Bitstream SHA256:
  dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14
Bitstream size:
  7,797,847 bytes
Builder SHA256:
  82ba3b226e16ac579cfc2527216f8acb02f9b13d3f42c5574344fcc9ce49e1a8
Synaptic RTL SHA256:
  2894f33a1c0054a0cf0231e1c4970e5eaea377bbe7524e4c57717c033b5ad88b
Fabric POR RTL SHA256:
  56dffdb178772296c7d751d75654aff8be44885939f752a9200ad1f961373fb2
Vivado: 2025.2, Ubuntu 24.04.5, K26 part xck26-sfvc784-2LV-c
Timing: WNS +0.136 ns, WHS +0.012 ns, TNS 0, THS 0
Clock: PS pl_clk0 requested 100 MHz; PS clock dependency YES, independence UNPROVEN
Reset: fabric-POR 256 cycles, PS HPM masters disabled
BRAM: 0xA0000000, 4 KiB; recurrent neuron AXI-Lite: 0xA0001000
Synapse engine ID: M4SN 0x4D34534E, version 0x00030000
JTAG known target: localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA
K26 expected device: xck26_0; debug AXI expected hw_axi_1 (verify fresh)
Fan TTC0 EMIO → A12, not an independent cooling guarantee
~~~

The builder/RTL and original .bit **have NOT been edited** to clear this review. The gate and physical runner were changed; original rejected native test output must remain in history. Do not overwrite any original .bit, route/DRC/timing report, Vivado log/journal, native result, or SHA ledger. Never copy a bitstream with a different name to pass the gate.

## 2. READ FIRST — actual source files (not only this handoff)

- This handoff; docs/M08_D3D2B_RECURRENT_SYNAPSE_PHYSICAL_PLAN_2026_11_20.md; roadmap.md; README.md; docs/M08_TESTS_EXPLAINED.md.
- scripts/m08_d3d2b_synaptic_gate.py and tests/test_m08_d3d2b_owner_native_review.py: original seven-warning exact DRC, owner binary/size/RTL/builder hash and timing gate; mutation/negative tests.
- tests/test_m08_d3d2b_synaptic_gate.py and scripts/m08_d3d2b_synaptic_vectors.py: actual M02 dense+queued fixture/reference, four-neuron Icarus RTL parity.
- scripts/run_m08_d3d2b_synaptic_physical_once.sh, scripts/m08_d3d2b_synaptic_readback_once.tcl, scripts/m08_d3d2b_synaptic_physical_audit.py and tests/test_m08_d3d2b_synaptic_physical.py: one-shot physical, six-file SHA and independent full hardware readback audit.
- rtl/m08/m08_d3d2b_synaptic_lif_axil.v; rtl/m08/tb_m08_d3d2b_synaptic_lif_axil.sv; scripts/m08_d3d2b_synaptic_build.tcl. DO NOT change these and then reuse old bitstream.
- Prior safety, genuine physical and recovery history: docs/M08_D3D_1_PHYSICAL_LIF_NEXT_CHAT_HANDOFF_2026_11_19.md; docs/M08_D3D2A_FOUR_NEURON_PLAN_2026_11_19.md; docs/M08_D3_2_STATUS_AND_NEXT_WORK_2026_11_18.md; docs/M08_D3B_NEXT_CHAT_HANDOFF_2026_11_12.md. Preserve original quarantines.

## 3. NEXT CHAT Step A — owner local source/CI and original native verification, NO BOARD

First inspect git status --short for user changes. Copy-paste in Linux VS Code terminal:

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2b-synaptic-routing
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2b-synaptic-routing
git rev-parse HEAD

cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_m08_d3d2b_owner_native_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2b_synaptic_gate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2b_synaptic_physical.py' -v
python3 scripts/m08_d3d2b_synaptic_gate.py --source-only
bash -n scripts/run_m08_d3d2b_synaptic_physical_once.sh

RUN="$HOME/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO"
BIT="$RUN/bitstream_candidate/m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
printf '%s  %s\n' \
  'dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14' \
  "$BIT" | sha256sum -c -
stat -c '%s %n' "$BIT"
python3 scripts/m08_d3d2b_synaptic_gate.py --run-dir "$RUN"
~~~

**STOP** if any test, source, SHA receipt, DRC, timing or native gate fails. No bitstream rebuild, no owner program. On a genuine read-only success, JSON should show nested native.status = **M08_D3D2B_NATIVE_ROUTED_SYNAPSE_CANDIDATE_ACCEPTED_NO_BOARD**, exact candidate SHA/size above, vendor_drc_warnings=7, WNS 0.136, WHS 0.012, TNS/THS 0, and reviewed_drc scoped first15. Outer top-level SOURCE_ACCEPTED_PC_ONLY is the source status and does NOT contradict nested native acceptance. Owner must report actual fresh output, not synthetic or CI inference.

The original Vivado generation already occurred. Do NOT rerun scripts/run_m08_d3d2b_synaptic_pc.sh for this candidate. If actual neural RTL/builder changes are later justified, build in a **new** unique original native directory and re-review that image separately.

## 4. NEXT CHAT Step B — physical preflight, STILL NO PROGRAMMING

- Owner confirms board is the real Kria KV260/K26 on known stock/recoverable boot, USB/JTAG connected, no conflicting Vivado manager, and retains stock recovery/power-cycle capability.
- **Independent powered external cooling** is running on SOM and thermal state safe; prior PL fan/A12 output is not an independent cooling protection. Stop if temperature, power or USB is abnormal.
- UART PuTTY/serial logging active and saved throughout. Any SSH/ICMP loss is a separate observation, not proof of kernel hang or physical neural error. Avoid arbitrary PS MMIO, Linux UIO, /dev/mem, DDR, xmutil, DFX-mgr, SD/flash writes.
- Vivado version is 2025.2 from /home/dna/Vivado/2025.2/Vivado/settings64.sh. Review a **real existing read-only K26 JTAG identity preflight** script from prior D3.D.1 before using it, or rely on the runner's checked unique target/device. Do not invent script names.
- Owner authorizes this exact one physical test and has confirmed that Step A original native gate PASSED. No implicit reprogram/retry permission.

## 5. NEXT CHAT Step C — ONE original physical synaptic neural parity attempt

**ONLY IF Steps A and B pass**, owner runs exactly once:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO"

M08_D3D2B_ALLOW_PROGRAM=YES \
bash scripts/run_m08_d3d2b_synaptic_physical_once.sh "$RUN"
RC=$?
echo "M08_D3D2B_PHYSICAL_RUN_EXIT=$RC"
~~~

This runner rechecks exact original native evidence, pinned image hash+bytes and strict DRC; launches a fresh distinct original hardware evidence directory (print and preserve the actual M08_D3D2B_NEW_PC_HW_EVIDENCE path), exactly one JTAG program, checks K26 target, BRAM echo 55AA22DD, M4SN v3 identity, then executes two independently golden-checked four-neuron/8-synapse/4-tick networks. The PC sends neuron params, EXTERNAL currents and synapse edges; **the FPGA computes delivered synaptic current from earlier real spikes**, and reads back **32 membrane voltages, 32 spike decisions and 32 separate delivered synaptic-current words**. The cases are chain_recurrent (spike masks [1,2,4,8]) and inhibition_half_decay (masks [1,10,4,8]). It checks nonce/status/count, creates six SHA entries and calls independent read-only physical auditor. No SSH required for JTAG data.

**No automatic retry, even if programming fails before neural readback.**

## 6. NEXT CHAT Step D — independent evidence audit, read-only

Use the actual new physical HW directory printed by the runner, never guess a path:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO"
HW="<ACTUAL_m08_d3d2b_synaptic_HW_XXXXXXXX_directory>"
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
cat "$HW/03_exit.txt"
cat "$HW/80_synaptic_parity_readback.txt"
python3 scripts/m08_d3d2b_synaptic_physical_audit.py \
  --run-dir "$RUN" --hw-dir "$HW"
~~~

A physical pass requires original 6/6 physical SHA entries OK, physical Vivado exit 0, both complete on-device workload receipts, and independent status **M08_D3D2B_PHYSICAL_RECURRENT_SYNAPTIC_ROUTING_M02_PARITY_ACCEPTED** (plus runner M08_D3D2B_HARDWARE_RECURRENT_SYNAPSE_M02_PARITY_SUCCEEDED). Programming completion or BRAM echo alone does **NOT** prove synaptic neural computation.

**On any failure:** STOP. Preserve first original HW folder, Tcl, Vivado log/journal, exit, SHA ledger if present, owner UART and first error. Do not edit receipts, fabricate missing result, auto-reprogram, rebuild or assert a pass. Diagnose target/programming vs BRAM transport vs peripheral ID vs DONE/nonce vs M02 synapse/voltage/spike mismatch before a later, separately owner-authorized action. If safety problem, shut down safely as appropriate.

## 7. After physical D3.D.2B parity: next D3.D.2C 32-neuron M06 reference

This current bitstream is only **four stateful LIF neurons, eight signed16 weighted directed edges, four logical ticks, delays 1..3**. It is NOT an M06 32-neuron image. If real physical recurrent routing passes, open a new stacked branch and plan D3.D.2C network state banks, 32-neuron address map, scheduler, edge/event capacity and exact M02/M06 32×4 workload; run new RTL/Icarus, genuine native Vivado DRC/timing, and real independent owner physical parity. DDR/paging is a later distinct physical boundary, not yet proven.

## 8. Non-negotiable development / evidence contract

- Read the live repository first, not only this handoff or prior chats. Preserve draft PR stack and all original D3.C/D3.D.1/D3.D.2A successes and first D3.D.2B warning rejection history. No merges without user instruction.
- Distinguish Python/M02, Icarus RTL/CI, owner genuine Vivado native, owner physical JTAG, Linux PS state and DDR. A source unit test is never a hardware result.
- Owner evidence files and failed runs are immutable. The DRC exception applies **only** to exact D3.D.2B image/source/size/original report and first 15 actually displayed RTSTAT nets; no generic seven-warning waiver for any future image.
- For any new code, preserve CI tests, negative/mutation tests, explicit original source/bitstream hash checks, route timing, and test all **8 GitHub Actions workflows on final HEAD**; report pending CI truth, don't overclaim.
- Give owner exact Git terminal commands after changes and tests. Do not assume access to the user's local PC; owner must supply actual native and JTAG outputs.
- Keep M08 OPEN, M09 PLANNED. After real physical acceptance update roadmap.md, README.md, docs/M08_TESTS_EXPLAINED.md, D3.D.2B plan, this handoff and PR #90. Don't start D3.D.2C as a physical claim until D3.D.2B is independently verified.
