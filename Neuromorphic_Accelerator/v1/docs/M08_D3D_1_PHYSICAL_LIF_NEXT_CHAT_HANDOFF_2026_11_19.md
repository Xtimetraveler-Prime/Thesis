# M08 D3.D.1 — NEXT CHAT HANDOFF: first **physical** signed16 LIF execution on KV260

**Updated:** 2026-11-19, following owner-verifiable genuine Vivado native image acceptance.  
**AUTHORITATIVE NEXT GATE:** **physical one-shot JTAG LIF parity on the existing, already-accepted D3.D.1 bitstream**. DO NOT rebuild automatically.  
**Repository:** `Xtimetraveler-Prime/Thesis`, project `Neuromorphic_Accelerator/v1`.  
**Current branch / draft PR:** `agent/neuromorphic-accelerator-v1-m08-d3d-neural-jtag-parity`, **draft PR #88**, base `agent/neuromorphic-accelerator-v1-m08-d3c-jtag-pl-link` (**draft PR #87**), further stacked on the existing M08 protective D3 branch. **DO NOT MERGE** PR #88, PR #87 or upstream drafts until separately owner-reviewed. Verify current HEAD via GitHub/`git rev-parse HEAD`; handoff-file creation itself moves HEAD, so do not hard-code a pre-handoff commit as final.

## 0. Executive status — exactly what has and has not passed

| Boundary | Honest current status |
|---|---|
| M01–M07 research software/HLS/model | Previously accepted, but **in explicitly bounded PC-only, HLS or vendor-simulation scopes**, not physical neural/DDR proof. |
| M08 D3.C r2 JTAG→AXI→BRAM | **PHYSICALLY PASSED**, owner original Vivado JTAG program + **four exact 32-bit BRAM write/read pairs**, immutable **5/5** SHA evidence. |
| M08 D3.D.1 signed16 LIF RTL and M02 fixture parity | First-party real RTL/Icarus and M02 independent dense/queued reference comparison tested in source/CI, not physical. |
| M08 D3.D.1 genuine native routed bitstream | **ACCEPTED OFFLINE, NO BOARD**. Owner original genuine Vivado 2025.2 generated .bit, **12/12** SHA receipt PASS, Python native gate accepted, **WNS +3.170 ns, WHS +0.010 ns, TNS/THS zero**, exact seven vendor/debug warning profile. |
| M08 D3.D.1 physical neural execution | **NOT YET RUN**. The next action is one operator-approved JTAG one-shot, only after cooling/UART/stock/recovery read-only preflight. |
| M06 32-neuron ×4-tick HLS neural/paged engine on KV260 | **NOT PHYSICALLY INTEGRATED**, neither streams/synapse routing nor DDR proved by D3.D.1. |
| Kernel-owned DDR/DMA, PS HPM0/Linux manager compatibility, physical throughput/energy | **UNPROVEN**. Old HPM0-linked dual-UIO physical image remains **QUARANTINED**. |

**CRITICAL interpretation:** The owner native auditor prints an **outer** `status=M08_D3D_SOURCE_ACCEPTED_PC_ONLY_NOT_BUILT` (source-gate phase label) and an **inner** `native.status=M08_D3D_NATIVE_NEURON_IMAGE_ACCEPTED_OFFLINE_NO_BOARD`. Genuine native acceptance is established by the **inner** field, not contradicted by the outer source label. The same output explicitly reports `hardware_programmed=false` and `neural_execution_proven=false`; do not claim a physical LIF pass yet.

## 1. Immutable owner evidence / precise hardware candidate

**Owner original D3.D accepted native run (never overwrite):**

```text
/home/dna/Thesis_Evidence/M08/m08_d3d_neuron_Yz3k4vsi
/home/dna/Thesis_Evidence/M08/m08_d3d_neuron_Yz3k4vsi/bitstream_candidate/m08_d3d_lif_jtag_UNRELEASED.bit
```

