# P08.1 NxTF MNIST Source Reconstruction

## Status

**Phase:** P08.1 source reconstruction / topology reconstruction  
**Topology state:** accepted project reconstruction on 2026-09-30  
**Training state:** prohibited until P08.2 proves the accepted graph can be hosted correctly  
**Official MNIST test set:** locked

This document separates facts recovered from the NxTF paper and surviving public
code from project reconstruction choices. It is intentionally conservative: an
unpublished or unrecovered detail is not promoted to an NxTF fact merely because
a nearby public tutorial makes one choice.

The four evidence labels used below are:

```text
SOURCED_EXACT
SOURCED_STYLE_OR_RANGE
PROJECT_RECONSTRUCTION
UNKNOWN_NOT_CLAIMED
```

`SOURCED_EXACT` means the cited source directly states or implements the item. It
does not mean an abbreviated paper value such as `~4k` or `341k` has more
numerical precision than the publication provides.

---

## 1. Primary-source search performed

The P08.1 pass checked the following source families before defining a proxy:

1. **NxTF paper/preprint**
   - B. Rueckauer et al., "NxTF: An API and Compiler for Deep Spiking Neural
     Networks on Intel Loihi," JETC 18(3), 2022.
   - DOI `10.1145/3501770`
   - arXiv `2101.04261`
2. **Intel NRC public model repository**
   - `https://github.com/intel-nrc-ecosystem/models`
   - current and historical versions of
     `nxsdk_modules_ncl/dnn/tutorials/a_image_classification_mnist.ipynb`
   - `nxsdk_modules_ncl/snntoolbox/nx_backend.py`
3. **SNN Toolbox repository and history**
   - `https://github.com/NeuromorphicProcessorProject/snn_toolbox`
   - `examples/mnist_keras_loihi.py`
   - historical Loihi example revisions, including commit
     `cc699d761884768077591c39ae50530e63d97677` from 2020-04-22
4. **Author repository/fork search**
   - Bodo Rueckauer's public repositories
   - `rbodo/models`, including its branch/tree history visible through GitHub
5. **Companion/checkpoint/config searches**
   - searches for the paper's `6746` shared-weight count, `341k` expanded
     connections, MNIST checkpoint/config names, and paper-specific model files.

### Search conclusion

No public primary artifact found in this pass contains the exact layer-wise
filter counts, kernels, strides, training checkpoint, or complete experiment
configuration for the paper's **frame-based MNIST Table-2 benchmark**.

The surviving Intel notebook is not that benchmark: it contains 33,802 trainable
parameters and uses 512 timesteps in the saved tutorial, while the paper reports
approximately 7k parameters and 100 timesteps. The historical SNN Toolbox Loihi
example supplies useful conversion/configuration evidence, but its network graph
also does not match the paper's aggregate footprint.

Therefore the exact paper topology remains `UNKNOWN_NOT_CLAIMED`. P08 proceeds
with a bounded `PROJECT_RECONSTRUCTION`, rather than claiming that a reverse-
engineered filter tuple is the unpublished NxTF network.

---

## 2. Reconstruction table

