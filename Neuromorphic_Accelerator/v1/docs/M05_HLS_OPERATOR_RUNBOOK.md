> **LATEST 2026-11-08 — M05.11a owner Vivado XSim VERIFIED; M05.11b AXI-Lite MMIO developed:** Owner's existing bridge XSim evidence `~/Thesis_Evidence/neuromorphic_v1_m05_11_bridge_20261108T224957Z_AQzMlG`, checkout `b3385619b81bc43ee69a082a2f5c8af258e03696`, `exit_status=0`: *both* genuine Vivado 2025.2 standalone bridge RTL snapshots passed (trace 3 TLAST terminal cases +12 egress stalls +sticky overflow, ingress 128/192 unpad +7 ingress stalls +bad TLAST quarantine). **M05.11b NEW:** `rtl/m05_11/m05_11_axil_session_controller.v` 32b AXI4-Lite slave, independently buffered AW/W channels, persistent B/R under backpressure, programmable session/count registers, start/finalize/ACK lifecycle, nonzero-status quarantine; `m05_11_stream_shell.v` structurally wires MMIO control to three input bridges and trace packetizer, all under single clock; typed host-only register client `m05_11_mmio.py` + 14 fake-MMIO tests; new independent RTL testbench + safe Vivado XSim runner. Original HLS kernel and real Vivado OOC timing unchanged. **Icarus RTL AXI bus test PASS + structural shell elaboration PASS**, but **M05.11b genuine Vivado XSim/PS-DMA/HLS integration pending**. Detailed [custom register-map and control lifecycle](M05_11B_AXIL_SESSION_CONTROL_2026_11_08.md), [3-question transport design ADR](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md), [evaluation engine evidence history](M05_EVALUATION_ENGINE_EVOLUTION.md). Operator next: `bash scripts/run_m05_11_axil_xsim.sh` in sourced Vivado 2025.2; no board. M05 OPEN, PR #79 DRAFT/UNMERGED.
>
> **LATEST M05.11a PS/PL TRANSPORT PROTOTYPE (2026-11-08):** The three required architecture questions are answered in the new [M05.11 detailed ADR](M05_11_PS_PL_TRANSPORT_ARCHITECTURE_2026_11_08.md): **(1)** proposed 3 separate 256-bit MM2S inputs + 1 256-bit S2MM trace, with 256→128/192 low-bit ingress adapters; **(2)** a 192→256-bit trace adapter appends a 32-byte terminal status+count+session footer asserting **TLAST even on zero-row errors**; **(3)** PS arms receive FIRST, feeds/drains concurrently, reads HLS ap_done/ap_return, commands finalize through a future MMIO bridge, verifies actual S2MM bytes/footer/status/quiescence and discards/reset-flushes on any error. All new hardware bridge modules and 2 SV benches are **independent of and leave unchanged** the verified signed32 HLS evaluation kernel. GitHub Actions **Icarus compiled/simulated both standalone RTL benches PASS** (12 output stalls, 7 input stalls, 3 terminal scenarios, malformed input and overproduction quarantines), **203 M05 native Python tests +91 prior=294 named native regression methods**. **Actual Vivado 2025.2 XSim bridge test still PENDING**; physical DMA, MMIO command block, full HLS+bridge RTL and full PS/PL implementation have NOT been built/tested. Local next: `bash scripts/run_m05_11_bridge_xsim.sh` in Vivado-sourced shell; it stores exclusive evidence under ~/Thesis_Evidence. [Canonical optimized engine evolution](M05_EVALUATION_ENGINE_EVOLUTION.md) and [controller development ledger](M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md) updated. M05 OPEN, PR #79 DRAFT/UNMERGED, no board/JTAG action.
>
> **M05.10 controller verification (NO hardware operations):** M05.9 direct real XSim PASSED operator on same signed32 rolling DUT, 8+20 rows status4 then0, 213 trace stalls, clean t8. New host-only `ExecutionController` tests with scripted finite FIFO, exact 128/192-bit TDATA codec, source hashes and simulated demo. [Full controller design and state/ABI/quiescence protocol](M05_EXECUTION_CONTROLLER_DESIGN_2026_11_08.md). After pulling development branch, run `python3 -m unittest discover -s tests -p 'test_m05_execution*.py' -v` and `python3 scripts/m05_controller_native_demo.py`, then entire M05 suite. **These are native-only, no real MMIO/PS DMA**. M05.11 must choose end-of-run framing because current HLS AXIS has **no TLAST**; real adapter requires independent tests. Kernel unchanged; no Vivado synth, board programming or PR merge.
>
> **LATEST M05.9 — 2026-11-08:** Operator's **real Vivado 2025.2 direct generated-RTL M05.8 late-error test PASSED** (original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T211756Z_234592`, exit0): 11 genuine generated RAM images staged, 8 ordered provisional rows from ticks0..3 including t0/n0 spike, real `BAD_EXTERNAL=4` at tick4, **56 output stalled cycles**, offline host `RollingTraceCommitGate` replay **drained 8 / committed 0**. Prior genuine directed 312 neuron-input and 7573 trace-output stalled cycles and routed 6.503ns OOC evidence unchanged. **New M05.9**: distinct SystemVerilog [two-run recovery test](M05_MULTI_RUN_RECOVERY_GATE_2026_11_08.md) runs the **same RTL instance without pulsing reset**: first run emits 8 provisional rows then status4, second run reloads an entirely new synapse-free network (2 neurons/10 ticks), emits exactly **20 valid rows** including a fresh t1/n1 spike and **zero stale t8 recurrence**, returns status0. New strict read-only XSim transcript replay feeds two independent host commit gates (0+20 committed). **15 new native synthetic/source tests = 157 M05 +91 accepted earlier =248 named native tests**. **Genuine M05.9 direct XSim NOT YET RUN**; do not claim physical PS/PL or DMA integration. [Canonical evaluation-engine optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md). Owner next: run `bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL" --multi-run` using existing immutable --impl proof. M05 OPEN; PR #79 draft/unmerged, no board/JTAG.
>
> **M05.8 OPERATOR COMMAND (Vivado 2025.2 / K26, NO BOARD):** M05.7 true direct RTL neuron-input and trace-output stall gate PASSED operator XSim: 768 rows, 312 input stalls, 7573 output stalls, 11 original RAM images. **New source-only implemented transactional late-error test**: after pulling current M05 branch, use `export ROLL_IMPL="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026"` then `bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL" --late-error`. Expected NEW XSim (not yet verified!) 8 provisional trace rows, final hardware AXI-Lite status4, 0 published rows; runner also executes `scripts/m05_rtl_transaction_replay.py`, stores `05_trace_commit.log`. Preserve old evidence and share new result, `04_xsim.log` and `05_trace_commit.log`. Do not synthesize/program board. [M05.8 detailed runbook](M05_LATE_ERROR_TRANSACTION_GATE_2026_11_08.md). HLS engine kernel unchanged, M05 open, PR #79 draft.
>
> **LATEST M05.7, 2026-11-08 — input-stall test coverage corrected, NOT DUT math:** Operator ran genuine direct XSim with *11 real Vitis RAM .dat assets staged successfully* (`neuromorphic_v1_m05_rolling_axis_rtl_20261108T205357Z_221064`), `xvlog` and `xelab` PASS, but XSim stopped at `RTL_STRESS_FAIL no meaningful incoming AXIS backpressure` (coverage gate) after the existing trace/status checks. Two neuron records + one edge/event weren't enough to make ingress TREADY deassert. Prior **separate XSim output-backpressure PASS** remains valid (24 rows, 188 output stalls, final status 0). **M05.7 development:** restored that proven two-neuron SV testbench byte-for-byte; created separate **64-neuron/12-tick/768-row ingress saturation test** with 300 prestart cycles, full trace/status scoreboard and real input VALID/TDATA hold + **>=10 measured input stalls**; runner now selects it using `--ingress`, retains identical original HLS IP, RAM asset checks and new/fatal-aware evidence. **New direct ingress XSim gate is PENDING.** [Canonical engine evolution](M05_EVALUATION_ENGINE_EVOLUTION.md) and [M05.7 runbook](M05_INGRESS_BACKPRESSURE_GATE_2026_11_08.md). M05 OPEN; PR #79 draft/unmerged, no board operations.
>
> **LATEST 2026-11-08 — M05.6 direct RTL PASS and next strict backpressure gate:** Operator direct Vivado 2025.2 XSim generated-Verilog test at source checkout after syntax fix **PASSED** (`exit_status=0`), evidence `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T203635Z_212333`: 24/24 two-neuron/12-tick trace records validated, 188 real output `TVALID && !TREADY` stall cycles, 1162 input VALID-gap cycles, correct final status 0. **Input stalls were N/S/E=0/0/0**, and XSim printed missing generated `*.dat` RAM-initialization warnings. Thus output backpressure is verified on this directed RTL workload; inbound stall and initialized-memory gates are **PENDING**. New development: offline runner stages only original Vitis-produced RAM images (fails closed if none exist), strengthened testbench primes input `TVALID` before start and asserts incoming hold-under-stall with >=10 measured input stall cycles. Kernel and earlier **6.503ns routed OOC timing, 35 BRAM/6257 LUT/6887 FF/2 DSP** unchanged. New native tests (9 RAM staging +1 input gate) make **128 M05 +91 older=219 native tests**. Follow-on genuine XSim rerun still required. [Canonical optimization history](M05_EVALUATION_ENGINE_EVOLUTION.md), [M05.6 operator runbook](M05_AXIS_RTL_STALL_TEST_2026_11_08.md). No board actions; M05 OPEN; draft PR #79 unmerged.
>
> **LATEST M05.6 OPERATOR VERIFIED OOC RESULT / EXPERIMENTAL DIRECT RTL GATE:** Original operator `--rolling --impl` succeeded at commit `334ca0ee78c2651019d72101f23f253b62396aed`, K26 Vivado 2025.2, **6.503ns routed period against 10ns**, WNS +3.497081ns / WHS +0.055ns / 0 unrouted, 6257 LUT/6887 FF/35 BRAM/2 DSP in offline OOC IP. Original evidence `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026`; no device operation. **NEXT GATE is NOT another HLS `--cosim` or `--impl`**. Run new [M05.6 direct Verilog/XSim ready-valid stressbench](M05_AXIS_RTL_STALL_TEST_2026_11_08.md): `bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL"` using original impl folder. This testbench has passed only source/native preparation tests; genuine direct RTL test is NOT YET verified. The Vitis HLS numerical kernel was deliberately left unchanged. 117 M05 native methods +91 prior accepted, 208 total; CI statuses separately checked. M05 OPEN, PR #79 DRAFT/UNMERGED, no board.
>
> **LATEST M05 ROLLING-i32 REAL RTL PASS / NEXT OOC GATE:** User Vitis 2025.2 K26 `--rolling --cosim` at commit `07913bbf925e5cd1ffc0d84dd6f9d5b4c2ee519a` returned exit 0, 10/10 Verilog XSim transactions PASS, C oracle postcheck PASS, timing report latency min/avg/max **265/6328/17225 cycles**, intervals **285/6869/17248 cycles** and total **63463 testbench cycles**. Do **NOT** compare its average to prior 8-case i64 XSim as if identical workloads. HLS synthesized signed32 rolling top estimated 8.256ns, 39 BRAM18K (vs old i64 53), 9956 LUT, 8346 FF, 2 DSP. [Canonical versioned engine ledger](M05_EVALUATION_ENGINE_EVOLUTION.md) and [local provenance/audit tool](../scripts/m05_hls_evidence_audit.py) now maintained. Next `--rolling --impl` creates an exclusive offline evidence directory and runs CSim+synth+cosim+Vivado OOC impl; report timing only if actual implementation reports support it. No board operations or shell integration.
>
> **LATEST M05.5 STATUS (2026-11-08):** Operator's optimized **signed32** rolling HLS top genuine Vitis 2025.2 K26 **CSim + synthesis PASS**, commit `827f719778472da39ffa294b431ee848fe360529`, original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_synth_20261108T193909Z_169727`. HLS estimated period **8.256ns** vs requested 10ns; **39 BRAM18K** (down 14 from prior i64 rolling 53), including `current_U` **16 BRAM18K** vs old 30; 9,956 LUT, 8,346 FF, 2 DSP. The single-port bias II lower-bound-2 warning remains; full-run latency unknown. **i32 rolling XSim C/RTL cosim NOT YET RUN** (the old i64 rolling version was verified). `m05_rolling.cpp` source **unchanged** since this synthesis, sha `e5443aa87dcc8819ee8aa680b6ca105facc1aced`. After it, developed a strictly HOST-ONLY [transactional output accept/abort gate](M05_TRACE_COMMIT_GATE_2026_11_08.md): validates row-major framing and per-tick counts, drains provisional records, commits only on final status 0 plus expected row count, discards the whole run on late status, malformed framing or timeout. Added 16 native receiver/model/CLI tests including a toy 1-beat FIFO stall model; **92 M05 +91 accepted prior=183 named native tests PASS**. This is NOT an AXIS RTL/TREADY test, DMA/PS driver, real hardware recovery or physical timing. **NEXT OPERATOR GATE:** after pulling current branch run `--rolling --cosim` (cumulative real CSim, synth then XSim), preserve original reports. M05 remains OPEN, PR #79 DRAFT/UNMERGED; no board operations. [Full boundary and commands](M05_TRACE_COMMIT_GATE_2026_11_08.md).
>
> **LATEST 2026-11-08 VERIFIED RTL AND NEW SOURCE OPTIMIZATION:** The operator's **unchanged i64 rolling engine** at commit `03c3fbc5f8866c44510ff67d2cce8151988fa4d7` has now passed **actual Vitis HLS 2025.2 CSim, synthesis AND XSim C/RTL cosim**. Report: Verilog PASS, all **8/8 transactions**, latency **265 / 3616 / 16492 cycles** min/avg/max, intervals **285 / 3919 / 16512 cycles**, **29077 cycles total**, simulated 10ns clock. Old synthesis **53 BRAM18K (30 for 64-bit current_U), 10,083 LUT, 8459 FF, 2 DSP**, estimated 8.244ns vs 10ns requested. **NEW development since that PASS:** changed only fifth rolling top's internal current wheel `[8][1024]` from signed i64 to **signed i32**, mathematically exact under max 4096 individual signed W16 deliveries per tick (bounds **-134217728 .. +134213632**, signed28 sufficient), and preserve i64 M04 API via explicit sign extension. Added HLS CSim/RTL vectors for both extremal 4096-arrival polarities and 4096 negative delayed recurrent synapses at t+8, plus two M02/M03 full reference tests. **76 M05 + 91 older = 167 named native tests PASS**; current code's genuine Vitis CSim/synthesis/cosim **NOT YET RUN**. NEXT: pull branch and run cumulative `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --synth` (new genuine CSim first; then synth), compare previous current_U 30/total 53 BRAM18K before any new cosim. No physical action, M05 OPEN/PR #79 UNMERGED. [Signed32 proof + gates](M05_ROLLING_I32_ACCUMULATOR_2026_11_08.md).
>
> **LATEST 2026-11-08 ROLLING HLS SYNTHESIS — user-provided original report, scoped to source commit `984f5baf45ce771e94e1e8b2947e1ef27ccc6d58`:** Genuine Vitis HLS 2025.2, target K26 (`xck26-sfvc784-2LV-c`), **exit_status=0**. Clock **10ns requested / 8.244ns HLS estimated** (1.20ns uncertainty). HLS area: **53 BRAM18K / 288, 10,083 LUT / 117,120, 8,459 FF / 234,240, 2 DSP / 1,248, 0 URAM**. Its future-current `current_U` alone occupies **30 BRAM18K** of 53; per-tick scratch state is resident BRAM as intended. Top-level latency/II **unknown (`?`)**, and a reported initialization-loop theoretical maximum `34,359,738,362` cycles is **not** a measured run; don't infer throughput from it. Warning `HLS 200-448` says **loop lower-bound II=2 from competing reads of single-port `bias`**, not that the whole engine achieves global II=2; reset is synchronous active low. All claims are HLS estimates, **not placed/routed clock, timing closure or physical throughput**. Memory compare against earlier eight-tick integrated top: **74→53 BRAM18K (-21)**, LUT **5,914→10,083 (+4,169)**, FF **3,122→8,459 (+5,337)**, DSP **6→2**, clock estimate **8.002→8.244ns**. The earlier integrated run is **8 ticks** vs rolling **64 ticks**, and their testbench workloads are not cycle-per-tick equivalent. No rolling C/RTL co-simulation result yet.
>
> **NEW SOURCE-PRESERVING TEST COVERAGE:** Following synthesis, only [`m05_rolling_csim_tb.cpp`](../hls/m05_rolling/m05_rolling_csim_tb.cpp) and [`test_m05_rolling.py`](../tests/test_m05_rolling.py) were extended—not the actual synthesized [`m05_rolling.cpp`](../hls/m05_rolling/m05_rolling.cpp). GitHub blob SHA **`5065bb5babad38e4f6685be34c77189be6a9e426`** is identical on synthesis commit and the updated branch. New RTL-ready CSim bench now independently computes every neuron state, spike, evaluated-bit and delivery count of a **64-tick** two-neuron signed recurrent network (including delay-8 self/parallel recurrence, last-tick zero event), and tests a **late out-of-order external input** causing BAD_EXTERNAL after speculative prefix emissions. Python adds 2 named native tests for full 64-tick M02/M03 oracle parity and the 1,024-neuron boundary. Native CI **74 M05 + 91 M01–M04 = 165 methods PASS**; **five** HLS CSim bench source executables compiled/executed NATIVELY in CI. **No actual Vitis CSim/RTL yet for the strengthened bench**, so next gate is **cumulative `--rolling --cosim`** which first reruns genuine CSim and synthesis before XSim. Original original roll-synth source/config/results remain in external `Thesis_Evidence`, no Git reports.

