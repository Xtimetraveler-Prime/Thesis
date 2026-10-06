# P02.4a Physical Attempt 2 — DDR/VIO Discovery Accepted, Object Handle Blocker

**Date:** 2026-10-05  
**Result:** Harness-only failure before first page command

## Newly proven

This attempt repeated and preserved the P02.4 DDR provisioning result:

```text
PASS: P02.4 DDR fixtures provisioned and verified with A53 cores halted
```

Vivado then:

- connected to `hw_server`;
- identified the physical `xck26`;
- programmed the accepted P02.3b2 bitstream;
- discovered exactly two VIO cores;
- selected the P02 paging VIO;
- enumerated every expected paging input/output probe;
- confirmed the complete port/type/width contract.

Observed paging-VIO inventory exactly matched:

```text
vio_input  ports 0..14:
1,1,1,32,32,64,1,1,1,32,32,64,1,1,9 bits

vio_output ports 0..4:
1,1,1,2,64 bits
```

and reached:

```text
PASS: P02.4 paging VIO probes bound by TYPE/PROBE_PORT metadata
```

## Failure

The first call into the page-command helper failed before pulsing
`cmd_start`.

The helper had converted the caller's array of Vivado `hw_probe` objects into
a Tcl list with `array get`, then rebuilt it with `array set`. Vivado object
handles became plain path strings during that serialization boundary.

The resulting failure was:

```text
Invalid option value '...completed_transfers' specified for 'object'
```

No page command executed.

## Correction

The page-command helper now receives the caller's probe-array **name** and uses
Tcl `upvar` to access the original array directly. The output-commit helper
does the same.

This preserves Vivado's live `hw_probe` Tcl objects for:

- `get_property INPUT_VALUE`;
- `set_property OUTPUT_VALUE`;
- `commit_hw_vio`.

The P02.4a offline preflight now explicitly rejects reintroduction of the
`array get` / `array set` serialization pattern.

## Current acceptance state

Accepted physical evidence so far:

- debugger provisioning of real K26 DDR: yes;
- debugger verification of all three provisioned records: yes;
- P02 paging VIO discovery and exact port/width mapping: yes.

Still unproven:

- first physical page-in;
- full physical page-out;
- mutable-only physical page-out;
- burst/byte accounting;
- DDR round-trip fingerprint equality.
