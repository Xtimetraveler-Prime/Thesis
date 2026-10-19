# P06-B1.1 — Source-audited scalable packing contract (host-only candidate)

**Status:** IMPLEMENTED FOR INDEPENDENT NATIVE REVIEW; **NOT YET USER-ACCEPTED**.  
**Base:** `main` commit `40b3d7c7092ea674e7d1d21647de2cd30e6b93b3` (post-PR-45 handoff).  
**Working branch:** `agent/v3-p06-b1-scalable-packing`.  
**Scope:** no official MNIST TEST files, training, weight changes, HLS/RTL/ELF/bitstream changes, or physical KV260 operations. The accepted Track A remains read-only.

## 1. Why B1 cannot just increase the old compiler core limit

`src/loihi_twin_v2/compiler.py::compile_network` (original P06) fills
`compartments_per_core` by sorted population/neuron order **before** grouping
input/neural sources by destination core. It then de-duplicates destination
synapse templates and checks logical capacities. A core with 40 destination
hidden neurons and 784 distinct input sources would have 31,360 stored
synapse words *plus* 784 headers and 784 input-axon bindings: under the
32,768-word bank, but **137,728 > 131,072 logical synapse bytes**.
Increasing `max_logical_cores` does not fix that placement decision.

P06-B1.1 adds an **opt-in post-compiler capacity and real packed-image audit**,
not a replacement compiler. P06-B1.2 will add a deterministic synapse-aware
partition algorithm and an independent versioned B manifest.

## 2. Source/physical contract (no native Loihi SRAM equivalence)

| Resource or ABI | Contract / limit | Accepted source and nuance |
|---|---:|---|
| Loihi-like logical compartments | 1,024/core | `resources.py`, `hardware_p03.py` |
| Input axon IDs | 4,096/core | `resources.py`; P03 axon RAM is 4,096 × 64 bits |
| Static output route words | 4,096/core | `resources.py`, P03 route RAM 4,096 × 32 bits |
| Stored packed synapse entries | 32,768/core | `hardware_p03.py`, P03 synapse RAM 32,768 × 64 bits |
| Project logical synapse memory | 131,072 bytes/core | `resources.py` simple cost: 4 × (stored template entries + headers + axon bindings), **not** native-Loihi packing |
| Input event bank capacity | 4,096 words/bank | `ddr_abi.py`: two banks, each 4,096 × 32 bits; CURRENT events cannot be silently dropped |
| Output packet bank capacity | 4,096 words/core/tick | `ddr_abi.py`: 4,096 × 64-bit packet words |
| Compartment configuration and state | 1,024 × 128 bits; 1,024 × 64 bits | `ddr_abi.py` |
| Context image header and total | 4 KiB header; exactly 524,288 bytes | `ddr_abi.py` magic `LTV3CTX1`, version 1, SHA-256 payload verification |
| DDR bank offsets | config `0x01000`; state `0x05000`; axon `0x07000`; synapse `0x0F000`; route-desc `0x4F000`; route `0x50000`; event0/1 `0x54000/0x58000`; trace `0x5C000`; packet `0x64000` | `ddr_abi.py` P02.1 fixed layout; payload ends at `0x6C000`, remaining `0x14000` reserved and zero-filled |
| Physical residency / execution | 3 resident contexts; **one** HLS engine | `hardware_p05.py`, `hardware_p08.py`; paging must retain each logical core's state |
| P05 diagnostic core IDs | 0–125 (126 IDs) | `scripts/p05_deployment.py` `MAX_CORES=126`; logical model and P02 expose 128, but old diagnostic admission is stricter |
| P05 diagnostic payload | 896 KiB max | `scripts/p05_deployment.py`, original `0x43F00000` payload through `0x43FDFFFF` before header |
| P05 accepted PL DDR page-in/out | `0x6B000` (438,272 B) in; `0x1A000` (106,496 B) mutable out | `scripts/p05_2i_axi_closeout.py` and `docs/P05_2I_ACCEPTANCE.md`. Only measured PL page-engine AXI payload traffic, **not** total system traffic or future B latency |
| P05 prior external input ABI | only one valid external axon/core in diagnostic | handoff; **not** a usable scaled 784-source ingress/streaming contract |
| P06-A fixed arithmetic/input | 24-bit signed saturated LIF, 64-bit wrapped synapse accumulation; 25 input + 1 drain; NEXT packet epoch | `p06_integer_oracle.py`, `p06_input_contract.py`, `p06_packed_replay.py` and accepted Track A. **Do not modify these modules** |

