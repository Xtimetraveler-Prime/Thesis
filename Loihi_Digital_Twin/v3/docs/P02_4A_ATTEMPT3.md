# P02.4a Physical Attempt 3 — VIO Command Formatting Blocker

**Date:** 2026-10-05  
**Result:** Harness-only failure while staging the first page command

## Newly proven

The third board attempt repeated the accepted physical bring-up evidence:

- deterministic P02.4 fixture generation passed;
- all three 512 KiB K26 DDR records were provisioned and verified;
- the accepted P02.3b2 bitstream programmed successfully;
- both VIO cores were discovered;
- the paging VIO inventory exactly matched the expected port/type/width contract;
- metadata-based VIO binding passed;
- live `hw_probe` preservation passed far enough to enter the first
  `PAGE_IN_FULL` command helper.

Observed marker:

```text
PASS: P02.4 paging VIO probes bound by TYPE/PROBE_PORT metadata
```

## Failure

The page-command helper configured VIO outputs with
`OUTPUT_VALUE_RADIX UNSIGNED`, then supplied the record base using the Tcl
literal string:

```text
0x40000000
```

Vivado rejected the `x` character because an UNSIGNED-radix VIO output expects
decimal digits:

```text
The VIO hw_probe value [0x40000000] has an illegal character [x]
... not allowed for radix [UNSIGNED]
```

The command failed while staging VIO output values. The start pulse was not
committed, so no physical page transfer began.

## Correction

The VIO output helper now normalizes every command field through Tcl integer
evaluation before writing it. In particular:

```tcl
set record_base_u [expr {wide($record_base)}]
set_property OUTPUT_VALUE $record_base_u $p(out4)
```

Thus `0x40000000` becomes decimal `1073741824` before it is passed to the
UNSIGNED-radix hardware probe.

The offline P02.4a preflight now checks that this normalization remains present.

## Current physical boundary

Proven:

- real K26 DDR provisioning and byte verification;
- K26 programming and paging VIO discovery;
- exact paging VIO port/type/width mapping;
- live Vivado `hw_probe` object handling up to command staging.

Still unproven:

- first committed page-in command;
- physical DDR -> HP0 -> PL -> resident URAM movement;
- full and mutable page-out;
- physical burst/cycle accounting;
- DDR round-trip byte equality.
