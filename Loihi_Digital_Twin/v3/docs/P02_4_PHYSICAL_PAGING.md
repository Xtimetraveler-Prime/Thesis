# P02.4 — Physical DDR-backed paging acceptance

**Status:** P02.4a accepted; P02.4b planned  
**Phase:** P02 — DDR-backed logical-core virtualization  
**Branch:** `agent/v3-p02-4-physical-ddr`

## 1. Purpose

P02.3b2 proved that the resident-context page path is synthesized, routed, and
connected to K26 DDR through `S_AXI_HP0_FPD`.

P02.4 must now prove that the path moves real context bytes correctly on the
KV260.

P02.4 is intentionally split into:

- **P02.4a — deterministic physical DDR round-trip.** Exercise all resident
  banks through real K26 DDR and verify byte-exact full and mutable-only
  transfers.
- **P02.4b — five-logical-core / three-resident-context workload.** Replace the
  v2 PC-RAM backing role with the accepted K26 DDR records and reproduce the
  normalized v2/Python boundary.

P02.4a is accepted. P02.4b is the remaining P02 acceptance work.

## 2. No FPGA redesign for P02.4a

P02.4a deliberately reuses the accepted P02.3b2 physical artifacts:

```text
bitstream SHA256:
e9c3fb490f726a1169ed4b7f0c330f5806961c6471e2b13f63f5e042e97421b1

debug probes SHA256:
f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

The P02.4a harness refuses to run if the selected bitstream or probes file does
not match those accepted fingerprints.

No synthesis or route step is required for P02.4a.

## 3. Fixture addresses

Three records at the edges of the accepted 64 MiB backing window are used:

```text
source logical record 0:
0x4000_0000

full-writeback scratch record 126:
0x43F0_0000

mutable-writeback scratch record 127:
0x43F8_0000

exclusive backing-window end:
0x4400_0000
```

Each record is exactly 512 KiB.

The scratch records are intentionally far from the low logical IDs used by the
representative five-core workload.

## 4. Deterministic fixture

`scripts/p02_4_fixture.py` builds three ABI-compatible records with
deterministic high-entropy payload bytes.

The payload values are not intended to represent a legal neural workload.
P02.4a is a transport test. High-entropy deterministic bytes make errors in bank
selection, word width, byte order, address calculation, or burst placement
unlikely to alias into a false pass.

Generated files include:

```text
source_core0.bin
full_scratch_core126.bin
mutable_scratch_core127.bin
full_expected_core126.bin
mutable_expected_core127.bin
manifest.json
```

The manifest records complete-record, payload, and per-bank SHA-256
fingerprints.

## 5. Why the header is not rewritten

The accepted P02 page walker moves only resident payload banks:

```text
0x01000 .. 0x6BFFF
```

It does not move:

- the 4 KiB record header; or
- the 80 KiB reserved tail.

Therefore a page-out preserves the destination record's header and reserved
tail.

After physical writeback the header's stored payload digest is intentionally
stale until the control plane refreshes it. That refresh is a separate
operation already modeled by P02.2 and will become part of the P03 runtime.

The P02.4a verifier therefore compares the exact raw record expected from the
hardware operation rather than pretending that the PL page mover updates
control-plane metadata.

## 6. Accepted physical sequence

The accepted one-command harness is:

```text
scripts/run_p02_4_physical_roundtrip.sh
```

The sequence that worked on the physical KV260 is:

1. generate deterministic records and expected results;
2. verify that the selected bitstream/probes match P02.3b2 acceptance;
3. connect with XSDB;
4. halt all visible Cortex-A53 cores;
5. provision each 512 KiB record with `dow -data <file> <address>`;
6. immediately verify each provisioned record with
   `verify -data <file> <address>`;
7. disconnect XSDB;
8. program the accepted P02.3b2 PL image;
9. locate the paging VIO;
10. bind VIO probes by `TYPE`, `PROBE_PORT`, and
    `PROBE_PORT_BIT_COUNT`, not by display name;
11. preserve the returned Vivado `hw_probe` objects with Tcl `upvar`;
12. configure VIO probes with UNSIGNED radix and normalize all command values
    through Tcl `wide()` evaluation before `set_property OUTPUT_VALUE`;
13. command one full page-in from DDR record 0 to resident slot 0;
14. command one full page-out from resident slot 0 to record 126;
15. command one mutable-only page-out from resident slot 0 to record 127;
16. reconnect with XSDB and dump all three DDR records using binary
    `mrd -bin -file`;
17. compare the DDR dumps against byte-exact expected records and fingerprints;
18. reboot the KV260 instead of resuming the halted Linux instance.

## 7. Linux / DDR safety rule

The physical backing window is not yet reserved from Linux by a P03 standalone
linker map or Linux device-tree reserved-memory entry.

Therefore P02.4a **must not write the backing window while Linux is running**.

The harness requires the board to boot far enough for PS DDR to be initialized,
then halts every visible Cortex-A53 core before provisioning the backing window.
The A53s remain halted throughout the test.

After the experiment, reboot the KV260 rather than resuming that frozen Linux
instance.

This is a bring-up restriction, not the final runtime model. P03 will own a
proper board-local memory reservation.

## 8. PC participation boundary

The PC still performs:

- initial fixture provisioning;
- low-rate VIO command issuance;
- post-run DDR dumping;
- reference comparison.

The PC does **not** act as the backing store during any tested page operation.

Once provisioned, the authoritative bytes consumed by page-in are in K26 DDR.
Page-in and page-out payload traffic flows only:

```text
K26 DDR <-> HP0 <-> PL burst adapter <-> PL page walker <-> resident URAM
```

This is the P02.4a claim boundary.

P02.4b must go further and use DDR as the authoritative backing store while the
representative five-over-three workload is dispatched.

## 9. Exact transfer expectations

The complete ten-bank resident payload is:

```text
0x6B000 = 438,272 bytes
```

The mutable-only subset is:

```text
state + event0 + event1 + trace + packet
= 0x1A000
= 106,496 bytes
```

Because the P02.3b1 transport uses exact 256-byte bursts, P02.4a expects:

```text
full page-in:
  1712 read bursts
  438,272 AXI bytes

