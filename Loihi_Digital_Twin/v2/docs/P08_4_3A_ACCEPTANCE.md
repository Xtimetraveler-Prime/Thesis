# P08.4.3a Acceptance Record — Host-Paged K26 Shell

**Status:** Accepted  
**Accepted:** 2026-09-30  
**Source branch:** `agent/p08.4-official-test-evaluation`  
**Follow-on branch:** `agent/p08.4.3b-physical-mnist-conformance`

## Accepted result

P08.4.3a physically implements the P08.2 execution boundary rather than reusing the older P05 three-resident-core scheduler. The routed K26 design retains three full resident context memories and one P03-compatible HLS compute engine, while `p08_paged_dispatch_controller` dispatches one selected resident logical context at a time. Cross-page packet routing and the global algorithmic barrier remain host-owned.

```text
logical backing contexts:       5
resident K26 context slots:     3
physical HLS compute engines:   1
host-paged dispatch:             yes
on-fabric cross-page router:     no
logical capacity changed:        no
```

## Independent local verification

The routed implementation and RTL regression were independently run on the K26-targeted Vivado 2025.2 flow. The accepted output was:

```text
PASS: p08_paged_dispatch_controller
PASS: P08.4.3a routed timing wns_ns=0.734 whs_ns=0.010
PASS: P08.4.3a physical topology logical_backing=5 resident_contexts=3 physical_engines=1 host_paged=true logical_capacity_changed=false
PASS: P08.4.3a routing ownership cross_page=host global_barrier=host on_fabric_cross_page_router=false
PASS: P08.4.3a resources uram=47
PASS: P08.4.3a artifacts bitstream_sha256=3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83 probes_sha256=e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
P08.4.3a host-paged K26 implementation gate completed successfully.
```

Both setup and hold slack are nonnegative. The accepted physical shell uses 47 URAM primitives, matching the retained three-full-context memory architecture.

## Frozen physical artifact identities

```text
p08_host_paged.bit SHA-256 = 3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83
p08_host_paged.ltx SHA-256 = e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
```

P08.4.3b must reject physical execution if these identities drift unless a new routed shell is explicitly reviewed and accepted.

## Acceptance boundary

P08.4.3a proves that the P08 host-paged dispatch shell routes successfully on the K26 target with positive timing margin and the intended memory/compute topology. It does not yet prove the trained MNIST deployment on physical fabric.

P08.4.3b therefore uses this exact shell and the frozen representative P08.4.2 official-test frame to verify a real host-driven context replacement, one deep logical-core dispatch, and exact post-dispatch architectural evidence against the accepted compiled execution. No model, conversion, quantization, threshold, timestep, decoder, or sample-selection decision may change after the official-test result.