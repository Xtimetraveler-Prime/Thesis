# P07-A — Final physical acceptance, canonical MNIST TEST benchmark

**ACCEPTED: 2026-10-17 (user-independent KV260 terminal evidence).**
**Status: P07-A1/A2/A3/A4.1/A4.2a/A4.2b/A4.2c/A4.3/A4.4 COMPLETE.**
**Research scope:** frozen compact Track A 784→32→10, 816 registered
input axons, 42 neuron compartments, 25 incoming spike ticks and one
drain tick, physical P03.2c FPGA PL neural engine orchestrated by
Cortex-A53 running the unchanged accepted P07-A4.2b standalone persistent
ELF. This is **not** Track B scaled implementation, P08 hardware power
or latency characterization, or native Intel Loihi silicon.

## Provenance and interpretation

The original official MNIST TEST dataset remained SEALED throughout
engineering, regression tests and all TRAIN-derived 16/128/1024
diagnostic experiments. The precommitted A4.1 full original-order
10000-image test population, MD5/IDX canonical archive checks,
model/readout, tie/silence policy and denominator were retained.
A4.3 provided separately user-consented TEST unseal (including the
accepted **one full-compartment trace per 10000-image launch**
observability policy). The test was then run **once** under the
separate explicit official physical runner and scored only after the
complete hardware journal passed independent numerical replay.
Host-only ground truth labels were not transferred to FPGA or A53.

**Immutable model/hardware identifiers accepted during engineering:**
- P03.2c FPGA XSA SHA256:
  `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
- P07-A4.2b standalone persistent A53 ELF SHA256:
  `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.