> **ROLLING NEXT:** On operator's machine after pulling current branch, run `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --cosim` (genuine Vitis 2025.2 required). This runs new HLS CSim + re-synthesis + XSim on same unchanged synthesized kernel but strengthened testbench. If genuine 64-tick or late-error case fails/hangs, preserve all logs; do not mark RTL verified or modify evidence in place. Output validity remains speculative until final return status. Resource warnings from report may be optimized only after RTL verification.

> **LATEST FIFTH-TOP STATUS (after 2026-11-08 operator PASS):** Initial rolling-wheel genuine Vitis 2025.2 CSim **PASS** (0 errors, exit 0; `neuromorphic_v1_m05_rolling_csim_20261108T185457Z_144435`). The *source was subsequently changed* to bound startup wheel-memory clears to admitted neuron IDs, with a 2→1→2 consecutive-run HLS testbench regression. This revised rolling source has **native CI verification only**; rerun **genuine CSim and HLS synthesis together** with `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --synth` (cumulative stages, new evidence folder), then inspect top `m05_rolling_replay_csynth.rpt` before any `--rolling --cosim`. The previous fourth integrated co-sim report shows **Pass**, latency min/avg/max **8463/10572/16396 cycles**, interval **8489/11300/16416 cycles**, total **42363 cycles**, **NOT physical network throughput**. More at [rolling design and exact report requests](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md).
>
> **LATEST 2026-11-08:** The *fourth* **integrated 8-tick** HLS top now also has a genuine Vitis 2025.2 CSim + HLS csynth + XSim C/RTL cosim **PASS** on the operator workstation. HLS estimates: 8.002 ns / 5,914 LUT / 3,122 FF / 6 DSP / 74 BRAM18K; top-level latency unknown. The original cosim report remains available locally but **not yet analyzed for transaction latency**. See [original evidence path and scope](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md). A *fifth*, separate [rolling-wheel candidate](../hls/m05_rolling/m05_rolling.cpp) is now native-tested only, with 72 M05 +91 accepted = **163 native tests** and five native-compiled benches; real Vitis proof **not yet obtained**. The prior commands/status sections below are historical for earlier IPs.
>
> **NEXT operator Vitis gate for new rolling top** (after pulling branch, with Vitis 2025.2 sourced and no board operations): `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --csim`. Stop on first failure; preserve the fresh `Thesis_Evidence` path. Only after this PASS consider `--rolling --synth`, resource inspection and `--rolling --cosim`. The new rolling wheel admits delays **1–8** and runs up to **64 ticks** (not continuous); late errors invalidate prior speculative trace rows. [Contract](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md).

