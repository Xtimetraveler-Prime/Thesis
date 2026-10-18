# P08-A2.2 — How the timing system works, limitations and sources

**State (2026-10-18): SOURCE CANDIDATE / HOST NATIVE TESTS NOT YET USER-RUN / A2.2 VITIS NOT YET BUILT / KV260 NOT RUN.**  
**User direction:** latency first. Physical power and energy **DEFERRED**. Any derived throughput remains secondary, **not** the A2 latency acceptance gate.

## 0. Fixed results, A2.1 build provenance and intended distinction

Prior frozen P07-A4.4 official MNIST test result is **9,456/10,000 = 94.56%** on KV260, with all 10,000 independent P03 packed-oracle spike/route comparisons. P08 does not alter its trained checkpoint, 25+1 logical tick semantics, P03 HLS fabric, original `P07A4R01` journal or signed24 arithmetic.

User supplied **A2.1 Vitis-build-only PASS**:
- Build: `/tmp/v3_p08_a2_build_20261018T193149Z/vitis_workspace/p08_a2_board.elf`
- A2.1 candidate ELF SHA256: `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`.
- Actual XSA SHA256: `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
- `P08_A2_A53_VITIS_BUILD_PASS=1`, `P08_A2_1_ELF_DDR_ISOLATION_PASS=1`, `P08_A2_1_VITIS_BUILD_PASS=1`, `P08_A2_1_KV260_LATENCY=NOT_RUN`.
- This records a **user-performed Vitis build**, not a P08 physical inference measurement. Local A2.1 native test markers were not pasted, so independent pytest acceptance cannot be claimed on that evidence alone.

**A2.2 is a separate new experimental firmware**, not a mutation of the accepted A2.1 ELF. It reuses the A2.1 `P08ALAT1` image timing sidecar and adds a second, `P08TCK02` sidecar with precise per-logical-tick service endpoints. A2.2 contains an instrumented copy of the accepted P07-A2 portable per-tick wrapper under `software/p08/p08_a2_2_runtime.c`; the **actual** original `software/p07/p07_a2_runtime.c` and `software/p03/` are not edited. It invokes the same original spike encoder, PL dispatcher, trace reader, route and barrier callbacks in the same order.

## 1. Physical execution ownership and timing clock domains

```text
A53 bare-metal (one persistent launch, one logical core)
  |
  +-- P07 raw 784B image -> accepted A1 ingress descriptor
  +-- reset/restore immutable core0 -> initial PL page-in
  +-- 26 ordered logical ticks:
  |     [A53 encode] -> [A53 writes external CURRENT bank]
  |     -> [A53 MMIO PL dispatch / wait for DONE / read hardware cycles]
  |     -> [A53 physical 10-output trace reads (42 for selected frame)]
  |     -> [A53 NEXT packet route or final drain]
  |     -> [A53 global barrier] -> [bank swap / next tick]
  +-- accepted neural result, original P07 CRC journal and selected trace
  +-- P08-A2.1 image timing record and new A2.2 tick records to DDR
  +-- host reads raw evidence AFTER separate hardware completion
