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

### 4. Physical route-target write/read witness

Passive VIO-visible registers were added around `recurrent_route_queue_v1` without feeding any values back into architectural computation. Case 07 physically reported:

```text
M12.2 route-target witness case 7: write_seen=1 write_addr=0 write_data=1 read_addr=0 read_data=1
```

Conclusion: **the physical router accepts target axon 1 at route-target address 0 and later reads target axon 1 into the routing work register**. This rules out the Python case, generated SV image, route-target preload interface, route-target RAM contents, route-target read address, and route-target RAM read value.

At this point the mismatch is downstream of `work_target`: either the inactive recurrent-bank append/write path is wrong, or recurrent-bank debug capture is observing the wrong stored value.

### 5. Duplicate recurrent-bank debug read

To test whether synchronous debug readback merely returned a stale value, a host-only case-07 diagnostic read the same committed routed-bank entry twice consecutively without changing the bitstream.

Observed:

```text
M12.2 case07 recurrent-bank duplicate read: bank=1 space=6 addr=0 first=0 second=0
```

The same run still reported:

```text
write_seen=1 write_addr=0 write_data=1 read_addr=0 read_data=1
routed=1
```

Conclusion: **a simple one-read stale-data explanation is ruled out**. Two independent post-commit reads of recurrent bank 1, address 0 both return axon 0 even though the route engine consumed target 1 and reports one routed event. The remaining localization boundary is therefore the recurrent-bank append/write itself versus a deeper bank-storage/readback implementation problem.

## Current localization plan

The next diagnostic bitstream adds passive physical witnesses at the actual inactive recurrent-bank write boundary:

- whether a recurrent-bank write enable fired,
- which bank was selected,
- the write address,
- the write data.

For case 07 the expected write witness is:

```text
write_seen = 1
write_bank = 1
write_addr = 0
write_data = 1
```

Interpretation:

- `write_seen=0` means the route append state never generated the queue write despite incrementing the routed count.
- `write_seen=1` with `write_data=0` means the payload changes between the route work register and the recurrent-bank write interface.
- `write_seen=1`, `write_bank=1`, `write_addr=0`, `write_data=1` while repeated bank reads still return `0` means the fault is below the logical append interface, most likely in physical recurrent-bank RAM inference/storage or its readback implementation.

No expected FPGA output is embedded into this diagnostic path. These signals are passive witnesses only; Python remains the independent golden reference.

## Closure rule

M12.2 remains **in progress** until the discrepancy is explained and the complete physical suite reports:

```text
cases=16
mismatches=0
```

A workaround that changes the Python expected value from axon `1` to axon `0` is not acceptable because it would hide the physical implementation defect rather than establish equivalence.
