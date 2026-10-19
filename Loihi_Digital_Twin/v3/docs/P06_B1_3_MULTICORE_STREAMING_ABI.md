# P06-B1.3 — Versioned multi-core ingress and routed-packet streaming

**Implementation state:** host-side B1.3 **native acceptance candidate committed**, no GitHub CI / PC native PASS or physical result claimed here.  
**User-attested prerequisite:** B1.1 and B1.2 native regressions passed; in particular the user supplied full 784→1000→10 synthetic probe `P06_B12_SYNTHETIC_STRUCTURAL_PASS=1`, 27 logical cores, 794,000 synthetic synapses, 14,155,776 DDR backing bytes, 128,576 maximum per-core logical synapse bytes, maximum CURRENT event pressure 1,000. User-supplied source-derived hashes in the test report are not independently rehashed raw PC artifacts.  
**Branch:** `agent/v3-p06-b1-scalable-packing` (draft PR #46, unmerged).

## Acceptance separation / unchanged baselines

Only NEW Track B files are added. No edits to accepted P06-A model, 784→32→10 trained checkpoint, P07-A single-core `P07A1IN1` encoder/firmware, P02 `LTV3CTX1` fixed 512 KiB DDR records, P03 packed arithmetic, P05 3-slot scheduler, accepted KV260 physical results or P08-A latency data. **No board programming, MMIO, JTAG or DDR modification occurs in B1.3.**

**Transport API:** `src/loihi_twin_v2/p06_b13_streaming.py`.

Two *new* versioned, little-endian, CRC32-checked frame types share a fixed 128-byte header. The header is independent of the prior P07/P05 diagnostic ABI:

| Byte offset | Type | Meaning |
|---:|---|---|
| 0..7 | `8s` | `P06B13I1` image+map or `P06B13R1` inter-core packet frame |
| 8..63 | `<14I` | 14 explicit uint32 fields, format v1, header size=128, payload bytes, type-specific dimensions/counts, payload CRC32 at byte 48, header CRC32 at byte 52, zero flags/reserved at 56/60 |
| 64..95 | 32 bytes | **B1.2 compiled deployment fingerprint**, raw SHA256 |
| 96..127 | 32 bytes | **B1.1 resource/packed-DDR audit SHA256**, raw SHA256 |
| 128..end | variable | body; strictly canonical, caller-verified, byte-length checked |

Both CRCs validate **before** any logical epoch is committed. Header CRC is calculated over the complete 128-byte header with its own four bytes zero; payload CRC covers the complete payload. The model/network ID binding is SHA256 equality against accepted B1.2 result. CRC32 detects accidental corruption and ordinary test tampering; **it is not a cryptographic authenticated transport/MAC**, and SHA equality is not a firmware trust root.

### Image+replication-map `P06B13I1`

Field meanings for the 14 uint32 in order:
`[version,header_bytes,payload_bytes,route_count,logical_core_count,input_channels,input_ticks,total_ticks,route_entry_bytes,pixel_bytes,payload_crc32,header_crc32,flags,reserved]`.

Body: `route_count` sorted records `<HHH` (6 bytes each:
**source pixel index**, destination **logical core ID**, destination **axon ID**) followed by the original **784 raw uint8 pixels** in immutable row-major order. No direct pixel→axon equality assumption. Every one of the 784 pixels must have at least one destination; routes duplicate one source pixel across multiple logical cores but never duplicate the same `(pixel, destination_core)`. Encoded routes must byte-for-byte match the actual B1.2 `CompiledDeployment.ingress_routes`. Both core IDs and axon IDs are checked against *real, existing* `LogicalCoreConfig.input_axons`.

The accepted `pixel_spikes` is reused unchanged: 25 event ticks, one drain tick, phase/quota formula; one event per active pixel for **each** mapped destination core on that tick. Ordering is canonical: pixel ascending → logical core ascending → destination axon. Pixels=255 triggers 784 active channels **on every one of the 25 input ticks**, then no new external packets on tick 25.

The 27-core synthetic reference requires exactly `784 × 26 = 20,384` source-replication map entries and per-input-tick logical external events; **509,600** logical external events across 25 input ticks (these are logical replicated events, **not** physical AXI transactions). Image+map frame size under this planned profile: `128 + 20,384×6 + 784 = 123,216 bytes`. This is distinct from and should never be fed to the earlier 896 KiB P05 diagnostic deployment transport.

### Routed `P06B13R1` packet frame

Fields: `[version,header_bytes,payload_bytes,emitted_timestep,packet_count,logical_core_count,packet_entry_bytes,max_packets_per_source_core,reserved,reserved,payload_crc32,header_crc32,flags,reserved]`.

Each route packet is a 12-byte record `<IHHHH`:
**target logical timestep** (uint32), **source core** (uint16), **source compartment** (uint16), **destination core** (uint16), **destination axon** (uint16). Emitted `t` always targets **`t+1`**, exactly matching P03 `SpikePacket`. The source timestep is reconstructed from frame `emitted_timestep` after validation. All records sorted by existing `SpikePacket.logical_key`, and checked against actual compiled source output-route tables. The frame must contain **all distinct routes** for every emitting source neuron it includes (reject missing/duplicate/spurious destination fanout). A frame may contain zero packets.

Packets emitted by one source core must never exceed 4,096 in its packet bank; pending packets targeted to one destination core must never exceed 4,096 in its NEXT event bank. **There is no invented per-chip global 4,096 packet ceiling**; capacity is per source / destination core. A tick's CURRENT bank must accommodate **all external events for that tick PLUS all prior-epoch routed packets**; fail before committing if this exceeds 4,096 in any one core.

### Transactional 26-epoch guard

`StreamingEpochGuard` validates:
- The two frames' shared B1.2 mapping fingerprint and exact B1.1 capacity audit SHA256; strict routing/axon existence.
- Epoch in 0..25, CURRENT bank index `t % 2`, all external traffic for current tick, all previously staged NEXT packets; reject any wrong timing.
- Routed frame source→destination legality, exact per-emitting-origin full fanout, per-core 4,096 event/packet buffers, static conservative all-255 capacity envelope.
- Optional **`source_spikes=((core,compartment),...)`** from independent chip trace: detect an **entire omitted emitted source** or an invented source that a packet-only frame would otherwise be unable to distinguish from a truly silent neuron. This optional provenance is available to B1.3 software tests; a future physical equivalent requires authoritative PL trace/packet counters.
- Reject nonempty outgoing packet list on the final tick 25 because inference would silently discard packets addressed to tick 26.
- All-or-nothing **transaction semantics**: on any rejection, `current_tick` and pending NEXT packet buffer are preserved. No partial bank commits.

`EpochReceipt` returns per-core current/NEXT occupancy, outgoing packet counts, external and routed event totals and normalized packet vectors. These receipts are planning/testing evidence only, **not actual physical DDR bank contents or AXI streams**.

**Important boundary:** source-spike provenance cannot be reconstructed from packet frames alone. Without an authentic source-spike trace the validator can reject incomplete fanout for a source *present* in the frame, but cannot reject an entirely omitted source group. Future P07-B firmware must supply packet/trace accounting or equivalent authoritative emitting-source evidence. The guard is **not** an independently implemented monolithic neural oracle (B1.4), a page-fault/eviction scheduler (B1.5), actual firmware, a tested resident/nonresident packet path, timing measurement or physical KV260 execution.

## B1.3 independent synthetic tests

File: `tests/test_p06_b13_streaming.py`. Expected gates:

1. An independent little-endian unpacker checks raw offset/length/CRC/SHA fields and 784-channel replication across two hidden partitions; identical event tuples to preexisting P06 compiler.
2. Malformed magic, version, frame lengths, SHA bindings, CRC, reserved flags, map substitution, wrong packet target/core/axon/epoch, missing fanout, duplicate fanout and spurious provenance are **fail-closed**.
3. Numerical **all-255 25+1 tick** logical chip exercise with **two hidden logical cores and one readout**. Under different valid servicing and reversed packet draining, manually expected hidden spikes (3 per input tick), readout spikes (2 per tick 1..25), per-core 784+784 external fanout, 6 routed output packets/tick and exact epoch bank occupancy must agree.
4. Explicit CURRENT bank **4096 exact limit vs 4097 rejection**, and transactional preservation on rejection. The adversarial queued-packet test directly injects a hypothetical transport buffer state and is **not** a reachable sample from its small accepted graph.
5. Optional **full synthetic 784→1000→10 27-core** ABI test: encoded route frame is 123,216 bytes, all 20,384 replicated ingress events on every all-255 input tick, readout max 1,000 prior routed packets, 390 maximum emitted packets per hidden core, and no per-core event/packet overflow. **No 794,000-synapse 26-tick numerical result is claimed for B1.3**.

## Native acceptance commands (Linux/VS Code, host only)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b1-scalable-packing
git pull --ff-only origin agent/v3-p06-b1-scalable-packing
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New binary transport / 26-tick numerical / corruption / overflow tests:
PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p06_b13_streaming.py

# B1.1+B1.2 original branch regressions:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b12_partition.py tests/test_p06_b1_contract.py

# Frozen P06-A compiler/input regression:
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_lif_compiler_probe.py tests/test_p06_lif_input_probe.py

PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b13_streaming.py \
  tests/test_p06_b13_streaming.py \
  scripts/p06_b13_synthetic_stream_probe.py

PYTHONPATH="$PWD/src" python scripts/p06_b13_synthetic_stream_probe.py --hidden 40

# Opt-in: larger memory/CPU 27-core full fanout/stream structural case:
P06_B13_FULL_SYNTHETIC=1 PYTHONPATH="$PWD/src" \
  python -m pytest -q -rs tests/test_p06_b13_streaming.py \
  -k full_27_core_1000_hidden_multicast_abi_exact_counts

PYTHONPATH="$PWD/src" python scripts/p06_b13_synthetic_stream_probe.py --hidden 1000
```

Expected script success marker: `P06_B13_SYNTHETIC_STREAMING_CONTRACT_PASS=1`. Native results are **PENDING USER VERIFICATION**. No JTAG, bare-metal boot, PL execution or official MNIST TEST access is required or permitted in B1.3.

## Next milestone (not yet begun)

**B1.4**: independent monolithic integer LIF reference and separately partitioned 26-tick oracle, verify every compartment's current/voltage/refractory and every spike/packet/readout count under randomized signed weights and adversarial service order. Passing this B1.3 packet transport contract does **not** satisfy that independent numerical acceptance gate. Then B1.5 estimated 3-slot scheduling/paging, B1.6 final B1 acceptance.

Do not merge draft PR #46 without explicit user approval.
