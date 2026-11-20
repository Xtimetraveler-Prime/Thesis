# M08 D3.D.2B — first genuine recurrent on-FPGA synaptic routing

## ACCEPTED ORIGINAL OWNER PHYSICAL RESULT (supersedes preflight/pending history below)

**2026-11-20 10:36–10:37 MST — OWNER ORIGINAL D3.D.2B PHYSICAL RECURRENT SYNAPSE PARITY PASS.** The owner supplied the genuine Linux PC / Vivado 2025.2 one-shot terminal transcript (not a direct assistant read of owner filesystem). The original read-only native gate returned exit **0** with 12/12 original SHA ledger entries OK and nested `M08_D3D2B_NATIVE_ROUTED_SYNAPSE_CANDIDATE_ACCEPTED_NO_BOARD`. The original bitstream was **not rebuilt**: SHA256 `dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14`, 7,797,847 bytes, owner native `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO`, original reviewed 7 vendor/debug warnings (only first 15 displayed RTSTAT paths individually reviewed), WNS **+0.136 ns**, WHS **+0.012 ns**, TNS/THS 0. The original third PDCN-1569 LUT warning used the exact `SWITCH_N_EXT_BSCAN.id_state[0]_i_1/I0` path and `is not included` text; narrowly corrected synthetic-gate assumptions were accepted without changing RTL, builder or image.

