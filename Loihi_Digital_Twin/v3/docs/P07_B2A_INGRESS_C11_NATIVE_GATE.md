# P07-B.2a — Independent A53-compatible `P06B13I1` ingress and native oracle gate

**Stage:** P07-B.2a **implementation candidate** on `agent/v3-p07-b-scaled-physical-inference`. **B.1 was independently user-attested native PASS** (see `P07_B1_USER_ACCEPTANCE_LEDGER.json`; no raw test counts supplied). **B.2a full user-native PASS remains PENDING.** B.2b routed `P06B13R1` transport/transaction guard, B.3 paging and board execution are **not implemented here**.

This is the first independently testable slice of P07-B.2. Original accepted Track A, B2 candidate, B2.4 33 files/27 frozen P02 records, and the sealed B2 official MNIST TEST remain **untouched**. No Vivado, Vitis, standalone ELF, bitstream, FPGA commands or K26 DDR writes were introduced.

## 1. Inputs and authoritative ABI

Reuse original `src/loihi_twin_v2/p06_b13_streaming.py` and `docs/P06_B1_3_MULTICORE_STREAMING_ABI.md` **without modification**. Its ingress frame is **not** the earlier P05 `P05G` or compact P07-A format. Every field is read as bytes, not as an aligned host-language struct:

| Offset | Contents |
| --- | --- |
| 0..7 | ASCII `P06B13I1` |
| 8..63 | 14 little-endian u32: `version=1`, `header_bytes=128`, payload size, route count, logical core count, `784` channels, `25` input ticks, `26` total ticks, `6` bytes/route, `784` bytes/pixels, payload CRC32, header CRC32, zero flags, zero reserved |
| 64..95 | 32 raw bytes of independent **trusted** B1.2 compiled deployment SHA256 |
| 96..127 | 32 raw bytes of independent **trusted** B1.1 capacity audit SHA256 |
| 128.. | Strictly sorted repeated `<HHH` routes (pixel index, destination core ID, destination axon) followed by original 784 unsigned row-major pixel bytes |

**Header CRC32** is IEEE/zlib-compatible CRC over all 128 bytes with bytes 52..55 zero. **Payload CRC32** covers the complete map and 784 pixels. All dimensions, complete byte length, SHA identity bytes, flags, CRC, route ordering, no duplicate (pixel,core), bounds (core<configured logical core count, axon<4096), every pixel 0..783 present, per-core static fanout and **exact map bytes** are checked before publishing a decoded view. CRC detects accidental corruption and is not a MAC or proof of the trained graph.

The binding parameter includes independently trusted route bytes and nonzero compiled/capacity digests. **Never derive the trusted digest or mapping from the incoming frame itself** in production. For the *real B2 model*, the accepted B2.3 compiled SHA is `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`, the capacity audit SHA is `82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498`. The new code does not load these from a frozen local directory or independently attest that directory; this remains a board firmware and provisioning prerequisite.

## 2. New source and native contract

