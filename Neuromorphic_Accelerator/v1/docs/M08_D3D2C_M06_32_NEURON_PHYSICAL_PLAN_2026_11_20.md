# M08 D3.D.2C — real M06 32-neuron ×4-tick FPGA neural workload (staged; NO BOARD)

**November 20, 2026; new stacked branch based on documented D3.D.2B physical PASS.**

## Why this is a distinct hardware milestone

D3.D.2B original physical owner receipt `~/Thesis_Evidence/M08/m08_d3d2b_synaptic_HW_Pw3KKKXl` independently accepted two four-neuron/eight-edge recurrent networks: **32/32 membrane voltages, 32/32 spike decisions and 32/32 hardware-derived synaptic currents** matched M02; one-shot JTAG, six physical hashes, exit 0. Original bit SHA256 `dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14`. **Do not rebuild or reprogram that image.**

D3.D.2C is NEW RTL and a NEW image: 32 stateful signed16 LIF neurons, four ticks, the **actual accepted M06 G3.3 32×4 fixture**, not an invented larger 4-neuron fixture. In `scripts/m06_generate_paged_lif16_vectors.py` and `scripts/m06_g3_3_m02_m03_owner_vectors.py`, the workload has **five signed recurrent synapses (including cross-half and self delays), 17 signed input events, 3/4 truncation-toward-zero decay**, 32 logical neurons and 4 ticks. M06 G3.3 already accepted this workload in *offline* original-HLS+AMD XSim and one-slot **simulated** canonical memory; no M06 32-neuron physical RTL or DDR was previously proven.

## D3.D.2C phase 1 implementation (PC SOURCE/RTL STAGED, NO OWNER NATIVE BUILD)

- `rtl/m08/m08_d3d2c_m06_32_lif_axil.v` — distinct `M32N` v4 AXI4-Lite peripheral; 32 neuron banks, four logical ticks, eight configured signed16 directed edges (five used by original M06), delay 1..3, signed64 summed inputs, saturate once to signed16, threshold-spike/reset and full hardware-generated synaptic currents. One neuron update per fabric clock. Reentrant START clears all 32 state/history/traces and increments completed run_count.
- `scripts/m08_d3d2c_m06_vectors.py` — imports the **existing** original M06 G3.3 `fixture_oracles()` and thereby requires independent M02 dense/event and M03 exact sparse agreement, then derives the exact expected per-tick voltage, spike masks, and independently counted delayed synaptic current words.
- `rtl/m08/tb_m08_d3d2c_m06_32_lif_axil.sv` — real Icarus clocked RTL/AXI simulation reading a unique 579-word M06 hex golden: 32×4 voltages (128), 32×4 spike decisions (128), 32×4 delivered synaptic current values (128), plus nonce/status/run_count and negative invalid-IDs/zero-delay/unextended-weight/partial-write/early-readback cases. Runs twice with distinct nonces and checks a cleared state/replay.
- `scripts/m08_d3d2c_m06_gate.py`, `tests/test_m08_d3d2c_m06_32_source.py` — source-only checks including genuine Icarus when installed. A synthetic pass is not a physical/native result.
- `scripts/m08_d3d2c_m06_build.tcl` and `scripts/run_m08_d3d2c_m06_pc.sh` — separate owner-PC Vivado 2025.2 **offline** candidate builder with exact K26 part, dual 4KiB JTAG address windows, PS HPM masters disabled, fabric 256-cycle POR, TTC0 EMIO fan A12, original 12-file SHA evidence and Vivado timing/DRC reports. It does **not** connect to or program the board.
- `scripts/m08_d3d2c_m06_native_review.py` — first new image SHA and metadata/timing/DRC reporter. **ALWAYS exits nonzero / image not released** until new original owner DRC, new bitstream SHA, source hashes, and timing are separately reviewed and narrowly authorized. No inherited seven-warning waiver from D3.D.2B.

### Important scope limitation: external-event coalescing

The **17 M06 external current events are aggregated by the Python golden/host into 32×4 signed32 input-current registers**. The FPGA independently computes every delayed recurrent current from its own previously emitted spikes. This confirms original M06 **neural arithmetic and recurrent routing** for a bounded 32×4 workload, but NOT physical ingestion/ordering of the 17 individual external events, original M06 HLS engine equivalence, M03 sparse evaluation-skip behavior, DDR/page-state residency, stream protocol, memory/page eviction, PS clock independence, or Linux-owned integration. Preserve this distinction in any physical-paper claim. Sparse M03 traces agree for the reference, but RTL evaluates all 32 neurons per tick.

## New 4 KiB peripheral ABI (relative to 0xA0001000)

| Region | Offsets | Register contract |
|---|---|---|
| Header | `0x000-0x020` | `M32N` magic `0x4D33324E`, v4 `0x00040000`, status, nonce, 0/half/one/three-quarter decay mode, START, DONE nonce, monotonic run count, edge count 0..8 |
| Neurons | `0x100+32*n+4*j` | `n=0..31`, `j=0..7`: initial, bias, threshold, reset, preaggregated external current t0..t3 |
| Edges | `0x500+16*e+4*j` | `e=0..7`, `j=0..3`: pre, post, signed16 weight, positive delay 1..3 |
| Voltage and spike mask results | `0x900+32*n+4*j` | `j=0..3` four signed16 voltage words, `j=4` four-bit tick spike mask; only accessible after DONE |
| Fabric-computed synaptic currents | `0xD00+4*(4*n+t)` | `n=0..31,t=0..3`, signed32 delivered recurrent-current words; only accessible after DONE |

The JTAG-only BRAM echo remains `0xA0000000`. New physical identity is **different** from D3.D.2B `M4SN`. All active synapses require valid neuron IDs and delay ≥1; AXI writes require full strobe and are blocked BUSY. No DRAM/LINUX MMIO access.

## PC-only owner replication (no Vivado needed for first part)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2c-m06-32-neuron
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_32_source.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2c_m06_native_boundary.py' -v
python3 scripts/m08_d3d2c_m06_gate.py --source-only
bash -n scripts/run_m08_d3d2c_m06_pc.sh
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

**STOP** if any test fails. Icarus without `iverilog`/`vvp` is SKIP, not accepted RTL parity.

## Proposed next owner-PC native gate — only after source/CI verification

**This command is optional offline synthesis/routing on the owner PC and must be run separately. It does not program the KV260.** Do **not** run the D3.D.2B builder again.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_d3d2c_m06_pc.sh
```

Expected after a successful bitgen: NEW, distinct `~/Thesis_Evidence/M08/m08_d3d2c_m06_XXXXXXXX` folder, **12 original SHA entries**, new routed DRC/timing reports, original new `m08_d3d2c_m06_lif_jtag_UNRELEASED.bit` and a **deliberate native-review-required exit 2**. This is a safety feature, NOT proof of a failed bitgen. Preserve the first stdout, timing, DRC report, bit SHA, utilization, original logs and receipts; do not rerun automatically. An actual negative-route/DRC or critical warning demands diagnosis, not waiver.

No JTAG programming command is authorized/staged at this source phase. The next development gate is new native routed-image review, SHA/RTL/builder source pinning, new timing/DRC classification (no inheritance), and only then a distinct one-shot owner-controlled physical readback/auditor with **128 voltages, 128 spike decisions, 128 delivered-synaptic-current words**. Independent external cooling, UART capture, exact K26 identity, stock recovery and no automatic retry remain mandatory. Keep M08 OPEN, M09 PLANNED and all stacked PRs drafts/unmerged.
