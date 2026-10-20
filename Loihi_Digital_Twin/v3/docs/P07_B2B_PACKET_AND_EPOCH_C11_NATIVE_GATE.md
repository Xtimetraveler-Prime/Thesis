# P07-B.2b — Independent C11 routed packet, source provenance and atomic NEXT-epoch gate

**Status: implementation candidate, user-native verification PENDING.** P07-B.1 and P07-B.2a were independently **user-attested HOST-NATIVE PASS** on 2026-10-19; accepted raw test stdout and test counts were not pasted. See external additive evidence ledgers `docs/P07_B1_USER_ACCEPTANCE_LEDGER.json` and `docs/P07_B2A_USER_ACCEPTANCE_LEDGER.json`. Branch `agent/v3-p07-b-scaled-physical-inference`, draft PR #49, **DO NOT MERGE** before user authorizes. No accepted Track A/B source, weights, snapshot, original P02 context, P07-A physical evidence or B2 official MNIST TEST protocol is modified.

## 1. Existing source of truth

The B.2b implementation independently parses the original **host-proposed** `P06B13R1` packet ABI in `src/loihi_twin_v2/p06_b13_streaming.py` and `docs/P06_B1_3_MULTICORE_STREAMING_ABI.md`, preserving original B1.2 output-routing semantics. This is **not** the old P05 one-axon-core diagnostic, the 64-bit direct P03 HLS packet register layout, or hardware firmware already installed on KV260. It must eventually be adapted to independently obtained P03 emitted route records and real PL spike provenance.

Every packet frame is a fixed **128-byte** header with magic `P06B13R1`, LE 14×u32 (version 1, header length, payload length, emitted epoch, packet count, logical core count, record bytes 12, per-source cap 4096, two reserved zero words, payload CRC32, header CRC32, flags and reserved zero), followed by two raw SHA256 identity fields: **B1.2 compiled fingerprint** at offsets 64..95 and **B1.1 packed-capacity audit** at 96..127. CRC32 header is over header with bytes 52..55 zeroed; payload is exactly `count * 12` bytes. Each packet is `<IHHHH`: **target_tick:u32, source_core:u16, source_compartment:u16, destination_core:u16, destination_axon:u16**. Packet transport order is original `SpikePacket.logical_key`: `target_tick, destination_core, destination_axon, source_core, source_compartment` (source tick and packet class are constant in this frame). Emitted tick `t` targets **t+1**.

The two 32-byte digest fields must match a **separate trusted binding** of the original frozen B2.4 mapping. CRC is error detection, not authentication; SHA equality without independent checkpoint custody is not secure attestation. The accepted original trained B2 identities remain **compiled** `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`, **capacity-audit** `82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498`; synthetic tests deliberately use unrelated SHA values. B2's 97.08% is TRAIN-derived validation, NOT official TEST.

## 2. New portable C module

- `software/p07/include/p07_b2_packet.h`: versioned tuple views, source-ordered trusted output-route map `(source_core, source_compartment, destination_core, destination_axon)`, core compartment bounds, two trusted SHA fields, optional decoded wire view and epoch receipt structures. No heap allocation, BSP, MMIO or DDR writes.
- `software/p07/p07_b2_packet.c`: independent byte-wise LE/CRC decoder, strict magic/version/dimensions/digest/reserved/order checks; source-compartment and destination-axon bounds, source and destination core bounds, exact route existence against the **separately supplied** trusted output route set. Each emitted source must have its **complete** fanout; duplicates and missing routes fail closed. The mapping is checked sorted/unique before any use; each source and destination has ≤4,096 statically reachable packet routes. Packet frame bytes are bounded by the B.1 *proposed* `0xE0000` staging region: at most `(0xE0000-128)/12 = 76,448` route packets in a single frame. This is a **firmware planning admission bound** and does not imply the board has independently allocated matching A53 RAM.
- **Source provenance REQUIRED at epoch admission:** caller provides the real emitting compartment list (core,neuron) from an independent authoritative trace of the HLS dispatch. There is no valid way to reconstruct a completely missing source group from only the packet frame. Source list order is not constrained, but duplicate and out-of-bounds provenance fail. Silent sources emit no packet; readout-source spikes with no outgoing routes are legal.
- `p07_b2b_epoch_init` binds the previously verified `P06B13I1` B.2a input view, trusted graph and caller-owned pending-event storage; resets the model epoch to zero. It does NOT reset actual PL compartment memory, P02 DDR records, per-image raw outputs or a physical run journal.
- `p07_b2b_step` validates the *entire* frame and source list, authenticates existing pending counts against caller storage, then sums **per-core CURRENT = current external events + prior routed events**, rejects any >4,096, checks new output **per-source packet count** and **per-destination NEXT count** ≤4,096, checks output storage capacity and final tick-25 nonempty NEXT rejection. On any error `state`, pending-buffer bytes and receipt stay unchanged. On success (and only then) packet destinations/axons are staged as NEXT events, counts and bank index committed, and epoch advances once. There is no physical current/next bank write or rollback performed in this phase.
- Epoch receipts are read-only planning evidence, including tick, bank parity `t % 2`, external/routed-current/routed-next totals, per-core CURRENT/NEXT/emitted counts and bytewise CRC of the B1.3 12-byte packet payload. This is **not** PL AXI telemetry or an ELF mailbox ABI.

