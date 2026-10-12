# P03.3b — Cortex-A53 physical AXI/DDR/packet adapter

**Implementation started:** 2026-10-11  
**Current gate:** P03.3b1 C transport, callback binding and host-native mock
regression — **authored, awaiting independent C compile/test**.  
**Physical board acceptance:** **NOT YET**.  
**Branch:** `agent/v3-p03-autonomous-runtime`; do not merge without approval.

## 1. Independent prerequisite

P03.3a was accepted after the user ran the portable C policy
engine's native regression suite and reported a pass. The P03.2c
physical MMIO page/read/dispatch smoke had already passed on the
FPD 128-bit PS HPM0 -> 1x1 SmartConnect -> 32-bit AXI4-Lite design.
This adapter targets **exactly that hardware ABI**: `0xA4000000`.
Do not accidentally program/use the failed 32-bit-PS-facing candidate.

## 2. Implementation structure

| New file | Responsibility |
|---|---|
| `software/p03/include/p03_hw_adapter.h` | DDR/bank constants, injected I/O/cache interface, per-core metadata and event counts |
| `software/p03/p03_hw_adapter.c` | Strict MMIO page/dispatch/debug commands; packet validation and resident or DDR NEXT-bank delivery |
| `software/p03/include/p03_hw_runtime_bridge.h` | Binds P03.3a C policy to MMIO and deployment hooks |
| `software/p03/p03_hw_runtime_bridge.c` | Page, dispatch, packet drain, barrier and result callback implementations |
| `software/p03/include/p03_hw_xilinx_io.h` | Real A53/Xilinx BSP binding |
| `software/p03/p03_hw_xilinx_io.c` | `Xil_In32`, `Xil_Out32`, cache flush/invalidate and read-only PS width preflight |
| `tests/native/p03_3b_hw_adapter_harness.c` | Host-simulated MMIO CSR state machine and DDR event sink |
| `tests/test_p03_3b_hw_adapter.py` | Strict C11 compilation + native behavioral tests |

No accepted P02/P03.2 RTL or `p03_mmio.h` register addresses
have been changed. The adapter has no PC algorithmic-loop callbacks.
The Xilinx-specific I/O file is isolated from the host-compiled logic.

## 3. Exactly preserved bank mapping and packet ABI

The DDR layout (P02.1) and physical resident host-bank indices
(`rtl/p05_context_memory_fabric.v`) are **not the same enumeration**:

| Logical data | Resident debug bank | DDR record offset | Word format |
|---|---:|---:|---|
| config | 0 | `0x01000` | 128-bit |
| event0 | **6** | `0x54000` | 32-bit |
| event1 | **9** | `0x58000` | 32-bit |
| packet | **8** | `0x64000` | 64-bit |

See the RTL `host_addr_valid` and `host_bank` cases, not assumptions
based on sequential DDR offsets. Debug operations use the existing
eight 32-bit little-word-order WDATA/RDATA registers, issue START
and wait for sticky DONE without errors. Debug **reads** require RVALID.
No slow-request ACK pulse is sampled directly.

The accepted `hardware_p03.py` packet packing is:

```text
bits  0.. 6 destination logical core (7 bits)
bits  7..18 destination axon         (12 bits)
bits 19..28 source compartment       (10 bits)
bits 29..60 target timestep          (32 bits)
bit      61 valid                     (must be 1)
bits 62..63 reserved                 (must be 0)
```

The destination core must be configured, the destination axon must be
**registered as a valid sparse binding from the compiled deployment**,
the source compartment must be in range, and the target timestep must
equal `current_timestep + 1`. NEXT is always
`1 - current_bank`. The per-bank capacity is 4096 events.

When a packet is routed to a **resident** destination, the adapter
writes the destination axon to resident debug bank **6 or 9** at
the destination NEXT count. For a **nonresident** destination, it writes
the 32-bit axon word to its physical DDR backing record's next-event
payload at `0x54000`/`0x58000`, cleans its cache line and orders it
before later PL reads. It never pages a destination just to deliver a
packet. The count increments **only after a successful write**.

The 64-bit output packet itself is read through debug bank 8 after a
completed dispatch. `p03_hw_runtime_bridge.c` drains exactly the
latched emitted packet count, rejects any malformed packet and refuses
a barrier until no CURRENT events or hardware work remain.

## 4. Page and dispatch ownership

