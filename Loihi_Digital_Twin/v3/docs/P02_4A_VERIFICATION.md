# P02.4a Verification and Acceptance

**Status:** Complete; accepted 2026-10-05  
**Branch:** `agent/v3-p02-4-physical-ddr`  
**Accepted:** 2026-10-05

## Offline gate

Run from the v3 root:

```bash
bash scripts/run_p02_4a_preflight.sh
```

Expected final marker:

```text
PASS: P02.4a software preflight completed successfully.
```

The gate checks:

- P02 DDR ABI/reference tests;
- deterministic physical fixture tests;
- exact full/mutable transfer byte counts;
- frozen fixture fingerprints;
- offline generate/verify CLI behavior;
- shell/Tcl delimiter sanity.

## Hardware prerequisites

1. Use the accepted P02.3b2 bitstream/probes:
   - bitstream SHA-256
     `e9c3fb490f726a1169ed4b7f0c330f5806961c6471e2b13f63f5e042e97421b1`
   - probes SHA-256
     `f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe`
2. Boot the KV260 normally far enough for PS DDR to be initialized.
3. Have JTAG/hw_server available.
4. Have Vivado and XSDB 2025.2 on PATH.
5. Do not rely on the running Linux instance after the test starts. The harness
   halts all visible Cortex-A53 cores before touching the DDR backing window.
6. Reboot the board after the test.

## Physical gate

```bash
bash scripts/run_p02_4_physical_roundtrip.sh
```

The script performs fixture generation, A53 halt, K26 DDR provisioning, FPGA
programming, VIO-controlled page operations, DDR dumping, and byte-exact
comparison.

## Required page-operation evidence

```text
PAGE_IN_FULL:
  438272 semantic bytes
  1712 AXI read bursts

PAGE_OUT_FULL:
  438272 semantic bytes
  1712 AXI write bursts

PAGE_OUT_MUTABLE:
  106496 semantic bytes
  416 AXI write bursts

TOTAL:
  3 completed transfers
  1712 read bursts
  2128 write bursts
  983040 AXI bytes
  0 pending write bytes
```

The Tcl sequence also records the physical PL-cycle count for each page
operation.

## Required final markers

```text
PASS: P02.4 deterministic DDR fixture generated
PASS: P02.4 DDR fixtures provisioned and verified with A53 cores halted
PASS: P02.4 PAGE_IN_FULL transfer completed
PASS: P02.4 PAGE_OUT_FULL transfer completed
PASS: P02.4 PAGE_OUT_MUTABLE transfer completed
PASS: P02.4 VIO physical paging sequence completed successfully
PASS: P02.4 DDR source/full/mutable records dumped for comparison
PASS: P02.4 physical DDR round-trip dumps match expected records
PASS: P02.4a physical DDR round-trip acceptance completed successfully.
```

## Accepted result

Independent hardware verification completed successfully.

Observed physical results:

```text
P02_4_PAGE_IN_FULL_CYCLES=535830
P02_4_PAGE_IN_FULL_READ_BURSTS=1712
P02_4_PAGE_IN_FULL_WRITE_BURSTS=0
P02_4_PAGE_IN_FULL_AXI_BYTES=438272

P02_4_PAGE_OUT_FULL_CYCLES=527232
P02_4_PAGE_OUT_FULL_READ_BURSTS=0
P02_4_PAGE_OUT_FULL_WRITE_BURSTS=1712
P02_4_PAGE_OUT_FULL_AXI_BYTES=438272

P02_4_PAGE_OUT_MUTABLE_CYCLES=131328
P02_4_PAGE_OUT_MUTABLE_READ_BURSTS=0
P02_4_PAGE_OUT_MUTABLE_WRITE_BURSTS=416
P02_4_PAGE_OUT_MUTABLE_AXI_BYTES=106496

P02_4_COMPLETED_TRANSFERS=3
P02_4_READ_BURSTS=1712
P02_4_WRITE_BURSTS=2128
P02_4_AXI_BYTES=983040
```

Final accepted markers:

```text
PASS: P02.4 VIO physical paging sequence completed successfully
PASS: P02.4 DDR source/full/mutable records dumped for comparison
PASS: P02.4 physical DDR round-trip dumps match expected records
PASS: P02.4a physical DDR round-trip acceptance completed successfully.
```

This accepts real physical DDR-to-resident and resident-to-DDR transport for all
ten full-context banks plus the accepted mutable-only subset.

It does not yet close P02. P02.4b must run the representative five-logical-core
/ three-resident-context workload with K26 DDR as the authoritative
non-resident backing store.

Primary record: `docs/P02_4A_ACCEPTANCE.md`.


## XSDB 2025.2 provisioning note

The first physical attempt exposed a debugger-command compatibility issue before
any PL page operation began: the local XSDB rejected the `mwr -bin -file`
form used by the initial harness.

The provisioning step now uses the XSDB binary-download interface:

```text
dow -data <file> <address>
verify -data <file> <address>
```

for each of the three 512 KiB records.  This both provisions the record and
verifies the exact binary bytes before the PL page mover is exercised.


## Physical attempt 1 update

The first post-XSDB-fix board attempt successfully provisioned and verified all
three 512 KiB DDR records, then stopped before any page command because the
initial Vivado harness assumed hardware-probe display names matched
`probe_inN` / `probe_outN`.

The retry candidate binds the VIO using `TYPE`, `PROBE_PORT`, and
`PROBE_PORT_BIT_COUNT` metadata instead. See
`docs/P02_4A_ATTEMPT1.md`.

The board must be rebooted before retrying because the attempt intentionally
left the A53 halted.


## Physical attempt 2 update

The second board attempt independently confirmed the entire P02 paging VIO
port/type/width inventory and passed metadata-based binding. It then stopped
before pulsing the first page command because the helper serialized Vivado
`hw_probe` objects through `array get` / `array set`.

The retry candidate preserves the live probe objects using Tcl `upvar`.
See `docs/P02_4A_ATTEMPT2.md`.


## Physical attempt 3 update

The third board attempt entered the first `PAGE_IN_FULL` helper after
successful VIO binding, then stopped while staging the 64-bit DDR base because
the VIO output used UNSIGNED radix while the helper passed a hexadecimal string.

The retry candidate converts all VIO command values to Tcl wide integers before
`set_property OUTPUT_VALUE`. See `docs/P02_4A_ATTEMPT3.md`.


## Final working harness notes

The accepted run required all of the following harness behaviors:

- XSDB provisioning through `dow -data` followed by `verify -data`;
- binary post-run DDR dumping with `mrd -bin -file`;
- VIO lookup by hardware metadata rather than display names;
- preservation of live Vivado `hw_probe` objects using Tcl `upvar`;
- decimal normalization of VIO values when using UNSIGNED radix.

These are now the documented P02.4a reproduction path. The earlier failed
attempts remain preserved in `P02_4A_ATTEMPT1.md`,
`P02_4A_ATTEMPT2.md`, and `P02_4A_ATTEMPT3.md` as bring-up history.
