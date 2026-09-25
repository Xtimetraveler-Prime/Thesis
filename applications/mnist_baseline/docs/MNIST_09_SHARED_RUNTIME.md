# MNIST-09 Shared Runtime Host Interface

**Status:** Complete

## Goal

MNIST-07 and MNIST-08 proved exact physical conformance, but their external-event schedules were compiled into validation bitstreams. MNIST-09 changes the application boundary from a fixed validation corpus to a reusable runtime interface:

```text
host MNIST image
    -> deterministic 16-tick encoder
    -> runtime event stream
    -> one reusable dual-profile FPGA bitstream
    -> physical output spikes
    -> host spike-count decoder
```

The accepted frozen neuron, synapse, arithmetic, weight-storage, and encoding semantics do not change.

Target commands are:

```text
python applications/mnist/scripts/classify_fpga.py --profile cropped-dense --index N
python applications/mnist/scripts/classify_fpga.py --profile native-sparse --index N
```

No Vivado rebuild is required when the image index or selected frozen profile changes.

## Runtime architecture

The reusable bitstream contains the two immutable `mnist-v1` static deployment images once:

```text
profile 0 = cropped-dense
profile 1 = native-sparse
```

Runtime event schedules are **not** compiled into the bitstream. The host loads the requested official MNIST test image, applies the same deterministic application encoder used in software/golden evaluation, and streams each tick's axon events over the existing JTAG/VIO control surface.

The architectural `recurrent_integrated_core_controller_v1` and packaged HLS neuron IP remain unchanged.

## Reuse of the M12.3 VIO shape

MNIST-09 deliberately preserves the existing M12.3 block-design/VIO port shape rather than adding a new debug IP interface.

The existing controls retain these roles:

- `capture_start` — begin a new classification session;
- `capture_step` — execute one algorithmic tick;
- `trace_read_req`, `trace_read_space`, `trace_read_addr` — indexed post-commit trace reads for spaces `0..6`;
- `capture_resetn` — local runtime reset.

For MNIST-09, previously unused trace space **7** is an application-local host command:

```text
trace_read_space = 7
trace_read_addr  = axon_id
pulse trace_read_req
```

Each command appends one axon event to the next tick's external-event buffer. The runtime controller maintains the write cursor and event count internally. Because the frozen FPGA-v1 application uses at most 784 input axons, the existing 12-bit trace address field is sufficient to carry every valid runtime axon ID.

At `capture_step`, the current buffered event count is presented to the unchanged core. After the tick commits, the host reads spike flags using the existing trace-space-3 path. The event buffer cursor/count are then cleared for the next tick.

## Profile/session behavior

At session start, the host places the frozen profile ID in `trace_read_addr` and pulses `capture_start`. The runtime controller then:

1. loads the selected frozen neuron configuration;
2. loads its frozen weight formats, synapse words, CSR row pointers, and empty route table;
3. performs the existing architectural reset;
4. restores zero initial neuron state;
5. exposes `step_ready` to the host.

A new `capture_start` can select either profile for the next classification without rebuilding application-specific logic.

The session completes after 16 committed ticks, matching the frozen application presentation window.

## Host request/result contract

`mnist_app/runtime.py` defines a small machine-readable boundary.

A request records:

- profile and frozen profile ID;
- official MNIST test index and label;
- exact 16-tick external-event schedule;
- total/event-per-tick counts; and
- independent frozen Python-golden prediction/spike counts for validation.

The Tcl-readable `events.tsv` preserves event order and multiplicity per tick.

The physical runtime result records:

- device;
- profile and test index;
- committed tick count;
- total streamed events;
- ten output spike counts; and
- decoded prediction.

The CLI compares physical spike counts/prediction against the independent golden result and writes `comparison.json`.

## Accepted physical runtime validation

One Vivado 2025.2 K26 runtime bitstream was built successfully with both frozen deployments and no compiled MNIST event schedule. The same generated bitstream artifacts were then used for four independent physical classifications:

```text
cropped-dense, index 3, label 0, golden prediction 0
native-sparse,  index 3, label 0, golden prediction 0
cropped-dense, index 1, label 2, golden prediction 2
native-sparse,  index 1, label 2, golden prediction 2
```

All four physical classifications passed the CLI's exact comparison against the corresponding frozen Python-golden spike-count vector and decoded prediction. This demonstrates both required runtime dimensions: switching between the two frozen profiles and changing the host-supplied MNIST image without rebuilding application-specific neuron logic or regenerating the bitstream.

The two selected indices also cover different labels and different event totals, so the accepted result is not merely a replay of the MNIST-07 anchor image.

## Runtime bring-up issues and fixes

MNIST-09 exposed two host/runtime-interface issues during physical bring-up. Neither changed the architectural core.

First, the bitstream script's safety check originally searched for the broad substring `EXTERNAL_EVENTS` and therefore rejected the legitimate static capacity constant `M12_3_MAX_EXTERNAL_EVENTS = 4096`. The guard was narrowed to reject only concrete compiled event arrays/rows/counts. Unit coverage now distinguishes static capacity metadata from forbidden runtime schedules.

Second, runtime event injection intentionally leaves VIO trace space 7 selected. The first host trace-read helper checked `trace_read_ready` before switching the requested space back to a normal read space, while the RTL intentionally deasserts read-ready for command space 7. The helper was corrected to select the requested normal trace space/address first, wait for read-ready, and then issue the read request. The successful four-case physical run used this corrected synchronization sequence.

These fixes affect only validation/runtime transport behavior. Neuron dynamics, synaptic accumulation, quantized weights, event ordering, and the validated architectural core remain unchanged.

## Transport timing boundary

The MNIST-09 transport is intentionally JTAG/VIO because it reuses the already proven physical-control path with minimal new hardware surface. Host/JTAG transaction time is **not** FPGA architectural execution latency and must not be reported as such.

MNIST-10 characterization uses core-visible cycle/tick timing for architectural performance. The JTAG runtime is a functional host interface and correctness/debug transport.

## Tooling

Host/runtime modules:

```text
mnist_app/runtime.py
mnist_app/runtime_static.py
scripts/generate_runtime_profiles.py
scripts/classify_fpga.py
```

Hardware/runtime files:

```text
fpga/mnist_09_runtime_controller_v1.sv
fpga/run_mnist_09_bitstream.sh
fpga/vivado/classify_mnist_09_runtime.tcl
```

The runtime bitstream generator reuses:

- the frozen `mnist-v1` deployments;
- M08 weight decoding;
- the validated Phase-B/core/routing RTL;
- `m12_trace_read_bridge_v1.sv`;
- the existing M12.3 BD wrapper and Vivado project flow; and
- the packaged `neuron_step_v1` HLS IP.

## Completion criteria

All criteria are satisfied:

1. the application pytest suite passed after the final host-side runtime synchronization fix;
2. `--prepare-only` regenerated valid schedules for both frozen profiles;
3. one Vivado 2025.2 K26 runtime bitstream contains both accepted static deployments and no compiled MNIST event schedule;
4. the same bitstream physically classified both profiles without rebuilding;
5. two distinct MNIST test indices were exercised through the runtime path;
6. every accepted runtime result matched independent Python-golden output spike counts and decoded prediction; and
7. documentation keeps JTAG/VIO transport overhead separate from architectural execution timing.