- `software/p07/include/p07_b2_ingress.h`: versioned `p07_b2_ingress_binding`, immutable borrowed `p07_b2_ingress_view`, portable C `p07_b2_input_event` (<u16 core, u16 axon>) and per-tick result struct. No Xilinx includes, malloc, global writable model memory or original frozen changes.
- `software/p07/p07_b2_ingress.c`: independent byte decoder and bitwise IEEE CRC32, strict checks, plus original `p06-uint8-quota-phase17-v1` integer formula: `phase=(tick+17*pixel)%25`; fire iff `floor((phase+1)*value/255)>floor(phase*value/255)`. Ticks 0..24 include external input; tick 25 is an **external-free drain**, no exceptions. Event order is pixel ascending then core ascending, not 27 consecutive per-core blocks.
- `tests/native/p07_b2a_ingress_harness.c`: host-only fixture loader and real C11 execution of 26 epochs; outputs `B2_TICK <tick> <count> <CRC32>` over repeated **little-endian (core,axon) 4-byte tuples**, then `P07_B2A_NATIVE_INGRESS_PASS=1`. This CRC is **native test telemetry**, not a P03 register or DDR image digest. The native harness owns its fixture buffers as static arrays; file operations are ONLY in the harness, never in the deployed C decoder.
- `tests/test_p07_b2a_ingress.py`: builds with `cc -std=c11 -Wall -Wextra -Werror -pedantic`; verifies three small **real B1.2/B1.3-compiled** synthetic networks/inputs against original Python `encode_ingress_frame`, `decode_ingress_frame`, `IngressEnvelope.events` and the independent `pixel_spikes` reference, every tick. A separate stress fixture has **synthetic** 27 cores and 20,384 pixel-to-hidden routes, including zeros, all-255 and phase-varied images. It uses **synthetic SHA markers distinct from B2 frozen SHA**; it does **not** assert that fabricated routes are the trained deployment. Adversarial CRC, digest, wrong counts/ticks/version, map substitution, noncanonical ordering, missing pixels, bad axons and old P07-A magic are rejected; C harness checks preservation of the previously accepted view/receipt on selected errors.

For synthetic all-255 with 26 hidden shards: exactly **20,384 events/tick** for 25 input ticks = **509,600 logical fanout events**, then zero external events on drain tick. These are logical event objects and **not** AXI transfers or performance measurements.

## 3. Firmware ownership and fail-closed boundary

The decoder is written for use by future standalone Cortex-A53 firmware, but **no firmware entry point uses it yet** and no board transport is claimed. A decoded view borrows input bytes from caller-managed buffer: the caller must keep that memory unchanged until the entire image's 26-tick consumption has ended or must make an immutable trusted snapshot. The independent trusted map must be stored separately from the untrusted frame and retained unchanged. The pointer/byte comparison does not make SHA a secure attestation root.

`p07_b2_decode_ingress` only assigns its output after all validation. `p07_b2_ingress_tick` does a capacity/count preflight before writing caller-owned output and receipt; on invalid tick, insufficient buffer, or overflow neither output is changed. The function **does not itself perform DDR bank insertion**. Future board firmware must also fail closed and avoid any hardware writes until route/current/NEXT budget checks are complete.

The worst-frame design bound `784*126` routes fits within the B.1 planned **917,504-byte** staging region. For the trained 27-core mapping, the expected frame is **123,216 bytes**. The C test harness deliberately reserves a large static event buffer. Future A53 must place actual event buffers in a verified ELF/static or permitted DDR memory plan rather than on a limited stack; the maximum synthetic 27 hidden event list is 20,384 * 4 = **81,536 bytes** per tick, BEFORE routed NEXT events. No physical event-bank or board-memory allocation is proven by B.2a.

**Not yet implemented and still blocking P07-B:** C parser + provenance for `P06B13R1`, exact P03 HLS emitted packet fanout, next-tick bank atomicity, complete 4,096 CURRENT = external + routed counts, zero-packet sources and complete source-spike provenance, three-slot live paging/dirty writeback, per-image reset, bound Vitis ELF linker segments, A53 DDR cache coherency and real 27-core board parity. These are explicitly scoped to B.2b/B.3/B.4. The new ingress decoder is necessary but **insufficient** for authorization to execute scaled inference.

## 4. Native verification (stop after this gate)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New independent native ingress+exact Python oracle gate:
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p07_b2a_ingress.py

# Previously accepted B.1 and B1.3 regression:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b1_owner_map.py tests/test_p06_b13_streaming.py \
  tests/test_p06_b12_partition.py tests/test_p06_b1_contract.py

# Optional original 33-file B2.4 read-only SHA/P02 integrity:
PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" --deep
```

**Acceptance:** Share exit codes, passed/skipped counts and any stdout errors from the P07-B.2a test plus regressions. Upon user-native PASS, begin **P07-B.2b** packet-frame decoder, HLS emission provenance and atomic NEXT routing admission. Do **not** merge PR #49 or unseal B2 official TEST absent separate explicit user authorization.