- Frozen master 512KiB DDR SHA256:
  `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
- Canonical MNIST t10k compressed archive **pinned MD5s**
  (images `9fb629c4189551a2d022fa330f9573f3`,
  labels `ec29112dd5afa0611ce80d1b7f02629c`).
  Full observed compressed archive SHA256s, IDX SHA256s,
  per-frame image hashes, physical bitstream/LTX and evidence
  journal/trace SHA256s are in the user-local final score report,
  **not** visible in the submitted terminal output. Do not
  invent or claim inspection of those individual values.
- Frozen Track A trained model and encoder/compiler behavior
  from P06-A4/P07-A accepted predecessors. No retraining,
  altered FPGA arithmetic, new bitstream or rebuilt ELF.

## P07-A4.2c — Physical pre-dispatch fault handling CLOSED

The user independently ran the precommitted **synthetic-only
ramp16 one-word descriptor corruption test**. Original
JTAG-only staged DDR passed byte-exact readbacks; then
one reserved 32-bit descriptor word at `0x43FE0090`
was altered before the unchanged A53 application started.
The A53 reported the expected **`0xDEAD0001`** input
rejection, no frame completions and no inference trace.
The independent native physical verifier checked
mutation/readback, the full failure journal and CRC
and all-zero outputs.

**User-submitted exact terminal markers:**

```text
P07-A4.2c standalone persistent A53 ELF downloaded; starting ONE dataset run
P07_A4_2C_JOURNAL_STATUS=0xDEAD0001
P07_A4_2C_JOURNAL=/tmp/v3_p07_a4_fail_closed_20261017T204554/p07_a4_journal_1m.bin
P07_A4_2C_TRACE=/tmp/v3_p07_a4_fail_closed_20261017T204554/p07_a4_trace_64k.bin
P07_A4_2C_KV260_STATUS=TERMINAL_FAILURE_INSPECT_JOURNAL
P07_A4_2C_EXPECTED_FAULT_STATUS=0xDEAD0001
P07_A4_2C_PHYSICAL_DESCRIPTOR_MUTATION_ONE_WORD_EXACT=1
P07_A4_2C_PHYSICAL_ORIGINAL_PROVISION_EXACT=1
P07_A4_2C_PHYSICAL_INFERENCE_FRAMES_COMPLETED=0
P07_A4_2C_PHYSICAL_RESULT_BODY_ALL_ZERO=1
P07_A4_2C_PHYSICAL_TRACE_ALL_ZERO=1
P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1
P07_A4_OFFICIAL_TEST=SEALED
P07_A4_2C_EXPECTED_DESCRIPTOR_REJECTION=0xDEAD0001
P07_A4_2C_PHYSICAL_FAULT_EVIDENCE_DIR=/tmp/v3_p07_a4_fail_closed_20261017T204554
P07_A4_2C_NEGATIVE_TEST_PASS=1
```

**Evidence directory (on user's PC):**
`/tmp/v3_p07_a4_fail_closed_20261017T204554`.
This is an *accepted negative experiment*, not 16
successful classified images. No official TEST archive
was accessed during this negative test.

## P07-A4.3 — Canonical full TEST source/protocol UNSEALED / ACCEPTED

After the accepted negative hardware gate, the user ran
the explicitly consented official t10k staging and
independent canonical test archive/readback procedure.
The final A4.4 gate (`P07_A4_4_CANONICAL_FULL_ORIGINAL_ORDER=10000/10000`,
`P07_A4_4_PREVIOUS_PHYSICAL_FAULT_ACCEPTANCE_PASS=1`)
rechecks the original full canonical IDX order, exact
dataset and original physical source. The user did
not separately paste the A4.3 staging CLI markers or
raw archive hashes; the final physically verified A4.4
pipeline provides the acceptance evidence that the
A4.3 source/order and physical negative prerequisites
passed. Exact official test split was evaluated **once**,
without reduction, relabeling, retuning or data-dependent
image selection.

**Frozen observability compromise:** the former
16-frame A2 batch approach would have selected 625
full 26×42 compartment traces for the complete official
TEST, but required 625 independent JTAG launches.
The accepted persistent A53 evaluation instead captures
**one full 26×42 neural state trace for original IDX
image 9999** for the entire 10000-image launch, while
preserving **26×10 = 260 output spike bits, 10 class
counts and routing/ingress summaries for every image**
(`10000×260=2,600,000` independently compared output bits).
It is incorrect to claim complete internal neuron-state
trace coverage for all 10000 images.

## P07-A4.4 — Canonical one-launch full 10000 TEST PASSED

The user independently executed the guarded A4.4
official physical runner on the KV260 and pasted:

```text
P07-A4.2c standalone persistent A53 ELF downloaded; starting ONE dataset run
P07_A4_2C_JOURNAL_STATUS=0x600D600D
P07_A4_2C_JOURNAL=/tmp/v3_p07_a4_official_full10000_20261017T204944/p07_a4_journal_1m.bin
P07_A4_2C_TRACE=/tmp/v3_p07_a4_official_full10000_20261017T204944/p07_a4_trace_64k.bin
P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS
P07_A4_4_CANONICAL_FULL_ORIGINAL_ORDER=10000/10000
P07_A4_4_PHYSICAL_INDEPENDENT_OUTPUT_SPIKES_ROUTES_EXACT=10000/10000
P07_A4_4_FINAL_IMAGE9999_FULL_COMPARTMENT_TRACE_EXACT=1
P07_A4_4_ALL_SIX_ORIGINAL_DDR_READBACKS_EXACT=1
P07_A4_4_PREVIOUS_PHYSICAL_FAULT_ACCEPTANCE_PASS=1
P07_A4_4_COMPLETE_PHYSICAL_DENOMINATOR=10000
P07_A4_4_OFFICIAL_TEST_CORRECT=9456/10000
P07_A4_4_OFFICIAL_TEST_ACCURACY_PERCENT=94.5600
P07_A4_4_OFFICIAL_TEST_ALL_SILENT=2/10000
P07_A4_4_FULL10000_KV260_INDEPENDENT_CLOSEOUT_PASS=1
P07_A4_4_SCORE_REPORT=/tmp/v3_p07_a4_official_full10000_20261017T204944/p07_a4_4_official_full10000_report.json
P07_A4_4_OFFICIAL_PHYSICAL_EVIDENCE_DIR=/tmp/v3_p07_a4_official_full10000_20261017T204944
P07_A4_4_FULL_CANONICAL_TEST_PASS=1
REBOOT THE KV260; do not resume the halted operating system.
```

**Final measured outcome (whole original canonical test population):**
- Correct: **9456 / 10000**
- Incorrect: **544 / 10000**
- Official MNIST TEST classification accuracy:
  **94.56%** (946? no: exact score `9456/10000`).
- All-silent: **2 / 10000** (0.02%). These remain included
  in the test denominator; not dropped.
- Numerical parity: **all 10000 indexed CRC-validated
  physical records**, **2.6 million 26×10 output spike bits**,
  routed/discarded packet and ingress totals match
  independent frozen P03 packed reference.
- Selected full-compartment trace: original test image
  **9999**, **26 ticks × 42 compartments**, physically
  exact to the reference. One selected trace only.
- Six original DDR staged-region binary readbacks
  exact; previous physical `0xDEAD0001` acceptance
  independently admitted. One persistent A53 FPGA
  inference launch, not 625 launches.

**Evidence directory (user PC):**
`/tmp/v3_p07_a4_official_full10000_20261017T204944`.
**Final JSON report (user PC):**
`/tmp/v3_p07_a4_official_full10000_20261017T204944/p07_a4_4_official_full10000_report.json`.
It contains the full 10000 prediction/label ledger,
per-image ten spike counts and pixel SHA256, confusion
matrix, class support and recall, initial source and
physical artifact provenance. **The report itself and
binary hardware artifacts were not provided in this
conversation.** The values above are user-provided
terminal results and successful self-check markers
rather than independently downloaded/reparsed artifacts
in the assistant's environment; do not fabricate any
unseen per-class metrics or archive SHA256s.

## P07-A research-claim boundary

**P07-A (single-core, compact physical FPGA inference) is
COMPLETE**, covering accepted P07-A1 ingress, A2
hardware/software neural equivalence, A3 validation and
reproducibility and A4.1–A4.4 sealed full canonical
TEST evaluation after persistent A53 engineering.

What is **NOT** measured/proven by P07-A completion:
no FPGA inference latency, PS overhead/throughput or
board rail power/energy accounting (deferred to P08-A);
no scaled P06-B/P07-B multi-logical-core hardware
inference, NoC, SRAM-transistor-level Intel Loihi 1
equivalence, physically asynchronous event logic,
or claim of full 10000 image complete per-neuron traces.
One positive official TEST run is not proof that 10000
test inference is reproducible across independent
reboots; separate A4.2c 128/1024 TRAIN-validation
cold repeat already established bounded repeatability.

**Next roadmap:** P08-A physical baseline before Track B
scaled hardware. Preserve physical logs and immutable
user-local source/test inputs; merge this completed
P07-A branch into `main` via an accepted PR only with
user's explicit authorization (granted in the
conversation associated with this acceptance). Do
not delete evidence directories. No model/RTL/ELF change
is required to document or merge these results.