```

A2.2 reuses the existing, board-implemented `read_ticks()` callback in `p08_a2_2_board.c`:

```c
__asm__ volatile("isb; mrs %0, cntvct_el0":"=r"(ticks)::"memory");
```

The A2.2 version includes a compiler `"memory"` clobber to keep C loads/stores on their intended side of each timing boundary; `ISB` supplies the processor-side instruction-synchronization step, and neither provides automatic calibration for the act of reading the timer. This reads the A53-accessible Arm Generic Timer **virtual count** (`CNTVCT_EL0`), not core-instruction cycles and not the PL fabric clock. `CNTFRQ_EL0` is read once at startup and stored **without substituting an assumed clock**. The reported A53 duration for same-domain, monotone timestamps `t_start` and `t_end` is:

`delta_seconds = (t_end - t_start) / CNTFRQ_EL0_hz`.

Arm documents that `CNTVCT_EL0` is derived from the physical system count minus a virtual offset in applicable configurations. Its subtraction is valid for a stable run with a common counter configuration, not a means to identify wall-clock time of day. Arm also documents that `CNTFRQ_EL0` is an **architectural frequency value programmed by firmware**, not hardware frequency measurement; confirm the observed register in board evidence and do not call it independently calibrated to a physical reference without an additional check.

Sources for this method:
- **Arm (primary):** [Learn the architecture — Generic Timer, ID 102379, v1.3, §§3 and 4.1](https://documentation-service.arm.com/static/65fac6957bcc0c1c661b36c0?token=), especially ordered reads with `ISB`, system-counter semantics, and firmware-programmed `CNTFRQ_EL0`.
- **Arm (primary):** [Use a system counter — Arm Learning Paths](https://learn.arm.com/learning-paths/servers-and-cloud-computing/arm_pmu/assembly/), practical `CNTVCT_EL0` / `CNTFRQ_EL0` subtraction and seconds conversion.
- **Actual project-specific implementation (authoritative for our endpoints):** `software/p07/p07_a2_runtime.c`, `software/p03/p03_runtime.c`, `software/p03/p03_hw_adapter.c`, `software/p08/p08_a2_board.c` and `software/p08/p08_a2_2_runtime.c`; [P03 autonomous application contract](P03_PS_AUTONOMOUS_APPLICATION.md).

## 2. Seven A53 timestamp boundaries per tick

Each **26-tick image** produces exactly 26 `P08TCK02` records; all seven timestamps are raw unsigned 64-bit `CNTVCT` values from the **same A53 clock**. Tick `0..24` collects spike input; tick `25` drains output and deliberately discards new NEXT packets. `source`, `append`, `dispatch`, `trace`, `route`, `barrier` below are **software service intervals** in the full FPGA-backed system, not HLS-only latency.

| Wire timestamp | Captured by | What happened before reading it |
|---|---|---|
| `start` | `tick_dispatch()` | Start of current tick just before `p07_a1_tick_events` |
| `after_encode` | `tick_dispatch()` | Accepted deterministic event encoder returned; includes host-side event generation |
| `after_append` | `tick_dispatch()` | `append_current()` finished event-bank preflight and all per-event MMIO writes |
| `after_dispatch` | `tick_dispatch()` | P03 `underlying.dispatch()` returned after MMIO setup, START/DONE poll, packet/status and PL cycle CSRs |
| `after_trace` | `tick_dispatch()` | Ten output compartment debug reads completed; selected trace frame instead performs full 42-compartment readback per tick |
| `after_route` | `tick_route()` | P03 NEXT packet acknowledgments written, or tick25 final-drop policy applied |
| `after_barrier` | `passthrough_barrier()` | Existing `underlying.barrier_ready` callback has returned success |

Derive the following **non-overlapping, ordered A53 callback spans**:

- `encoder = after_encode - start`.
- `event_bank_append = after_append - after_encode`.
- `MMIO_dispatch_and_poll = after_dispatch - after_append` (includes **hardware elapsed time plus A53 MMIO/poll overhead**, not pure FPGA LIF).
- `trace_readback = after_trace - after_dispatch`.
- `route_policy = after_route - after_trace`.
- `barrier_callback = after_barrier - after_route`.

`after_barrier - start` is **instrumented tick service**, **not** the complete scheduler tick including `p03_rt_execute()` event-bank-swap bookkeeping or between-callback gaps. Thus `Σ 26 (after_barrier-start)` is **not** the accepted complete per-image latency. Use A2.1 `after_commit-service_start` for complete image service (input, full reset/initial residency, 26 ticks, result/selected trace journal). The difference includes preparation, scheduler gaps, result commitment and all added instrumentation.

`external_events`, `emitted_packets`, `acknowledged_packets`, `flags` and tick index are captured without changing the accepted values. In tick25, `acknowledged_packets` also counts intentionally discarded NEXT packets, so do not interpret it as a hardware NEXT write count.

**Important:** the output-trace readback cost is diagnostic overhead inherent to the accepted P07 implementation, not intrinsic LIF computation. The *selected full-trace frame* follows a different work path (42 compartments versus normal 10). Always report/flag it separately.

## 3. PL cycles have a DIFFERENT physical meaning

`pl_dispatch_cycles` for each tick is the original completed-latch, split-64-bit register read from `P03_REG_DISPATCH_CYCLES_LO/HI` in `software/p03/p03_hw_adapter.c`. The C adapter only reads this number after a successful FPGA dispatch acknowledgment. The sum for all 26 ticks is required to **exactly** equal the existing `p03_rt_counters.pl_dispatch_cycles` captured in `P08ALAT1`, for that same image.

**Do not** divide PL cycles by `CNTFRQ_EL0`. We have not yet confirmed the physical counter's RTL precise start/stop definition or the **actual routed fabric frequency on this exact bitstream**. HLS latency/synthesis estimates or target clock periods are not a direct physical stopwatch or evidence of routed achieved timing.

Source for this caution:
- **AMD (primary):** [Vitis HLS UG1399, Specifying the Clock Frequency, 2025.1](https://docs.amd.com/r/2025.1-English/ug1399-vitis-hls/Specifying-the-Clock-Frequency?contentId=2qxvFsf7Z8jgzoxetgokNw) distinguishes HLS configured target period from later placement and routing.
- **Project-specific P03 implementation**: `software/p03/p03_hw_adapter.c`, `software/p03/include/p03_mmio.h`, `docs/P03_PS_AUTONOMOUS_APPLICATION.md`, `docs/P05_2I_ACCEPTANCE.md`. These—not vendor general documents—define what the current design's custom counter includes.

## 4. New separate wire format and bounded DDR ownership

The previously accepted physical P07 records remain **unchanged**:

- `0x42000000`: P07 original 1MiB `P07A4R01` 96-byte-per-frame numerical journal.
- `0x43FF0000`: one selected 64KiB full compartment trace.
- `0x43F00000`: immutable original P07 frozen master DDR image.
- `0x43000000..0x430FFFFF`: existing A2.1 **1MiB** `P08ALAT1` image time sidecar.
- **New A2.2** `0x43100000..0x433FFFFF`: **3MiB** `P08TCK02` per-tick sidecar, inside the already reserved JTAG-only DDR owner window.

The A2.2 sidecar is deliberately **limited to at most 1,024 images**; 256-byte header + 1,024 × 26 × 96-byte tick records fits 3MiB. A larger frame count triggers a **pre-dispatch failure**, rather than claiming support for the entire 10,000-image official TEST or silently truncating samples. No t10k official TEST re-execution is part of A2.2.

Header (`256B`; all little-endian): `0..7 magic P08TCK02`; `8 version=2`; `12 header_bytes=256`; `16 status`; `20 completed`; `24 frames`; `28 ticks_per_frame=26`; `32..39 CNTFRQ`; `40 base`; `44 capacity`; `48 record_bytes`; `52 original descriptor CRC32`; `56 selected trace frame`; `60 zero`; `64..71 dataset start`; `72..79 dataset stop`; `80..251 zero`; `252..255 CRC32 over first 252 bytes`.

Per-tick `96B` record: `0 frame index`, `4 tick index`, `8 external event count`, `12 emitted packets`, `16 acknowledged packets`, `20 flags (final drain=1)`, `24..79 seven ordered CNTVCT u64 timestamps`, `80..87 PL dispatch u64 cycles`, `88..91 CRC32 over first 88 bytes`, `92..95 zero`. CRC is IEEE polynomial `0xEDB88320`, verified by independent Python `zlib.crc32`.

The C codec tests all records before writing any of the 26 tick records for an image. The header is updated as a **separate independently CRC-checked progress record**. Success must show all 1,024 or selected smaller count committed, both A2.1/A2.2 terminal status `0x600D600D`, original P07 journal terminal `0x600D600D`, and no missing/corrupted/tail bytes. Host parser checks all timestamps monotone within A2.1 image-service interval, frames in original declared order, raw A53 frequencies match, clock/descriptor/trace provenance and per-image PL cycle sums. Distinguish **host-side wire integrity** from independent oracle parity and classification accuracy.

## 5. Intrusiveness, uncertainty and controls

Instrumentation is **not passive**. Seven `ISB; MRS CNTVCT_EL0` readings per tick, per-tick struct bookkeeping, and 2,496 bytes/image of sidecar DDR writes/flushes add overhead to the original P07 implementation. The A2.1 image interval is also instrumented, so A2.2 is not a zero-overhead reference. We will **not** subtract a fabricated fixed per-timestamp cost.

Future **physical** protocol (not authorized as an automatic board run):
1. Keep A2.1 user-verified build `fc44b5d...` immutable, separately build A2.2 and record its **actual new ELF SHA256**.
2. Use the **same** original-order synthetic 16-frame pilot and subsequent first1,024 TRAIN-derived held-out validation images, same XSA/bitstream/immutable master/temperature controls, with separate complete **cold-reboot JTAG-only** runs (not multiple independent unique samples).
3. Independently verify P07 full journal, all 26×10 output spikes/routes for every image and selected 26×42 trace against the accepted P03 packed replay for BOTH instrumented versions before trusting timing; do not rerun official t10k by default.
4. Compare paired **A2.1 and A2.2** image-service distributions and overall A53 launch intervals, reporting added overhead and variance; note selected-trace image separately. Profile-only sidecar writes happen *after* A2.1 `after_commit`, but before next frame: affect autonomous throughput and potentially cache/memory contention.
5. Record observed `CNTFRQ_EL0`, optional measured timestamp baseline cost, PL counter clock/source and exact endpoint caveats in an immutable no-overwrite evidence manifest. Reject wrong-version ELF, unsynchronized JTAG setup, missing original-stage checks or any mismatch.

This protocol does not demonstrate physical asynchronous silicon, power efficiency, Loihi hardware parity, or true hardware neuronal execution time alone.

## 6. Native/CI and Vitis reproduction — user-only validation

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p08_a2_2_ticks.py tests/test_p08_a2_timing.py \
  tests/test_p07_a4_official.py tests/test_p07_a4_fault.py

bash -n scripts/build_p08_a2_2.sh
python -m py_compile \
  software/p08/build_p08_a2_2.py \
  src/loihi_twin_v2/p08_a2_2_ticks.py \
  scripts/p08_a2_2_timing_check.py
```

