# P02 Acceptance — DDR-Backed Logical-Core Virtualization

**Accepted:** 2026-10-06

## Decision

P02 is complete.

The phase progressed from a deterministic DDR ABI and software transfer model
through routed HP0 integration and physical K26 validation.

The final P02.4b acceptance run satisfied the phase-level criterion: the
representative five-logical-core workload executed through three resident
contexts with K26 DDR as the authoritative backing store, while complete final
DDR records matched the frozen golden model.

## Accepted implementation boundary

P02 freezes the following board-local memory architecture for P03:

- fixed 512 KiB backing record per logical core;
- 128 logical-core IDs over a reserved 64 MiB DDR window;
- ten resident payload banks totaling 428 KiB per loaded context;
- three full resident context slots in K26 URAM;
- one P03-compatible HLS execution engine;
- full 428 KiB page-in;
- legal 104 KiB mutable-only page-out;
- PL page walker -> range guard -> 128-bit burst adapter -> SmartConnect ->
  `S_AXI_HP0_FPD`;
- explicit logical-core ID / resident-slot / physical-engine separation;
- CURRENT/NEXT event-bank preservation;
- host-visible physical page and dispatch counters.

## Final physical evidence

The accepted P02.4b run produced:

```text
dispatches=35
barriers=7
routed_packets=30
page_ins=60
page_outs=60
evictions=57
page_hits=8
axi_read_bursts=102720
axi_write_bursts=24960
axi_bytes=32686080
authoritative_backing=k26-ddr
result=PASS
```

All five final 512 KiB DDR backing records matched their expected golden images.

Accepted physical artifacts:

```text
bitstream_sha256=0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26
probes_sha256=f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
wns_ns=+0.807
whs_ns=+0.010
uram=47
resident_context_slots=3
physical_engines=1
```

## Phase claim boundary

P02 proves physical DDR-backed virtualization. It does not remove the PC from
the algorithmic control loop.

The P02 acceptance run still uses the external host for:

- logical-core service order;
- page-victim decisions;
- dispatch/page command issue;
- packet decode and cross-page routing bookkeeping;
- global barrier advancement.

Those responsibilities intentionally move to the Cortex-A53 in P03.

Primary records:

- `docs/P02_1_DDR_ABI.md`
- `docs/P02_2_ACCEPTANCE.md`
- `docs/P02_3B2_ROUTE_ACCEPTANCE.md`
- `docs/P02_4A_ACCEPTANCE.md`
- `docs/P02_4B_ACCEPTANCE.md`
