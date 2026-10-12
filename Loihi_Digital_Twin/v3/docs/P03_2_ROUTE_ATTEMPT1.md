# P03.2 Route Attempt 1 — XSA Export After Route-Only Implementation

**Date:** 2026-10-06  
**Phase:** P03.2 — PS-visible MMIO control/status shell  
**Result:** Route completed; fixed-XSA export failed because `impl_1` had not run its project-mode `write_bitstream` step.

## Evidence before failure

The route log showed:

```text
PASS: P03.2a AXI-Lite control-register simulation completed successfully.
PASS: P03.2 MMIO contract static checks
PASS: P03.2 HPM0/Vivado ownership static checks
PASS: P03.2 PS-visible MMIO preflight completed successfully.
```

Vivado also reserved:

```text
0xA400_0000 [4K]
```

through the HPM0 SmartConnect, generated the P03 MMIO block design, completed
implementation through routed DRC/report generation, and wrote the routed
checkpoint.

The failure occurred only at:

```text
write_hw_platform -fixed -include_bit
```

with:

```text
ERROR: Unable to get BIT file from implementation run.
Please ensure implementation has been run all the way through Bitstream generation.
```

## Root cause

The P03.2 Tcl launched:

```tcl
launch_runs impl_1 -to_step route_design
```

and later called standalone:

```tcl
write_bitstream -force ...
```

against the opened routed design.

That can produce a valid standalone BIT file, but it does not make the
project-mode `impl_1` run a bitstream-complete run. In Vivado Project Mode,
`write_hw_platform -include_bit` queries the implementation run for its BIT
artifact.

AMD's documented project flow uses:

```tcl
launch_runs impl_1 -to_step write_bitstream
wait_on_run impl_1
```

when the hardware platform must include the implementation-run bitstream.

## Correction

The normal P03.2 implementation flow now launches `impl_1` through
`write_bitstream` and copies the run-owned BIT artifact into the report
directory before fixed-XSA export.

A recovery flow was also added so this already-routed attempt does not need to
repeat synthesis/place/route:

```text
vivado/recover_p03_mmio_xsa.sh
vivado/recover_p03_mmio_xsa.tcl
```

The recovery gate:

1. validates the existing post-route metrics;
2. reopens the existing Vivado project;
3. advances `impl_1` from route completion through `write_bitstream`;
4. exports BIT, LTX, and fixed XSA;
5. fingerprints all three artifacts.

No MMIO RTL, HPM0 address, P02 HP0 data path, or logical architecture changed.