**Genuine board observation:** `xck26_0` on `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, configuration startup HIGH, `M08_D3D2B_PROGRAM_COMPLETED`, `hw_axi_1` 32-bit JTAG AXI, BRAM echo `55AA22DD`, and new synaptic engine ID `M4SN` / `0x00030000`. Both real on-device recurrent networks passed: `chain_recurrent` spike masks `[1,2,4,8]` and `inhibition_half_decay` spike masks `[1,10,4,8]`. **32/32 voltages, 32/32 per-tick spike decisions, and 32/32 hardware-delivered synaptic currents** matched independently generated M02 dense/event reference. The first one-shot physical folder is **immutable**: `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_HW_Pw3KKKXl`. Its original **6/6** physical SHA ledger entries checked `OK`, independent physical audit returned `M08_D3D2B_PHYSICAL_RECURRENT_SYNAPTIC_ROUTING_M02_PARITY_ACCEPTED`, runner printed `M08_D3D2B_HARDWARE_RECURRENT_SYNAPSE_M02_PARITY_SUCCEEDED`, and `M08_D3D2B_PHYSICAL_RUN_EXIT=0`. This report establishes *bounded* recurrent routed synaptic computation on fabric; it does **not** prove physical 32-neuron M06, physical DDR/paging, Linux/PS compatibility, PS-clock independence, sustained cooling, performance, or energy. **D3.D.2B PHYSICAL COMPLETE; M08 OPEN, M09 PLANNED. D3.D.2C next: distinct 32-neuron ×4-tick RTL/ABI/synapse-capacity design with independent M02/M06 oracle, Icarus, then separate genuine native+owner physical gates.** Earlier "pending" entries below remain historical and are superseded by this owner-supplied original pass. Draft PR stack remains unmerged.



## NEW OWNER-ORIGINAL D3.D.2B DRC REVIEW VERDICT — no bitstream rebuild (2026-11-20)

**THE ORIGINAL BITSTREAM IS TECHNICALLY ELIGIBLE FOR A FIRST GUARDED PHYSICAL TEST AFTER THE OWNER RE-RUNS THE UPDATED NATIVE GATE.** Full owner original report supplied and reviewed in this chat (first attempt DRC gate exit 2 was intentional, NOT a bitgen failure). New image path and provenance are preserved exactly; **NO RTL/Vivado builder rework is indicated**, and no native source/bitstream/evidence was edited.

- **Original owner directory:** /home/dna/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO.
- **Original accepted-for-review bit SHA256:** dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14; **size 7,797,847** bytes.
- **Provenance:** Vivado 2025.2, part xck26-sfvc784-2LV-c; builder SHA 82ba3b226e16ac579cfc2527216f8acb02f9b13d3f42c5574344fcc9ce49e1a8; synaptic RTL SHA 2894f33a1c0054a0cf0231e1c4970e5eaea377bbe7524e4c57717c033b5ad88b; POR SHA 56dffdb178772296c7d751d75654aff8be44885939f752a9200ad1f961373fb2.
- **Original timing:** +0.136 ns setup slack, +0.012 ns hold slack, TNS/THS zero, user-specified constraints met, zero failing endpoints; 100 MHz nominal requested PS PL0. This setup margin is narrow. Physical device/PS runtime clocks are still unproven independent of Linux.
- **Original DRC:** 7 Warn-only, no reported user synapse RTL-specific violation. PDCN-1569 three exact debug XSDB LUT advisories (pin A1/I0, A3/I1, A4/I0), REQP-1857 rx_fifo_i once, REQP-1858 rd_cmd_fifo_i and wr_cmd_fifo_i once, RTSTAT-10 39 nets without load / 37 listed / first **15** printed. The first fifteen are exact previously known debug-hub/JTAG FIFO paths under the renamed current module instance. The other 22 were not printed individually and are NOT claimed reviewed. Warning severity/count/hierarchy and real original report provenance must match a fail-closed allowlist.
- **Fix committed:** scripts/m08_d3d2b_synaptic_gate.py now binds original folder name, bit SHA and bytes, original RTL and builder hashes and all seven detailed DRC paths/pins; tests/test_m08_d3d2b_owner_native_review.py checks positive synthetic review and fail-closed mutations. The one-shot physical shell/Tcl independently recheck exact reviewed image hash/size. The original failed native exit-2 remains historical evidence. **GitHub CI and operator original-gate outcomes are separate**.
- **Owner next:** follow the authoritative [NEXT CHAT D3.D.2B ORIGINAL-BITSTREAM PHYSICAL HANDOFF](M08_D3D2B_NEXT_CHAT_PHYSICAL_HANDOFF_2026_11_20.md). First do source/tests and **READ-ONLY native** revalidation against the original 12 SHA files; require nested M08_D3D2B_NATIVE_ROUTED_SYNAPSE_CANDIDATE_ACCEPTED_NO_BOARD. If it passes, fresh stock/independent cooling/UART/JTAG preflight followed by *one* explicitly authorized hardware run. No current D3.D.2B physical neural evidence exists; no 32-neuron physical result exists. No new Vivado build is necessary unless the gate or real hardware reveals a specific design/source issue.

### Historical original native DRC rejection preserved below


## Owner first genuine D3.D.2B native build — BITGEN PASS / DRC GATE PENDING (2026-11-20 00:50 MST)

Owner ran `scripts/run_m08_d3d2b_synaptic_pc.sh` and supplied original Vivado 2025.2 stdout. The **separate routed four-neuron recurrent-synapse bitstream was generated successfully** (`Bitgen Completed Successfully`, `write_bitstream completed successfully`, Vivado bitgen reports 0 errors/critical warnings/warnings). All **12/12 original evidence SHA256 rows returned OK**. The owner-native evidence folder is **`~/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO`**, with `bitstream_candidate/m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit`. The native gate deliberately returned **exit 2**, `D3D2B_NEW_DRC_REVIEW_REQUIRED`, because the **first new design's report contains seven DRC findings**. Neither the actual DRC report detail, bitstream SHA256 value nor routed WNS/WHS/TNS/THS was included in this supplied extract. **DO NOT call the bitstream broken, accepted, or physically programmed. DO NOT rebuild it yet.** Preserve original evidence and original failed acceptance output without alteration.

**Exact next read-only owner commands (no Vivado, no JTAG, no new bitgen):**

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2b_synaptic_DakjdpCO"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
printf '\n===== ORIGINAL D3.D.2B DRC REPORT =====\n'
cat "$RUN/reports/20_route_drc.rpt"
printf '\n===== ROUTED TIMING SUMMARY =====\n'
grep -A 3 -m 1 'WNS(ns)' "$RUN/reports/21_route_timing.rpt"
grep 'All user specified timing constraints are met' "$RUN/reports/21_route_timing.rpt" || true
printf '\n===== ORIGINAL NATIVE BUILD METADATA =====\n'
cat "$RUN/reports/30_native_result.txt"
printf '\n===== ORIGINAL NEW BITSTREAM SHA256 =====\n'
sha256sum "$RUN/bitstream_candidate/m08_d3d2b_synaptic_lif_jtag_UNRELEASED.bit"
printf '\n===== ORIGINAL VIVADO FATAL DIAGNOSTICS =====\n'
grep -nE '^(ERROR:|CRITICAL WARNING:)' "$RUN/00_vivado.log" || true
```

