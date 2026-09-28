# FPGA weight-storage profile v1

M08.5 freezes the binary storage contract used to carry the validated static
weight representation from Python into an HDL testbench or FPGA memory image.
This is a project-specific Loihi-inspired storage profile; it is not a claim
about the undocumented physical SRAM layout of an Intel Loihi device.

## Why a frozen representation is necessary

The validated software objects preserve all relevant semantics, but Python
classes and enum values are not a hardware interface. RTL requires exact word
widths, bit positions, signed encodings, capacities, and behavior for unused
values. Freezing those details before implementing the neuron/core datapath
prevents later BRAM convenience decisions from changing already validated
weight behavior.

A stable memory image also gives the host software, Python model, HDL
simulation, and physical FPGA one common configuration artifact.

## Storage organization

Profile v1 uses three memories:

```text
weight_formats.mem     16-bit shared format entries
weight_synapses.mem    32-bit per-synapse records
weight_axon_rows.mem   32-bit CSR row pointers
```

For axon `a`, the corresponding synapse records occupy:

```text
synapse_words[row_pointer[a] : row_pointer[a + 1]]
```

The axon ID is therefore the row-table address and is not repeated inside every
synapse word.

## Shared format word

Each format entry is sixteen bits:

```text
15                    10 9      8 7          4 3          0
+-----------------------+----------+------------+------------+
| reserved = 0          | sign     | weight bits| exponent   |
+-----------------------+----------+------------+------------+
        6 bits             2 bits      4 bits       4 bits
```

| Bits | Field | Encoding |
|---|---|---|
| `[3:0]` | exponent | signed four-bit two's complement, `-8..7` |
| `[7:4]` | `num_weight_bits` | unsigned, valid values `0..8` |
| `[9:8]` | sign mode | `00=mixed`, `01=excitatory`, `10=inhibitory`, `11=reserved` |
| `[15:10]` | reserved | must be zero |

The four-bit format index in each synapse word limits one storage image to
sixteen unique formats.

## Synapse word

Each synapse record is thirty-two bits:

```text
31       29 28                       13 12       9 8          0
+-----------+--------------------------+-----------+------------+
| reserved  | target neuron            | format idx| mantissa   |
+-----------+--------------------------+-----------+------------+
   3 bits              16 bits             4 bits      9 bits
```

| Bits | Field | Encoding |
|---|---|---|
| `[8:0]` | requested mantissa | signed nine-bit two's complement, `-256..255` |
| `[12:9]` | format index | unsigned index into the sixteen-entry format table |
| `[28:13]` | target neuron | unsigned sixteen-bit neuron ID |
| `[31:29]` | reserved | must be zero |

The record stores the requested mantissa rather than the quantized mantissa or
final effective integer. Requested mantissa plus the referenced format is the
validated source representation. Passing those fields through the existing
integer encoder deterministically reconstructs quantization, exponent scaling,
alignment, clipping, and the effective weight delivered to the core.

Legacy integer-only `Synapse` objects are rejected during freezing because the
original mantissa and format are not always recoverable after quantization,
negative-exponent alignment, or clipping.

## Axon row-pointer table

Axon IDs are sixteen-bit direct row-table addresses, supporting IDs `0..65535`.
Each row pointer is an unsigned thirty-two-bit synapse-table offset. A storage
image with `A` configured axon rows contains `A + 1` pointers; the final pointer
equals the number of synapse records.

Synapse words are ordered by ascending axon ID. Input order is preserved within
one axon row.

## Reserved values

All reserved bits must be zero. Readers reject:

- nonzero reserved bits;
- sign-mode code `11`;
- `num_weight_bits` values outside `0..8`;
- mantissas invalid for the referenced sign mode;
- format indices outside the loaded format table; and
- malformed or nonmonotonic axon row pointers.

Changing the meaning of a reserved bit requires a new storage-schema version.

## Shared versus inline format storage

An inline record containing target neuron, requested mantissa, and all format
fields requires thirty-five used bits:

```text
16 target + 9 mantissa + 4 exponent + 4 precision + 2 sign = 35 bits
```

That record rounds naturally to a thirty-six-bit memory word. Profile v1 instead
uses a thirty-two-bit synapse word plus one sixteen-bit entry per unique format.
Ignoring the row-pointer table, which is identical in both organizations:

```text
shared format:  32N + 16F bits
inline format:  36N bits
savings:         4N - 16F bits
```

Here `N` is the number of synapses and `F` is the number of unique formats.
Shared storage breaks even at `N = 4F` and saves space when `N > 4F`.

Representative logical-capacity estimates are:

| Synapses | Formats | Axons | Shared total | Inline total | Saved | Capacity-only BRAM36 lower bound |
|---:|---:|---:|---:|---:|---:|---:|
| 256 | 8 | 64 | 10,400 bits | 11,296 bits | 896 bits | 1 vs. 1 |
| 1,024 | 16 | 256 | 41,248 bits | 45,088 bits | 3,840 bits | 2 vs. 2 |
| 4,096 | 16 | 1,024 | 164,128 bits | 180,256 bits | 16,128 bits | 5 vs. 5 |
| 16,384 | 16 | 4,096 | 655,648 bits | 720,928 bits | 65,280 bits | 18 vs. 20 |

The BRAM36 values are capacity-only lower bounds using 36,864 bits per block.
Actual use can be higher because legal width/depth modes, banking, parity,
placement, and timing constraints are device- and design-specific.

## Python API

Pack and unpack individual words:

```python
format_word = pack_weight_format(weight_format)
format_again = unpack_weight_format(format_word)

synapse_word = pack_synapse_word(
    target_neuron=7,
    requested_mantissa=-127,
    format_index=0,
)
fields = unpack_synapse_word(synapse_word)
```

Freeze a collection of encoded production synapses:

```python
storage = freeze_encoded_synapses(synapses)
decoded_synapses = storage.decode_synapses()
estimate = storage.estimate()
```

Write host- and HDL-consumable artifacts:

```python
artifacts = write_weight_storage_image(storage, "weight_image")
```

The directory contains:

```text
weight_storage.json
weight_formats.mem
weight_synapses.mem
weight_axon_rows.mem
```

The JSON schema is:

```text
neuromorphic-twin-fpga-weight-storage-v1
```

Each `.mem` file contains one zero-padded hexadecimal word per line and can be
used directly by host tooling or an HDL testbench memory loader.

## Validation contract

The focused M08.5 suite checks:

- all 432 possible format configurations pack and unpack exactly;
- signed mantissa and boundary routing fields round-trip;
- reserved and invalid values are rejected;
- formats are deduplicated deterministically;
- CSR rows reconstruct complete `Synapse.encoded(...)` objects;
- JSON and hexadecimal memory artifacts are reproducible;
- memory estimates match the documented equations; and
- all 147,456 valid static-weight combinations retain their exact
  `StaticWeightEncoding`, including final effective weight, after
  pack/unpack/re-encoding.
