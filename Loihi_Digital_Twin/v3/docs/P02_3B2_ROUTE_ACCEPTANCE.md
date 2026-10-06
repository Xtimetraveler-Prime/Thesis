# P02.3b2 Routed Acceptance Record

**Phase:** P02 — DDR-backed logical-core virtualization  
**Sub-milestone:** P02.3b2 — HP0 Vivado integration  
**Accepted:** 2026-10-05

## Independent routed implementation evidence

The routed P02.3b2 gate completed successfully on the K26 target with:

```text
PASS: P02.3b2 routed timing wns_ns=0.875 whs_ns=0.015
PASS: P02.3b2 physical topology resident_contexts=3 physical_engines=1 hp0=128bit
PASS: P02.3b2 DDR transport backing_base=0x40000000 backing_bytes=0x04000000 burst_bytes=256
PASS: P02.3b2 resources uram=47
PASS: P02.3b2 artifacts bitstream_sha256=e9c3fb490f726a1169ed4b7f0c330f5806961c6471e2b13f63f5e042e97421b1 probes_sha256=f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
PASS: P02.3b2 routed HP0 implementation gate completed successfully.
```

## Accepted physical shell

The accepted routed shell therefore demonstrates:

- one P03-compatible HLS physical engine;
- three full resident logical-context slots;
- 47 of 64 K26 URAM288 blocks used;
- positive routed setup slack: +0.875 ns;
- positive routed hold slack: +0.015 ns;
- 128-bit `S_AXI_HP0_FPD` path;
- fixed backing window `0x4000_0000..0x43FF_FFFF`;
- 64 MiB backing capacity for 128 fixed 512 KiB logical-core records;
- 16-beat × 128-bit = 256-byte AXI transfer units;
- physical page-walker, range-guard, burst-adapter, SmartConnect, and HP0 integration;
- generated bitstream and debug-probe artifacts.

The `AWUSER_WIDTH` / `ARUSER_WIDTH` IP Integrator messages remain warnings.
They did not prevent block-design validation, synthesis, routing, timing closure,
DRC/report generation, or bitstream generation.

## Artifact fingerprints

```text
bitstream:
e9c3fb490f726a1169ed4b7f0c330f5806961c6471e2b13f63f5e042e97421b1

debug probes:
f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

## Acceptance boundary

P02.3b2 proves that the complete PL paging path is physically integrated and
routable against K26 DDR through HP0.

It does **not** yet prove a real DDR round-trip of known logical-context data on
the KV260. That is the responsibility of P02.4.
