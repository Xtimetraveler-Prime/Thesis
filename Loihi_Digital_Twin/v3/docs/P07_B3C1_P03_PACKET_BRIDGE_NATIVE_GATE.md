# P07-B.3c1 — Hardware packet-bank readback and lossless P03→B1.3 preflight

**Status:** native verification candidate; USER-NATIVE PASS PENDING. This is the first deliberately gated implementation **within P07-B.3c**, not complete B.3c physical runtime closure. The user attested B.3b host-native PASS on 2026-10-20, recorded in `docs/P07_B3B_USER_ACCEPTANCE_LEDGER.json`. PR #49 remains draft/unmerged; accepted Track A/B and original P03/P05 sources are unchanged; official B2 MNIST TEST remains SEALED.

## 1. Why B.3c needs a hardware packet adapter

The accepted P03 physical adapter `software/p03/p03_hw_adapter.c` reads HLS packet-bank entries as **64-bit hardware words** via debug bank **8** (`p03_hw_read_packet`). Layout: destination logical core **[6:0]**, destination axon **[18:7]**, source compartment **[28:19]**, 32-bit target epoch **[60:29]**, spike-valid bit **61**, zero/reserved bits **62..63**. The originating **source core is NOT in the 64-bit word**; it must come from the known **completed source-core dispatch**. Each accepted routed spike targets epoch `t+1`, never current `t`.

B.2b and B.3b accept a separate proposed host B1.3 wire ABI `P06B13R1`, containing 128-byte strict identity/CRC header plus **12-byte records** `<IHHHH>`: target tick, source core, source compartment, destination core, destination axon. It is incorrect to cast the 64-bit PL word to the 12-byte transport record or to send packets through the existing per-packet P03 writer before full source-routing/provenance validation.

## 2. New independent C11 modules and native tests

**New `software/p07/include/p07_b3c_packet_bridge.h` and `software/p07/p07_b3c_packet_bridge.c`:**

1. `p07_b3c_capture_p03_core(...)` checks a registered source, correct physical slot bound and `p03_hw_quiescent()` (GLOBAL_STATUS=0, PAGE_PENDING_BYTES=0) via the **unchanged real P03 adapter**, and captures up to 4096 raw packet-bank words by repeatedly calling `p03_hw_read_packet`. It uses a **caller-owned disjoint temporary word buffer**, not a large implicit A53 stack allocation. Its capture ledger does not publish any raw words/counts if a read callback errors partway through. A failed actual P03 adapter read may latch `hw->last_error`.
2. `p07_b3c_capture_core(...)` also exposes an injected read-only packet reader for host-native fake-bus fault injection; the physical path uses `p07_b3c_p03_reader()` which invokes the accepted hardware adapter. No P03 hardware source is modified.
3. `p07_b3c_encode_frame(...)` accepts a **complete** 0..N−1 array of per-source core capture views; N≤27 and total raw words ≤8192 (the existing B.2b prototype capacity). It decodes explicit P03 packet bitfields, rejects invalid valid-bit/reserved bits/target epoch/core/compartment, sorts 12-byte records in original B1.3 logical order, packs independent bound compiled/capacity SHA256 fingerprints and both zlib/IEEE CRC32 fields, and calls **the unchanged B.2b full-fanout validator** `p07_b2_packet_decode` with an **independent, sorted, duplicate-free source-spike provenance list**. The source spike provenance MUST come from future genuinely verified emitted HLS neuron information; it is never guessed or reconstructed from observed packets. A completely missing source group would otherwise be impossible to detect.
4. A frame is published to the caller's output only after full validation. On rejection output bytes and previous frame-length receipt remain unchanged. Caller must provision separate, immutable hardware packet/source/provenance buffers, distinct 98,432-byte frame/scratch buffers, and an explicit ~32-KiB raw-word capture workspace. The new source rejects overlapping buffers. These are **host-memory frame bounds**, not verified A53 linker reservations.
5. Capturing and verifying a frame **does not write any physical FPGA/DDR NEXT event banks**. This is intentional: later adapter work must preflight all 27 sources and whole-epoch fanout/capacity before any nonrollbackable AXI write. The accepted P03 original `p03_hw_route_word` writes one packet at a time, and therefore is **not** used for this stage's all-or-nothing epoch commit.

**Native tests:** `tests/test_p07_b3c_packet_bridge.py` uses the original B1.2/B1.3 Python compiler and `encode_packet_frame` on synthetic small neural networks to demand **byte-identical canonical B1.3 frames**. Additional synthetic 27-core, 26-source/one-readout cases check multi-source frames at epochs 0,1,12,24,25. Test mutations include bad physical spike-valid/reserved bits, wrong target tick, invalid destination, valid-bits-but-illegal route axon, totally omitted originating source, partial fanout, insufficient output capacity, and injected mid-capture read failure with unchanged ledger. A new `tests/native/p07_b3c_p03_readback_harness.c` compiles the **actual** P03 C adapter with fake `p03_hw_io` register callbacks and checks actual debug bank 8, quiescence preflight, sticky busy/PAGE_PENDING errors and packet-read timeout.

**No real MMIO calls against a KV260** are made by the tests: the P03 callback bus is simulated. The tests are not proof of an A53 ELF, FPGA layer, HLS emitting-neuron trace, 27-core inference, real AXI traffic/latency/energy or trained B2 accuracy.

## 3. Outstanding B.3c gates (NOT yet implemented or accepted)

- **B.3c2:** integrate B.3a LRU pager with P03 `p03_hw_page` and `p03_hw_dispatch`, reconcile the original P03 preloaded/round-robin runtime policy with B1.5 LRU; ensure dispatch, packet capture, NEXT staging and final flush have true completion acknowledgments, sticky first errors and a consistent per-image reset.
- **B.3c3:** verify full P02 neuron voltage/current/refractory and both banks preserved by real 0x6B000/0x1A000 page transfers, not just B.3b mock event slices. Implement physically safe atomic/quiescent multi-packet destination event-bank insertion (resident debug bank 6/9 or nonresident DDR+cache clean); rollback or unrecoverable poisoned-run semantics must be proven on partial I/O failure. Design and validate A53 linker LOAD/BSS/stack/heap/reserved-64MiB nonoverlap and hardware startup gating.
- **P07-B.4:** actual KV260 27-logical-core execution over predeclared TRAIN-derived images, independent full 26-tick state/spike/packet parity and measured page/dispatch/latency observability. B2 official MNIST TEST must remain sealed until a separate explicit unseal authorization.

## 4. User-native verification commands (B.3c1 gate only)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3c_packet_bridge.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b3b_event_owner.py \
  tests/test_p07_b3a_pager.py \
  tests/test_p07_b2b_transaction.py \
  tests/test_p07_b2b_packets.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b1_owner_map.py \
  tests/test_p06_b13_streaming.py
```

**Stop after the native gate; do not report B.3c complete, merge PR #49, program the KV260, or unseal B2 official TEST from this host-only proof.**