**DRC review criteria before accepting this exact candidate:** compare all seven rule IDs, warning severities/counts, detailed instance paths, BRAM write-collision advisories, XSDB/debug-hub-only LUT notices, and the RTSTAT net-count and sampled paths. Their coincidence with prior D3.D.2A's seven warnings is *insufficient* for waiver; a genuinely new synaptic RTL hierarchy or unreviewed nonvendor path must be investigated. Independently verify positive setup/hold timing at the constrained 100 MHz PL clock and correct new image/source hashes. Only then update `m08_d3d2b_synaptic_gate.py` with an **exact owner-original bitstream SHA256/size, RTL+builder hashes and scoped DRC allowlist**; run the read-only gate on the **same** evidence directory and complete its tests. No original receipts or bitstream may be edited. If genuine routing/neural critical findings are present, diagnose design and generate a separate new run, retaining this first attempt.

**Architecture boundary before D3.D.2C:** D3.D.2B supports four neurons, eight directed synapses, four logical ticks and positive delays 1–3. Its arrays and address map are hard-coded for that scope. The **M06 32-neuron ×4-tick physical reference is a NEW D3.D.2C hardware design**, not a property of this existing bitstream and not yet verified. First close D3.D.2B *physical* recurrent-synapse parity using the accepted original D3.D.2B image, then specify 32-neuron state storage, synapse/event capacity and addressing, scheduler, and exact M02/M06 network oracle for separate RTL/native/physical gates.

### Earlier pre-native test plan (historical)


**Current: SOURCE/RTL CANDIDATE + PHYSICAL TEST HARNESS CREATED; GENUINE OWNER D3.D.2B NATIVE ROUTE/DRC/IMAGE AND BOARD EXECUTION NOT YET ACCEPTED.** This is a *new* staged development branch, not an update to the independently accepted previous bitstream.

## Prior accepted physical baseline

At 2026-11-20 00:02–00:03 MST the owner's first-attempt D3.D.2A original JTAG run physically PASSED: `xck26_0`, programming startup HIGH, `hw_axi_1`, BRAM echo `55AA22DD`, v2 magic/version, two different 4-neuron ×4-tick M02 workloads with **32/32 voltages and 32/32 spike decisions exact**, six original SHA ledger entries OK, independent `M08_D3D2A_PHYSICAL_FOUR_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED`, exit `0`. Immutable owner evidence: `~/Thesis_Evidence/M08/m08_d3d2a_four_HW_UBi3VCax`; native original `~/Thesis_Evidence/M08/m08_d3d2a_four_w4YfdBuE`; bit SHA256 `3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411`. Do not alter or rebuild those runs. These physically tested **independent** neurons only; no physical synaptic networking has yet been demonstrated.

## D3.D.2B distinct hardware hypothesis

The FPGA must compute the *connection-weight contribution* itself from **previous ticks' actual spike records**, rather than accepting that contribution from the PC. For each neuron n and logical timestep t, the new signed16 LIF engine computes:

`I_syn(n,t) = sum_{edges e=(pre,n,w,d): 1<=d<=3 and t>=d and spike(pre,t-d)} w`, then `V_next=clamp16(trunc_zero(D_num*V_previous/D_den)+bias+I_external+I_syn)` followed by inclusive threshold and reset. All 4 neurons update every tick; no same-tick delivery or wraparound of spikes beyond the 4-tick horizon. Signed weights may be negative, parallel edges may cancel, recurrent and delayed self edges are legal. Accumulate in signed64, *saturate once* at final LIF update. Capacity exactly four neurons, 4 ticks, at most eight directed edges, delay 1..3, decay modes 0,1/2,1. Neither full M06 32-neuron engine nor DDR/PS-clock independence is claimed.

### New isolated AXI-Lite ABI at 0xA0001000

| Offset | Access | Meaning |
|---|---|---|
| `0x000`,`0x004` | R | New magic `0x4D34534E` (`M4SN`), version `0x00030000` |
| `0x008`,`0x00C`,`0x010` | R,RW,RW | DONE bit0/BUSY bit1; nonzero nonce; global decay mode 0,1,2 |
| `0x014`,`0x018`,`0x01C`,`0x020` | W,R,R,RW | START=1; completed nonce; monotonic run count; synapse count 0..8 |
| `0x040+0x020*n` | RW | n=0..3: initial, bias, threshold, reset, external currents tick0..3 (eight words) |
| `0x100+0x020*n` | R after DONE | n=0..3: four signed16 voltage words then 4-bit spike mask (five words) |
| `0x200+0x010*e` | RW | e=0..7: `pre`, `post`, signed16 `weight`, positive `delay` (four 32-bit words) |
| `0x300+0x010*n+0x004*t` | R after DONE | **Hardware-computed delivered synapse sum** n=0..3,t=0..3, signed32 (16 words) |

