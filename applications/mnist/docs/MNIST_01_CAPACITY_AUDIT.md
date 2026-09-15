# MNIST-01 Capacity Audit and Dual-Profile Architecture

**Status:** Complete

## Purpose

MNIST-01 determines how the existing FPGA-v1 core can support useful MNIST classifiers without changing the frozen platform implementation. Rather than forcing one mapping strategy, the application intentionally keeps two hardware-fit profiles so the thesis can compare two different ways of living within the same synapse budget.

## Frozen FPGA-v1 capacity

The source-controlled K26 profile supports:

| Resource | Capacity |
|---|---:|
| Physical neurons | 256 |
| Physical axons | 1,024 |
| Synapses | 4,096 |
| Weight formats | 16 |
| Recurrent routes | 4,096 |
| External events per tick | 4,096 |
| Recurrent events per tick | 4,096 |

These are project implementation capacities, not claimed Intel Loihi hardware limits.

## Why one dense native-input network does not fit

Standard MNIST contains 28x28 = 784 pixels. A direct dense ten-class classifier would require:

```text
784 input axons x 10 output neurons = 7,840 synapses
```

The 784 axons and ten output neurons fit, but 7,840 synapses exceed the physical 4,096-synapse table. That creates a useful architectural choice: preserve all input pixels and remove connectivity, or preserve dense connectivity and reduce input resolution.

## Profile A — native-sparse

```text
28x28 native uint8 MNIST image
        |
        v
784 row-major input axons
        |
        v
sparse direct connectivity
<=4096 stored synapses
        |
        v
10 LIF output neurons
        |
        v
argmax(output spike count)
```

Properties:

```text
source pixels:          784
input axons:            784
output neurons:          10
maximum stored synapses:4096
routes:                    0
```

A completely dense 784x10 float training matrix may exist temporarily in the software trainer, but the accepted deployment must contain no more than 4,096 nonzero/stored connections. The first training strategy is dense training followed by magnitude pruning and masked fine-tuning.

This profile is the primary Loihi-facing MNIST profile because it retains the native 28x28 image representation.

## Profile B — cropped-dense

A 14x14 fallback would use only 1,960 synapses, but the current physical core can support a larger square dense input. The largest simple square input that fits ten fully connected outputs is 20x20:

```text
20 x 20 = 400 input axons
400 x 10 = 4,000 synapses
```

The resulting path is:

```text
28x28 native uint8 MNIST image
        |
        v
center crop [4:24, 4:24]
        |
        v
20x20 = 400 row-major input axons
        |
        v
fully connected 400x10 classifier
<=4000 stored synapses
        |
        v
10 LIF output neurons
        |
        v
argmax(output spike count)
```

This profile leaves only 96 physical synapse slots unused and provides the cleanest dense FPGA-v1 baseline.

## Shared neuron profile

Both classifiers intentionally use the same simple subset already implemented by the platform:

```text
current_decay      = 4096  # full current decay each tick
voltage_decay      = 0     # membrane persists across presentation ticks
reset_voltage      = 0
refractory_ticks   = 0
bias               = 0
```

The floating training threshold begins at `1.0`. Export scales threshold and weights together into the existing signed-24-bit integer state domain.

## Shared input encoding

Presentation length is fixed at **16 algorithmic ticks**.

For either profile, each selected uint8 pixel is converted to an integer spike count:

```text
level = round_half_up(pixel * 16 / 255)
level in 0..16
```

The spikes are distributed deterministically across the 16 ticks using integer cumulative counts. A pixel can therefore appear at most once per tick.

Worst-case event counts are:

| Profile | Input axons | Maximum events/tick | FPGA limit |
|---|---:|---:|---:|
| native-sparse | 784 | 784 | 4,096 |
| cropped-dense | 400 | 400 | 4,096 |

Both profiles preserve ascending row-major axon order inside each tick and require no stochastic Poisson source.

## Shared weight/export plan

Deployment uses the existing M08 encoded-weight representation and CSR row storage. Two exponent-zero formats are sufficient for the initial application:

- excitatory, 8 weight bits;
- inhibitory, 8 weight bits.

The cropped-dense profile may use up to 4,000 stored records. The native-sparse profile must use at most 4,096 stored records and may contain irregular or empty axon rows; this is already legal under the CSR storage contract.

## Frozen dual-profile contract

```text
shared:
  dataset:               standard MNIST
  output neurons:        10
  presentation ticks:    16
  encoding:              deterministic rate / integer schedule
  current decay:         4096
  voltage decay:         0
  reset/refractory/bias: 0
  routes:                0
  decoder:               highest spike count; lowest ID breaks ties

native-sparse:
  preprocessing:         none
  input axons:           784
  stored synapses:       <=4096

cropped-dense:
  preprocessing:         exact center crop [4:24, 4:24]
  input axons:           400
  stored synapses:       <=4000
```

No baseline-core semantic or RTL change is required for either profile. The two-profile experiment intentionally asks whether, under the same physical synapse ceiling, it is better to preserve complete sensory resolution with sparse connectivity or preserve dense connectivity with reduced image resolution.