**Bitstream SHA256:** `b071adcec0ba33077cdf70543d5cc9c354f6746bcc8138e8c741c41a3cbb1c8b`  
**Length:** `7797836` bytes  
**Builder SHA256:** `3fcaaa0e839effe49addb0ae258ec91cc4f544ff37caf4880b26239c93ecd7f4`  
**LIF RTL SHA256:** `3d1194ab1c9e248f79560c89955a02e06b47dcd546c85e6a7f584ac62d06ed29`  
**Fabric POR SHA256:** `56dffdb178772296c7d751d75654aff8be44885939f752a9200ad1f961373fb2`  
**Nominal clock:** PS `pl_clk0` requested 100 MHz; PS clock **dependency YES**; actual board runtime independence **NOT PROVEN**.  
**Reset:** 256-cycle fabric-POR, rather than Linux-managed PS reset for PL JTAG/BRAM/LIF logic.  
**JTAG BRAM address:** `0xA0000000` (4 KiB, 1,024×32).  
**LIF AXI-Lite base:** `0xA0001000` (4 KiB decoded aperture).  
**K26:** `xck26_0`; known target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`; prior real debug AXI `hw_axi_1`.  
**Route timing:** WNS `+3.17 ns`, WHS `+0.01 ns`, TNS/THS `0.0 ns`, no reported failing endpoints.  
**DRC:** 7 known vendor/debug **Warnings**, profile `EXACT_REVIEWED_VENDOR_JTAG_PROFILE`: PDCN-1569×3, REQP-1857×1, REQP-1858×2, RTSTAT-10×1. D3.D-specific RTSTAT detail `39 net(s) have no routable loads`, `(the first 15 of 37 listed)`, **exact ordered first 15 owner-review paths** all under `dbg_hub/inst/` or `m08_d3d_lif_jtag_i/jtag_axi/inst/`. **Only the displayed 15 of 37 were individually examined**; do not claim full unused-net exhaustive inspection. The original D3.C profile is different (47 unused/45 listed) and retained.

**Owner original D3.D verification already supplied:**
```text
00_vivado.log: OK
01_vivado.jou: OK
02_vivado_exit.txt: OK
reports/10_fan_a12.xdc: OK
reports/11_fabric_por.v: OK
reports/12_lif_axil.v: OK
reports/20_route_drc.rpt: OK
reports/21_route_timing.rpt: OK
reports/22_route_utilization.rpt: OK
reports/23_route_clocks.rpt: OK
reports/30_native_result.txt: OK
bitstream_candidate/m08_d3d_lif_jtag_UNRELEASED.bit: OK
native.status=M08_D3D_NATIVE_NEURON_IMAGE_ACCEPTED_OFFLINE_NO_BOARD
```

**Physically proven D3.C predecessor:** owner `~/Thesis_Evidence/M08/m08_d3c_jtag_HW_sMEfyq6l`, **5/5** original physical receipt SHA lines OK, `vivado_physical_exit=0`, `result=FOUR_BRAM_WORDS_WRITTEN_READ_AND_MATCHED`, four exact patterns at `0xA0000000..0xA000000C`; its distinct bitstream SHA256 `87e04662b038ded01bd020141c541a33d62370df02bdeaacdad695b17c9d00a1`. That physical test **did not compute neural states**. Never misrepresent D3.C as D3.D or reuse the older `.bit`.

**Preserve negative history:** D3.D original native `m08_d3d_neuron_BVm2BQh9` failed Vivado IPI SystemVerilog module reference (fixed by Verilog `.v` top). D3.D original `m08_d3d_neuron_R3BZiFI7` bitgen succeeded but auto-replaced a typoed wrapper top and had an actual `filemgmt 20-742` critical warning (fixed by validating generated `m08_d3d_lif_jtag_wrapper`). The accepted `Yz3k4vsi` source/image was not regenerated after two later read-only checker policy corrections. DRC checker first rejected expected renamed vendor JTAG FIFO hierarchy, then detected D3.D `RTSTAT-10` **39/37** versus older D3.C **47/45**. The exact original D3.D sample was reviewed and narrowly allowlisted. **Do not rewrite historical receipts or blindly loosen constraints.**

**Original dangerous HPM0-linked M08 image:** `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`, previous Linux first identity access stalled RCU/timer CPU and SSH; PS/ATB/AFI/PL0 root cause unknown. **QUARANTINED: never program or access its PS UIO/MMIO.** Raw JTAG tests can make SSH unavailable even when a programming transaction succeeds. Board has previously been owner-power-cycled back to stock; not a general Linux-compatibility guarantee.

## 2. What D3.D.1 actually executes

The new synthesizable `rtl/m08/m08_d3d_lif_axil.v` is a **real clocked** LIF peripheral: **one signed16 neuron, 4 finite hardware update ticks per START**, four signed32 externally aggregated tick currents, signed16 bias/initial/threshold/reset, allowed decay `0`, `1/2`, `1`, truncation toward zero for negative halves, saturation and inclusive threshold/spike/reset. It exposes output only after `DONE`; independent AW/W AXI4-Lite requests have stable B/R responses under backpressure. `m08_d3d_lif_jtag` BD retains D3.C JTAG AXI→BRAM transport and adds SmartConnect M01→neuron S_AXI. The **PC writes inputs, never expected voltage/spike values**; only the actual fabric computes output. No recurrent synapses, stream shells, scheduler, backing DDR, classifier, Loihi digital twin, chip-scale performance.

**Register offsets from `0xA0001000`** (32-bit aligned): `0x000` magic `0x4D384C46`; `0x004` version `0x00010000`; `0x008` DONE bit0 / BUSY bit1; `0x00C` nonzero nonce; `0x010` initial voltage; `0x014` bias; `0x018` threshold; `0x01C` reset; `0x020` decay mode; `0x024` through `0x030` four signed current words; `0x034` START=1; `0x038` completed nonce; `0x03C` four spike bits; `0x040` through `0x04C` four signed-extended membrane trace results; `0x050` completed-run count. No output-voltage registers are host writable.

The preexisting `scripts/m08_d3d_neuron_vectors.py` uses **both M02 dense and M02 queued event reference** and requires agreement. Fixtures are `negative_trunc_spike`, `positive_negative_saturation`, `autonomous_bias_equality`, `negative_half_toward_zero` (4 total; each 4 ticks). `scripts/m08_d3d_neuron_readback_once.tcl` sends four separate parameter/current sets to real JTAG AXI, checks `DONE`, nonce, all four membrane results, spike mask and increasing hardware-completed run count; it first confirms a retained single BRAM echo. The physical launcher creates a new `m08_d3d_neuron_HW_*` PC evidence directory with actual JTAG log, executed Tcl, M02 goldens, 03 exit, and, on success, complete neural result receipt and 6-entry SHA ledger.

**Physical acceptance success markers:**
```text
M08_D3D_BRAM_TRANSPORT_REGRESSION_PASS
M08_D3D_HW_NEURAL_M02_PARITY_PASS|negative_trunc_spike|...
M08_D3D_HW_NEURAL_M02_PARITY_PASS|positive_negative_saturation|...
M08_D3D_HW_NEURAL_M02_PARITY_PASS|autonomous_bias_equality|...
M08_D3D_HW_NEURAL_M02_PARITY_PASS|negative_half_toward_zero|...
M08_D3D_HARDWARE_M02_LIF_FOUR_FIXTURE_PARITY_SUCCEEDED
```
`80_neural_parity_readback.txt` must report `result=FOUR_HARDWARE_NEURON_FIXTURES_MATCHED_M02`. The **separate** Python `scripts/m08_d3d_neuron_physical_audit.py` must then accept with `status=M08_D3D_PHYSICAL_SINGLE_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED`, `hardware_execution_verified=true`, while `full_m06_neuromorphic_accelerator_verified=false` and `physical_ddr_verified=false`.

## 3. READ FIRST — relevant repository files, in order

1. `roadmap.md` — **current front-page owner D3.D.1 native status overrides old dated chronological roadmap paragraphs**.
2. This handoff and `docs/M08_D3D_PHYSICAL_NEURAL_PARITY_PLAN_2026_11_19.md` — actual owner SHA, warning review, precise computational/physical scope.
3. `docs/M08_D3C_JTAG_BRAM_PL_LINK_2026_11_19.md` — original physically PASS JTAG r2 link and prior failure.
4. `docs/M08_D3_2_STATUS_AND_NEXT_WORK_2026_11_18.md` and `docs/M08_D3B_NEXT_CHAT_HANDOFF_2026_11_12.md` — prior PS/Linux/fan incident, stock recovery, quarantine. Historical **no-board** instructions belong to prior blocked protected PS track, not to the newly demonstrated D3.C standalone JTAG mode; still preserve HPM0 quarantine and preflight safeguards.
5. `docs/M02_PROVISIONAL_LIF_CONTRACT.md`, `docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md`, `docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md` — numerical oracle, 32×4 reference, fair later benchmarking.
6. Actual scripts: `scripts/m08_d3d_neuron_gate.py`, `scripts/m08_d3d_drc_inspect.py`, `scripts/m08_d3d_neuron_vectors.py`, `scripts/run_m08_d3d_neuron_physical_once.sh`, `scripts/m08_d3d_neuron_readback_once.tcl`, `scripts/m08_d3d_neuron_physical_audit.py`.
7. `tests/test_m08_d3d_neuron_gate.py`, `rtl/m08/m08_d3d_lif_axil.v`, `rtl/m08/tb_m08_d3d_lif_axil.sv`. Read actual sources; do not rely on the handoff description alone when giving hardware commands.

## 4. NEXT CHAT: owner PC verification and physical workflow

**A. Start with a read-only branch/source check and owner-local verification, no board mutation.** In a Linux VS Code terminal, and **only after inspecting `git status --short` for local edits**, use:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d-neural-jtag-parity
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d-neural-jtag-parity
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3d_neuron_gate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3c_jtag_bram_gate.py' -v
python3 scripts/m08_d3d_neuron_gate.py --source-only
bash -n scripts/run_m08_d3d_neuron_physical_once.sh

RUN="$HOME/Thesis_Evidence/M08/m08_d3d_neuron_Yz3k4vsi"
BIT="$RUN/bitstream_candidate/m08_d3d_lif_jtag_UNRELEASED.bit"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
printf '%s  %s\n' 'b071adcec0ba33077cdf70543d5cc9c354f6746bcc8138e8c741c41a3cbb1c8b' "$BIT" | sha256sum -c -
python3 scripts/m08_d3d_neuron_gate.py --run-dir "$RUN"
cat "$RUN/reports/30_native_result.txt"
```