# M05 Vitis HLS 2025.2 offline operator verification (KV260/K26, NO BOARD)

**Current scope:** Three independent, project-owned **HLS-oriented C++ candidate IPs** in `Neuromorphic_Accelerator/v1/hls/`: `m05_stream_eval` (stateless per-neuron update), `m05_stateful_service` (persistent 1,024-row neural state/config memory with exact-once per-ID/tick guard), and `m05_event_accumulator` (signed i64 per-neuron coalescing, 4,096 individual contributions/tick with SEALED readout and sticky overflow). They are **not yet joined into a complete PL scheduler**. On 2026-11-08 the **operator** ran and reported genuine Vitis HLS CSim, HLS synthesis, and XSim C/RTL co-simulation **PASS for all three standalone tops**, with reports and evidence paths cataloged in [the real HLS evidence summary](M05_REAL_HLS_RESULTS_2026_11_08.md). The assistant has not run Vitis locally; there has been no integrated simulator or physical KV260 action.

This runbook uses Vitis HLS **2025.2** and K26 part **`xck26-sfvc784-2LV-c`** with a **10 ns requested clock, 12% uncertainty**. These are goals, not achieved timing/area. Original source and reports live in new exclusive-create directories under `$HOME/Thesis_Evidence`, never tracked/overwritten in Git. Do NOT run old v3 JTAG/DDR scripts. No Vivado Hardware Manager/device programming here.

