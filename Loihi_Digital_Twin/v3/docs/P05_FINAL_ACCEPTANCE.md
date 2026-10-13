# P05 — Final architectural physical regression and observability acceptance

**Status: CLOSED / ACCEPTED within the explicit scope below, 2026-10-13.**
**User authority:** independently supplied positive real KV260
`P05_2I_VERIFY_EXIT=0` output and expressly requested Phase 5
closeout and merging `agent/v3-p05-board-regression` into `main`.

**P04 multi-engine acceleration remains DEFERRED; P06 published
MNIST benchmark selection remains PLANNED.** P05 closure does not
close P04 or imply P06–P09 were executed.

## What was physically accepted

| Gate | Independent physical acceptance | Primary record |
|---|---|---|
| P05.1a | 5 logical / 3 resident, 7 steps, 35 dispatches, 30 packets, 35 CRC checks and five entire DDR images | [First physical](P05_1_FIRST_PHYSICAL_ACCEPTANCE.md) |
| P05.1b | Different 3-core triangle, 12 direct-resident routed packets, 15 actual checkpoints and 3 complete DDR images | [Triangle](P05_1_TRIANGLE_ACCEPTANCE.md) |
| P05.2a | Intentionally corrupted checkpoint produces specific real A53 first-fault (step 2/core 1/state0), not unrelated error | [First mismatch](P05_2A_FIRST_MISMATCH_ACCEPTANCE.md) |
| P05.2b | Actual fast/no-checkpoint mode preserves complete golden 3-core DDR exactly | [Fast equivalence](P05_2B_FAST_ACCEPTANCE.md) |
| P05.2c | One legal reordered [2,0,1] service schedule preserves physical/modeled full DDR and 15 CRCs | [Order](P05_2C_ORDER_ACCEPTANCE.md) |
| P05.2d | Two-destination fanout: 24 live packets, convergent NEXT bank and three full DDR images | [Fanout](P05_2D_FANOUT_ACCEPTANCE.md) |
| P05.2e | Reordered 5-over-3 eight-barrier composite: 48 packets (24 resident/24 nonresident), 37 evictions, 40 CRCs, five complete physical DDR references, with independent HLS output-route packet ordering | [Composite recheck](P05_2E_RECHECK_ACCEPTANCE.md) |
| P05.2f | Signed 24-bit saturation and negative weights, decay/refractory, 30 CRCs, 27 evictions, five complete DDR images | [Arithmetic](P05_2F_ACCEPTANCE.md) |
| P05.2g | Precisely 4096 genuine external CURRENT-bank input events and full DDR success; separate **CRC-valid 4097-event descriptor** rejected by real A53 before hardware action, unchanged DDR | [Capacity](P05_2G_ACCEPTANCE.md) |
| P05.2h | 16 real barriers, 80 FPGA dispatches, 318 actual multi-bank/state/packet checks, 156 routed packets (78 resident/78 nonresident), 77 evictions, five complete DDR images | [Barrier/routing](P05_2H_ACCEPTANCE.md) |
| **P05.2i** | **Final independently confirmed read-only FPGA page AXI counter check: 136,960 read bursts + 33,280 write bursts = 43,581,440 actual 256-byte successful-transfer bytes**, same P05.2h physical trial, five complete DDR records | [Final AXI physical acceptance](P05_2I_ACCEPTANCE.md) |

For the final gate, the user reported the original physical
`P05R` and the independently read, **twice-stable live PL AXI
registers** with measured read/write bursts and 64-bit byte
register matching the frozen Python victim/page replay and
each other, and additionally reported:
`P05_2I_VERIFY_EXIT=0`. This is the expected final
acceptance signal for P05.2i.

**Physical P05.2i evidence directory:**
`/tmp/v3_p05_2i_axi_20261013T010913Z`.
**P05R SHA-256:** `3de43163e98d3368ee1bf52afcdbdc4737840962f449850b842f4e1ab68f4cfb`.
**PL counter witness SHA-256:** `51ea572f1cb83902d6d853da2fc1b657bcfc28371763201fad32de41cc7d01f9`.
Five whole-DDR SHA-256 digests and exact raw timer
measurements are retained in `P05_2I_ACCEPTANCE.md`.

