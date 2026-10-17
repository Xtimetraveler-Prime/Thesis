# P07-A4.2 — Persistent DDR-backed A53 inference implementation

**2026-10-17 — approved engineering direction after user accepted A4.1.**
**Current phase:** A4.2a **USER-ACCEPTED**; A4.2b **candidate A53
firmware, Vitis-native build pending**; A4.2c **physical entry tooling
implemented, KV260 numerical gate NOT RUN**. Native host CI green.
**Official canonical t10k TEST remains SEALED / NOT READ.**

## Why this is a distinct version, not an A2 modification

The accepted P07-A2 firmware reads at most 16 complete P07A1
(2480-byte) ingress records from `0x43F80000`, writes
a 64KiB result/selected full trace at `0x43FF0000`
and then permanently halts. The prior original-order
10,000 TEST run would take **625 JTAG launches and board
reboots**. The user has authorized a persistent A53
dataset execution path, not a change to the frozen
10,000-image evaluation population. A2 and accepted P03/P05
are preserved byte-for-byte. No Loihi neurons, HLS FPGA engine,
accepted bitstream, quantized weights, input phase,
26-tick logic, NEXT routing or readout tie policy change.

A4.2 introduces **P07A4P01** (separate descriptor + one
frozen mapping + raw pixels) and a **P07A4R01**
fixed-size progress/result journal. Memory addresses and
field offsets below are **candidate contract v1**, requiring
native C/Python parity before any physical test.

## Physically reserved DDR ownership (bare-metal JTAG ONLY)

The application claims the same **0x40000000–0x43FFFFFF
64MiB** DDR test reservation proven by A2. Never run with Linux
or another owner using that DDR range.

| Exclusive half-open address interval | Bytes | Owner / contents |
|---|---:|---|
| 0x40000000–0x40080000 | 524,288 | mutable core0 DDR backing/page-in+out, unchanged |
| 0x41000000–0x41800000 | 8,388,608 | **NEW** 10,000×784 raw uint8 image stream; exact bytes are 7,840,000 |
| 0x42000000–0x42100000 | 1,048,576 | **NEW** journal header 256B + up to 10,000×96B physical per-frame records = 960,256B |
| 0x43F00000–0x43F80000 | 524,288 | frozen original P06-A4.2 immutable master DDR image; SHA256 `9617a822…0d955` |
| 0x43FE0000–0x43FE0100 | 256 | **NEW** versioned `P07A4P01` run descriptor |
| 0x43FE0100–0x43FE0720 | 1,568 | **NEW** one copy of exact compiled 784×LE-u16 unique pixel→destination-axon map |
| 0x43FF0000–0x44000000 | 65,536 | selected one-image full 26×42×256-bit diagnostic trace |
| All other reserved bytes | — | no owned data; guard against overlap |

Image and result journals intentionally use **disjoint** regions
of the original 64MiB reservation. Values do not indicate
additional physical DDR capacity; A53 ELF LOAD segments must
remain outside the full 64MiB region. Data remains staged by
XSDB and explicitly cache-flushed/invalidated.

## `P07A4P01` descriptor (256B, independent of P07A2B01)

All scalar fields explicitly little-endian; no native struct
casting. Bytes:

| Offset | Size | Contract |
|---:|---:|---|
| 0 | 8 | ASCII `P07A4P01` |
| 8 | 4 | version=1 |
| 12 | 4 | header size=256 |
| 16 | 4 | sample_count=1..10000 (full official run exactly 10000) |
| 20 | 4 | raw pixel stride=784 |
| 24 | 4 | image base=0x41000000 |
| 28 | 4 | image allocation bytes=0x800000 |
| 32 | 4 | journal base=0x42000000 |
| 36 | 4 | journal allocation bytes=0x100000 |
| 40 | 4 | record stride=96 |
| 44 | 4 | trace base=0x43FF0000 |
| 48 | 4 | index of one trace-selected image within this run |
| 52 | 4 | flags=0 |
| 56 | 4 | CRC32 IEEE of exactly sample_count×784 raw pixels |
| 60 | 4 | CRC32 IEEE of full 1568-byte frozen mapping |
| 64 | 4 | map count=784 |
| 68 | 4 | map base=0x43FE0100 |
| 72 | 4 | immutable master base=0x43F00000 |
| 76 | 4 | mutable core0 backing base=0x40000000 |
| 80 | 32 | accepted 512KiB DDR master SHA256 raw bytes |
| 112 | 32 | accepted compiler fingerprint raw bytes |
| 144 | 108 | reserved, **all zero** |
| 252 | 4 | CRC32 IEEE of bytes 0..251 |

Mapping and whole-image CRCs must be checked **before any
neural dispatch**; mapping must be a 784-entry distinct set
of valid uint12 destination axons. The builder that
constructs real bundles must reload the accepted frozen
checkpoint and derive `mapping_from_compiled`, not invent
an identity mapping. C verifies DDR and compiler identity
fields and reconstructed per-image accepted P07-A1 ingress
CRC independently.