> **LATEST PASS STATUS (after the originally failed attempts):** The three retried genuine CSim benches **all passed**, three individual RTL syntheses **all passed**, and three individual XSim C/RTL cosimulations **all passed** on the operator's Vitis 2025.2 installation. See [exact original evidence directories, resources and scope](M05_REAL_HLS_RESULTS_2026_11_08.md). The older failure diagnosis below is historical and explains the corrected absolute-path generator. **Do not confuse independent IP PASS with a completed M05 on-chip event scheduler.**
>
> **Next engineering work:** PL event routing/scheduling and state/accumulator integration, full-system temporal parity. OOC implementation is optional and does not substitute for an integrated RTL bench.

## 2026-11-08 real HLS failure and fix — review before rerunning

The operator ran all three **genuine** Vitis v2025.2 Csim commands on M05 source commit `6f5ca78a`; **all three failed** with `HLS 200-2001` (source and testbench not found) then `HLS 200-627` (no C testbench). This occurred because Vitis changed into the external `Thesis_Evidence` directory before resolving project-relative `syn.file`, `tb.file` and `-I` paths. The Vitis logs also confirmed `syn.output.format` is **deprecated** and should be `package.output.format`. Those failures prove **a configuration defect**, not faulty neural arithmetic; **no neuron logic reached Vitis CSim**. Preserve all three old failure folders unchanged. See [original failure analysis](M05_HLS_CSIM_FAILURE_2026_11_08.md).