## Important investigative history preserved

- The original P05.2e physical byte-for-byte comparison
  **identified a real expected-output ordering mismatch**:
  normalized logical packet destinations [0,4] versus
  registered hardware route-order [4,0] for core3. The
  original logical Loihi reference and physical evidence
  were not changed. A **separate deterministic physical
  packet-bank layout reference** proved the complete
  actual device DDR matched its hardware contract.
- The first P05.2i run succeeded in neural/DDR/barrier
  validation but the **unforced XSDB debugger memory
  read** was blocked by the debugger's software map at
  `0xA4000044`. With the **KV260 not rebooted**,
  the additional **read-only** `mrd -force` capture
  recovered live physical counters from the same run.
  The final strict verifier passed; no modified HLS,
  bitstream or A53 inference program was required.
  The first blocked step was never mislabeled as PASS.

## Provenance and execution boundary

The accepted architecture uses 5 logical contexts over
3 resident FPGA context slots, **one physical HLS engine**
and an autonomous bare-metal Cortex-A53 scheduler. The PC
provisions initial DDR/model data, launches the binary once,
passively observes, and retrieves physical evidence;
it does **not** schedule per-step dispatches, route
individual packets, select page victims or advance
global barriers. Independent `LogicalChip` model output
is the reference, never substitute FPGA data.

Existing accepted P02/P03 physical PS/PL, FPGA-v2 original
accepted evidence, P03.2c routed bitstream/XSA and frozen
P03 hardware adapters remained intact. P05 introduces
test-driven standalone A53 deployment/control/diagnostic
code, independent fixtures, source-derived packet
ordering and pass/fail tooling rather than rewriting
the original frozen neural reference to fit hardware
results.

The raw full FPGA evidence directories, bitstream/ELF
artifacts and P05R binaries remain on the user's machine;
only independently reported digests/log summaries and
the version-controlled sources are recorded here.
Not all full raw board logs, hashes, or complete
native pytest totals were supplied in conversation;
**do not claim they were uploaded or reexecuted
by the assistant**.

## Precise claims P05 does NOT make

1. **Runtime route-overflow/backpressure recovery not
   physically proven.** P05.2g shows the physical full
   4096-entry external CURRENT bank and pre-MMIO
   rejection of a separately CRC-valid 4097-event
   **deployment**. Host-compiled adapter/C tests
   exercise the 4095/4096 NEXT-bank packet append
   boundary. None of this proves successful recovery
   after a **4097th HLS-generated routed NEXT-bank**
   packet, its stall latency or automatic continuation.
   The design uses fail-closed error behavior where
   tested; never call it hardware flow-control recovery.
2. **AXI scope:** P05.2i measures **PL page-engine HP0
   successful read/write bursts and payload bytes only**.
   It does not measure host provisioning or PS cache
   maintenance, CPU routing stores, whole-system
   traffic/DDR bandwidth, or operating system effects.
3. **Benchmark/performance:** P05's raw PS/PL timing
   numbers apply to the regression profile; they are
   **not** application-level MNIST accuracy, throughput,
   end-to-end energy/power, or calibrated workload
   latency. P06 freezes a source-audited benchmark,
   P07 runs the board-local application and P08
   develops fair time/power/energy measurements.
4. **Parallelism:** Only one physical HLS engine
   was tested. P04 multi-engine execution is explicitly
   deferred; P05 cannot be used as evidence of
   concurrent HLS core execution.

## Closure decision and next steps

**P05.1 COMPLETE; P05.2a–P05.2i COMPLETE within the
listed physical/native coverage. Therefore P05 is
ACCEPTED and CLOSED for its scoped architectural
regression/observability deliverables on the KV260.**
The user expressly authorized the merge to `main`.

Keep the historical unmerged-development acceptance
reports unchanged (they describe conditions at
capture); this final document is the consolidated
post-acceptance record. The roadmap and v3 README
are updated to point here. Any extension of
live route-overflow behavior must be planned and
separately qualified rather than silently asserted
to be P05-accepted. P06 remains the next active
milestone; P04 is deferred.