Reject out-of-range neuron IDs, missing/zero/too-long active edge delay, non-sign-extended weights/parameters, partial strobes, misalignment, malformed START, writes while BUSY, and any host attempts to write output traces. Result windows are read-only; data before DONE is not accepted. Restore all state and spike history on new valid START. Preserve D3.C JTAG–AXI–BRAM at `0xA0000000`, PS HPM masters disabled, original isolated 256-cycle fabric POR and TTC0 EMIO fan A12.

## Golden workload acceptance

`scripts/m08_d3d2b_synaptic_vectors.py` uses both **actual independent M02 dense and event-queued** evaluators and separately fixed hand-calculated voltages, spike masks and synapse sums; `rtl/m08/tb_m08_d3d2b_synaptic_lif_axil.sv` drives the real AXI RTL in Icarus. The physical Tcl compares all 32 voltage words, 32 individual spike decisions represented by eight four-bit masks and 32 actually delivered-current words. Two 4-neuron, 8-synapse, 4-tick networks:

| Workload | Neuron spike masks | Key synaptic behavior |
|---|---|---|
| `chain_recurrent` | `[1,2,4,8]` | Spike propagates 0→1→2→3 with delay1; positive/negative parallel two-tick edges cancel; 1→1 self delay2; 3→0 delivery past horizon ignored |
| `inhibition_half_decay` | `[1,10,4,8]` | Negative weight 1→0, 0→2 opposite parallel weights cancel, 1→1 self delay2, quiet-neuron negative truncation and autonomous bias spiking |

Verify *delivered current* separately from voltage: e.g. first case neuron1 tick1 receives 4, neuron2 tick2 receives 5 after +2/−2 cancellation, neuron0 tick3 receives −3, and neuron3 tick3 receives 4. Second case neuron2 tick1 receives 0 after +6/−6 cancellation, neuron0 tick2 receives −4, neuron1 tick3 receives +4, neuron3 tick3 receives +10. A design that merely returns host-provided aggregated currents is noncompliant.

## Owner Step A — local PC source + actual RTL simulation (NO BOARD)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2b-synaptic-routing
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2b-synaptic-routing
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_m08_d3d2b_synaptic_gate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2b_synaptic_physical.py' -v
python3 scripts/m08_d3d2b_synaptic_gate.py --source-only
bash -n scripts/run_m08_d3d2b_synaptic_pc.sh
bash -n scripts/run_m08_d3d2b_synaptic_physical_once.sh
```

Do not advance on source/RTL error. M02 reference and Icarus simulation must agree with frozen independent anchors.

## Owner Step B — genuinely NEW Vivado 2025.2 route/bit candidate (PC ONLY)

After A passes, the dedicated runner creates a fresh `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_XXXXXXXX` folder, new BD and RTL, all original route/DRC/timing reports, separate new UNRELEASED `.bit` and exactly twelve SHA files. It performs no programming.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_d3d2b_synaptic_pc.sh
```

**Preserve the FIRST genuine owner result**, even if the native gate returns `D3D2B_NEW_DRC_REVIEW_REQUIRED` or fails routing. Do not automatically rerun bitgen. Unlike D3.D.2A, the new design's DRC warnings are not reviewed yet: the gate initially accepts **only zero** findings. Owner-original new DRC/timing/log/SHA output must be inspected before a narrow, image-specific candidate authorization. The hardware runner is staged in the repository but its new native gate will STOP programming unless the genuinely new owner candidate has passed.

## Step C — first actual physical synaptic JTAG verification (AFTER NEW NATIVE ACCEPTANCE ONLY)

`scripts/run_m08_d3d2b_synaptic_physical_once.sh <accepted-native-dir>` performs one explicit owner-armed JTAG program with a distinct accepted original bitstream, runs the preserved BRAM echo and new peripheral ID checks, then writes **only external current and edge parameters**, STARTs two networks and reads 32 membrane voltages, eight spike masks and 32 hardware computed synaptic-current words. It creates separate `m08_d3d2b_synaptic_HW_XXXXXXXX` evidence with six SHA entries and independently calls `scripts/m08_d3d2b_synaptic_physical_audit.py`. The physical command is intentionally **not** the next action until new native gate passes; never reuse the D3.D.2A bitstream. Keep independent cooling, UART and recovery observation. No automatic reprogramming or retry.

Acceptance: `M08_D3D2B_PHYSICAL_RECURRENT_SYNAPTIC_ROUTING_M02_PARITY_ACCEPTED` with hardware delivered-current, voltage and spike parity. This is real recurrent synapse networking for the **bounded 4×4×8 case**, not full M06. D3.D.2C 32×4 and D3.D.3 DDR remain future. M08 OPEN; M09 PLANNED; PR stack draft/unmerged.
