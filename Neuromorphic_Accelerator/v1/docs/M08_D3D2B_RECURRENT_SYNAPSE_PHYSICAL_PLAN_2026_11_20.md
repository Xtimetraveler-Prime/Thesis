# M08 D3.D.2B — first genuine recurrent on-FPGA synaptic routing

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
