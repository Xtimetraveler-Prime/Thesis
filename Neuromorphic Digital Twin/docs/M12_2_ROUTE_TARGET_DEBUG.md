# M12.2 Physical Route-Target Debug Record

Status: **Open physical conformance discrepancy**

Milestone: **M12.2 — exact single-tick Python-vs-physical-FPGA conformance**

Branch: `agent/m12-2-single-tick-physical`

## Problem

The first complete M12.2 physical directed suite executed and captured all 16 single-tick cases successfully, but the exact host-side differential reported one mismatch:

```text
M12.2 case FAIL: 07 threshold-over-refractory-entry mismatches=1
  snapshot.routed_output_axons: expected=(1,) actual=(0,)
```

The other 15 cases passed exactly. For case 07, the neuron state transition, spike result, recurrent-bank selector/count metadata, and routed-event count all matched the Python golden model. The FPGA therefore reported that one recurrent event was generated, but the payload stored in the newly committed recurrent queue was axon `0` instead of axon `1`.

This localizes the discrepancy to the route-target payload path after spike generation rather than to the neuron/HLS transition, threshold/refractory behavior, route count, or host differential logic.

## Expected case-07 route

The independently generated Python case contains:

```text
source neuron: 0
spike: true
route target axon: 1
expected routed_output_axons: (1,)
```

Case 07 is intentionally the only M12.2 directed case that exercises a nonempty spike-to-recurrent-axon route, which is why this defect can coexist with 15 otherwise exact cases.

## Investigations and attempted fixes

### 1. Cross-case contamination hypothesis

The first hypothesis was that repeatedly reconfiguring one physical core in a single JTAG session allowed a prior case to interfere with case 07. A targeted `run_m12_2_case07_probe.sh` flow was added that programs the FPGA and executes case 07 as the first and only case.

Result:

```text
M12.2 targeted case FAIL: 07 threshold-over-refractory-entry mismatches=1
  snapshot.routed_output_axons: expected=(1,) actual=(0,)
```

Conclusion: **cross-case contamination is ruled out**. The failure reproduces from a fresh programming/reset boundary.

### 2. Reset-before-reload hypothesis

A temporary experiment changed the per-case sequence to architectural reset first, then static config/weight/route loading. This did not reach execution. The capture shell timed out waiting for `step_ready` during case preload/reset.

Inspection of `neuron_array_controller_v1` showed why: architectural reset reads and validates `neuron_config_mem`, so valid neuron configuration must exist before `core_reset_start`. The reset-first experiment therefore violated an existing hardware contract and was reverted.

The accepted ordering remains:

```text
load config / weights / route image
        -> architectural reset
        -> load arbitrary runtime neuron state
        -> load external events
        -> execute one tick
```

Conclusion: **the reset-first change was not a valid fix and is not part of the M12.2 design**.

### 3. Python/generator/flattened-index verification

A source-side diagnostic regenerated the exact SystemVerilog include used by the M12.2 bitstream and checked the flattened route-target image.

Observed:

```text
M12.2 DIAG max_routes=1
M12.2 DIAG case07 route_count=1 targets=(1,)
M12.2 DIAG case07 flattened_index=7 flattened_value=1
```

The generated SV block contains seven zero entries followed by:

```systemverilog
16'h0001
```

at case 07's exact flattened index.

Conclusion: **the Python golden model, route freezing, SV corpus generator, and flattened case/route indexing all preserve target axon 1 correctly**. The discrepancy occurs downstream of the generated load image.

## Current localization plan

The next diagnostic bitstream adds read-only physical witnesses around the existing `recurrent_route_queue_v1` route-target path without changing architectural computation:

- whether a route-target write was actually accepted by the router,
- the accepted write address,
- the accepted write data,
- the route-target address read during routing,
- the route-target data read into the router's work register.

The expected case-07 witness is:

```text
write_seen = 1
write_addr = 0
write_data = 1
read_addr  = 0
read_data  = 1
routed_output_axons = (1,)
```

Interpretation:

- `write_data=0` means the defect is between the generated constant image and the router write interface.
- `write_data=1` but `read_data=0` means the accepted route-target memory write/read path is defective or synthesized differently than intended.
- `read_data=1` but routed queue payload `0` means the defect is in the route append / recurrent-bank write path.

No expected FPGA output is embedded into this diagnostic path. These signals are passive witnesses only; Python remains the independent golden reference.

## Closure rule

M12.2 remains **in progress** until the discrepancy is explained and the complete physical suite reports:

```text
cases=16
mismatches=0
```

A workaround that changes the Python expected value from axon `1` to axon `0` is not acceptable because it would hide the physical implementation defect rather than establish equivalence.