**Fix on the same branch:** each new run generates and saves `hls_effective_config.cfg` beside its original evidence logs, containing verified **absolute** paths for every C++ source, testbench, and include directory. All Csim, synthesis, cosim and OOC commands now receive this effective config. The helper refuses a missing file or overwriting another run's config. `package.output.format=rtl` is used. The local mock-Vitis regression exercises the exact *directory change* and tests all 3 tops; it is **not genuine HLS evidence**.

After pulling the new branch, check:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05_hls*.py' -v
```

The three genuine `--csim` commands in section C are **the next required operator validation**. Start with the stream top; stop at the first failure, upload the new original log and `hls_effective_config.cfg`. Do not proceed to synthesis until ALL three genuine Csim logs pass.

## New M05 integrated finite-horizon IP — fourth top, not covered by prior genuine HLS PASS

The first connected **PL-oriented** scheduler + LIF datapath is now source-staged at [`m05_integrated_replay`](../hls/m05_integrated/m05_integrated.cpp). A single run has resident synapses and state, 8 future-tick aggregate buckets, recurrent positive delays, a 4096-individual-deliveries-per-tick cap, output buffer with failure suppression, and complete ticks without host orchestration. **12 new native test methods PASS; no genuine Vitis tool results exist yet for THIS new top.** [Detailed contract](M05_INTEGRATED_FINITE_HORIZON_DESIGN.md).

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v  # expect 60
# Source your installed Vitis 2025.2 if needed, then:
export HLS_PART=xck26-sfvc784-2LV-c
bash hls/m05_stream_eval/run_m05_offline_hls.sh --integrated --csim
# AFTER successful genuine integrated CSim ONLY:
bash hls/m05_stream_eval/run_m05_offline_hls.sh --integrated --synth
# AFTER successful synthesis and resource inspection ONLY:
bash hls/m05_stream_eval/run_m05_offline_hls.sh --integrated --cosim
```