## 3. New native regression and evidence limitations

`tests/native/p07_b2b_packet_harness.c` is a **host-only fixture loader**, never built into production firmware. It verifies the original B.2a ingress independently, binds predeclared byte-exact input and output maps, processes all 26 epochs, prints normalized receipt and NEXT vectors as CRC digests, and asserts that a rejected frame cannot mutate pending storage, epoch bookkeeping or the prior receipt. Its staged `--inject` adversarial case is an **unreachable hypothetical bank state** used only for precise 4,096 CURRENT acceptance/4,097 rejection.

`tests/test_p07_b2b_packets.py` compares C receipts against original B1.3 `StreamingEpochGuard` for six 26-tick runs (genuine small compiled B1.2 synthetic graph, two readout placement modes, zero/all-255/mixed input), using the original Python `encode_packet_frame`, source-spike traces and full original 25+1 epoch semantics. Negative tests include CRC-valid forged semantics, wrong version, magic, SHA bindings, invalid epoch/target/route, noncanonical order, duplicates, incomplete/missing entire emitting source, missing/duplicated provenance, final tick-25 packet rejection and retry after a rejected transaction. A separate **synthetic 27-core, 26-hidden+one-readout routing-only** stress case proves 26 physical-logical core identifiers can be included in a B1.3 stream, 20,384 external fanout events per input tick, and exactly 26 routed NEXT packets per emitting epoch. This is **not** a trained physical dense result or even a full B1.2 neural numerical 27-core result. No full B2 candidate or original TEST image is opened by the new tests.

**Capacity domain warning:** per-source packet and per-destination CURRENT/NEXT ceilings are not a made-up aggregate chip-wide 4,096 limit. B1.2 may legitimately compress 10 hidden-to-readout synapses into one axon route event. The original B2 graph has 1,000 distinct hidden-to-readout source events/tick *maximum*, not 10,000 synapse contributions. Source-level zero weights remain part of the untouched P02 packing and source graph.

## 4. Remaining mandatory physical blockers

This is **P07-B.2b host-native transport admission**, not an accepted KV260 runtime. Missing work before B.3/B.4 includes a verified standalone A53 build/ELF and linker placement, physical 0x40000000–0x43FFFFFF DDR exclusivity, explicit 27-context page residency/dirty writeback, continuous 26-tick barrier/eviction scheduling and coherent LAST flush, authoritative **real PL source-spike provenance**, actual P03 64-bit packet-to-B1.3 adapter, actual atomic event-bank insertion/rollback and error mailbox, per-image hardware state/current/NEXT/packet/reset, independent 27-core TRAIN-derived host/board parity and physical counters. The caller-owned pending buffer, trusted-route data and borrowed B.2a input frame **must not overlap** and must stay immutable when treated as source data; B.3 must pin exact placement in the runtime owner map. No new FPGA is programmed here.

**GO** for P07-B.3 design only after user B.2b native acceptance. **NO-GO** for scaled physical KV260 inference, physical page traffic measurements and B2 official MNIST TEST unseal.

## 5. Reproduce on the original Linux workstation

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# NEW portable C11 source + true B1.3 Python oracle/negative suite:
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p07_b2b_packets.py

# Previous B.1 / B.2a / accepted B1.3 regression, no B2 TEST:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b1_owner_map.py tests/test_p07_b2a_ingress.py \
  tests/test_p06_b13_streaming.py tests/test_p06_b12_partition.py \
  tests/test_p06_b1_contract.py

# Optional prior frozen B2.4 33-file read-only host check, never B2 TEST:
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" --deep
```

**Evidence categories:** local standalone C module compile and a manually staged synthetic C smoke are not equivalent to the above tests against the full repository Python oracle; exact full-repository results remain **user-native PENDING**. No GitHub Actions PASS, Vitis ELF, bitstream, DDR dump, live paging performance or physical correctness is claimed. Record skips explicitly; do not infer native PASS from committed test source.

**Gate:** after the user posts P07-B.2b test results, log them as an *external evidence ledger* while preserving original B1/B2 frozen artifacts. Then begin **P07-B.3**, not a speculative new PL engine. Draft PR #49 stays unmerged until explicit user authorization.


### Additional exact packet-bank boundary gate

`tests/native/p07_b2b_capacity_harness.c` directly constructs an independently checksummed 4,096-packet `P06B13R1` frame with one source and one NEXT destination, verifies **exact acceptance** and both decoded counters, then checks that a 4,097th route fails when added to the same emitting source and when spread over distinct emitting sources into the same destination. Both malformed bindings are independently rejected **before decoding** and cannot modify a previously published frame view. `test_independent_large_source_and_next_4096_vs_4097_boundary` builds and executes this C harness in the main B.2b pytest. This is structural packet-bank admission, not a real FPGA packet burst or SRAM measurement.
