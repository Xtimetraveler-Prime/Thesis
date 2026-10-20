# P07-B.2b — Independent C11 routed packet, source provenance and atomic NEXT-epoch gate

**Status: implementation candidate, user-native verification PENDING.** P07-B.1 and P07-B.2a were independently **user-attested HOST-NATIVE PASS** on 2026-10-19; accepted raw test stdout and test counts were not pasted. See external additive evidence ledgers `docs/P07_B1_USER_ACCEPTANCE_LEDGER.json` and `docs/P07_B2A_USER_ACCEPTANCE_LEDGER.json`. Branch `agent/v3-p07-b-scaled-physical-inference`, draft PR #49, **DO NOT MERGE** before user authorizes. No accepted Track A/B source, weights, snapshot, original P02 context, P07-A physical evidence or B2 official MNIST TEST protocol is modified.

## 1. Existing source of truth

The B.2b implementation independently parses the original **host-proposed** `P06B13R1` packet ABI in `src/loihi_twin_v2/p06_b13_streaming.py` and `docs/P06_B1_3_MULTICORE_STREAMING_ABI.md`, preserving original B1.2 output-routing semantics. This is **not** the old P05 one-axon-core diagnostic, the 64-bit direct P03 HLS packet register layout, or hardware firmware already installed on KV260. It must eventually be adapted to independently obtained P03 emitted route records and real PL spike provenance.

Every packet frame is a fixed **128-byte** header with magic `P06B13R1`, LE 14×u32 (version 1, header length, payload length, emitted epoch, packet count, logical core count, record bytes 12, per-source cap 4096, two reserved zero words, payload CRC32, header CRC32, flags and reserved zero), followed by two raw SHA256 identity fields: **B1.2 compiled fingerprint** at offsets 64..95 and **B1.1 packed-capacity audit** at 96..127. CRC32 header is over header with bytes 52..55 zeroed; payload is exactly `count * 12` bytes. Each packet is `<IHHHH`: **target_tick:u32, source_core:u16, source_compartment:u16, destination_core:u16, destination_axon:u16**. Packet transport order is original `SpikePacket.logical_key`: `target_tick, destination_core, destination_axon, source_core, source_compartment` (source tick and packet class are constant in this frame). Emitted tick `t` targets **t+1**.

The two 32-byte digest fields must match a **separate trusted binding** of the original frozen B2.4 mapping. CRC is error detection, not authentication; SHA equality without independent checkpoint custody is not secure attestation. The accepted original trained B2 identities remain **compiled** `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`, **capacity-audit** `82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498`; synthetic tests deliberately use unrelated SHA values. B2's 97.08% is TRAIN-derived validation, NOT official TEST.

## 2. Committed portable C module (implementation candidate)

- `software/p07/include/p07_b2_packet.h`: trusted source-ordered route bindings, compartment counts, 32-byte compiled/audit identity checks, an immutable borrowed decoded frame view, and a transactional **per-core count-only** epoch state/receipt API.
- `software/p07/p07_b2_packet.c`: strict independent LE wire header/payload CRC32 and digest decoder, canonical packet ordering by destination then source, checked route membership, exact complete fanout from an independently supplied **sorted, unique, authoritative source-spike list**, and 4,096 per-source/per-destination capacity. Reject nonempty tick-25 frame. `p07_b2_packet_commit` checks combined external plus prior pending CURRENT pressure, then prepares NEXT counts, and only publishes its state and receipt when all validation succeeds. Maximum **8,192 trusted route entries** for this initial bounded prototype; this restriction is not a claim that every future graph fits.
- `tests/native/p07_b2b_packet_harness.c`: standalone host C fixture checks one authenticated source-to-destination route, complete 26-epoch progression, identity/header CRC rejection, missing spike provenance, full 4,096 event capacity accepted and 4,097 rejected with state/receipt preservation, and final drain rejection.
- `tests/test_p07_b2b_packets.py`: compiles the native harness and decoder against C11 `-Wall -Wextra -Werror -pedantic` and checks the native PASS marker.

**Important implementation scope:** This initial B.2b prototype is **not** yet a complete A53-ready transactional routed-event system. It retains *NEXT event counts*, not the actual per-destination ordered packet vectors, and does not perform event-bank insertion. It takes trusted routes and authoritative source spikes from its caller but does not itself derive either from the original B2.4 frozen package or a real HLS trace. A complete independent end-to-end Python-B1.3 `StreamingEpochGuard`/C randomized differential suite and immutable tuple-buffer transaction implementation are **outstanding**. The C harness is a focused smoke/negative acceptance candidate, not evidence of the full 27-core runtime or full B.2b closeout.

