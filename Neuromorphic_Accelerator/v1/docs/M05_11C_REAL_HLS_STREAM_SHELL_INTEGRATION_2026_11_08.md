# M05.11c — Real generated HLS evaluation engine + AXI-Lite stream shell

**2026-11-08 · Active research branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` · **PR:** #79 DRAFT, not merged · **Stage:** first **full RTL boundary** exercise of the original signed32 HLS top with four new stream adapters and the new transport command bank.

**Status (as implemented):** Testbench, provenance-checked Vivado XSim runner, and raw 256-bit accepted-handshake replay added. Host Python tests are synthetic. **REAL M05.11c XSIM RESULT IS PENDING OPERATOR RUN**. No DMA IP, PS, DDR, actual register-mapped MMIO driver, physical FPGA, full-system place/route or new bitstream. Do not promote this gate before the operator submits `exit_status=0` and both independent simulator + replay PASS markers.

This document extends [three-question PS/PL transport ADR](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md), [custom AXI-Lite register map and session controller](M05_11B_AXIL_SESSION_CONTROL_2026_11_08.md), [host-side execution controller protocol](M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md), and [numerical evaluation engine history](M05_EVALUATION_ENGINE_EVOLUTION.md). Maintain all dated evidence, performance limits and functional details through future revisions, never overwrite original evidence folders.

## 1. Exact verified starting point — owner M05.11b XSim acceptance

The user performed **genuine Vivado Simulator 2025.2** testing on checkout `90c31f05a40603914fed507b7f9507220df4d932`, original proof folder:

`~/Thesis_Evidence/neuromorphic_v1_m05_11_axil_20261108T230817Z_HFWBlw`

- `exit_status=0` and the original SHA256 file manifest:
  - `m05_11_axil_session_controller.v` = `c709a4a88660836f706ed6cb7638b7945fe998033a8b4b4246a0c82561d02e7e`;
  - `m05_11_stream_shell.v` = `daeff77d7bc29c819e1524c1c78ddcb85b248b03db8642406c11bedde7fc89a4`;
  - trace packetizer = `f7a75d811a3dddda6103bd8a92e6789ac69b75bb9b94002cf5784c4a83ff0758`;
  - input unpad = `347cc09b05e15422d5741cbd5d20977d4720135c6c2c99f3ccf7536e91e0645c`;
  - AXI-Lite standalone SV bench = `d02e0cc094a906591ed2a62eb193cee7ced369116704173424324de3afd6b`;
  - runner = `20742ed750001a5847a0d712878ee80da10dd19683f6a37ae8eb7f95adf24175`.
- Actual `xvlog`/`xelab` produced an AXI-Lite snapshot and genuine `xsim` PASS at simulated 2,730 ns: `PASS: M05.11b AXI-Lite separated AW/W, persistent R/B backpressure, session START/FINISH/ACK, failure quarantine and clean restart`.
- Vivado warned `[XSIM 43-3431] LIBRARY_PATH` about a nonstandard compiler environment but completed normally; this was not an observed functional failure.
- This proves **standalone command-bus RTL and simulated bridge-status sequencing only**. The earlier M05.11a standalone input/output shims also passed genuine Vivado XSim. **Neither result alone was a full connection to the original HLS engine.**

## 2. System now connected in the new M05.11c test

```text
Testbench “PS” (two independently driven AXI-Lite banks and 256b streams)
         |                                    |
   Vitis-generated HLS AXI-Lite     NEW M05.11b AXI-Lite bank
   neuron_count, synapse_count,    session, input counts, START,
   external_count, ticks,          FINAL_STATUS/FINISH/ACK,
   decay, ap_start/ap_done/return   observed counters/faults
         |                                    |
         V                                    V
  +------------------------+       +------------------------------+
  | ACTUAL generated        |<----->| m05_11_stream_shell          |
  | m05_rolling_replay RTL  |       | 3 × 256→128/192 input unpad |
  | ORIGINAL signed32       |       | 192→256 trace+TLAST footer   |
  | 8-slot temporal wheel   |       | AXI-Lite session FSM         |
  +------------------------+       +------------------------------+
         ^  HLS native ports                 ^
         |                                   |
         +--- 3 individual 256-bit input packet sources in testbench
                  1 × 256-bit output sink with deliberate TREADY stalls
