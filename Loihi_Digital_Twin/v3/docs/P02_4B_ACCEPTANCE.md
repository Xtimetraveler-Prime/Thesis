# P02.4b Five-Over-Three Physical Acceptance

**Phase:** P02 — DDR-backed logical-core virtualization  
**Sub-milestone:** P02.4b — five-over-three DDR-backed workload  
**Accepted:** 2026-10-06  
**Branch:** `agent/v3-p02-4-physical-ddr`

## Result

P02.4b is accepted.

The KV260 executed the complete directed five-logical-core / three-resident-
context workload with K26 DDR as the authoritative backing store for every
non-resident logical context.

The accepted run completed:

```text
logical cores:       5
resident contexts:   3
physical engines:    1
algorithmic steps:   7
dispatches:          35
barriers:            7
routed packets:      30
page-ins:            60
page-outs:           60
evictions:           57
page hits:           8
AXI read bursts:     102720
AXI write bursts:    24960
AXI bytes moved:     32686080
result:              PASS
```

All five complete final 512 KiB DDR records matched the frozen golden final
images byte-for-byte.

## Accepted routed artifacts

The final physical run used the rebuilt arbiter-fix shell:

```text
bitstream_sha256:
0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26

probes_sha256:
f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

The routed shell retained the accepted physical topology:

```text
resident_context_slots=3
physical_engines=1
uram=47
hp0_width_bits=128
wns_ns=+0.807
whs_ns=+0.010
```

## What was physically demonstrated

The accepted run proves that:

- five logical cores execute through only three resident URAM contexts;
- all three physical resident slots are exercised;
- K26 DDR, not PC RAM, stores complete non-resident logical contexts;
- a deterministic replacement policy can repeatedly evict and reload contexts;
- mutable-only writeback preserves static context banks;
- resident state survives repeated eviction/reload;
- logical packet destination is independent of the resident slot carrying the
  destination core;
- both CURRENT/NEXT event banks participate in the seven-step run;
- all 35 physical HLS dispatches agree with the frozen state/spike/packet
  oracle;
- all seven global barriers occur only after the required packet deliveries;
- transport accounting is internally exact;
- the final five complete DDR records agree byte-for-byte with the golden
  physical-record oracle.

The run also retained diagnostic static-image checks before and after every
mutable eviction. They remained correct throughout the accepted execution.

## Debug/ownership defect resolved before acceptance

Earlier P02.4b attempts exposed a false-response race at the VIO debug boundary.

A slow VIO requester could hold `debug_req` high after an ACK. The original
page/debug arbiter could re-arm on that same level while the P05 memory fabric
still exposed the prior response, allowing stale data to appear as a phantom
second completion.

The accepted arbiter fix:

- latches completed debug ACK/RVALID/ERROR/RDATA;
- keeps that response visible until `debug_req` returns low;
- prevents the held request from being forwarded/re-armed while the response is
  pending;
- accepts a later fresh request normally.

A dedicated held-request RTL regression is now part of the P02.3b2 and P02.4b
preflight gates.

This correction changed the bitstream but did not change VIO topology, so the
probe fingerprint remained unchanged.

## DDR provisioning/retrieval procedure

For reproducible physical access, the accepted P02 procedure is:

1. allow the PS boot path to initialize DDR;
2. halt visible Cortex-A53 execution contexts before touching the temporary
   project DDR window;
3. select the non-processor PSU target, with APU fallback, so XSDB operates on
   physical DDR addresses rather than an A53 MMU context;
4. provision records with `dow -data`;
5. verify provisioning with full `mrd -bin -file` physical readback and
   byte-exact comparison;
6. run the PL paging/dispatch workload;
7. dump final records through the same PSU/APU physical-memory path;
8. compare all five complete records byte-for-byte with the frozen golden
   outputs;
9. reboot rather than resume the halted Linux instance.

## Acceptance boundary

P02.4b closes the P02 research question: non-resident logical-core state can
live authoritatively in K26 DDR while a five-core logical workload executes
through three resident contexts and one physical engine.

P02.4b does **not** claim board-autonomous scheduling, routing, or barrier
ownership. During P02 the external host still supplies low-rate orchestration
and routing bookkeeping. Moving those responsibilities onto the Cortex-A53 is
P03.