`p03_hw_page()` validates core/slot/DDR range, flushes the corresponding
512 KiB DDR record before PL access and invalidates PS DDR caches
around page-out. It uses the original P03 register contract:

- PAGE_CONFIG selects page direction, mutable-only mode and slot.
- PAGE_BASE_LO/HI identify the logical-core 512 KiB record.
- PAGE_COMMAND START is followed by sticky DONE polling. PAGE errors
  or timeouts fail closed; expected transferred bytes and pending write
  bytes are checked.
- A dirty page-out by the scheduler selects the accepted
  **104 KiB mutable-only** transfer (`0x1A000` bytes), preserving
  static config/axon/synapse/route images in DDR.

`p03_hw_dispatch()` forms the 64-bit packed metadata from the
per-core immutable metadata plus the **runtime's current-bank event
count**. It writes slot, bank, timestep and metadata before START,
then checks sticky DONE/errors, packet count, HLS core status and
active core/slot/bank. After success, the dispatched CURRENT count is
retired. The active register is compared against the requested
**nonzero** logical core ID, avoiding the single-core smoke's implicit
assumption that the active core must be zero.

P03.3a retains deterministic round-robin replacement and the
conservative resident dirty rule: after routed packets, all resident
slots are marked dirty until the adapter can return more precise
per-destination dirty acknowledgments.

## 5. Validation and safety gates

The host-native mock simulates the register map and command completion.
The first test suite covers:

- identity/capabilities;
- actual MMIO page and 104 KiB mutable page-out sequencing;
- resident debug command;
- dispatch from logical core **5** (not just core 0);
- resident vs DDR-backed event writes, including exact offsets/counts;
- invalid target timestep, invalid axon binding, event-capacity
  overflow and PAGE hardware errors;
- a two-timestep policy-to-MMIO bridge run with zero emitted packets.

The physical Xilinx BSP transport includes
`p03_hw_xilinx_fpd128_ready()`, which **reads** the actual
`FPD_SLCR.afi_fs` bits `[9:8]` and refuses anything other than
the independently measured 128-bit setting. It never writes those
static PS registers.

Before launching on KV260, the user must still supply/verify:
the 512 KiB DDR backing records and P02 ABI/digests,
deployment metadata and sparse axon bindings, initial event counts,
input event provisioning and cache ownership, board-local result
storage, a standalone ELF and linker regions that do not overlap
`0x40000000..0x43FFFFFF`. Those final launch/result duties belong
to P03.3c. The adapter's injectable fake callbacks are **not**
proof of actual physical packet routing or golden equivalence.

## 6. Exact host verification commands

```bash
cd ~/Git/Thesis
git switch agent/v3-p03-autonomous-runtime
git pull --ff-only origin agent/v3-p03-autonomous-runtime

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p03_3b_hw_adapter.py \
  tests/test_p03_3a_native_runtime.py \
  tests/test_p03_1_runtime_contract.py \
  tests/test_p03_2c_smoke_contract.py
```

Direct native C test:

```bash
cc -std=c11 -Wall -Wextra -Werror -pedantic -O0 -g \
  -I software/p03/include \
  software/p03/p03_runtime.c \
  software/p03/p03_hw_adapter.c \
  software/p03/p03_hw_runtime_bridge.c \
  tests/native/p03_3b_hw_adapter_harness.c \
  -o /tmp/p03_3b_hw_adapter_harness

/tmp/p03_3b_hw_adapter_harness
```

Expected final marker (after independent execution):

```text
PASS: P03.3b host-native hardware adapter suite
```

The full C code and offline tests were authored through the GitHub
connector, which cannot itself compile with the user's installed
Vitis/host gcc environment. **No host-native PASS nor physical
FPGA PASS is asserted until the user runs those commands.**

## 7. Remaining P03.3b steps

- **P03.3b1:** Native and source regression of adapter primitives and
  packet correctness. Await user verification.
- **P03.3b2:** Construct a dedicated standalone A53 adapter probe ELF
  using the accepted FPD128 candidate XSA and a safe 1-core,
  no-packet directed scenario; verify MMIO/cache sequencing with
  actual board-side result mailbox.
- **P03.3b3:** Physical packet production/drain, resident and nonresident
  NEXT delivery, mutable page-out/in and counters; verify against
  directed Python expectations. Only then accept P03.3b.

The subsequent P03.3c launch/runtime result integration and P03.4
seven-timestep/35-dispatch golden comparison remain independent gates.