```

The testbench is [`rtl/m05_11/tb_m05_11c_real_hls_shell.sv`](../rtl/m05_11/tb_m05_11c_real_hls_shell.sv). Both instances (`m05_rolling_replay hls_dut` and `m05_11_stream_shell shell_dut`) are explicitly instantiated in **one clock domain**. The original HLS generated RTL **does not need to be rewritten, resynthesized or repackaged** for this test.

The old accepted HLS top AXI-Lite address map is extracted **from its actual generated Vitis driver**, by `m05_axis_regmap.py` against the prior valid `--impl` source. The **new custom session bridge** has separately documented fixed register offsets (0x00 command, 0x04 state, 0x08/0x0c ID, 0x10 expected trace rows, 0x14..0x1c 3 input counts, 0x20 final status, 0x24..0x30 observed counters, 0x34 flags, 0x38 version). **Do not confuse those two address spaces**; real PS physical base addresses are not assigned yet.

## 3. Two consecutive generated-HLS transactions, no fabric reset between

### Run 0 — genuine successful neural inference through the shims

- Two neurons with threshold5/reset0/bias0; one synapse neuron0→neuron1, weight+5, delay8; one external event at tick0 to neuron0 with current+5; 12 logical ticks.
- Encode three input packets to fixed **32-byte** padded TDATA; input TLAST exactly at last respective input packet. The new shell strips padding and TLAST and presents original 128/192/128-bit native HLS words.
- Hardware must generate **exactly 24 true neural trace records**, with neuron0 spike at tick0 and neuron1 recurrent spike at tick8. Each trace output beat is converted to **256-bit** TDATA with TKEEP=0xFFFFFFFF; 24 data beats have TLAST=0.
- PS testbench reads actual generated HLS `ap_done`/`ap_return` from its independent AXI-Lite register bank. Must return **status0**. Only then issue **FINISH** to custom session AXI-Lite bank, causing **exactly one 256-bit metadata footer** with matching 64-bit session ID `0x0102030405060708`, status0, count24 and TLAST=1.
- Custom bridge must reach state **COMPLETE=3** with matching observed output and input counters (24 / 2,1,1). Only then testbench acknowledges success (`COMMAND=4`) and verifies IDLE.
- Testbench logs `M05_11C_COMMIT run=0 accepted_rows=24`. This models a validated commit outcome in the *simulated* PS receiver, not actual DDR atomic publication.

### Run 1 — real late HLS failure and guaranteed reject of partial trace

- **Same HLS and shell instances, no intervening `ap_rst_n` or `rst_n` pulse.**
- Replay original proven intentionally malformed external stream tick order **0,4,3**, with same neurons, 1 delay8 synapse, 12 ticks. The HLS top must really return **`BAD_EXTERNAL=4`** after 4 ticks of valid output.
- Exactly **8 provisional neural trace beats** (t0..3, 2 neurons each), then **one** terminal 256-bit footer/TLAST, session ID `0x1020304050607080`, hardware status4, row count8.
- The new command controller must move to **FAULT=4**; success ACK and subsequent START both return AXI-Lite **SLVERR**. The host may publish **zero** of those eight rows, and no trace beat may leak after the terminal footer.
- This is an intentionally **failing inference that must PASS the failure-path test**, not a random simulator error. A true timeout or missing footer must fail the XSim gate.

### Deliberate backpressure and order checks

The output DMA sink drives TREADY high one cycle in seven. The end-to-end test verifies TDATA/TVALID/TLAST/TKEEP remain unchanged under stall, that actual neural trace semantics are exact for every tick and neuron, and that **backpressure propagates through the packetizer into real HLS trace TREADY**. The source models hold input VALID and TDATA until handshake; separate original input counts are checked at both DMA face and the new bridge MMIO observed counts.

## 4. Independent read-only accepted-TDATA transcript audit

Rather than reconstructing expected rows from the oracle and claiming they came from RTL, the SystemVerilog bench prints **the actual accepted 256-bit DMA-facing handshakes** as `M05_11C_DMA run=<0|1> data=<64 hex> last=<0|1> keep=<8 hex>`.

**C struct padding boundary:** 16 non-semantic HLS output bits at [159:144] may be uninitialized/X in RTL. The testbench checks every **semantic** bit is known, then normalizes *only those 16 padding bits to zero* for conversion to a portable 32-byte transcript. All neural values, footers, output counts, session IDs, status and TLAST are the actual checked hardware-transfer values; this normalization is explicitly **not** a claim to have preserved unspecified C padding bits.

[`scripts/m05_11c_replay.py`](../scripts/m05_11c_replay.py) decodes each raw 256-bit (normalized-padding) hex word **little-endian** and feeds the resulting real-XSim packet bytes into the unchanged [`accept_dma_frame`](../src/neuromorphic_accelerator_v1/m05_dma_frame.py), which itself feeds `RollingTraceCommitGate`.

- Must see exactly **25** 32-byte handshake words in run0, with one terminal TLAST, status0/24/ID, **24 committed**.
- Must see exactly **9** handshake words in run1, including terminal TLAST, status4/8/ID, **0 committed**.
- Reject wrong/missing TLAST, unexpected TKEEP, wrong 32-byte count, missing/duplicate/inconsistent run marker, wrong final status, invalid neural trace, stale session ID, extra output or a simulator fatal.
- The script saves `05_dma_frame_replay.log` alongside the genuine Vivado logs. **Synthetic native tests** for this replay are deliberately marked native, not real RTL.

**This remains an OFFLINE simulated PS capture.** The real Linux PS DMA transport has not certified TLAST, DDR cache, actual transfer length or quiescence. The dummy arguments passed to the native decoder are valid **only within this already waveform-verified isolated simulation**, not as evidence of DMA hardware.

## 5. Provenance-checked user-operated XSim runner

[`scripts/run_m05_11c_hls_shell_xsim.sh`](../scripts/run_m05_11c_hls_shell_xsim.sh) accepts only the original authentic **K26** M05 rolling `--impl` evidence, expected:

`~/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026`

The runner refuses an invalid top/part/`exit_status`, refuses HLS source changes relative to its original SHA256 manifest, and requires the original `work/hls/syn/verilog/m05_rolling_replay.v` and sibling RTL. It stages exact original eleven Vitis-generated RAM `.dat` files with proven manifest and builds a fresh original evidence folder:

`~/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_<UTC>_<unique>/`

It regenerates the **actual HLS-only register-offset SV header** from existing driver, compiles generated HLS modules + four new RTL modules + M05.11c bench, elaborates, runs actual XSim and executes the independent Python transcript audit. **Any** simulator fatal, missing RAM image, nonzero process result, absent PASS marker, or failed transcript validation fails the whole gate.

This **does not** use hardware, re-run Vitis HLS synthesis, invoke Vivado implementation, or replace earlier evidence logs. The only new files are unique to a fresh evidence folder.

## 6. Reproducible operator commands (Vivado 2025.2 sourced)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

# Host-only tests, not generated Verilog:
python3 -m unittest discover -s tests -p 'test_m05_11c_hls_shell.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -v

# Actual original signed32 HLS Verilog, new shell, Vivado 2025.2 XSim:
export ROLL_IMPL="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026"
bash -n scripts/run_m05_11c_hls_shell_xsim.sh
bash scripts/run_m05_11c_hls_shell_xsim.sh "$ROLL_IMPL"

export SHELL_EVIDENCE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_* | head -n 1)"
echo "$SHELL_EVIDENCE"
cat "$SHELL_EVIDENCE/result.txt"
cat "$SHELL_EVIDENCE/commit.txt"
cat "$SHELL_EVIDENCE/source_impl_evidence.txt"
cat "$SHELL_EVIDENCE/01_ram_init.log" 2>/dev/null || true
tail -n 60 "$SHELL_EVIDENCE/02_xvlog.log" 2>/dev/null || true
tail -n 60 "$SHELL_EVIDENCE/03_xelab.log" 2>/dev/null || true
tail -n 120 "$SHELL_EVIDENCE/04_xsim.log" 2>/dev/null || true
cat "$SHELL_EVIDENCE/05_dma_frame_replay.log" 2>/dev/null || true
```

