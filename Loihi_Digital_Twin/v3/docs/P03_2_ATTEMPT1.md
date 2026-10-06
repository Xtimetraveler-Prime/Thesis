# P03.2 Offline Attempt 1 — AXI Testbench Sampling Race

**Date:** 2026-10-06  
**Phase:** P03.2 — PS-visible MMIO control/status shell  
**Result:** Offline regression failed; hardware RTL not implicated by this attempt

## Observed result

The focused Python portion completed successfully:

```text
............ [100%]
```

The directed `p03_ps_control_regs` RTL regression then reported repeated:

```text
FAIL: AXI read address handshake timeout
FAIL: AXI write address/data handshake timeout
```

followed by page/dispatch/resident-memory field and completion mismatches.

The test ended with:

```text
FAIL: p03_ps_control_regs failures=45
```

## Diagnosis

The AXI testbench helper sampled `AWREADY`, `WREADY`, and `ARREADY`
one simulation timestep (`#1`) **after** the rising edge on which the DUT
accepted the transaction.

That sampling order is incorrect for this register block.

For example, on a valid write:

1. before the rising edge, `AWVALID && AWREADY` is true;
2. the DUT samples the address on the rising edge and raises
   `aw_pending`;
3. after the nonblocking assignment settles, combinational `AWREADY`
   deasserts;
4. the old testbench then samples `AWREADY` and incorrectly concludes that
   no handshake occurred.

The same issue applies to `WREADY` and to reads through `ARREADY`.

Therefore the timeout failures were a **testbench observation race**, not
evidence that the register block rejected AXI traffic.

The later field/status failures are cascading consequences of the failed helper
bookkeeping and are not treated as independent RTL failures.

## Correction

`rtl/tb/test_p03_ps_control_regs.v` now:

- drives VALID on the falling edge;
- observes READY while it is stable before the accepting rising edge;
- lets the transaction handshake on that rising edge;
- deasserts VALID on the following falling edge;
- samples B/R responses only after the corresponding request has been
  accepted.

The DUT `rtl/p03_ps_control_regs.v` was not changed by this correction.

## Acceptance impact

P03.2 remains **open**.

The corrected offline preflight must pass before any P03.2 route/bitstream
attempt is accepted.
