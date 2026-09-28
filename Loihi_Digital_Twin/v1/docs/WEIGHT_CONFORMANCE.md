# Encoded-weight conformance

M08.3 validated the pure static-weight arithmetic against Brian2Loihi. M08.4
moves that validated representation into production synapses, the generic
Brian2Loihi backend, and portable trace artifacts.

## M08.3 result

The initial dedicated arithmetic suite passed:

```text
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

For every directed static-weight boundary in that suite:

- the Python encoder produced exactly the same final effective weight as
  Brian2Loihi `w_act`;
- the resulting one-tick synaptic delivery produced identical current, voltage,
  and spike traces; and
- no ambiguity remained in the tested exponent, precision, sign-mode,
  alignment, zero-bit, extrema, or clipping cases.

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

## M08.4 production contract

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

Backend traces have a structured synapse collection. Trace schema v3 serializes
the encoding metadata alongside M09 routing data. The reader remains compatible
with v1 and v2 traces; v1 loads with an empty structured synapse collection.

## Generic Brian2Loihi grouping

The generic adapter translates each scenario synapse into a requested mantissa
and a shared format key:

```text
(exponent, num_weight_bits, sign_mode)
```

- Encoded synapses use their original requested mantissa and `WeightFormat`.
- Legacy integer synapses retain the original exponent-zero mapping and are
  assigned excitatory or inhibitory sign mode from the effective weight.
- Connections sharing the same format key are placed in one `LoihiSynapses`
  object.
- Each group records original scenario indices so observed Brian2Loihi `w_act`
  values are restored to scenario order.

This grouping is a backend translation concern. It does not change the core's
single integer accumulation path.

## Production conformance path

The fifteen directed cases construct `Synapse.encoded(...)` objects and run
through the same generic backends used by ordinary scenarios:

```text
production ComparisonScenario
        ├── Python backend → NeuromorphicCore
        └── generic Brian2Loihi backend
                ├── group by shared format
                ├── pass requested mantissas
                └── restore observed w_act values to scenario order
```

A case passes only when:

1. the generic Brian2Loihi backend's observed `w_act` equals the production
   synapse's effective weight; and
2. current, voltage, and spike traces agree exactly.

## M08.4 completion evidence

The completed production-path validation was independently reproduced on
2026-08-03:

```text
68 passed
```

The eight focused M08.4 integration tests also passed:

```text
8 passed
```

The original legacy scenarios remained unchanged:

```text
cases=12, pass=12, fail=0, error=0, ticks=34, mismatches=0
```

All fifteen encoded-weight scenarios passed through the production
`Synapse.encoded(...)` and generic Brian2Loihi path:

```text
cases=15, pass=15, fail=0, error=0, ticks=15, mismatches=0
```

A generated trace-v3 artifact preserved the expected source encoding:

```text
{
  'requested_mantissa': 124,
  'quantized_mantissa': 124,
  'exponent': 0,
  'num_weight_bits': 8,
  'sign_mode': 'excitatory',
  'effective_weight_before_clip': 7936,
  'clipped': False
}
```

For this case, `124 × 64 = 7936`, so the stored pre-clipping value is consistent
with the exponent-zero, eight-bit excitatory format. The matching requested and
quantized mantissas show that no precision truncation occurred, and
`clipped=False` shows that the result remained within the supported range.

Together these results establish that:

- the production encoded-synapse representation preserves its source format;
- the generic adapter groups and executes encoded formats without changing
  legacy behavior;
- Brian2Loihi `w_act` and Python effective weights agree for all fifteen cases;
- current, voltage, and spike traces remain exact; and
- trace-v3 artifacts retain every encoded-weight field required for audit and
  later FPGA comparison.

This completes M08.4. It does not define the packed FPGA memory representation;
that work remains M08.5.

## Reproduce the validation

Install the comparison dependencies:

```bash
python -m pip install -e ".[dev,compare]"
```

Run all Python tests:

```bash
pytest
```

Run the original twelve-case suite:

```bash
python examples/run_directed_conformance.py
```

Run the fifteen production encoded-weight cases:

```bash
python examples/run_weight_conformance.py
```

Artifacts are written under:

```text
comparison_output/weights/
```

Each case receives normalized Brian2Loihi and Python trace-v3 files plus a
comparison report. Trace files preserve routing, effective weight, requested and
quantized mantissas, exponent, configured precision, sign mode, pre-clip value,
and clipping status. The suite-level JSON additionally records the effective
value observed from Brian2Loihi.
