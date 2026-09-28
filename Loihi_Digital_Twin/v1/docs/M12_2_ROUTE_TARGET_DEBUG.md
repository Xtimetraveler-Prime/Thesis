# M12.2 Physical Route-Target Debug Record

Status: **Resolved — M12.2 physical conformance closed**

Milestone: **M12.2 — exact single-tick Python-vs-physical-FPGA conformance**

Branch: `agent/m12-2-single-tick-physical`

## Problem

The first complete M12.2 physical directed suite executed and captured all 16 single-tick cases successfully, but the exact host-side differential reported one mismatch:

```text
M12.2 case FAIL: 07 threshold-over-refractory-entry mismatches=1
  snapshot.routed_output_axons: expected=(1,) actual=(0,)
```

The other 15 cases passed exactly. For case 07, the neuron state transition, spike result, recurrent-bank selector/count metadata, and routed-event count all matched the Python golden model. The FPGA therefore reported that one recurrent event was generated, but the host-visible payload in the newly committed recurrent queue appeared as axon `0` instead of axon `1`.

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

Conclusion: **the Python golden model, route freezing, SV corpus generator, and flattened case/route indexing all preserve target axon 1 correctly**.

### 4. Physical route-target write/read witness

Passive VIO-visible registers were added around `recurrent_route_queue_v1` without feeding any values back into architectural computation. Case 07 physically reported:

```text
M12.2 route-target witness case 7: write_seen=1 write_addr=0 write_data=1 read_addr=0 read_data=1
```

Conclusion: **the physical router accepts target axon 1 at route-target address 0 and later reads target axon 1 into the routing work register**. This rules out the Python case, generated SV image, route-target preload interface, route-target RAM contents, route-target read address, and route-target RAM read value.

### 5. Duplicate recurrent-bank debug read

To test whether synchronous debug readback merely returned a one-off stale value, a host-only case-07 diagnostic read the same committed routed-bank entry twice consecutively without changing the bitstream.

Observed:

```text
M12.2 case07 recurrent-bank duplicate read: bank=1 space=6 addr=0 first=0 second=0
```

Conclusion: **the problem is reproducible across repeated host reads**. This ruled out a single transient/stale VIO sample, but it did not yet distinguish queue storage from a bank-selection alignment error in the synchronous debug path.

### 6. Physical recurrent-bank write witness

Passive witnesses were added at the exact RAM write boundary. Case 07 physically reported:

```text
M12.2 recurrent-bank write witness case 7: write_seen=1 bank=1 addr=0 data=1
```

Combined with the route-target witness, the physical datapath is now proven through the append boundary:

```text
route target image = 1
    -> route-target RAM read = 1
    -> work_target = 1
    -> bank-1 write enable fires
    -> bank-1 write address = 0
    -> bank-1 write data = 1
```

This result rules out the routing decision, append data path, bank choice, and write address/data generation.

## Identified root cause

Source inspection after the write witness exposed an observability bug in `recurrent_route_queue_v1`.

The recurrent event banks are synchronous memories. A debug request for bank 1 asserts `debug_bank=1` during the request cycle and the bank-1 RAM output becomes valid on the subsequent clocked response. However, `debug_rdata` was selected using the **live** request signal:

```systemverilog
assign debug_rdata = debug_bank ? bank1_mem_rdata : bank0_mem_rdata;
```

The M12 trace bridge only drives `debug_bank=1` while issuing the request. Once that pulse ends, the live selector returns to bank 0 before the synchronous bank-1 response is consumed. The RAM write can therefore be completely correct while the response mux exposes bank 0's stale/zero data. Repeating the same request does not help because every request repeats the same selector timing error, explaining the observed `first=0 second=0` result.

The fix latches the requested bank when `debug_re` is accepted and uses that registered selector for the synchronous response:

```systemverilog
debug_bank_latched <= debug_bank;
assign debug_rdata = debug_bank_latched ? bank1_mem_rdata : bank0_mem_rdata;
```

This changes only the debug/readback alignment. It does **not** modify spike routing, recurrent queue writes, bank counts, route order, tick timing, or any frozen M10 computational semantics.

A dedicated RTL regression (`tb_m12_2_recurrent_debug_bank_latch.sv`) deliberately requests bank 1 and then returns the live `debug_bank` input to bank 0 before the response. The expected response remains the bank-1 payload. `run_m12_2_recurrent_debug_bank_latch_sim.sh` provides the Vivado/XSIM regression runner.

## Next verification

Before closing the defect, the corrected RTL must pass:

1. the targeted debug-bank XSIM regression;
2. the focused/full Python regression suites;
3. a rebuilt M12.2 bitstream;
4. the physical case-07 probe, which must change from `actual=(0,)` to `actual=(1,)`;
5. the complete 16-case physical suite with `mismatches=0`.

The passive route-target and recurrent-bank write witnesses remain useful until physical closure, after which they may be removed from the final M12.2 capture image if they are no longer needed.

## Closure rule

M12.2 remains **in progress** until the discrepancy is physically closed and the complete suite reports:

```text
cases=16
mismatches=0
```

Changing the Python expected value from axon `1` to axon `0` is explicitly not an acceptable workaround.


## Final resolution and closure

The physical recurrent-bank write witness reported:

```text
M12.2 recurrent-bank write witness case 7: write_seen=1 bank=1 addr=0 data=1
```

This proved the route engine and queue-write datapath were correct all the way to the bank-1 RAM write interface. The final root cause was the synchronous debug response bank selector, not architectural recurrent routing.

`recurrent_route_queue_v1` originally selected `debug_rdata` with the live `debug_bank` request signal. Because the recurrent banks use registered synchronous reads and the trace bridge releases the request selector before the response cycle, a bank-1 request could correctly load `bank1_mem_rdata` while the output mux had already switched back to bank 0. The correction latches the requested bank when `debug_re` is accepted and holds that selector through the registered response.

A dedicated RTL regression reproduces the exact timing condition by requesting bank 1, immediately returning the live selector to bank 0, and requiring the synchronous response to remain the bank-1 payload.

After rebuilding the corrected physical image, case 07 passed exactly and the complete M12.2 directed physical corpus completed:

```text
cases=16
mismatches=0
```

M12.2 is therefore closed. The expected route target remained axon `1`; no golden-model expectation was weakened to obtain the pass.
