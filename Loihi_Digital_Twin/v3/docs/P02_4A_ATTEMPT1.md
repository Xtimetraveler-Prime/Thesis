# P02.4a Physical Attempt 1 — Provisioning Accepted, VIO Binding Blocked

**Date:** 2026-10-05  
**Result:** Harness-only failure before first page command

## Proven by this attempt

The deterministic fixture was generated with the accepted P02 ABI dimensions:

- full resident payload: 438,272 bytes;
- mutable-only payload: 106,496 bytes;
- 512 KiB record stride;
- source record: `0x4000_0000`;
- full scratch record: `0x43F0_0000`;
- mutable scratch record: `0x43F8_0000`.

XSDB successfully:

1. halted the accessible A53 execution context;
2. downloaded all three 512 KiB records into K26 DDR;
3. verified all three records byte-for-byte using `verify -data`.

Observed marker:

```text
PASS: P02.4 DDR fixtures provisioned and verified with A53 cores halted
```

This establishes that the debugger-side DDR provisioning method works on the
physical KV260.

## What did not execute

Vivado successfully:

- connected to hw_server;
- found the xck26 device;
- programmed the accepted P02.3b2 bitstream;
- rediscovered two VIO cores.

The harness then failed while looking for a probe literally named
`probe_in0`.

Vivado hardware probes are named from connected design signals in the probes
file; the display name is not guaranteed to equal the VIO port name.

No P02 page command was issued before this failure.

Therefore this attempt provides no evidence yet about:

- DDR -> HP0 -> PL -> resident URAM page-in;
- resident URAM -> PL -> HP0 -> DDR page-out;
- physical AXI burst counts;
- physical page-transfer cycles;
- physical payload round-trip equality.

## Correction

`p02_4_vio_roundtrip.tcl` now binds each VIO probe using hardware metadata:

- `TYPE == vio_input` or `TYPE == vio_output`;
- exact `PROBE_PORT` index;
- exact `PROBE_PORT_BIT_COUNT` width.

The expected page-VIO contract remains:

Outputs:

```text
0: cmd_start          1 bit
1: cmd_page_out       1 bit
2: cmd_mutable_only   1 bit
3: cmd_context_slot   2 bits
4: cmd_record_base   64 bits
```

Inputs:

```text
 0 busy                     1
 1 transfer_done            1
 2 start_blocked            1
 3 bytes_transferred       32
 4 completed_transfers     32
 5 last_transfer_cycles    64
 6 error_command            1
 7 error_host               1
 8 error_ddr                1
 9 completed_read_bursts   32
10 completed_write_bursts  32
11 axi_bytes_moved         64
12 protocol_error           1
13 range_error              1
14 pending_write_bytes      9
```

The retry must reboot the KV260 first because the failed attempt intentionally
left the A53 halted.
