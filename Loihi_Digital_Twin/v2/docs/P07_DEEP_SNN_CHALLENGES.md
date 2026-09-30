# P07 Deeper Mapped SNN Challenges and Closure Notes

## Purpose

This document records the design decisions, validation pressure points, and closure evidence for P07. It complements `P07_DEEP_SNN_VALIDATION.md`, which defines the six-layer mapped validation workload itself.

P07 did not introduce another FPGA compute architecture. Its purpose was to demonstrate that the P06 compiler and the accepted P05/P06 physical shell could execute a deeper mapped SNN that meaningfully exercised local and remote routing, connection sharing, logical-core capacity pressure, virtualization, and normalized Python/FPGA conformance.

## 1. Making the workload deeper without bypassing the accepted hardware boundary

The accepted P05 shell retains three full logical contexts and services them with one physical HLS engine. A P07 network that simply required more than three simultaneous resident contexts would mostly measure the current physical retention limit rather than validate deeper mapped execution.

P07 therefore uses six feed-forward neuron layers with two neurons per layer and compiles with four compartments per logical core. Deterministic P06 placement packs two layers per logical core:

```text
core 0: layer0 + layer1
core 1: layer2 + layer3
core 2: layer4 + layer5
```

This produces six algorithmic propagation stages while remaining inside the already accepted three-context physical shell.

## 2. Exercising both local and remote traffic in one mapped graph

The placement deliberately alternates traffic scope through the network:

```text
layer0 -> layer1  local
layer1 -> layer2  remote
layer2 -> layer3  local
layer3 -> layer4  remote
layer4 -> layer5  local
```

The resulting compiler report records ten static neural routes: six local and four remote. The physical tick corpus reproduces the expected alternating local/remote packet pattern under both forward and reverse logical-context service order.

## 3. Requiring measurable connection sharing

Every layer transition uses repeated dense 2x2 relative fanout. The P06 mapper normalizes equivalent relative weighted patterns and stores them as reusable synapse templates plus target offsets.

For the accepted P07 deployment:

```text
expanded_connections=28
stored_shared_parameters=6
expanded_per_stored_parameter=4.666666666666667
```

This is project-defined architectural sharing and is not claimed to reproduce native Loihi SRAM compression byte-for-byte.

## 4. Recording a real mapping-capacity failure

P07 also compiles the exact same six-layer workload with the mapping policy artificially limited to two logical cores. The compiler must reject that placement explicitly rather than silently repack beyond policy or truncate the network.

The accepted capacity probe reports:

```text
capacity_probe_result=EXPECTED_REJECTION
capacity_probe_code=logical_core_capacity
capacity_probe_required=3
capacity_probe_limit=2
```

This gives P07 evidence for both successful occupancy and a concrete mapping boundary.

## 5. Preserving a single workload definition

The six-layer network is defined in `src/loihi_twin_v2/workload_p07.py`. Unit tests, JSON generation, mapping analysis, physical-vector generation, and the board runner all derive from that same workload definition. This avoids topology drift between software and hardware validation paths.

## 6. Reusing the accepted physical conformance engine

P07 reuses the accepted P06 Hardware Manager checker and P05 `.bit/.ltx` shell rather than forking another nearly identical VIO/JTAG validation implementation. P07 changes the compiled network and expected physical vectors, then wraps the raw P06-style board result with a P07-specific result schema and evidence bundle.

This keeps the validation delta focused on deeper mapped execution rather than introducing another hardware-control implementation.

## 7. Physical closure

The accepted K26 run used three scenarios:

- `pixel0`
- `pixel0_pixel2`
- `all_pixels`

Each scenario executed seven algorithmic timesteps under both forward and reverse logical-context service order, for 42 directed physical ticks total.

The accepted run observed reset release with the heartbeat changing from `5,903,621` to `8,486,799` before workload execution. All 42 directed ticks reported nonzero physical cycle counts and matched Python-generated state, trace, packet, routed-event, traffic, barrier, identity, and error/status expectations.

The accepted result identity is:

```text
schema=p07-deep-mapped-snn-v1
source_fingerprint=4d11e473a427b153a23226bd3294d6a243292f14931d6d85f6705c9e85146b76
deployment_fingerprint=5e5a16062faa8d92d0077de56fcbd07ff74c602f96e52f98e25ccf49a4af34f9
layers=6
neurons=12
input_channels=4
logical_contexts=3
physical_engines=1
logical_capacity_changed=0
expanded_connections=28
stored_shared_parameters=6
physical_ticks=42
result=PASS
```

The accepted evidence archive is:

```text
hardware/evidence/p07_physical_20260930T022814Z/
```

## 8. Implementation observations

For the directed corpus, physical tick costs ranged from 97 to 143 PL cycles. The highest observed cost occurred on the `all_pixels` first timestep, while later quiescent timesteps completed in 97 cycles. These are synchronous FPGA implementation observations for this workload; they are not native-Loihi timing claims.

P07 did not require another synthesis/place-and-route cycle because the accepted P05 physical architecture was unchanged. Resource occupancy therefore remains the accepted P05 shell occupancy: 47/64 URAM288, 2/144 BRAM tiles, 5,062 LUTs, 7,686 registers, and 2 DSPs at the routed 100 MHz artifact.

## Closure

P07 closes the gap between directed architectural examples and the final application phase. The compiler-generated six-stage network exercises multiple logical cores, local and remote packet delivery, reusable synapse templates, a real logical-core mapping-capacity rejection, virtualized execution on one physical engine, and physical Python/FPGA conformance across 42 directed ticks.

P08 can therefore focus on the application-level MNIST workload and bounded NxTF comparison rather than proving the multicore mapping/execution machinery again.