**Current B1.1 fail-closed model:** every external source is assumed active
simultaneously, and every incoming neural route is assumed to deliver a prior
epoch spike simultaneously. Their sum must fit **one 4,096-entry CURRENT
event bank** on each destination core. Every source core's emitted routes must
fit its 4,096-word packet bank. These are conservative *structural* bounds, not
a fabricated board scheduling result. All-255 pixels activate all 784
external channels in **each** of the 25 input ticks. The readout receives
hidden packets in the NEXT logical epoch. Detailed ingress streaming and
outstanding packet-buffer scheduling belong to B1.3.

## 3. What is now implemented

- `src/loihi_twin_v2/p06_b1_contract.py`: independent `CorePressure`
  bound checks plus `audit_compiled_candidate`. It interrogates a genuine
  `CompiledDeployment`, materializes every source-derived P03 packed core
  using the accepted P08 page exporter, builds a **real** complete P02 DDR
  initial record for each, validates headers/payload SHA, checks logical
  cost versus packed counts, and emits deterministic SHA256s, bank layout,
  per-core event/route budgets, and physical/nonphysical claim flags.
- `tests/test_p06_b1_contract.py`: directed numerical hand-oracle for
  the two-epoch signed integer spike case; independently decoded signed24
  P03 synapse weights; minimum four-logical-core/two-layer split with 3
  resident slots, reversed legal service order, exact DDR and corruption
  checks; 128KiB/32,768-word/input axon/output route/4,096 event/packet
  capacity tests; conservative 39-versus-40 destination-neuron pressure.

**Planning calculation, not accepted mapping:** for *unshared*, fully dense
784-input hidden partitions using 784 separate source template headers and
784 bindings per destination core, 39 hidden neurons require
`4 * (784*39 + 784 + 784) = 128,576` logical bytes, whereas 40 require
`137,728`. Thus 1,000 hidden neurons would require **at least 26
destination partitions** under that explicit representation. This alone does
**not** prove 26 hidden cores + 1 readout fits all route/event/paging/buffering
limits. A future algorithm and complete source/weight graph check are needed.

## 4. B1.1 native review gate

From the repository root on the **development branch**:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b1-scalable-packing
git pull --ff-only origin agent/v3-p06-b1-scalable-packing
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b1_contract.py
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_lif_compiler_probe.py tests/test_p06_lif_input_probe.py
PYTHONPATH="$PWD/src" python -m compileall -q src/loihi_twin_v2/p06_b1_contract.py tests/test_p06_b1_contract.py
```

All commands are **host-only**: no JTAG, no physical DDR modifications, no
official MNIST TEST access. This document does **not** assert they passed
on the user's machine or in GitHub CI. The B1.1 gate remains open until
independent native results are supplied and reviewed.

## 5. Remaining B1 work / explicit stop boundary

**B1.2:** opt-in deterministic synapse-aware allocation, destination/source
identity and resource-aware fit, genuine per-core packed images, impossible
network rejection, separate signed source/weight/compiled manifest.  
**B1.3:** new versioned multi-core ingress/packet-streaming ABI; all-255
replication, NEXT/current fanout and per-core bank safety; no P05 diagnostic
ABI reuse as a physical deployment guarantee.  
**B1.4:** independently authored arbitrary-size monolithic integer oracle
versus partitioned event/packet/compartment replay, 26-tick first-mismatch
gate. The B1.1 tiny hand oracle is not a substitute.  
**B1.5:** three-slot paging/service-order model, full page-in versus mutable
page-out **estimated** byte counts, no extrapolated physical throughput.  
**B1.6:** original source SHA ledger, real graph feasibility, independent
native user acceptance, and recommendation before B2 training.

P06-B1.1 changes do not authorize B1.2 acceptance, P07-B physical
execution, any official TEST use, or Track A source modifications.