If it fails, **do not change the verified HLS source or relax test assertions**. Diagnose separately whether the new SV bench has a scheduling/clock-edge bug, bridge register/state logic does not respect an authentic HLS AXI control signal, or the transport shell has a real backpressure/ordering issue. Keep original logs; adjust *only* the new shell/testbench if justified, with native CI and re-run the full genuine XSim gate.

## 7. Explicit remaining acceptance boundaries

| Milestone | Target | Required independent evidence | Status |
|---|---|---|---|
| **M05.11a** | Stream ingress and trace footer independently | User's genuine Vivado XSim both tests | **VERIFIED 2026-11-08** |
| **M05.11b** | Custom AXI-Lite control slave independent | User's genuine Vivado XSim bus test | **VERIFIED 2026-11-08** |
| **M05.11c** | Original HLS RTL *with* 4 new shims, 2 AXI-Lite banks and end-to-end final trace | Real Vivado XSim success+late error, raw packet audit and source checks | **PENDING operator** |
| **M05.12** | Real PS DMA integration/descriptor lifecycle, full clock/reset/CDC, AXI-Lite base addresses, true quiescence | Native + integrated VIP/RTL + full block design | PENDING |
| **M05.13** | Whole-system routed timing and actual physical K26 operations | Operator authorization and physical evidence | PENDING |

Earlier signed32 **6.503 ns OOC** timing is for the neural HLS IP only and must **not** be called full PS/PL clock closure. The user has not authorized physical FPGA deployment. M05 OPEN, PR #79 DRAFT/UNMERGED.
