# M08 D3.D.2A — four independent signed16 LIF neurons × four ticks

**STATUS (2026-11-19): new source/RTL and native PC-only candidate workflow CREATED; owner Icarus, genuine native Vivado, and physical parity PENDING.** The accepted D3.D.1 one-neuron FPGA remains immutable.

## Objective and computational boundary

The first step toward physical M06 32-neuron ×4-tick parity is FOUR distinct hardware-stateful signed16 neurons, FOUR clocked logical ticks each, independent state/threshold/reset/bias, externally summed signed32 per-neuron currents. Computation is tick-major: neurons 0–3 are updated for tick0 before tick1. Every neuron updates each tick even with zero current. No synapse routing, recurrent delay, M06 HLS integration, AXI streams, DDR paging or measured throughput are claimed in D3.D.2A.

## FPGA register map

New isolated peripheral at AXI-Lite base 0xA0001000, alongside D3.C preserved 4KiB BRAM at 0xA0000000, on nominal PS pl_clk0 100MHz and 256-cycle fabric POR. PS HPM masters remain disabled; fan TTC0 EMIO to A12 retained. Each 32-bit access must be word-aligned.

| Offset | Access | Description |
|---|---|---|
| 0x000 / 0x004 | R | Magic 0x4D344C46 (M4LF), version 0x00020000 |
| 0x008 | R | DONE bit0, BUSY bit1 |
| 0x00C / 0x010 | RW | Nonzero caller nonce / global decay mode {0,1,2} for {0,1/2,1} |
| 0x014 / 0x018 / 0x01C | W/R/R | START=1 / completed nonce (after DONE) / completed run count |
| 0x040 + 0x020*n | RW | For n=0..3: eight 32-bit words, signed16 initial/bias/threshold/reset followed by four signed32 currents, t=0..3 |
| 0x100 + 0x020*n | R after DONE | For n=0..3: four hardware voltages as signed-extended words and a four-bit spike mask |

Parameters must be full-word WSTRB and signed-extended, threshold >0 and reset < threshold; invalid writes/start reject. Host cannot write trace outputs; outputs before DONE reject. State is explicitly reset to per-neuron initial values at each accepted START. 16 real LIF updates occur over 16 fabric clocks, with M02 signed rounding, full-add then one saturation, inclusive threshold and reset.

## Independent reference fixtures

scripts/m08_d3d2a_four_vectors.py calls BOTH the actual M02 dense and M02 queued evaluator, requires equality, then verifies frozen hand-reviewed numeric anchors. Two four-neuron ×4-tick workload cases:

- independent_half_decay: voltages [[2,-2,-4,-1],[-5,-32768,-16386,-8195],[3,4,-1,3],[-1,-1,-1,-1]], spike masks [2,1,0,0].
- independent_unit_decay: voltages [[3,0,-3,0],[-5,-32768,-32768,-32768],[-1,-2,-5,-4],[-2,-3,-4,-5]], spike masks [2,1,2,0].

RTL testbench: rtl/m08/tb_m08_d3d2a_four_lif_axil.sv. Source + Icarus tests: tests/test_m08_d3d2a_four_gate.py. Neither source/CI nor PC native tests constitute physical proof.

## Owner Step A — PC-only source/RTL verification

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2a-four-neuron
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2a-four-neuron
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_m08_d3d2a_four_gate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d_neuron_gate.py' -v
python3 scripts/m08_d3d2a_four_gate.py --source-only
bash -n scripts/run_m08_d3d2a_four_pc.sh
~~~

If these tests fail, preserve the first error; do not advance to native bitgen or board.

## Owner Step B — new genuine native Vivado 2025.2 (PC-only; NO BOARD)

After source/RTL pass, the separate owner PC-only builder uses a NEW exclusive m08_d3d2a_four_XXXXXXXX directory under ~/Thesis_Evidence/M08, retains builder/RTL/POR copies and all Vivado report hashes, and generates a distinct m08_d3d2a_four_lif_jtag_UNRELEASED.bit.

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_d3d2a_four_pc.sh
~~~

Capture the printed M08_D3D2A_FRESH_PC_EVIDENCE_DIR and original Vivado exit, DRC, timing and SHA. The new gate rejects ALL new DRC warnings until exact owner-original new reports can be reviewed: D3.D.1's seven reviewed vendor/debug warnings DO NOT automatically transfer to this design. No source change or native failure permits reusing the old accepted bitstream, rewriting evidence, or programming the board.

## Next physical operation (gated; NOT implemented/authorized as a new image yet)

After a separately verified new offline candidate, implement and source-review one-shot physical owner JTAG readback + independent auditor, using the new exact image SHA: one K26 program, BRAM echo regression, new M4LF/version identity, two genuine four-neuron runs and comparison of ALL 32 hardware-voltage words / eight neuron-specific spike masks against M02, completed nonces and run counts, distinct SHA ledger and original UART/cooling evidence. No automatic retry. This step is required before claiming D3.D.2A physical acceptance.

Afterward: D3.D.2B positive-delay recurrent synapse routing; D3.D.2C physical 32×4 M06 reference; D3.D.3 separately protected DDR/paged integration; M09 quantitative comparisons. M08 stays OPEN; draft PR stack unmerged.
