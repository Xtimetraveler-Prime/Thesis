# M05 — Next chat handoff / open implementation gates (2026-11-07 local)

**Project:** `Xtimetraveler-Prime/Thesis`, independent `Neuromorphic_Accelerator/v1`, **not** v3/v4 of Loihi Digital Twin.

## Accepted foundation

- M01, M02, M03: prior user-accepted PC scopes. The **M02 revision-1** neural equation (exact signed W-bit voltage, rational leak trunc toward zero, full current sum before one clamp, inclusive threshold/reset, positive delays and recurrence) is unchanged.
- **M04 user-approved closure and merged PR #78**: verified main merge **`7d97494a972c9fbf9ff65a805c97bef9b0b951d7`**. Initial 13 M04 tests were user-reported native PASS; nine extra M04.5 tests were CI PASS and no separate user-local SHA was supplied. M04 documented the v3 reuse rejection and W16/u32/i64/4096 K26 first-profile requirements.
- **M05 NEW and NOT ACCEPTED:** branch `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`, started from that exact M04-merged main. Draft **PR #79** remains **UNMERGED**.

## What has actually been developed in this session

1. **M05.1 first HLS-oriented kernel:** [m05_stream.cpp](../hls/m05_stream_eval/m05_stream.cpp) and [m05_stream.hpp](../hls/m05_stream_eval/m05_stream.hpp) wrap the actual M04 C++ exact fixed-domain neuron step in a loop of <=1024 work-items. HLS stream pragma request/response and AXI-Lite scalar control are proposed, with `#pragma HLS PIPELINE II=1` as a **wish, not achieved II**. The native test fallback stream is an unbounded C++ queue and **does not verify real AXIS ready/valid**.
2. **M05.2 host-only live event prototype:** [m05_host_runtime.py](../src/neuromorphic_accelerator_v1/m05_host_runtime.py) independently schedules signed external/delayed synaptic events, M03-exact sparse worklists, positive-delay recurrence and caps each tick at 4096 individual deliveries. It calls the **actual compiled C++ batch** per active tick; full voltage/spike trace and worklist checked against M02 dense/event + M03 independent sparse. State is a Python list; **not on-chip BRAM**. Native subprocess overhead is not a PL benchmark.
3. **M05.4 offline preparation, NOT executed:** [Vitis HLS config](../hls/m05_stream_eval/m05_hls_config.cfg), [Csim vectors](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) and [safe evidence runner](../hls/m05_stream_eval/run_m05_offline_hls.sh) for Vitis 2025.2 / part `xck26-sfvc784-2LV-c`, 10ns target and 12% uncertainty.
4. **Source-native CI:** 17 M05 tests plus 22 M04, 28 M03, 21 M02 and 20 M01 = **108** named tests PASS in [initial working code run 42454758437](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42454758437) at SHA `cd483fe5`. Final branch head CI and user-native verification must be rechecked before accepting any more submilestone.

## Source and comparison documentation

- [M05_ENGINE_V3_COMPARISON.md](M05_ENGINE_V3_COMPARISON.md) identifies exact changes from the old v3 **full-core**, current+voltage+refractory, strict-threshold, per-core-paged dispatch to a new **per-neuron stateless stream**, M02-exact numerical step and independent sparse worklist.
- [M05_TESTS_EXPLAINED.md](M05_TESTS_EXPLAINED.md) explains all 17 actual tests, deterministic trace fixtures, negative admission/CLI cases, discovered unused-label compile failure and evidence limits.
- [M05_PC_ONLY_VERIFICATION.md](M05_PC_ONLY_VERIFICATION.md) has exact VS Code fetch/switch/pull, native commands, original no-overwrite evidence capture and optional **offline only** Vitis commands.
- [Roadmap](../roadmap.md) retains M05 **IN PROGRESS**, M04 **COMPLETE**.

## Next steps in sequential order (M05 is NOT complete)

1. **M05.1 true offline HLS gate:** when Vitis/Vivado 2025.2 is available, run isolated Csim; inspect actual packed stream interfaces, tool warnings, support for C++ top/arrays and cross-translation-unit `m04_eval_one`; revise while preserving M02. Run genuine isolated csynth and C/RTL cosim, record original source/config/report SHA, measured *estimated* II, latency/LUT/FF/BRAM/URAM/DSP and 10ns clock target. **No toolchain is available in this agent runtime; none of this was executed.**
2. **M05.2 PL hardware scheduler:** replace Python host worklist with bounded on-chip event worklist, timestamped buckets, exact 64-bit accumulation and a real ready/valid protocol. Duplicate (tick,id) suppression, backpressure, overflow handling, positive-delay recurrence, bias/no-input wakeups and barrier completion are mandatory. 4096 is a per-tick event-admission rule, **not** maximum all-future queued events. If queue cannot fit, reject run or prove **lossless** spill.
3. **M05.3 on-chip state fabric:** implement 1024-resident-neuron baseline with configurable grouping (M01), state/config RAM interfaces, proper read/write ownership and RAW/WAW hazard protection. Ensure one committed state per neuron per tick, correct reset, and deterministic trace under reordered work; test resident capacity and per-tick barriers. Current Python list is *not* this deliverable.
4. **M05.4 integrated RTL/HLS parity and acceptance:** golden trace checks on hardware-language simulation, memory/AXIS stalls, corner cases and resource/clock reports. Only after that consider any physical KV260 deployment with **new specific operator approval**.

## Immutable claim boundaries / workflow

- No board, JTAG, PS Linux halt, DDR writes, FPGA programming, physical energy, real DDR transactions, achieved II or matched acceleration was measured or authorized.
- Do NOT use old v3 JTAG scripts or change accepted M02 without a versioned approval. Official MNIST TEST remains sealed.
- M05 draft PR #79 stays **unmerged** pending user's own native PASS, milestone-specific docs, CI and explicit approval. If toolchain unavailable, document **NOT RUN**, not an inferred HLS pass.
- Source and original measurements belong outside git under new `$HOME/Thesis_Evidence` exclusive-create directories with source SHA.
- Continue from branch and the sources above; do not restart from the now-merged M04 branch. Follow exact [native verification](M05_PC_ONLY_VERIFICATION.md).
