> **M05.11c LATEST (2026-11-08):** Owner **genuine Vivado 2025.2 M05.11b AXI4-Lite controller XSim PASS** `exit_status=0` on checkout `90c31f05a40603914fed507b7f9507220df4d932`; original `~/Thesis_Evidence/neuromorphic_v1_m05_11_axil_20261108T230817Z_HFWBlw`, actual AW/W stagger, R/B backpressure, START/FINISH/ACK, FAULT + verified reset. **M05.11c developed (NOT YET operator XSim verified):** real original Vitis-generated signed32 `m05_rolling_replay` Verilog plus current `m05_11_stream_shell` in one full RTL testbench with **two separate AXI-Lite banks**, 3 padded 256-bit input shims, one 256-bit S2MM-facing TLAST footer. Test two consecutive runs: valid 2-neuron/12-tick recurrent inference must stream **24 rows+1 footer**, hardware status0, COMMIT 24; deliberately unsorted external ticks 0,4,3 must stream **8 provisional+1 footer**, actual HLS status4, REJECT all, custom FAULT (no ACK). Output TREADY 1/7 cycles, exact row semantics and footer counts/session IDs. New `scripts/run_m05_11c_hls_shell_xsim.sh` reuses immutable K26 --impl HLS RTL source + RAM init and regenerates actual HLS regmap, no resynthesis/board. `scripts/m05_11c_replay.py` replays **actual simulator-captured 256-bit handshake words** (16 undefined C padding bits explicitly normalized) through native `accept_dma_frame` and `RollingTraceCommitGate`; independent **14 synthetic native tests**. 231 named M05+91 M01–M04 =322 native tests; **no physical DMA/PS/DDR or new routed clock result**. [Full M05.11c engineering/verification runbook](M05_11C_REAL_HLS_STREAM_SHELL_INTEGRATION_2026_11_08.md); [M05.11b verified register protocol](M05_11B_AXIL_SESSION_CONTROL_2026_11_08.md); [canonical evaluation-engine evolution](M05_EVALUATION_ENGINE_EVOLUTION.md). M05 OPEN; PR #79 DRAFT UNMERGED; no physical board actions.
>

# M05.11b — AXI4-Lite Session Controller and PS Register Contract

