# P07-B.3b — P03 Event-Slice Ownership / Native Verification Gate

**Status: B.3b implementation candidate, user-native PASS pending.** P07-B.3a is user-attested native PASS (see P07_B3A_USER_ACCEPTANCE_LEDGER.json). PR #49 remains draft and unmerged. The B2 official MNIST TEST is **SEALED**.

## 1. What is implemented

New files: software/p07/include/p07_b3b_event_owner.h, software/p07/p07_b3b_event_owner.c, and tests/test_p07_b3b_event_owner.py. They implement an independent **host C11 mock event-slice integration** between previously accepted B.2a ingress (P06B13I1), B.2b complete NEXT event vectors (P06B13R1), and B.3a LRU page/dispatch/barrier actions. No original accepted Track A/B/P03/P05 files were modified.

The C11 source compiles against original P03/P05 headers. Fixed 27 P02 logical records at 0x40000000 + core*0x80000, three resident context slots, one serial dispatch engine, and 26 global barriers. Each **simulated** event bank contains up to 4096 32-bit destination-axon words, at original P03/P02 physical record offsets +0x54000 (EVENT0) and +0x58000 (EVENT1). P03 resident debug bank IDs are **6** and **9** respectively, not 6 and 7. Real P03 page transfers are 0x6B000 full-in and 0x1A000 mutable-out; the mock C memory copies only the 32-KiB two-event-bank subset and **does not transfer full neuron state**.

### Independent per-core ownership and transaction

* CURRENT is the previous NEXT (routed axon list) plus phase17/quota17 external events for that epoch. New ingress is staged only after all 27 per-core counts pass the 4096 ceiling; axon words are sorted ascending for canonical consumption. The final tick 25 has no external spikes.
* A resident logical core's event banks are authoritative in its mock slot; the corresponding DDR backing slice may be stale until an acknowledged dirty PAGE_OUT. A nonresident core is authoritative in backing memory. On a PAGE_IN ACK, a mock event-bank slice is loaded into the chosen slot; a DISPATCH ACK consumes only CURRENT for that core, retaining NEXT.
* The pending B.3a BARRIER is completed only after all 27 cores dispatch exactly once and their CURRENT words are consumed. A shadow B.2b transaction independently parses the full packet frame with CRC/compiled SHA/capacity audit bindings, source-spike provenance, complete fanout, NEXT-only epoch and per-core limits, without mutating the original transaction.
* Once all checks pass, one host-memory-only commit ACKs the B.3a barrier, appends every routed NEXT axon to either resident slot or DDR-backed event slice, and publishes B.2b pending vector/occupancy, receipts, and tick. Native rejection leaves *authoritative backing/slots, original transport pending, and prior receipt unchanged*; the paging run is sticky faulted. Any failed page/dirty-writeback ACK similarly permanently faults the run. This is not a rollback guarantee for later real hardware writes.
* Route-targeted nonresident cores are never paged in only to receive a spike. The model preserves their NEXT tuples until their later acknowledged PAGE_IN.

## 2. Host-native verification and exact limitations

The new test builds all five **real repository** sources with cc -std=c11 -Wall -Wextra -Werror -pedantic, plus original P03/P05 include directories. It generates synthetic, independently CRC/SHA bound B1.3 ingress with all 784 input pixels replicated into 26 hidden shards (20,384 ingress routes) and 26 synthetic source-to-readout routes. The synthetic source-spike provenance is declared by the test: this is **not signed24 LIF execution**, not trained B2.4, and not official MNIST TEST. Synthetic SHA values are not frozen B2 identities.

Six complete 26-epoch trials (ascending/alternating service order crossed with all-zero/all-255/phase-varied pixels) compare every per-core consumed CURRENT axon list against the independent accepted Python quota/phase17 encoder and previous-tick NEXT reference. They check 702 dispatches, 26 barriers, external/routed event occupancy, all 27 core slots/DDR ownership, final dirty flushes, and routed delivery to **nonresident readout core on odd alternating epochs**. Negative tests inject a bad frame CRC at barrier (verify no partial state commit), corrupted resident bank contents (must be caught before another dispatch), and a failed dirty readout PAGE_OUT (backing remains stale, dirty resident state retained, sticky fault).

**No P07-B.3b full native pytest PASS has yet been observed in this chat.** GitHub commits are implementation candidates until the user verifies them.

## 3. Required next milestone work (B.3c and B.4, not included)

Physical A53/Vitis ELF with verified LOAD/BSS/heap/stack nonoverlap against reserved 64MiB DDR; actual P03 MMIO shell/capability verification; coherent page-in/out 0x6B000/0x1A000 *whole* P02 mutable state and event bank preservation; reconcile original P03 round-robin initial preload with new B1.5 LRU policy; actual RTL debug-bank event writes or nonresident cache-cleaned DDR stores and ACKs; HLS 64-bit packet-to-B1.3 source route translation with independent emitting-neuron provenance; authoritative per-image neuron/packet/bank/output reset; durable first-error mailbox; true PL 27-core inference and pretrained TRAIN-derived numerical trace comparison. No physical timing/energy or measured 27-core page bytes claimed. Accepted Track A/B artifacts unchanged. Official B2 TEST remains SEALED.

## 4. Native verification commands (user gate)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p07_b3b_event_owner.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3a_pager.py \
  tests/test_p07_b2b_transaction.py \
  tests/test_p07_b2b_packets.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b1_owner_map.py \
  tests/test_p06_b15_paging.py \
  tests/test_p06_b13_streaming.py
```

Stop after B.3b native gate. Do not merge PR #49 or unseal official MNIST TEST absent explicit user authorization.