Stop and send the new `01_csim.log`/`02_csynth.log`/`03_cosim.log` on the first failing stage. Do not claim the prior standalone co-sims establish integrated RTL equivalence. This is a bounded finite-run prototype: **continuous temporal queueing, live backpressure and physical placement remain open**.

## A. Prepare VS Code Ubuntu terminal

```bash
cd ~/Git/Thesis
git status --short                   # check for uncommitted work; preserve it
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip || \
  git switch --track origin/agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 --version
g++ --version
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
```

Expected source-only count **60 M05 + 22 M04 + 28 M03 + 21 M02 + 20 M01 = 151 named unittest methods**; there are additional randomized subcases. Four staged Vitis bench files are also compiled and executed **natively** by CI, but that is not Vitis Csim or C/RTL evidence.

## B. Load Vitis 2025.2 tools (example; adjust INSTALL_ROOT)

Find your real `settings64.sh` using your system's Vitis installation location. Do **not** copy the placeholder literally:

```bash
# EXAMPLE if your installation is /tools/Xilinx/Vitis/2025.2:
source /tools/Xilinx/Vitis/2025.2/settings64.sh

# Verify commands are actually available in THIS terminal
command -v vitis-run
command -v v++
vitis-run --version
v++ --version
echo "$XILINX_VITIS"
pwd  # should end in Neuromorphic_Accelerator/v1
```