**Created:** 2026-11-08 · **Branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` · **PR:** #79 DRAFT / UNMERGED. This is an additive transport interface increment. **The signed32 HLS neuron evaluation engine, its HLS-generated Verilog and all previously verified timing/evidence remain unchanged.**

**Documentation policy:** Append dated operator evidence, exact Git checkout, raw evidence path, relevant source digests, test results and limitations every time this interface advances. Treat Icarus, genuine XSim, HLS co-sim, OOC route and physical PS/PL integration as separate levels of proof. This document supplements [M05.11 three-question architecture](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md) and [M05.10 host controller design](M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md).

## 1. M05.11a acceptance — now *genuine Vivado XSim PASS*

Operator tested at checkout `b3385619b81bc43ee69a082a2f5c8af258e03696` using **Vivado Simulator v2025.2**. Original evidence is preserved at:

`~/Thesis_Evidence/neuromorphic_v1_m05_11_bridge_20261108T224957Z_AQzMlG`

The evidence contains `exit_status=0`, original `commit.txt` and five SHA256 source hashes. Actual `xvlog` / `xelab` / `xsim` PASS for **both independent RTL components**:

| Original test | PASS output | Scope |
|---|---|---|
| `tb_m05_11_packetizer.sv` | `PASS: M05.11 RTL packetizer 3 TLAST footers (success, zero-error, truncated-success); output_stalls=12; overflow quarantined` | 192→256-bit trace framing, TLAST terminal, 12 output stalls, overproduction fault |
| `tb_m05_11_ingress.sv` | `PASS: M05.11 RTL ingress 128/192-bit unpad, exact TLAST and zero-count; input_stalls=7; early-TLAST quarantined` | 256→128/192-bit input unpack, input VALID/READY stalls, exact LAST position, empty channels, malformed input |

The XSim warning `XSIM 43-3431` mentioned nonstandard `LIBRARY_PATH` environment, but elaboration, snapshots and both XSim executions succeeded. It does not establish S2MM DMA/DDR or the whole-K26 routed clock. **M05.11a is complete at its standalone *real XSim* acceptance level.**

## 2. What M05.11b adds

### New synthesizable source

| Path | Purpose |
|---|---|
| `rtl/m05_11/m05_11_axil_session_controller.v` | 32-bit AXI4-Lite register slave; independent AW/W buffering, sticky BVALID/RVALID, readback/configuration, start pulse, held finish request, status and quarantine |
| `rtl/m05_11/m05_11_stream_shell.v` | Structural single-clock composition: **one AXI-Lite control block + three 256-bit MM2S unpad bridges + one 256-bit S2MM footer packetizer**. The genuine HLS top is deliberately external and unchanged. |
| `rtl/m05_11/tb_m05_11_axil_controller.sv` | Directed RTL test of reordered AW/W channels, RREADY/BREADY stalls, register strobes, errors, start/finalize, failed session quarantine and subsequent success after explicit reset |
| `scripts/run_m05_11_axil_xsim.sh` | Safe operator-run Vivado 2025.2 XSim gate in an exclusive `~/Thesis_Evidence/neuromorphic_v1_m05_11_axil_*` directory; logs, original commit and SHA256 manifest |

### New host-side files

| Path | Purpose |
|---|---|
| `src/neuromorphic_accelerator_v1/m05_11_mmio.py` | Typed software client for the **new bridge register map ONLY**, explicit version/readback checks, start/finish handoff, zero-publication on failed statuses, and ACK only after independently verified full S2MM frame/ingress counts. Uses abstract `WordRegisterIO`; **not real PS MMIO**. |
| `tests/test_m05_11_mmio.py` | **14 synthetic host unit tests** for register map, session ID, start/finalize/ACK boundaries, MMIO readback/mismatch, external reset fence, HLS-done gating, DMA-attested publication and corrupt status. |

**Crucial boundary:** M05.11b currently controls **transport/shim sessions**, not the actual neuron kernel's AXI-Lite registers. The PS must operate TWO distinct AXI-Lite register banks: (1) this newly defined bridge bank, (2) the HLS bank generated by Vitis. Do **not** reuse these offsets for `m05_rolling_replay`; always discover the HLS bank from the actual generated `xm05_rolling_replay_hw.h` or control RTL and the Vivado address map.

## 3. Exact new register map (32-bit AXI4-Lite, byte offsets)

All accesses are 32-bit little-endian, byte-addressed; register addresses must be aligned to 4. The slave uses an 8-bit AXI-Lite **offset** port. The full physical PS bus address is not assigned yet and must come from a future Vivado Address Editor export.

| Offset | Name | Access | Meaning |
|---:|---|---|---|
| `0x00` | `COMMAND` | WO | Full-word writes, **onehot only:** `1=START`, `2=FINISH`, `4=ACK_SUCCESS`. Read/other values return SLVERR. |
| `0x04` | `STATE` | RO | `0 IDLE`, `1 RUNNING`, `2 FINALIZING`, `3 COMPLETE`, `4 FAULT`. Read has no side effect. |
| `0x08` | `SESSION_LO` | RW IDLE | Low 32-bit session ID |
| `0x0C` | `SESSION_HI` | RW IDLE | High 32-bit session ID |
| `0x10` | `TRACE_EXPECTED` | RW IDLE | Neurons × ticks, 1..65536 |
| `0x14` | `NEURON_BEATS` | RW IDLE | Neuron input packets, 1..1024 |
| `0x18` | `SYNAPSE_BEATS` | RW IDLE | Synapse packets, 0..4096 |
| `0x1C` | `EXTERNAL_BEATS` | RW IDLE | External event packets, 0..262144 |
| `0x20` | `FINAL_STATUS` | RW RUNNING | **PS-supplied actual HLS** return status 0..6; must read HLS `ap_done`/`ap_return` independently first |
| `0x24` | `TRACE_ROWS_OBSERVED` | RO | Number of HLS trace beats packetizer accepted |
| `0x28` | `NEURON_BEATS_OBSERVED` | RO | Number of neuron input beats delivered through unpad |
| `0x2C` | `SYNAPSE_BEATS_OBSERVED` | RO | Number of synapse input beats |
| `0x30` | `EXTERNAL_BEATS_OBSERVED` | RO | Number of external input beats |
| `0x34` | `FLAGS` | RO | bit0 packetizer footer handshaked; bit1 any shim packet/ingress fault; bit2 all three input shims done; bit3 finish pending; bit4 finish acknowledged |
| `0x38` | `VERSION` | RO | `0x0005110B`; driver refuses unexpected register maps |

Config writes accept independent `WSTRB` bytes, preserved until new write; commands require `WSTRB=0xF`. Invalid/misaligned addresses, invalid state transitions and unsupported writes return `BRESP=SLVERR (2)`. Read invalid/misaligned address returns `RRESP=SLVERR`.

**VERSION is a new custom bridge contract, not a source of HLS register offsets.** Each new revision changing these offsets must increment/version the map and update driver tests/docs.

## 4. AXI-Lite behavior and trust boundaries

- **Separate AWADDR/AWVALID/AWREADY and WDATA/WSTRB/WVALID/WREADY:** A single buffered address and a single buffered data response slot can arrive in either order, and cannot be reused until a BRESP is consumed. The slave never assumes address and data appear simultaneously.
- **Read channel:** one outstanding RDATA/RRESP; it retains both until RREADY, with no read-to-clear side effects in the new bridge. Read/write responses remain stable while stalled.
- **AWPROT/ARPROT:** declared in RTL (ignored for the currently unprivileged transport prototype). Security, privilege checks, Linux device permissions, AXI firewalls and SoC MMU setup are **not** part of M05.11b.
- **One-clock design:** all bridge and register signals share one synchronous reset and fabric clock. Real clock-domain crossing requires explicit AXIS CDC and reset synchronization later.
- **No interrupts implemented:** PS performs nonblocking status polling in this initial model. IRQ aggregation, CDC, and register-read side effects belong to later hardware integration.

## 5. Exact control-plane sequence

### A. Receive-first setup + START

1. Validate a frozen `RunPlan` and allocate per-port 32-byte packet buffers from M05.11a codec. Supply a unique 64-bit session ID. **Check all DMA error bits and verify old session isolation first**.
2. Read new bridge `VERSION=0x0005110B` and `STATE=0`. Configure session LO/HI, expected trace rows, and three source-beat counts. Read every register back. Invalid config/count or any bridge not ready makes the `START` write return SLVERR and **does not issue bridge start pulses**.
3. Arm PS S2MM destination **first**, with buffer `32*(N*T+1)`; arm nonempty MM2S input streams with `32*count` bytes and correct LAST. Zero-length streams skip their DMA descriptor.
4. Issue `COMMAND=1 START` to this new bridge. It emits a **single-cycle start pulse to all four bridges** and transitions to RUNNING.
5. Independently configure **Vitis-generated HLS AXI-Lite** counters, ticks and decay and issue **one** HLS `ap_start`. The bridge's START is **not** the HLS accelerator's ap_start.

### B. During the neural run

- Independently progress all active MM2S channels and the S2MM receive, interleaving with control reads. Never block awaiting `ap_done` before draining trace; a stalled trace output can keep the evaluator from finishing.
- Poll the **real HLS** generated AXI-Lite `ap_done` (which may be read-to-clear) and latch actual `ap_return`, not the new bridge `STATE`. The new bridge cannot determine neuron-specific errors by itself.
- On HLS terminal: write `FINAL_STATUS=actual_ap_return` in the new register bank and then write `COMMAND=2 FINISH`. The bridge latches the status and keeps `finish_valid` asserted until the packetizer can accept it. The packetizer emits one terminal footer with TLAST and the actual neural trace count/session ID.

### C. Success publication and ACK

- Receive actual DMA completion with correct `TLAST`, verify the **real transferred byte count**, cache synchronization, footer magic, session ID and independently observed HLS return, zero overflow/fault, full N*T trace and matching input beat counts.
- Confirm **transport quiescence**, including in-flight DDR writes, old DMA descriptors and FIFO entries (not merely `ap_idle`). Host parser `accept_dma_frame` validates packet length and the existing `RollingTraceCommitGate` accepts the **whole run or nothing**.
- Only after the new bridge reaches `STATE=3 COMPLETE` and its `OBSERVED` counts match validated input sizes does the typed host client permit `COMMAND=4 ACK_SUCCESS`. This transitions new bridge to IDLE, ready for the next session. ACK **does not** itself prove S2MM completion: the PS must establish it *before* issuing ACK.

### D. Hardware error, short success, DMA error or timeout

- If HLS returned a nonzero status, S2MM can still receive a footer/TLAST even for an empty or partial trace. All provisional trace rows are discarded. The bridge eventually transitions to `FAULT`; `ACK_SUCCESS` is denied, preventing silent restart.
- If HLS status0 but fewer than expected trace rows were produced, packetizer rewrites footer status to reserved `FRAME_MISMATCH`, controller faults and host rejects. Output overproduction prevents further DMA writes and holds a sticky shim fault until system reset.
- A timeout, CRC/corrupt packet, bus fault, incomplete S2MM or stale session likewise requires the broader controller's `FAULTED` state; do **not** attempt ACK or software-only “clear status.”
- Recovery must **stop/cancel/flush verified DMA traffic and ensure PS DDR writes are retired**, then apply coordinated fabric/shim/HLS reset and verify actual idle, finally clear host transaction ownership. M05.11b provides the **register-level policy**, not a completed physical DMA reset sequencer.

## 6. Newly verified simulation scopes and pending evidence

The **M05.11b directed SystemVerilog testbench** exercises the slave with fake bridge-ready/done/fault inputs:

- A full AXI4-Lite write response with **AW before W and W before AW**, with BREADY held low and BRESP stable.
- RVALID/RDATA/RRESP held through delayed RREADY.
- A 32-bit session ID split across two addresses, exact readback, and partial WSTRB byte update.
- Rejected misaligned accesses, rejected unconfigured START and START when bridges are not ready.
- Exactly one START pulse despite repeated/invalid command writes.
- FINISH held valid while trace bridge reports not ready; exactly one FINISH handshake.
- Nonzero HLS status **4** causes sticky FAULT; ACK and new START denied until reset.
- After coordinated RTL reset, a fresh session status0 with correct rows and ingress beat counts reaches COMPLETE; a single ACK restores IDLE.
- It does **not yet simulate an actual bus-connected HLS core or AMD AXI DMA**. The `m05_11_stream_shell` is separately compiled/elaborated from all four stream RTL modules to detect structural integration problems. Do not claim a full-system wrapper directed test from structural elaboration alone.

**Verification chronology:**
- M05.11a: genuine operator Vivado XSim **PASS**, path and commit above.
- M05.11b native Icarus: 32-bit AXI4-Lite bus test **PASS** and structural shell elaborates. Original CI run needed a **workflow-only correction** because it erroneously listed a shell script as Verilog and listed one RTL source twice. The corrected workflow then passed; none of the HLS algorithms were involved.
- M05.11b host typed MMIO: **14 new unit tests**, entirely FAKE register reads/writes (not a physical PS MMIO driver).
- **Genuine operator-run Vivado 2025.2 XSim M05.11b test remains PENDING** until user runs `scripts/run_m05_11_axil_xsim.sh` with original success logs. Code/testbench, changes to bridge, and next stages documented here.

## 7. Commands to repeat on the local workstation

Requires a current checkout, working Python environment, and **sourced Vivado 2025.2** for genuine XSim. No board, old HLS generated HDL rebuild, JTAG, bitstream, physical DDR or program operation.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m unittest discover -s tests -p 'test_m05_11_mmio.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
bash -n scripts/run_m05_11_axil_xsim.sh
bash scripts/run_m05_11_axil_xsim.sh

export AXIL_PROOF="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_11_axil_* | head -n 1)"
echo "$AXIL_PROOF"
cat "$AXIL_PROOF/result.txt"
cat "$AXIL_PROOF/commit.txt"
cat "$AXIL_PROOF/source_sha256.txt"
tail -n 60 "$AXIL_PROOF/02_xvlog.log" 2>/dev/null || true
tail -n 60 "$AXIL_PROOF/03_xelab.log" 2>/dev/null || true
tail -n 120 "$AXIL_PROOF/04_xsim.log" 2>/dev/null || true
```

