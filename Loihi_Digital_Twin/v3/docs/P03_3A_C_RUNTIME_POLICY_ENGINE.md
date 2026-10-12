# P03.3a — Portable C runtime policy engine

**Status:** implementation complete; independent host C compiler regression
requested before advancing to P03.3b.  
**Branch:** `agent/v3-p03-autonomous-runtime`; not merged.  
**Predecessor:** P03.2c physically accepted 2026-10-11 (see
`P03_2C_ACCEPTANCE.md`).

## Why this sub-milestone

P03.2c proved the KV260's standalone Cortex-A53 can issue real
page/resident/debug/dispatch commands and collect correct results over
the boot-matched 128-bit FPD -> 32-bit AXI-Lite SmartConnect path.
It did **not** implement autonomous scheduling.

P03.3a isolates the **platform-independent control decisions** in
plain C11 so their ordering and fail-closed behavior can be regression-
tested on the development PC before introducing PS-specific cache,
MMIO, packet layout and DDR ownership bugs.

Code:

- `software/p03/include/p03_runtime.h`: frozen initial native API,
  phase/fault enums and callback interface.
- `software/p03/p03_runtime.c`: heap-free deterministic control loop.
- `tests/native/p03_3a_runtime_harness.c`: native fake hardware
  enforcing completion acknowledgments and operation ordering.
- `tests/test_p03_3a_native_runtime.py`: `cc`/gcc/clang compile
  with `-std=c11 -Wall -Wextra -Werror -pedantic`, then run harness.

The first implementation has no `xil_io.h` dependency, no firmware
linker script, no live MMIO accesses, and does not claim real FPGA
inference. The Cortex-A53 adapter in P03.3b will supply the callbacks.

## Normative policy (from accepted P03.1)

1. Accept 1–128 **unique** logical IDs in `0..127`, 1–3 resident
   slots, and a nonzero number of timesteps. Reject duplicates,
   out-of-range IDs or illegal slot/timestep counts before invoking
   hardware.
2. Lock external algorithmic control as soon as the board-local
   runtime starts.
3. Validate deployment, initialize backing, page in the first
   up-to-three configured logical cores and then load the input.
4. Within each timestep, visit logical cores in compiled deployment
   order and dispatch each **exactly once**.
5. On a resident hit, dispatch without paging. On a miss, choose the
   next slot using a deterministic round-robin victim pointer.
6. If a victim is dirty, **complete and acknowledge page-out before
   page-in**. Never overwrite a dirty unsaved slot.
7. After dispatch, drain exactly the emitted packet count; commit
   packets only to NEXT bank `1 - (timestep & 1)`.
   The packet-route callback must signal how many packets were
   *actually committed*, not just a count requested.
8. The runtime proceeds to barrier only when all configured cores
   completed, no packets remain pending, and the hardware adapter
   confirms quiescence and finalized NEXT counts.
9. Swap CURRENT/NEXT bank ownership **only after** successful
   barrier acknowledgment. Advance the timestep afterward.
10. Keep first fault code and phase sticky; stop on any hardware
    failure or incomplete route. Recovery requires explicit
    reinitialization, never automatic retries across ERROR.
11. Record dispatch/page/event counts and optional monotonic
    timer/PL cycle measurements for the final result callback.

Page-in during initial residency is tracked separately as
`initial_page_ins`. Ordinary replacement increments `page_ins`,
`evictions`, and (for dirty victims) `page_outs`. Page hits count
all dispatches that avoid a new page-in.

The first runtime uses a **conservative dirty-state policy**:
a successfully dispatched logical core becomes dirty; packet insertion
may mutate a different resident destination. With nonzero committed
packets, **all resident slots are conservatively marked dirty** until
P03.3b can report exact per-destination dirty effects. This can cause
extra writebacks, but it prevents losing NEXT events when a resident
destination is evicted before its own dispatch.

## Callback safety boundary

The C runtime does not know AXI register addresses or DDR memory maps.
Each callback must implement the accepted behavior and return zero
**only after successful hardware completion**:

| Callback | P03.3b responsibility |
|---|---|
| `load_deployment` | Parse/validate compiled deployment metadata and IDs |
| `initialize_backing` | Validate 512 KiB P02 records and reserve fixed 64 MiB backing region |
| `page_in` / `page_out` | Write MMIO page commands, poll sticky done/errors, enforce caches/DDR ownership |
| `load_input` | Inject/flush initial event/input data safely |
| `dispatch` | Set bank/timestep/core metadata, issue dispatch command, await done and latched packet count |
| `drain_route` | Read exactly N packets, decode/validate, write destination NEXT bank in resident URAM or DDR, update counts, acknowledge only committed packets |
| `barrier_ready` | Check HLS/page quiescence, no uncommitted packets, finalized NEXT counts |
| `write_result` | Emit autonomous result/counter schema in board-local DDR |
| `read_ticks` | Optional monotonic PS timer for routing/barrier/control/inference intervals |
| `on_error` | Optional fail-closed sticky fault/result publication |

Callbacks may not delegate scheduling, paging decisions, packet-routing
interpretation or barrier decisions to an external PC. Hardware
low-level operations may use the host only *before* launch or for
stopped-board diagnostics.

**Important:** `drain_route` must implement actual physical packet
draining/delivery in P03.3b; simply returning `committed=emitted`
without writing events would violate the callback contract. The
P03.3a mock deliberately stands in for that hardware behavior and
does not prove P03.4 packet correctness.

## Host validation

```bash
cd ~/Git/Thesis
git switch agent/v3-p03-autonomous-runtime
git pull --ff-only origin agent/v3-p03-autonomous-runtime
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p03_3a_native_runtime.py \
  tests/test_p03_1_runtime_contract.py \
  tests/test_p03_2c_full_smoke_candidate.py \
  tests/test_p03_2c_smoke_contract.py
```

With `cc` or `gcc` available, the P03.3a harness compiles the actual
C implementation and reports:

```text
PASS: P03.3a native five-over-three seven-barrier scheduling
PASS: P03.3a partial packet route fails closed
PASS: P03.3a dirty victim must save before reload
PASS: P03.3a barrier quiescence required for bank swap
PASS: P03.3a invalid configuration blocked and reset explicit
PASS: P03.3a complete host-native C runtime policy suite
```

The seven-step mock exercises 35 dispatch callbacks, seven barriers,
35 successfully committed mock packets and deterministic resident
replacement, including negative paths for dirty writeback, partial
packet delivery, barrier refusal and invalid run configuration.

**The source was authored through the GitHub connector, not compiled
in this environment**. The user must run this regression locally and
return the output before P03.3a is accepted.

## Staged plan

- **P03.3a:** Pure C board-local control policy and failure semantics;
  locally compile/run the native mock. No actual packet format or MMIO
  source code in this sub-milestone.
- **P03.3b:** Board adapter and physical packet/bank/DDR ownership.
  First directed one/two-core tests with real MMIO, then full
  5-logical/3-resident mapping.
- **P03.3c:** Standalone ELF with compiled deployment/input, linker
  reservation, board-local result, timer/counter instrumentation and
  fail-closed error record; independent physical start-to-DONE tests.
- **P03.4:** Independent seven-timestep/35-dispatch live K26 golden
  agreement with PC absent from the algorithmic loop.
- **P03.5:** 100 timesteps and normalized golden-model agreement.

Current `P03.3a` callback API is provisional until independent
host-native verification; preserve the accepted P03.1 state/fault
semantics even if the physical adapter later requires an extension.
