# Encoded-weight conformance

M08.3 validates the pure static-weight encoder against Brian2Loihi. M08.4 then
moves the validated representation into production synapses and trace artifacts.

For each of the fifteen M08.3 directed cases:

1. The Python candidate calls `encode_static_weight()` and gives the resulting
   effective integer weight to the existing `NeuromorphicCore`.
2. The Brian2Loihi reference receives the original requested mantissa together
   with its exponent, configured precision, and sign mode.
3. The suite compares Brian2Loihi's directly observable `w_act` value with the
   Python encoder's effective weight.
4. The same one-synapse impulse is compared through current, voltage, and spike
   traces.

## M08.3 result

The complete external suite passed:

```text
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

This means that, for every directed static-weight boundary in the suite:

- the Python encoder produced exactly the same final effective weight as
  Brian2Loihi `w_act`;
- the resulting one-tick synaptic delivery produced identical current, voltage,
  and spike traces; and
- no ambiguity remained in the tested exponent, precision, sign-mode,
  alignment, zero-bit, extrema, or clipping cases.

The pass does not by itself prove that production `Synapse` objects or the
portable trace schema preserve the original encoded representation. That is the
separate purpose of M08.4.

## Directed cases

The suite covers:

- baseline exponent-zero excitatory expansion;
- positive and negative exponents;
- exact and fractional alignment under negative exponents;
- reduced-precision excitatory and inhibitory truncation;
- mixed-mode positive and negative quantization;
- maximum excitatory and minimum inhibitory mantissas;
- extreme negative 21-bit-aligned clipping; and
- zero configured weight bits in all three sign modes.

## M08.4 integration contract

Production `Synapse.weight` remains the one effective integer consumed by the
core. An encoded synapse additionally retains an immutable
`StaticWeightEncoding` containing the source mantissa, shared format,
quantization result, pre-clipping value, final value, and clipping flag.

Use:

```python
synapse = Synapse.encoded(
    axon_id=0,
    target_neuron=0,
    mantissa=-127,
    weight_format=WeightFormat(
        exponent=2,
        num_weight_bits=6,
        sign_mode=WeightSignMode.MIXED,
    ),
)
```

The core still sees only:

```python
synapse.weight
```

Backend traces now have a structured synapse collection, and trace schema v2
serializes the encoding metadata. The reader remains compatible with v1 traces,
which load with an empty structured synapse collection.

The generic Brian2Loihi adapter currently rejects encoded production scenarios
until M08.4 groups connections by exponent, precision, and sign mode. This guard
prevents an encoded synapse from being silently remapped through the legacy
exponent-zero path. The dedicated M08.3 runner remains the validated external
reference path during that refactor.

## Run the conformance suite

Install the comparison dependencies:

```bash
python -m pip install -e ".[dev,compare]"
```

List available cases:

```bash
python examples/run_weight_conformance.py --list
```

Run the complete encoded-weight suite:

```bash
python examples/run_weight_conformance.py
```

Artifacts are written under:

```text
comparison_output/weights/
```

Each case receives normalized Brian2Loihi and Python traces plus a comparison
report. The suite-level JSON records requested and quantized mantissas, format
fields, pre-clip and final effective values, clipping status, and the effective
value reported by Brian2Loihi.