## Full output progress journal

`P07A4R01` header, 256B at journal base:
magic at 0..7; version at 8; header size at 12; run status at 16
(0=NOT_STARTED, 0x600D600D=COMPLETE, other values are failure);
requested count 20; completed count 24;
first failure frame index 28 (0xffffffff means none);
bound descriptor CRC 32; trace frame index 36;
reserved zeros to 251; CRC32 at 252.

Each following 96B record is indexed by its **ordinal**
0..sample_count-1. This equals official TEST ID for
the frozen original-order 10000 run; validation samples
are joined to their separate preselected source-ID ledger.
No ground-truth label enters DDR.

| Byte offset in each 96B record | Data |
|---:|---|
| 0..3 | ordinal image index |
| 4..7 | CRC32 of the original raw 784 image bytes |
| 8..11 | status=0x600D600D on verified frame completion |
| 12..15 | predicted class 0..9 |
| 16..19 | all-silent flag 0/1 |
| 20..23 | committed hidden NEXT routes |
| 24..27 | discarded final-tick hidden packets |
| 28..31 | external event total |
| 32..51 | ten little-endian uint16 output spike counts |
| 52..87 | 9 little-endian uint32 output spike bitwords, 10 bits/timestep×26 ticks |
| 88..91 | optional measured 32-bit cycle count (0 if unmeasured); NOT a whole-system latency |
| 92..95 | CRC32 IEEE of the preceding 92 bytes |

The A53 must flush/invalidate caches appropriately, write the complete
CRC-protected per-frame record **before** incrementing
the completed counter, and set terminal success only after
10000 verified frames and a validated diagnostic trace. Faults
must preserve an immutable first-error marker and never label
a partial journal COMPLETE. A host independent reader MUST
re-derive spike counts/class/silence from packed output
spike bitwords, check CRC, sample index/order and
actual pixel CRC, and refuse to score incomplete journals.

Only one full trace (34,944 bytes plus metadata in 64KiB)
is reserved for the selected image; other images preserve
**all 26×10 physical output spike bits**, ten class counts and
NEXT routing summary. To claim full per-compartment
equivalence for all 10000 images, we would need separately
planned trace capture and storage; A4 acceptance must
explicitly report this measurement boundary.

## Engineering gates — no official TEST unseal yet

- **A4.2a CLOSED / USER-NATIVE ACCEPTED:** versioned host/Python and portable C11
  descriptor/mapper/journal format, byte-exact parity with
  accepted P07-A1 record builder; strict boundaries,
  1/16/128/10000 stress fixtures, negative tamper/CRC,
  no-load/no-download of actual MNIST TEST.
- **A4.2b CODE IMPLEMENTED / USER VITIS BUILD PENDING:** new *separate* standalone A53 board firmware,
  extending accepted per-frame `p07_a2_run_frame`
  with a persistent dataset loop, full per-image context
  reset, progress commits and fatal-first-error telemetry;
  deterministic fault-injection native tests. Rebuild
  a new ELF against the same accepted XSA; never mutate
  accepted A2 source or claim reuse of A2 ELF identity.
- **A4.2c HOST TOOLING IMPLEMENTED / BOARD NOT YET RUN:** guarded new physical XSDB staging and one-shot
  runner, independent real KV260 validation on selected
  synthetic and TRAIN-derived validation samples,
  16/128/large corpus equivalence, byte-identical cold-start
  repeats, complete 26×42 selected-image physical trace
  and journal contents plus full artifact hashes.
- **A4.3 LATER:** user explicitly authorizes the *already
  precommitted full canonical 10000 original-order*
  official TEST unseal, archive MD5/observed SHA256
  provenance and one-time frozen dataset staging.
  `p07_a4_prepare.py` currently requires explicit
  `--i-accept-unseal`; do NOT call it until A4.2c passes.
- **A4.4 LATER:** run every official TEST image physically
  in the accepted new persistent A53 loop with full
  first-mismatch oracle and run journal verification, then
  reveal the official 10000-image test score. No retuning
  or post hoc denominator changes.

**NO CURRENT CLAIM** that a single hardware launch works,
that FPGA DDR has been staged with this new ABI, that official
MNIST TEST was read or that measured power/latency improved.

## Development note (2026-10-17)

The user independently verified A4.2a. A4.2b source and
CI portable tests now exist; A4.2c independent staging/run
and packed-oracle verification scripts also exist, but no
new A53 ELF Vitis build or KV260 device execution has been
accepted. The authoritative next-user-gate instructions
are in `P07_A4_2B_2C_PERSISTENT_GATE.md`. The official
TEST has not been opened. Do not confuse source completion
or a native CI pass with actual physical inference.