**Gate to continue:** all 12 SHA rows `OK`, exact pinned .bit SHA `OK`, native nested `status=M08_D3D_NATIVE_NEURON_IMAGE_ACCEPTED_OFFLINE_NO_BOARD`, WNS `3.17`, WHS `0.01`, DRC known 7 vendor findings. If any mismatch, **STOP** and inspect existing original report; **do not** rebuild or overwrite old run to make the receipt pass. The new chat assistant has no direct user's PC/board connection and must not claim to have executed owner hardware or Vivado on their behalf.

**B. Physical preflight with owner present, STILL NO PROGRAMMING.** Guide the owner through and *record fresh actual results* for each item:
- Confirm the actual **KV260/K26** is safely powered/booted to known **stock** configuration. Use prior owner-proven UART PuTTY session / serial pins, USB/JTAG cable, Vivado 2025.2, original known Xilinx target `xck26_0`. Do not assume the K26 is the only device without identity verification.
- **Independently powered backup cooling is running and directed at SoM**, not dependent on a potentially reconfigured PL fan PWM. Fan A12 path exists in the image but is not an independently proven operational thermal safeguard. Observe board thermal state; stop on abnormal conditions.
- Keep UART capture/logging active throughout. Record pre-/post-load SSH/ICMP only as **separate diagnostics**, not prerequisites for the PL JTAG result or proof of kernel health. Prior stock network target reported `ubuntu@10.42.0.135` but verify actual link/config rather than assuming it. No additional Linux PS MMIO, FPGA-manager mutation, `xmutil loadapp/unloadapp`, arbitrary `/dev/mem` or DDR transactions.
- Confirm owner has power-cycle/stock recovery access, backup firmware still available, no conflicting Vivado JTAG process, stable cable and correct physical environment. **Do not power-cycle until after capturing JTAG outputs unless a safety condition forces an immediate shutdown**.
- Confirm that the owner authorizes **this one** raw-JTAG reprogram of the *new D3.D signed16 LIF image*, distinct from permission to generate a bitstream. Prior owner has requested moving on to physical tests, but still verify the real-time physical readiness and exact candidate before triggering `program_hw_devices`.

