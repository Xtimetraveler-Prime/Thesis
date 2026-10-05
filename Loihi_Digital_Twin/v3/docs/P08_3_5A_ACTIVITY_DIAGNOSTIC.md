# P08.3.5a Converted-SNN Activity Diagnostic

**Trigger:** P08.3.5 validation gate produced no output spikes  
**Status:** Verification candidate  
**Official MNIST test split:** locked  
**Conversion/execution policy changes:** none

## Observed P08.3.5 failure

The first full 5,000-example validation execution completed the software tests and exact conversion-identity checks, but failed the output-activity acceptance condition:

```text
SNN validation accuracy: 0.100000
ANN validation reference: 0.992600
ANN - SNN delta:          0.892600
total output spikes:      0
silent examples:          5000
tied examples:            5000
```

The 10% result is not evidence of meaningful classification. With zero output spikes every example is a ten-way tie, and the already-frozen lowest-class-index tie rule selects class 0.

The official test split remained locked and no conversion parameter was changed after observing this result.

## Purpose of P08.3.5a

P08.3.5a localizes the first layer at which spike activity disappears before any corrective change is considered. It evaluates the first 100 images of the same frozen validation partition for the same 100 timesteps and records:

- total encoded input spikes;
- total spikes emitted by conv1, conv2, conv3, and conv4;
- number of examples producing at least one spike in each layer;
- maximum instantaneous synaptic input seen by each layer;
- maximum pre-threshold candidate voltage seen by each layer;
- first timestep at which each layer emits any spike; and
- maximum final membrane voltage at the end of the 100-timestep window.

The threshold remains 512 and the accepted conversion fingerprint remains:

```text
686e801cf2459d66772a3517cfff0411746ce97d7a84fb45554ca3ee8345cb75
```

## Interpretation

The diagnostic is intentionally non-corrective.

If conv1 is already silent, the investigation should focus first on the input encoding / integer scale / threshold interface.

If conv1 is active but a later layer is the first silent layer, the investigation should focus first on inter-layer converted weight/bias scale, packet-latency semantics, and threshold accumulation at that boundary.

A layer whose maximum candidate voltage remains far below 512 provides direct evidence that its effective drive is insufficient under the current frozen representation. A layer whose candidate voltage exceeds 512 but records no spikes would instead indicate an execution/simulator bug.

No threshold, DThIR, normalization percentile, weight scale, input encoding, timestep count, reset mode, or decoder is changed by this diagnostic.

## Verification command

```bash
bash scripts/run_p08_3_5a_activity_diagnostic.sh
```

The diagnostic result is written to the Git-ignored local path:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_5a_activity_diagnostic/activity_diagnostic.json
```

The next corrective decision will be made only after this localization result is independently verified.