If Vitis is installed at `/opt/Xilinx/Vitis/2025.2`, change the source path accordingly. `vivado -version` is optional; no board access is needed. If either Vitis executable is missing, stop, share your tool path/version output, and do not claim an HLS PASS.

## C. Phase 1 — **Genuine** Vitis C simulation, one independent top at a time

The repository script performs **real** `vitis-run --mode hls --csim`, checks Vitis 2025.2/part/source config, generates `hls_effective_config.cfg` with absolute paths for all design/testbench files and headers, and writes originals to a newly created `$HOME/Thesis_Evidence` folder. It **does not** silently run a Python substitute.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
export HLS_PART=xck26-sfvc784-2LV-c

# C++ stateless neuron evaluator: M02 correctness + AXIS candidate
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --csim

# Persistent on-chip 1K neuron state/config store candidate
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --csim

# Exact signed event accumulator and seal/overflow contract
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --csim
```

**Stop if a command exits nonzero.** Keep its original evidence folder, including `01_csim.log`, `result.txt`, `source_sha256.txt`, `tool_version.txt` and `commit.txt`. Share that failure before continuing. All 3 Csim results should show the individual testbench PASS and tool process success; a native `g++` PASS is insufficient.

For the first review, sending only the outputs from these **three Csim commands** is ideal. Actual synthesis may expose interface and arithmetic restrictions that we must resolve.

## D. Phase 2 — HLS synthesis (only after Csim passes)

Each command creates a **fresh** evidence folder, reruns its C simulation and then executes the AMD documented `v++ -c --mode hls` flow.

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --synth
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --synth
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --synth
```

**Required assessment (each top separately):** report actual **estimated clock period, requested 10ns, achieved loop II, min/max latency, LUTs, FFs, DSPs, BRAM_18K/BRAM_36K, URAM** and complete tool warning/error list. A `PIPELINE II=1` pragma is *only a directive*. For stateful/accumulator tops, confirm that RAM binding actually inferred BRAM rather than treating the entire array as registers or eliminating it. If synthesis fails, capture the error and do **not** assume the design meets M05. No LUT/throughput speedup claims should be made from C++ test times.

## E. Phase 3 — C/RTL co-simulation (only after successful synthesis)