**C. ONE program + neural test if and only if A & B pass.** Show the command, confirm all context, then owner runs it **once** (no silent retries). The runner rechecks native audit, generates fresh independent M02 fixture file, invokes Vivado Hardware Manager with one `program_hw_devices`, runs a BRAM transport regression and 4 true LIF parity cases, and writes a distinct PC evidence directory. It does **not** require SSH or direct PS memory access for the result.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
RUN="$HOME/Thesis_Evidence/M08/m08_d3d_neuron_Yz3k4vsi"
M08_D3D_ALLOW_PROGRAM=YES bash scripts/run_m08_d3d_neuron_physical_once.sh "$RUN"
```

Record the exact printed `M08_D3D_NEW_PC_HW_EVIDENCE=/home/dna/Thesis_Evidence/M08/m08_d3d_neuron_HW_XXXXXXXX` line **even on failure**. The physical launcher has a bounded timeout, no automatic retry, and should not run as root.

**D. Verify REAL outputs, never infer from a Vivado message alone.** Use the **exact actual HW directory printed by runner** (it is not the native RUN and not the .bit path):

```bash
HW="<ACTUAL_m08_d3d_neuron_HW_XXXXXXXX_DIRECTORY>"
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
cat "$HW/03_exit.txt"
cat "$HW/80_neural_parity_readback.txt"
python3 scripts/m08_d3d_neuron_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"
```

Expected: **6/6** SHA lines OK on successful physical run, `vivado_physical_exit=0`, 4 fixture lines ending `hardware=PASS`, `result=FOUR_HARDWARE_NEURON_FIXTURES_MATCHED_M02`, independent audit `M08_D3D_PHYSICAL_SINGLE_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED`. Compare every returned voltage/spike value to M02, no reliance on BRAM echo or successful JTAG program only.

**E. Any failure = STOP and collect evidence.** DO NOT immediately reprogram, retry on a new HW folder or overwrite the initial log/receipt. Inspect `$HW/01_jtag_neuron.log`, `$HW/02_jtag_neuron.jou`, `$HW/03_exit.txt`, `$HW/99_evidence_sha256.txt`, and original UART capture. If `80_neural_parity_readback.txt` is absent on failure that is expected; do not invent one. Distinguish (1) program/target failure; (2) failed BRAM transport or PS PL0 clock/reset dependency; (3) missing AXI slave identity; (4) timeout/DONE/nonce; (5) correct I/O protocol but different neural arithmetic; (6) Linux-only network loss. Preserve original status and cause as unknown until supported. Owner controls safe power-cycle/stock restore afterward; collect post-recovery stock state separately. An SSH timeout alone is **not** proven Linux kernel hang and should not be used to erase a valid PL result.

## 5. Development workflow contract for the next ChatGPT instance — NONNEGOTIABLE

1. **Read real repo files first.** Do not use an older chat summary or this handoff as a substitute for current code. Check remote HEAD/PR #87/#88 before proposed changes. Preserve the draft PR stack and keep M08 open. No merge without explicit owner approval.
2. **Hardware-scoped truth.** Maintain the labels **SOURCE/CI** vs **genuine native owner Vivado** vs **physical JTAG/PL observed** vs **Linux PS/DDR runtime**. A passed bitstream check, JTAG echo, or a Python goldens-only fixture never proves physical neural execution. Never claim full-scale accelerator or DDR throughput from D3.D.1.
3. **One unique evidence directory per run.** All owner-PC native and physical outputs under `~/Thesis_Evidence/M08` in new exclusive sibling folders. Never edit/overwrite an original .bit, `99_evidence_sha256.txt`, native project/log/report or physical receipt; revalidation is **read-only**. Preserve genuine failures, first-error diagnostics and UART. Do not tamper with hashes/allowlists to clear a gate. Audit all unexpected DRC/clock/timing/fan behavior with original evidence.
4. **Small source changes → new feature branch** from current reviewed D3.D HEAD, stacked draft PR if a code defect is found; do not make speculative architectural changes while an original physical failure is being diagnosed. Review vendor/Linux instructions if tooling or register semantics change. Keep old D3.C accepted image/history intact. If source changes, create new native evidence and new candidate SHA; no old-image provenance reuse.
5. **Tests after every change.** `python3 -m compileall -q src scripts tests`; targeted `python3 -m unittest discover -s tests -p 'test_m08_d3d_neuron_gate.py' -v`; `-p 'test_m08*.py'` then full `-p 'test_*.py'` if applicable; real Icarus RTL/VVP rather than mocked hardware; execute read-only source/native gate on owner original if unchanged. Explicit negative tests for errors, stale nonce/results, changed metadata, wrong SHA, target, timing and DRC classes. **Check all eight GitHub Actions workflows on FINAL pushed HEAD**, not earlier commits; record counts and skip reasons. GitHub CI does not program the FPGA or run owner's Vivado.
6. **Owner replication after EVERY code/test commit.** Give copy-paste Linux VS Code commands `git status --short`, `git fetch origin`, `git switch <branch>`, `git pull --ff-only origin <branch>`, `git rev-parse HEAD`, `cd Neuromorphic_Accelerator/v1`, exact new tests, SHA receipts and expected markers. Pause at a hardware dependency until owner supplies outputs, rather than claiming execution from remote CI.
7. **Physical safety is a distinct gate.** Any FPGA JTAG programming requires actual present owner readiness, independent powered cooling, UART monitoring, stable cable, known stock boot/recovery and exact accepted .bit SHA. No automatic reprogramming/retries. Avoid original HPM0-connected quarantined firmware, raw PS MMIO/UIO, unsourced DDR, `xmutil`/dfx-mgr mutations and assumptions of Linux clock/boot compatibility. Don't weaken cooling or protections.
8. **Documentation each accepted gate.** Keep `roadmap.md`, `README.md`, `docs/M08_TESTS_EXPLAINED.md`, `docs/M08_D3D_PHYSICAL_NEURAL_PARITY_PLAN_2026_11_19.md`, this handoff and draft PR #88 aligned with actual owner evidence. Include dates, scope, exact SHA, acceptance marker and work still pending. Mark an observed failure as FAILURE and stop rather than presenting partial progress as completion.
9. **Separate future architectural milestones.** After physical one-neuron parity: plan **D3.D.2** genuine multi-neuron/tick state and synapse routing, targeting the M06 32-neuron ×4-tick accepted oracle; then neural workload scaling with controlled capacity and measured resource/latency, keeping JTAG command overhead separate. **D3.D.3** real DDR/HLS paging requires actual protected PS/Linux clock/AFI/ATB/AIB/DDR ownership evidence, safe allocations and independent new physical tests. Leave M09 quantitative cross-mode thesis closeout planned until valid matched hardware data exist. No shortcuts to a fake “full-scale” claim.

## 6. Recommended first reply from the next chat

Acknowledge that the owner **has accepted the native image** with original 12/12 SHA and positive setup/hold margin, but **no D3.D.1 physical neural test**. Read current repo files and verify remote branch/PR and script behavior first. Present the owner with the **exact copy/paste read-only Step A** and **practical Step B cooling/UART/stock preflight**, explain precisely which steps are non-programming. Only if those pass, walk the owner through the **single** explicit one-shot D3.D.1 physical run (Step C), then the independent **6-file + per-fixture M02** audit (Step D). Be ready to diagnose real log errors without reprogramming, and insist on evidence before altering the design or changing the gate.

**Handoff acceptance:** original owner D3.C physical JTAG transport **PASS**; D3.D.1 actual K26 bitstream **NATIVE OFFLINE ACCEPTED**; D3.D.1 PL neural inference, synapse routing and DDR **NOT YET PHYSICALLY PROVEN**. Next chat must not relabel this stage or skip the owner-operated hardware safety gate.