## 3. Native gate (B.2b initial candidate; full B.2b acceptance still pending)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b2b_packets.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b1_owner_map.py \
  tests/test_p06_b13_streaming.py
```

The user has attested B.1 and B.2a native PASS, but these newly committed B.2b bytes have **not yet been independently tested on the user's PC**. This result is a checkpoint within B.2b, not permission to proceed directly to B.3 or to flash the board.

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


## 5. B.2b follow-on: complete ordered NEXT vectors and original Python/C differential (new)

**Status: additional code committed, awaiting independent native execution.** The user separately attested that the first B.2b count-only parser native tests passed. This is recorded in `P07_B2B_INITIAL_USER_ACCEPTANCE_LEDGER.json` without fabricating stdout, count, or board results.

**New additive API (legacy B.2b parser/count API is retained unchanged):**

- `software/p07/include/p07_b2b_transaction.h` and `software/p07/p07_b2b_transaction.c` introduce `p07_b2b_transaction_init` and `p07_b2b_transaction_step`. The actual accepted B.2a `P06B13I1` ingress view and B.2b `P06B13R1` decoded packet must be supplied, as must separately verified compiled routes and emitting-source provenance.
- Caller supplies a **preallocated ordered NEXT tuple buffer** (max accepted prototype capacity 8,192 tuples; no dynamic allocation), with a per-core occupancy mirror. All existing staged tuples are checked against occupancy before current-tick addition. External CURRENT is independently recomputed using the frozen quota/phase17 25+1 schedule. Every destination CURRENT total is `prior routed + current external`; 4,096 passes and 4,097 rejects.
- Full source-route membership, complete fanout, canonical ordering, input digests and CRC are inherited from the **original B.2b frame validator** `p07_b2_packet_decode`, and verified again at preflight where required. A valid frame emits a deterministic ordered sequence of `<HH>` NEXT tuples; pending count, per-core counts, logical tick and receipt all publish at one commit point. Failures leave **the entire caller-owned NEXT array, state struct and prior receipt bitwise unchanged**; even the uninitialized/stale tail is not touched on rejection.
- A newly declared native verification module `tests/test_p07_b2b_transaction.py` compiles the *real three repository C modules* into a host shared library with `-std=c11 -Wall -Wextra -Werror -pedantic`. It uses Python ctypes to read exact C packet tuples and receipts over **six 26-tick** synthetic, genuine B1.2/B1.3-compiled cases (2 readout partition placements × raw input: all-zero, all-255, nontrivial phase pattern), comparing every epoch with the **existing, unchanged** `StreamingEpochGuard` and its real `encode_packet_frame`. Bytewise untouched state/receipt/NEXT buffer after failure, corrupted CRC/digest/order/target/fanout, omitted source group, duplicate provenance, retry, 4,096/4,097 CURRENT and nonempty drain NEXT are covered. No official TEST or trained B2.4 data is accessed.

**Important limitations:** This is still *host-only*, and the firmware source has not been linked to an A53 ELF. New code stores actual tuple vectors in portable caller memory; it **does not physically insert, cache-clean or rollback resident or DDR NEXT banks**, nor derive authoritative spike lists from HLS physical trace. The transient frame and trusted map must remain immutable while decoded; the caller must reserve and prove nonoverlapping firmware RAM and perform physical reset/ownership admission. B.3 must integrate runtime page-residency and next epoch bank ownership before hardware tests. Do not misrepresent native packets/CRCs as board trace or measured FPGA AXI traffic.

### New verification commands

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New complete ordered NEXT-vector and independent Python/C gate:
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p07_b2b_transaction.py

# Original B.2b and previous stage regressions:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b2b_packets.py \
  tests/test_p07_b2a_ingress.py \
  tests/test_p07_b1_owner_map.py \
  tests/test_p06_b13_streaming.py \
  tests/test_p06_b12_partition.py \
  tests/test_p06_b1_contract.py

# Original B2.4 frozen checkpoint verification (read-only, no B2 TEST):
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" --deep
```

**Acceptance gate:** user-native PASS for the newly added differential tests is still required before the B.2b software transport can be considered accepted. Do not advance to B.3 or merge PR #49 without authorization. The official B2 MNIST TEST remains sealed.
