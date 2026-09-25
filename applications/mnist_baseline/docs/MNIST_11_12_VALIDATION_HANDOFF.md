# MNIST-11/12 Validation Handoff

This file defines the first local validation gate for the matched external-reference work. Do not run the 30-image or 10,000-image scopes until this anchor gate is reviewed.

## 1. Pull the development branch

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/mnist-11-12-matched-comparison-dev
git pull --ff-only origin agent/mnist-11-12-matched-comparison-dev
source .venv-mnist/bin/activate
```

## 2. Normal MNIST regression

```bash
pytest applications/mnist_baseline/tests -q
```

This gate exercises the frozen-contract, R=0/R=1 equivalence, Brian mapping validation that does not import Brian itself, Catalyst capacity audit, exact 4,086-edge matrix reconstruction, and the Catalyst wide-fan-in delivered-drive rule.

## 3. Generate the one immutable two-image anchor bundle

Still in `.venv-mnist`:

```bash
python applications/mnist_baseline/scripts/prepare_matched_reference_bundle.py \
  --scope anchor \
  --output applications/mnist_baseline/build/matched-reference/anchor.bundle.json
```

The bundle contains indices 3 and 1, their exact 16-tick schedules, frozen golden spike vectors/predictions, and hashes of the deployment/weight package. Both external backends consume this exact file.

Pure audit commands, still with no external backend required:

```bash
python applications/mnist_baseline/scripts/run_mnist_11_brian2loihi.py --audit-only
python applications/mnist_baseline/scripts/run_mnist_12_catalyst.py --audit-only
```

Expected Catalyst capacity decision:

```text
generic_cpu_graph_fit=True
k26_graph_fit=False
physical_source_supported=False
```

The K26 result is an accepted feasibility boundary inherited from pinned M13.5 source evidence, not a reason to attempt a physical Catalyst MNIST run at this stage.

## 4. MNIST-11 pinned Brian2Loihi anchor

Create the isolated environment:

```bash
deactivate 2>/dev/null || true
bash applications/mnist_baseline/scripts/setup_mnist_11_brian2loihi_env.sh
source .venv-mnist-brian2loihi/bin/activate
```

Run the exact two-image bundle:

```bash
python applications/mnist_baseline/scripts/run_mnist_11_brian2loihi.py \
  --bundle applications/mnist_baseline/build/matched-reference/anchor.bundle.json
```

Each case reports:

```text
project prediction
Brian2Loihi prediction
exact trace mismatch count
effective-weight mismatch count
pass/fail
```

A pass requires all 4,086 Brian effective weights plus all compared current/voltage/spike ticks to match exactly.

## 5. MNIST-12 pinned Catalyst CPU anchor

Create/fetch the isolated pinned Catalyst environment:

```bash
deactivate 2>/dev/null || true
bash applications/mnist_baseline/scripts/setup_mnist_12_catalyst_env.sh
source .venv-mnist-catalyst/bin/activate

export PYTHONPATH="$PWD/Neuromorphic Digital Twin/build/m13_1/catalyst-n1/sdk:$PWD/Neuromorphic Digital Twin/src:$PWD/applications/mnist_baseline"
```

Then run:

```bash
python applications/mnist_baseline/scripts/run_mnist_12_catalyst.py \
  --bundle applications/mnist_baseline/build/matched-reference/anchor.bundle.json
```

The runner executes two independent Catalyst CPU views per image:

1. graph-preserving `784 sources -> 10 outputs` with the exact 4,086 effective-weight matrix and one declared native pipeline tick;
2. an exact delivered-drive control that collapses the same active axon rows into ten per-output fan-in sums and injects those sums directly into the output neurons.

Individual Catalyst graph weights remain signed-int16. The collapsed fan-in sum is **not** restricted to signed-int16: several simultaneously active source weights may sum beyond that range. The pinned Catalyst CPU simulator stores both its external-current buffer and synchronous soma accumulator as signed 32-bit NumPy values, so the control preserves those sums exactly with no clipping or rescaling. This wider direct-current path is a CPU-reference control only and must not be presented as a K26 host-transport capability.

Project-vs-Catalyst differences are allowed and are experimental evidence. The command exits nonzero only if the two independently constructed Catalyst paths disagree after the declared one-tick graph-pipeline normalization. The internal control now compares **every normalized output voltage vector and spike set**, as well as final spike counts/prediction.

### Anchor bring-up harness finding

The first local anchor attempt exposed one adapter-scope issue before index 1 completed:

```text
Catalyst direct current tick 1 neuron 7=-55680 is outside signed int16
```

This was not a Catalyst behavioral failure. The first implementation reused M13.3's signed-int16 direct-stimulus guard, which was intentionally frozen for the smaller hardware-common directed probes. In MNIST, the value is a post-synaptic **fan-in sum** of multiple individually valid int16 weights, and therefore may legitimately exceed int16. The MNIST-12 CPU control now computes the exact sum in signed 32-bit, verifies the pinned simulator's `int32` external-current buffer at runtime, and records the maximum absolute delivered current plus the number of values outside signed-int16 in each result JSON.

## What to return

For the first gate, retain or send the terminal summary from:

```text
pytest
matched bundle generation
MNIST-11 anchor suite
MNIST-12 anchor suite
```

The detailed JSON remains under `applications/mnist_baseline/build/` and can be inspected or archived after the result is accepted.

## Next step after anchor acceptance

No new adapter design should be necessary. Generate the 30-image bundle:

```bash
source .venv-mnist/bin/activate
python applications/mnist_baseline/scripts/prepare_matched_reference_bundle.py \
  --scope corpus \
  --output applications/mnist_baseline/build/matched-reference/corpus.bundle.json
```

and execute the same two backend CLIs against that file. The full 10,000-image scope remains gated on understanding the 30-image result first.
