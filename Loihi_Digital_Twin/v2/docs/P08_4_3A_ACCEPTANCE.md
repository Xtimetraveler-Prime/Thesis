# P08.4.3a Acceptance — Host-Paged K26 Shell

**Status:** Accepted  
**Accepted:** 2026-09-30  
**Source branch:** `agent/p08.4-official-test-evaluation`

P08.4.3a establishes the routed physical shell required for representative P08 MNIST conformance. The shell keeps the accepted P05/P03 physical resource boundary — three complete resident context memories and one P03-compatible HLS compute engine — while replacing the P05 all-resident scheduler/router with the P08 one-dispatch controller.

The physical boundary is therefore:

```text
logical/backing contexts expected by P08 workload: 5
simultaneously resident K26 context slots:          3
physical HLS compute engines:                       1
cross-page packet routing owner:                    host
algorithmic barrier owner:                          host
on-fabric cross-page router:                        no
logical capacity changed:                           no
```

## Independently reproduced routed result

The local routed implementation gate was run after the P08.4.2 compiled-execution conformance gate had been accepted. The accepted local result was:

```text
PASS: p08_paged_dispatch_controller
PASS: P08.4.3a routed timing wns_ns=0.734 whs_ns=0.010
PASS: P08.4.3a physical topology logical_backing=5 resident_contexts=3 physical_engines=1 host_paged=true logical_capacity_changed=false
PASS: P08.4.3a routing ownership cross_page=host global_barrier=host on_fabric_cross_page_router=false
PASS: P08.4.3a resources uram=47
PASS: P08.4.3a artifacts bitstream_sha256=3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83 probes_sha256=e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
P08.4.3a host-paged K26 implementation gate completed successfully.
```

Both setup and hold timing therefore close with positive slack. The implementation retains the expected 47 UltraRAM primitives.

## Frozen physical artifacts

P08.4.3b must use the exact routed artifacts identified by:

```text
p08_host_paged.bit
sha256 = 3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83

p08_host_paged.ltx
sha256 = e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
```

If either hash differs, P08.4.3b must stop rather than silently validating a different physical shell.

## Acceptance boundary

P08.4.3a proves that the real host-paged shell routes and closes timing on the K26 target. It does **not** yet prove execution of the frozen MNIST state on physical fabric. That belongs to P08.4.3b.

P08.4.3b will use fixed P08.4.2 execution state rather than selecting a new image, class, checkpoint, quantization, threshold, or model configuration after observing the official test set.