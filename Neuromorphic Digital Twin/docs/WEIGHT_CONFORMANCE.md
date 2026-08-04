# Encoded-weight conformance

M08.3 validates the pure static-weight encoder against Brian2Loihi without yet
changing the production `Synapse` or trace schemas.

For each directed case:

1. The Python candidate calls `encode_static_weight()` and gives the resulting
   effective integer weight to the existing `NeuromorphicCore`.
2. The Brian2Loihi reference receives the original requested mantissa together
   with its exponent, configured precision, and sign mode.
3. The suite compares Brian2Loihi's directly observable `w_act` value with the
   Python encoder's effective weight.
4. The same one-synapse impulse is then compared through current, voltage, and
   spike traces.

This separation keeps M08.3 focused on weight arithmetic. Encoded-weight
integration into `Synapse`, comparison scenarios, and trace metadata remains
M08.4.

## Directed cases

The initial suite covers:

- baseline exponent-zero excitatory expansion;
- positive and negative exponents;
- exact and fractional alignment under negative exponents;
- reduced-precision excitatory and inhibitory truncation;
- mixed-mode positive and negative quantization;
- maximum excitatory and minimum inhibitory mantissas;
- extreme negative 21-bit-aligned clipping;
- zero configured weight bits in all three sign modes.

## Run locally

Install the comparison dependencies:

```bash
python -m pip install -e ".[dev,compare]"
```

List available cases:

```bash
python examples/run_weight_conformance.py --list
```

Run one case first:

```bash
python examples/run_weight_conformance.py \
    --case weight-baseline-excitatory
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
report. The suite-level JSON also records requested and quantized mantissas,
format fields, pre-clip and final effective values, clipping status, and the
effective value reported by Brian2Loihi.

## Interpretation

A pass means both of the following agree exactly for that case:

- Brian2Loihi `w_act` equals the Python encoder's final effective weight.
- The effective weight produces identical current, voltage, and spike behavior
  in the one-synapse observable scenario.

A failing direct `effective_weight` comparison identifies an encoding mismatch.
A trace-only mismatch indicates that weight expansion agrees but delivery or
state-update behavior differs.