Commands each rerun Csim and synthesis in a new evidence folder and then execute **`vitis-run --mode hls --cosim`**:

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --cosim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --cosim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --cosim
```

Require all expected response values, correct order, invalid/duplicate handling and no unexpected deadlock. **Check both testbench PASS and actual RTL cosimulation summary PASS**; the testbench itself can pass natively while the RTL sim fails. If the HLS interface protocol introduces TLAST/framing, wide struct packing, ap_ctrl_hs start/done or backpressure limitations, capture original wave/log and revise source; do not silently waive those issues.

## F. Optional Phase 4 — Offline OOC Vivado implementation

This is **NOT** board programming, and **NOT** integrated system-level routed timing. Only after C/RTL co-sim success, if you choose to evaluate single-IP place/route:

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --impl
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --impl
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --impl
```

Each `--impl` run independently repeats Csim, synthesis and C/RTL cosim first. Report **OOC WNS, target clock, resource utilization, tool version/part** separately from HLS estimates, and always label them "isolated IP OOC", **not a complete accelerator or physical KV260 result**.

## G. Evidence collection and how to share results

Every command prints a new directory like:
`$HOME/Thesis_Evidence/neuromorphic_v1_m05_stream_csim_YYYYMMDDTHHMMSSZ_PID`

To list your original runs:

```bash
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
  -name 'neuromorphic_v1_m05_*' -print | sort
```

Pick a single folder of interest and **substitute its actual path** (do not guess it):

```bash
export M05_RUN="$HOME/Thesis_Evidence/PASTE_ACTUAL_FOLDER_NAME_HERE"
cat "$M05_RUN/commit.txt"
cat "$M05_RUN/top.txt"
cat "$M05_RUN/part.txt"
cat "$M05_RUN/tool_version.txt"
cat "$M05_RUN/mode.txt"
cat "$M05_RUN/result.txt"
cat "$M05_RUN/report_paths.txt"
cat "$M05_RUN/report_sha256.txt"
cat "$M05_RUN/log_sha256.txt"
find "$M05_RUN" -type f \( -name '*_csynth.rpt' \
  -o -name '*cosim*.rpt' -o -name 'syn_report*.xml' \) -print
```

**Send:** the terminal summary and any **complete original** `01_csim.log`, `02_csynth.log`, `03_cosim.log`, or `04_ooc_impl.log` actually produced. For completed synthesis, share the complete `*_csynth.rpt` (or its actual report filename) and `report_paths.txt`. For errors, paste the first error **plus preceding warnings and source/line context**, not only the last `ERROR:` line. Include the `commit.txt`, `source_sha256.txt`, `hls_effective_config.cfg`, and `effective_config_sha256.txt` so we can confirm exactly which source and resolved paths Vitis received. You can upload selected logs/report files; entire build directories/bitstreams are unnecessary.

**Safety:** do not give me private credentials or machine-specific tokens, and do not perform JTAG or DDR writes. Retain failed evidence unchanged and rerun in a new directory after any source correction.

## H. Honest gate interpretation and next engineering choices

Passing all three independent HLS cores at Csim/csynth/cosim would **advance M05.1 and the standalone subcomponents of M05.2/M05.3/M05.4**. It would **not yet close M05** because there is currently no integrated PL event router/positive-delay scheduling FIFO/ready-valid backpressure test between the three cores, no end-to-end hardware tick barrier, and no physical state-cache residency controller. The *host* scheduler continues to provide those semantics today.

Next system-level work must integrate the three components and enforce exactly-once evaluation, zero/bias/nonzero-voltage wakeups, all delayed self/parallel synapses, full W16 current coalescing, 4,096 cap with sticky invalid-run handling, and no partial publication on overflow. Only a **full end-to-end** simulation against accepted M02 traces and a reproducible hardware-resource/performance report can satisfy final M05. Until then, **M05 stays OPEN / draft PR #79 UNMERGED**. Physical KV260 deployment requires separate explicit authorization.

### Official 2025.2 tool basis

- AMD UG1399 `vitis-run --mode hls --csim`, `v++ -c --mode hls`, `vitis-run --mode hls --cosim`, and `--impl`: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/vitis-v-and-vitis-run-Commands
- 2025.2 HLS config keys/flow: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/HLS-Config-File-Commands
- HLS internal RAM binding: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/pragma-HLS-bind_storage
- AXIS stream interface semantics: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/Interfaces-for-Vitis-Kernel-Flow
