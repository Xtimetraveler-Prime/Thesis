# P02.4a Physical DDR Round-Trip Acceptance

**Phase:** P02 — DDR-backed logical-core virtualization  
**Sub-milestone:** P02.4a — deterministic physical DDR round-trip  
**Accepted:** 2026-10-05  
**Branch:** `agent/v3-p02-4-physical-ddr`

## Result

P02.4a is accepted.

The KV260 physically moved deterministic logical-context payloads through the
accepted DDR paging path:

```text
K26 DDR
  <-> PS S_AXI_HP0_FPD
  <-> AXI SmartConnect
  <-> P02 128-bit burst adapter
  <-> P02 page walker
  <-> resident URAM context banks
```

The final DDR records were dumped and compared byte-for-byte against the
expected full-writeback and mutable-only-writeback images.

## Accepted physical artifacts

P02.4a reused the accepted P02.3b2 routed artifacts without RTL, synthesis, or
route changes:

```text
bitstream SHA256:
e9c3fb490f726a1169ed4b7f0c330f5806961c6471e2b13f63f5e042e97421b1

debug probes SHA256:
f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

## Working bring-up sequence

The accepted hardware procedure is:

1. Boot the KV260 far enough for PS DDR initialization.
2. Start `hw_server`.
3. Generate deterministic P02.4 fixture records.
4. Connect with XSDB.
5. Halt all visible Cortex-A53 execution contexts before touching the reserved
   DDR window.
6. Provision the three 512 KiB records with:
   ```text
   dow -data <file> <address>
   verify -data <file> <address>
   ```
7. Disconnect XSDB.
8. Connect Vivado Hardware Manager to the same `hw_server`.
9. Program the accepted P02.3b2 `.bit` and `.ltx`.
10. Locate the P02 paging VIO.
11. Bind VIO probes using hardware metadata, not display names:
    - `TYPE`;
    - `PROBE_PORT`;
    - `PROBE_PORT_BIT_COUNT`.
12. Preserve Vivado `hw_probe` objects directly with Tcl `upvar`; do not
    serialize them through `array get` / `array set`.
13. Use `UNSIGNED` VIO radix and normalize command values through Tcl integer
    evaluation before `set_property OUTPUT_VALUE`.
14. Execute:
    - full page-in from record 0 into resident slot 0;
    - full page-out from resident slot 0 into record 126;
    - mutable-only page-out from resident slot 0 into record 127.
15. Reconnect with XSDB and dump all three 512 KiB records with binary
    `mrd -bin -file`.
16. Compare the dumps against the deterministic expected records and per-bank
    fingerprints.
17. Reboot the KV260 rather than resuming the Linux instance that was halted for
    the experiment.

## Accepted addresses

```text
source record 0:
0x4000_0000

full-writeback scratch record 126:
0x43F0_0000

mutable-writeback scratch record 127:
0x43F8_0000

exclusive backing-window end:
0x4400_0000
```

## Physical measurements

### Full page-in

```text
semantic bytes:    438,272
PL cycles:         535,830
AXI read bursts:   1,712
AXI write bursts:  0
AXI bytes:         438,272
```

At the generated PL clock of approximately 99.999001 MHz, this corresponds to
approximately 5.358 ms and 81.8 MB/s of semantic payload bandwidth.

### Full page-out

```text
semantic bytes:    438,272
PL cycles:         527,232
AXI read bursts:   0
AXI write bursts:  1,712
AXI bytes:         438,272
```

At approximately 99.999001 MHz, this corresponds to approximately 5.272 ms and
83.1 MB/s of semantic payload bandwidth.

### Mutable-only page-out

```text
semantic bytes:    106,496
PL cycles:         131,328
AXI read bursts:   0
AXI write bursts:  416
AXI bytes:         106,496
```

At approximately 99.999001 MHz, this corresponds to approximately 1.313 ms and
81.1 MB/s of semantic payload bandwidth.

### Aggregate transport accounting

```text
completed page transfers:  3
read bursts:               1,712
write bursts:              2,128
AXI bytes moved:           983,040
pending write bytes:       0
```

The burst counts exactly match the accepted 256-byte AXI transport:

```text
438,272 / 256 = 1,712 bursts
106,496 / 256 =   416 bursts
```

## Byte-exact acceptance

After the three PL-controlled transfers, XSDB dumped the source, full-writeback,
and mutable-writeback records.

The Python verifier accepted all three:

```text
PASS: P02.4 DDR source/full/mutable records dumped for comparison
PASS: P02.4 physical DDR round-trip dumps match expected records
PASS: P02.4a physical DDR round-trip acceptance completed successfully.
```

The comparison covers the complete 512 KiB records, including sentinels in the
non-resident header area and reserved tail. This proves that the page mover
changed exactly the intended resident banks and did not overwrite the
non-resident regions.

## Bring-up issues resolved

Three harness problems were discovered before the successful run. None required
an RTL or bitstream change:

1. **XSDB binary provisioning:** `mwr -bin -file` was not accepted by the
   installed XSDB. The accepted method is `dow -data` followed by
   `verify -data`.
2. **VIO probe lookup:** Hardware-probe display names are connected signal names,
   not guaranteed `probe_inN` / `probe_outN` strings. The accepted method
   binds by `TYPE`, `PROBE_PORT`, and width.
3. **Vivado hardware objects and radix:** `hw_probe` objects must remain live
   Tcl objects; serializing them through arrays converts them to strings.
   `upvar` preserves the objects. VIO outputs configured as `UNSIGNED` also
   require decimal numeric values, so command fields are normalized through Tcl
   `wide()` evaluation.

These corrections are now guarded by the P02.4a offline preflight.

## Claim boundary

P02.4a proves real physical full-context and mutable-only payload transport
between K26 DDR and the accepted three-slot resident URAM fabric.

It does **not** yet prove that the representative five-logical-core /
three-resident-context workload executes with DDR as the authoritative backing
store. That is P02.4b.

It also does not prove board-autonomous scheduling/routing/barrier ownership.
Those remain P03 responsibilities.