Expected: native C11 `-std=c11 -Wall -Wextra -Werror` C→Python 2-frame × 26-tick parity passes, tests for malformed 3MiB sidecar fail closed, previous selected regression suites all pass, shell and syntax success. **Tests have not been executed by the assistant in the user's connected clone, so no PASS is asserted before seeing the output.**

Only after native checks pass, load Vitis 2025.2 tools as in previous accepted A2.1 build and keep `P03_DIAG_REPORTS` pointing to the **same pinned routed artifact directory**, then:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
export P08_A2_2_BUILD_DIR="/tmp/v3_p08_a2_2_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_a2_2.sh
```

Expected **build-only** markers:
```text
P08_A2_2_A53_VITIS_BUILD_PASS=1
P08_A2_2_ELF_DDR_ISOLATION_PASS=1
P08_A2_2_VITIS_BUILD_PASS=1
P08_A2_2_KV260_LATENCY=NOT_RUN
```

New ELF is `$P08_A2_2_BUILD_DIR/vitis_workspace/p08_a2_2_board.elf`. It must have new marker `P08_A2_2_PER_TICK_KV260_A53_CANDIDATE_V1`, freshly recorded SHA256, and the **same pinned XSA SHA256**; it must **never overwrite** the A2.1 ELF. `vivado/p08_a2_2_xsdb_run.tcl` is **prepared for later A3**, NOT to be run during A2 native/build verification; it demands separate JTAG-only/validation consent, waits all three journals and will collect 1MiB P07 + 64KiB selected trace + 1MiB A2.1 + 3MiB tick raw evidence. A separate guarded, stage-aware physical A3 runner still needs design and user approval.

**Stop at build-only verification. No physical timing result or power characterization has yet occurred.**

## A2.2 regression correction (2026-10-18)

The first user-run regression reported **one assertion failure** in `test_unchanged_accepted_runtime_and_32bit_reserved_ddr`. The test had searched the entire `p08_a2_2_board.c` source text for the bare substring `p07_a2_run_frame` and mistakenly matched a stale **comment** in the independent A2.2 board source; the executable call is `p08_a2_2_run_frame(...)`. The board comment was corrected to describe the actual P03 `WRITE_RESULT` timing, and the test now strips C block/line comments and checks C-like function-call patterns. A separate guard regression verifies that comment-only references pass while a real legacy call fails. No accepted P03/P07 runtime or FPGA bitstream logic was changed by this repair. **The full user-native regression suite still requires a rerun; one isolated helper smoke check is not equivalent to suite acceptance.**