full page-out:
  1712 write bursts
  438,272 AXI bytes

mutable-only page-out:
   416 write bursts
  106,496 AXI bytes

total:
  1712 read bursts
  2128 write bursts
  983,040 AXI bytes
  3 completed page transfers
  0 pending coalesced write bytes
```

Any mismatch fails the hardware gate.

## 10. Observability

The paging VIO already exposes:

- semantic bytes transferred;
- completed page transfers;
- page command/host/DDR errors;
- last transfer cycles;
- completed AXI read/write bursts;
- AXI bytes moved;
- AXI protocol error;
- DDR range error;
- pending write bytes.

The P02.4a Tcl sequence emits machine-readable cycle counts:

```text
P02_4_PAGE_IN_FULL_CYCLES=...
P02_4_PAGE_OUT_FULL_CYCLES=...
P02_4_PAGE_OUT_MUTABLE_CYCLES=...
```

These are PL clock cycles and must not be confused with algorithmic timesteps.

## 11. Accepted debugger/VIO mechanism

The physical bring-up that worked uses XSDB:

```text
dow -data <file> <address>
verify -data <file> <address>
mrd -bin -file <file> <address> <word_count>
```

The first two commands provision and then verify the deterministic DDR records.
The final command dumps the records after PL paging for byte-exact comparison.

Vivado Hardware Manager controls the paging VIO with
`OUTPUT_VALUE` + `commit_hw_vio` and samples it with
`refresh_hw_vio` + `INPUT_VALUE`.

The hardware-probe objects are discovered by port/type/width metadata and kept
as live Vivado Tcl objects. VIO output values are normalized to decimal integers
because the probes use UNSIGNED radix.

These debugger interfaces are used only for provisioning, low-rate command
issuance, and evidence collection. The payload movement itself remains the
PL/HP0 path.

## 12. P02.4a acceptance

P02.4a passed independently on 2026-10-05. The accepted board run reported:

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

There were no page-command, host, DDR, protocol, range, byte-count,
burst-count, or fingerprint mismatches.

Accepted physical measurements:

```text
PAGE_IN_FULL:
  bytes       438272
  cycles      535830
  read bursts 1712
  AXI bytes   438272

PAGE_OUT_FULL:
  bytes        438272
  cycles       527232
  write bursts 1712
  AXI bytes    438272

PAGE_OUT_MUTABLE:
  bytes        106496
  cycles       131328
  write bursts 416
  AXI bytes    106496

TOTAL:
  completed transfers 3
  read bursts         1712
  write bursts        2128
  AXI bytes           983040
```

Primary acceptance record: `docs/P02_4A_ACCEPTANCE.md`.

## 13. Remaining P02 work

P02.4a does not close P02.

After P02.4a is independently verified, P02.4b will adapt the representative
five-logical-core / three-resident-context host-orchestrated regression so that:

- all five complete backing records are provisioned into K26 DDR;
- non-resident page replacement uses the PL DDR page mover;
- the PC no longer carries authoritative non-resident context bytes;
- logical IDs remain independent of resident slot identity;
- CURRENT/NEXT event semantics remain unchanged;
- normalized output matches the accepted v2/Python boundary.

P03 then moves the remaining scheduling/routing/barrier orchestration itself
onto the A53.
