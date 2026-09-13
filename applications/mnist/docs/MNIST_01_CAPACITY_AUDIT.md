# MNIST-01 Capacity Audit and Baseline Architecture

**Status:** Complete

## Purpose

MNIST-01 determines the largest simple dense MNIST classifier that can be mapped onto the existing FPGA-v1 core without changing the frozen platform implementation.

The audit uses the source-controlled K26 capacity profile and RTL parameters. The current physical core supports:

| Resource | Capacity |
|---|---:|
| Physical neurons | 256 |
| Physical axons | 1,024 |
| Synapses | 4,096 |
| Weight formats | 16 |
| Recurrent routes | 4,096 |
| External events per tick | 4,096 |
| Recurrent events per tick | 4,096 |

These are implementation capacities for this project, not claimed Loihi hardware limits.

## Candidate architectures

The original 28x28 MNIST image contains 784 pixels. A direct dense ten-class classifier would therefore require:

```text
784 input axons x 10 output neurons = 7,840 synapses
```

That exceeds the 4,096-synapse physical profile even though the axon and neuron counts fit.

A 14x14 input would require only 1,960 synapses, but it discards more spatial information than necessary. The largest square dense input that fits ten outputs is 20x20:

```text
20 x 20 = 400 input axons
400 x 10 = 4,000 synapses
```

This leaves 96 synapse slots unused while preserving substantially more of the original image than the 14x14 fallback.

The first deployment topology is therefore frozen as:

```text
28x28 uint8 MNIST image
        |
        v
center crop [4:24, 4:24]
        |
        v
20x20 = 400 pixels / external axons
        |
        v
400 -> 10 direct weighted synapses per pixel row
        |
        v
10 LIF output neurons
        |
        v
argmax(output spike count)
```

No recurrent routes are required for this first workload.

## Frozen neuron profile

The first classifier intentionally uses a simple subset already implemented by the platform:

```text
current_decay      = 4096  # full current decay each tick
voltage_decay      = 0     # membrane persists across presentation ticks
reset_voltage      = 0
refractory_ticks   = 0
bias               = 0
```

The floating-point training threshold is `1.0`; export scales threshold and weights together into the existing signed-24-bit integer state domain.

Full current decay means each tick's external drive is consumed on that tick and does not persist in the current register. Voltage remains the temporal integration state.

## Frozen input encoding

Presentation length is fixed at **16 algorithmic ticks**.

Each original uint8 pixel in the 20x20 crop is converted to an integer spike count:

```text
level = round_half_up(pixel * 16 / 255)
level in 0..16
```

The `level` spikes are then distributed deterministically across the 16 ticks using integer cumulative counts. A single pixel therefore appears at most once per tick.

Consequences:

- maximum external events in any tick: 400;
- physical event capacity: 4,096;
- event-capacity margin: 3,696 events/tick;
- encoding is deterministic and requires no random Poisson source;
- axon order within each tick is ascending row-major pixel ID.

## Weight representation plan

The direct network can contain at most 4,000 nonzero weights. Export uses two existing exponent-zero weight formats:

- excitatory, 8 weight bits;
- inhibitory, 8 weight bits.

Using separate sign formats retains one requested-mantissa step and gives effective integer weight steps of 64. A single global scale maps floating weights and threshold into the project's integer state units. Export additionally constrains the scale using a conservative all-white-image accumulation bound so quantization does not intentionally depend on SAT24 clipping.

## Decision

MNIST-01 closes with the following application contract:

```text
source image:           28x28 uint8 MNIST
preprocessing:          exact 20x20 center crop
input axons:            400
output neurons:         10
maximum dense synapses: 4,000
presentation ticks:     16
encoding:               deterministic rate / integer schedule
current decay:          4096
voltage decay:          0
reset:                  0
refractory:             0
bias:                   0
routes:                 0
output decoder:         highest spike count; lowest neuron ID breaks ties
```

No baseline-core semantic or RTL change is required for this architecture.
