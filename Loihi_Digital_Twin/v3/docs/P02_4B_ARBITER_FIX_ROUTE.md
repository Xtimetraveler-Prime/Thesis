# P02.4b Arbiter-Fix Routed Candidate

**Date:** 2026-10-06  
**Status:** Routed verification candidate for renewed P02.4b physical acceptance.

## Reason for rebuild

The P02 page/debug arbiter was corrected so a completed slow VIO debug response
is latched until the requester releases `debug_req`. This prevents a held-high
VIO request from re-arming on a stale P05 host response.

Because this changes RTL, the previous P02.3b2 bitstream is historical evidence
only and is not the P02.4b verification candidate.

## Independent routed evidence

The rebuilt K26 shell passed:

```text
PASS: p02_page_host_arbiter_held_request
PASS: P02 held-request arbiter regression completed successfully.
PASS: p02_context_page_bank_walker
PASS: p02_axi128_burst_adapter
PASS: P02.3b1 AXI burst-adapter simulation completed successfully.
PASS: p02_ddr_backing_range_guard
PASS: P02.3b2 DDR range-guard simulation completed successfully.
PASS: P02.3b2 preflight completed successfully.
PASS: P02.3b2 routed timing wns_ns=0.807 whs_ns=0.010
PASS: P02.3b2 physical topology resident_contexts=3 physical_engines=1 hp0=128bit
PASS: P02.3b2 DDR transport backing_base=0x40000000 backing_bytes=0x04000000 burst_bytes=256
PASS: P02.3b2 resources uram=47
```

## Candidate artifact fingerprints

```text
bitstream_sha256=0d96ae6af0cc313ccbd8f9c802aeb0c8c7946bfeabaca3152ef5c7b9d2b23f26
probes_sha256=f4a9cb8c0ba676b86de784444968ec928cc4fc2be979f006bc39380ab86a8dbe
```

The probe fingerprint is unchanged because the VIO topology did not change.

## Acceptance boundary

This routed result proves that the arbiter fix still meets the physical shell
constraints and timing closure. It does not yet accept P02.4b. The five-logical-
core / three-resident-context physical workload must pass using these artifacts
before P02 can close.