| Field | Classification | P08.1 conclusion |
|---|---|---|
| Input shape | SOURCED_EXACT | MNIST frames are 28 x 28 x 1. |
| Input preprocessing | SOURCED_STYLE_OR_RANGE | Public Intel tutorial scales image values by 1/255. Exact paper preprocessing beyond standard MNIST framing was not recovered. |
| Network family | SOURCED_EXACT | Paper states a four-layer CNN trained with Keras. |
| Exact filters/layer | UNKNOWN_NOT_CLAIMED | Not stated in the paper and no benchmark checkpoint/config was recovered. |
| Exact kernel sizes | UNKNOWN_NOT_CLAIMED | Not stated for the paper benchmark. Public Intel tutorial uses 5x5, 3x3, 3x3, 4x4. |
| Exact strides/padding | UNKNOWN_NOT_CLAIMED | Not stated for the paper benchmark. Public tutorial uses valid convolutions with stride pattern 2,1,2,1. |
| Hidden nonlinearities | SOURCED_STYLE_OR_RANGE | Public tutorial trains ReLU convolution stages; exact paper layer code was not recovered. |
| Output form | SOURCED_STYLE_OR_RANGE | Public tutorial uses a ten-channel 4x4 convolution followed by flatten/softmax. |
| Learned biases | SOURCED_STYLE_OR_RANGE | Public Intel NxTF path extracts/quantizes biases and the tutorial Conv2D layers use biases. Exact paper bias settings were not recovered. |
| Dropout/regularization | SOURCED_STYLE_OR_RANGE | Public Intel tutorial inserts Dropout(0.1) after the first three convolutions. Exact paper regularization was not recovered. |
| Neuron count | SOURCED_EXACT | Paper reports approximately 4k neurons. |
| Trainable parameter count | SOURCED_EXACT | Paper reports approximately 7k trainable parameters. |
| Expanded convolution connections | SOURCED_EXACT | Paper reports 341k discrete connections without connection sharing. |
| Shared weights | SOURCED_EXACT | Paper reports 6,746 shared weights. |
| ANN error | SOURCED_EXACT | 0.74% in the paper. |
| Converted-SNN error | SOURCED_EXACT | 0.79% in the paper. |
| Optimizer | SOURCED_STYLE_OR_RANGE | Public Intel tutorial uses Adam. Exact paper optimizer was not recovered. |
| Learning rate | UNKNOWN_NOT_CLAIMED | Exact paper value not recovered. |
| Batch size | SOURCED_STYLE_OR_RANGE | Public Intel tutorial uses 32; this is not promoted to the paper benchmark. |
| Epoch/model-selection policy | UNKNOWN_NOT_CLAIMED | Tutorial's short example run is not benchmark training evidence. |
| ANN-to-SNN path | SOURCED_EXACT | Paper identifies SNN Toolbox rate-based conversion. |
| SNN Toolbox normalization | SOURCED_STYLE_OR_RANGE | Paper states SNN Toolbox performs parameter normalization; historical Loihi example enables threshold normalization with desired threshold/input ratio 0.75. Exact benchmark config not recovered. |
| Quantization | SOURCED_STYLE_OR_RANGE | Public NxTF/SNN Toolbox code uses integer Loihi parameters; historical/public examples use 8-bit weights, with bias handling varying by path. Exact benchmark quantization config not recovered. |
| Threshold | SOURCED_STYLE_OR_RANGE | Public Intel and historical SNN Toolbox examples use threshold mantissa 512 (`2**9`). Exact benchmark setting not recovered. |
| Reset/leak/refractory behavior | SOURCED_STYLE_OR_RANGE | Historical Loihi SNN Toolbox example selects soft reset; backend supports multiple choices. Exact benchmark neuron settings were not recovered. |
| Input encoding | SOURCED_EXACT | Paper describes rate-based ANN-to-SNN conversion for frame MNIST. Exact per-timestep encoder implementation details remain unrecovered. |
| Decoder/readout | SOURCED_STYLE_OR_RANGE | Paper describes accumulating output spikes/evidence over the run; exact tie/readout implementation was not recovered. |
| Algorithmic timesteps | SOURCED_EXACT | 100 timesteps/sample. |
| NxTF Loihi mapping | SOURCED_EXACT | Paper reports 14 Loihi neurocores. |
| Native-Loihi energy/latency | SOURCED_EXACT | 0.66 mJ/sample and 6.65 ms/sample; contextual reference only, not an FPGA target. |

---

## 3. Source-bounded project reconstruction

Because the exact filter tuple was not recovered, P08.1 retains the strongest
surviving architectural clue—the public Intel tutorial's all-convolutional
spatial scaffold—and searches only the three hidden/output-feature channel
counts that are missing from the paper.

The reconstructed family is:

```text
28 x 28 x 1
  -> Conv2D(F1, 5x5, stride 2, valid) -> 12 x 12 x F1
  -> Conv2D(F2, 3x3, stride 1, valid) -> 10 x 10 x F2
  -> Conv2D(F3, 3x3, stride 2, valid) ->  4 x  4 x F3
  -> Conv2D(10, 4x4, stride 1, valid) ->  1 x  1 x 10
```

The kernel/stride scaffold itself is `PROJECT_RECONSTRUCTION`: it is sourced from
the surviving Intel tutorial, not from a statement that the paper benchmark used
those exact dimensions.

### Deterministic selection rule

`applications/mnist_v2_nxtf/mnist_v2_nxtf/reconstruction.py` enumerates integer
`F1`, `F2`, and `F3` from 1 through 64. It scores each graph by the unweighted
sum of absolute **relative** errors against four paper anchors:

```text
~4,000 neurons
~7,000 trainable parameters
341,000 expanded connections
6,746 shared weights
```

For the score only, ordinary convolution kernel-coefficient count is compared to
the paper's shared-weight count. This is a reconstruction heuristic, not a claim
that Keras kernel count, NxTF native connection storage, and P06 shared-template
storage are identical quantities.

The deterministic best candidate under that project rule is:

```text
F1 = 14
F2 = 20
F3 = 12
```

so the accepted P08.1 project topology is:

```text
28 x 28 x 1
  -> Conv2D(14, 5x5, stride 2, valid) -> 12 x 12 x 14  = 2,016 neurons
  -> Conv2D(20, 3x3, stride 1, valid) -> 10 x 10 x 20  = 2,000 neurons
  -> Conv2D(12, 3x3, stride 2, valid) ->  4 x  4 x 12  =   192 neurons
  -> Conv2D(10, 4x4, stride 1, valid) ->  1 x  1 x 10  =    10 neurons
```

Aggregate reconstruction metrics:

| Quantity | NxTF paper anchor | Accepted reconstruction | Difference |
|---|---:|---:|---:|
| Neurons | ~4,000 | 4,218 | +218 (+5.45%) |
| Trainable parameters incl. biases | ~7,000 | 7,006 | +6 (+0.086%) |
| Bias parameters | not separately reported | 56 | project-derived |
| Convolution kernel coefficients | compared to 6,746 shared weights | 6,950 | +204 (+3.02%) |
| Expanded connections | 341,000 | 338,880 | -2,120 (-0.62%) |
| Algorithmic timesteps | 100 | 100 | exact match |

This candidate is not called "the NxTF topology." It is the accepted
**source-bounded P08 project reconstruction** used for subsequent development.

---

## 4. P06 structural representation

`applications/mnist_v2_nxtf/mnist_v2_nxtf/structural.py` expands the accepted
convolutions into the existing P06 `NetworkSpec` boundary without adding any
training assumptions.

Important representation choices:

- each convolution output channel is a separate P06 population;
- this preserves a future place for the one learned Keras Conv2D bias per output
  channel instead of pretending all neurons in a whole layer share one bias;
- the structural probe currently sets bias to zero because trained biases do not
  exist yet;
- integer connection values are **coefficient-identity tokens**, not inference
  weights;
- repeated spatial uses of one convolution coefficient receive the same token;
- the graph contains exactly 338,880 expanded projection connections.

The P06 shared-template count is expected to differ substantially from the
paper's 6,746 NxTF shared weights. P06 uses the project's normalized template
representation and logical-core partition boundaries; it is not a byte-for-byte
model of Loihi/NxTF convolution compression.

### Capacity probe policy

The P06 default first-fit policy allows 1,024 compartments per logical core. On
this graph that packing is expected to fail the project's modeled 128-KiB
synapse-memory limit on an intermediate logical core even though the network has
only 4,218 neurons.

P08.1 therefore defines a **mapping-only** structural probe at:

```text
compartments_per_core = 900
```

This does not alter the neural graph. It is chosen to keep the same graph within
all current P06 logical resource limits while retaining the mathematical minimum
of five logical cores (`ceil(4218 / 1024) = 5`).

The accepted deterministic probe contract is:

```text
logical cores:                 5
placements / neurons:          4,218
external ingress routes:       2,187
expanded connections:          338,880
P06 stored shared parameters:  64,235
static output routes:           7,860
  local:                          737
  remote:                       7,123
```

Expected per-core P06 usage:

| Core | Compartments | Input axons | Output routes | Synapse bytes | Shared params | Expanded conns |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 900 | 729 | 2,700 | 12,120 | 2,197 | 22,500 |
| 1 | 900 | 729 | 2,700 | 16,336 | 3,211 | 22,500 |
| 2 | 900 | 2,745 | 1,210 | 82,360 | 17,181 | 91,584 |
| 3 | 900 | 2,016 | 729 | 101,024 | 22,680 | 113,400 |
| 4 | 618 | 3,828 | 521 | 95,464 | 18,966 | 88,896 |

Diego independently ran the P08.1 preflight on 2026-09-30. The suite reported
`21 passed`, reproduced the accepted filter tuple and aggregate counts exactly,
and completed the P08.1 source-reconstruction preflight successfully.

---

## 5. Consequence for P08.2

The existing K26 shell retains three full logical contexts at once. The accepted
source-bounded workload requires **five logical cores under the current P06
capacity-safe probe**. It must therefore not be shrunk to fit the shell.

P08.2 must implement deterministic backing-state/context paging for more logical
cores than resident slots, preserving:

```text
logical core identity
per-core architectural state
current/next event banks
routing destination identity
timestep/barrier semantics
resource limits
normalized trace equivalence
```

The five-core P06 count is not expected to equal the paper's 14 Loihi neurocores:
NxTF and P06 have different partitioning and storage models.

P08.2 must also keep channel-specific bias representation in view when it turns
the structural graph into a trained deployment. The topology probe deliberately
does not invent converted-SNN thresholds, trained biases, or quantized weights.

---

## 6. P08.1 acceptance record

P08.1 was accepted on 2026-09-30 after the repository preflight reported:

```text
21 passed
filters=(14, 20, 12)
neurons=4218
params=7006
expanded=338880
```

The accepted status markers are:

```text
TOPOLOGY_STATUS = "P08_1_RECONSTRUCTION_ACCEPTED_P08_2_PENDING"
RECONSTRUCTION_STATUS = "ACCEPTED_P08_1_SOURCE_BOUNDED"
```

This acceptance freezes the reconstruction choice for subsequent P08 work. It
does **not** claim the unpublished NxTF topology was recovered, does not authorize
official-test use, and does not authorize ANN training until P08.2 demonstrates
that the five-logical-core graph is correctly hostable through the accepted K26
virtualization boundary.

**Next phase:** P08.2 — deterministic context paging / architecture adaptation.