If a new testbench elaboration fails, preserve the original evidence and correct **only this new control logic/testbench**. If simulated AXI-Lite behavior is wrong, report as control bridge failure and block integration; do not alter the validated neural kernel. Do not mark M05.11b genuine XSim PASS until the operator-supplied record includes `exit_status=0` and the exact AXI4-Lite test PASS marker.

## 8. Roadmap and acceptance conditions

| Increment | Engineering deliverable | Acceptance proof | Current |
|---|---|---|---|
| M05.11a | 256b MM2S unpad, 192→256b S2MM footer/TLAST, host packet validator | **Genuine Vivado XSim both standalone RTL tests** | **VERIFIED**, user 2026-11-08 |
| M05.11b | AXI4-Lite session MMIO controller, structural stream shell, typed host register protocol | Native tests + Icarus standalone bus test + **new genuine Vivado XSim** | **Implemented; Vivado gate pending** |
| M05.11c | Connect *actual existing generated HLS RTL* to four stream shims and MMIO; generated port width, status, start, backpressure, late error, dual-session isolation | Actual RTL mixed-wrapper XSim; no invented register offsets | PENDING |
| M05.12 | Choose exact AMD AXI DMA IP & PS interconnect, cache coherency, input/output descriptor lifecycle, HLS register client and full reset/timeout recovery | Generated Vivado block design / PS DMA driver + independent verification | PENDING |
| M05.13 | Complete PS/PL routed design and physical K26 tests (only upon explicit user authorization) | Full route/timing/resources + physical transactions | PENDING |

**Preservation:** M05 stays OPEN, draft PR #79 UNMERGED. Do not replace/erase old proof folders, Loihi digital-twin physical reports, Vivado journals or bitstreams. The user's signed32 optimized HLS evaluation engine remains unchanged throughout M05.11b.
