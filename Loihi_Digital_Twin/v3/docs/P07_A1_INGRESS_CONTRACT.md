# P07-A1 — Versioned 784-pixel/A53 ingress, host gate (USER-ACCEPTED)

**Branch:** `agent/v3-p07-a-784-axon-streaming` (from
`main@11440d6604b9c591388dd60a5f7a5a92b5d9ce3e`).
**Scope:** contract, portable Python builder/parser, independent C11 validator
and pixel event planner, host regressions. **USER-ACCEPTED on 2026-10-17**;
see `P07_A1_FINAL_CLOSEOUT.md` for user-attested native PASS, actual
full DDR SHA256 and trained compiler fingerprint. No physical KV260
MNIST inference or official TEST evaluation is implied.

## Why a new contract is necessary

Accepted `software/p05/p05_deployment.c` validates one sole external axon per
logical core, although the existing P03 adapter already supports registering
up to 4096 independently addressed valid axons/core in a bitset and the PL
event bank accepts up to 4096 32-bit axon IDs. P06's frozen compiler
`CompiledDeployment.ingress_routes` provides explicit source-pixel to
destination-core/axon mappings; their IDs are not intrinsically equal to pixel
indices. The existing P05 `P05G` v1 diagnostic format and parser remain
unchanged. P07-A1 transfers a **raw image plus its compiled ingress map**,
not 25 pre-expanded spike banks, to keep event generation autonomous on A53.

## P07-A1IN1 v1 byte layout (all integers unsigned little-endian)

The single-frame wire record is exactly **2480 bytes**. Header (128 B):

| Byte offset | Width | Contents / required value |
|---|---:|---|
| 0 | 8 | ASCII `P07A1IN1` |
| 8 | 4 | version = 1 |
| 12 | 4 | header_bytes = 128 |
| 16 | 4 | payload_bytes = 2352 |
| 20 | 4 | map_bytes = 1568 |
| 24 | 4 | image_bytes = 784 |
| 28 | 4 | input_channels = 784 |
| 32 | 4 | input_ticks = 25 |
| 36 | 4 | total_ticks = 26 |
| 40 | 4 | destination_core = 0 |
| 44 | 4 | mapping entries = 784 |
| 48 | 4 | per-core axon address capacity = 4096 |
| 52 | 4 | reserved flags = 0 (otherwise reject) |
| 56 | 4 | CRC-32/ISO-HDLC of all 2352 payload bytes |
| 60 | 4 | CRC-32/ISO-HDLC of 128-byte header, with bytes 60–63 zero |
| 64 | 32 | Actual complete 524,288-byte P02.1 static DDR-file SHA-256 |
| 96 | 32 | Frozen compiled-deployment fingerprint (SHA-256) |

Payload (2352 B): from byte 128, exactly 784 `uint16 LE` destination
**axon IDs**, indexed by *pixel index* 0..783; at byte 1696, exactly 784
raw row-major `uint8` pixels. No labels, variable-length lists, implicit
padding, native-endian structs, event timestamps, or preexpanded frames.
Total bytes = 128 + 1568 + 784. No zero SHA-256 fields are allowed.

The map MUST contain one entry per pixel, exactly one **distinct** core-0
destination axon for each index, in 0..4095. No assumption that axons are
consecutive or sorted, or equal to original pixel indices. The Python export
extracts this from `CompiledDeployment.ingress_routes`, rejects unknown,
missing, duplicate, wrong-population and wrong-destination routes. The C
validator independently checks every map entry and collision using a
4096-bit bitset. Out-of-range header counts, unknown flags, wrong lengths,
bad CRCs, invalid axons and invalid provenance fields are rejected before
hardware access. The two SHA fields name frozen artifacts; their mere
presence is NOT authentication. Before any A53 deployment, an independent
trusted expected-DDR/compiled-fingerprint comparison is required in P07-A2.

## Event generation, ordering, lifetime and bank ownership

For each image, A53 validates the record and generates logical tick
`t=0..24` events in **ascending pixel index**. For each source pixel `i`:
`s=(t+17*i)%25`; emit its mapped destination axon iff
`((s+1)*pixels[i])//255 > (s*pixels[i])//255`.
A given pixel fires at most once per tick. Thus each input tick produces at
most 784 external events, always beneath the hard 4096-entry event bank
depth; **the aggregate occupancy includes hidden→output packets already
in CURRENT**. The A53 caller must verify `existing_count + generated_count
<= 4096` before writing any entries. Input events append *after*
existing routed CURRENT packets, preserving those packets and the original
per-image causal order. Tick **25** adds zero external events and drains
previously routed hidden spikes. Every tick performs exactly one core
dispatch, routes only to NEXT (`t+1`), and executes an explicit barrier.

The portable `p07_a1_tick_events` API is **planning only**: it revalidates
the immutable record on each call, computes the count before touching caller
memory, and never writes a partial output list. `out_axons` is
caller-owned scratch; no pointer to untrusted DDR is retained. The C
implementation does not generate or modify an actual FPGA event bank.

**P07-A2 owns** the safe A53 placement/DDR address, cache maintenance,
DMA/PL MMIO, 784+32 axon registration, current-bank append, NEXT-bank
routing, full-image neuron/state reset, discarded final NEXT emissions,
10-class output-spike trace readout, and errors/telemetry. The P07-A1
buffer must remain immutable while A53 validates or consumes it. P07-A2
must use a separately versioned A53 application and must not reinterpret
P05 v1 diagnostic headers as P07 input. This version supports one image,
one logical core only; future multi-frame and multi-core Track B formats
will be versioned independently.

The HLS datapath is clocked and operates with explicit logical barriers,
not a clock-free asynchronous neuromorphic device. Accepted signed-24
arithmetic, `strict voltage > threshold`, decay rounding, hidden→output
one-step NEXT delivery, threshold values and class readout are unchanged.

## Native reproducible checkpoint

From user's VS Code Linux repository with the existing virtualenv:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch --track origin/agent/v3-p07-a-784-axon-streaming
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a1_ingress.py \
  tests/test_p06_a2_input_contract.py \
  tests/test_p05_1_deployment.py

sha256sum artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin
python -m json.tool artifacts/p06_a4_static_ddr_seed20261013/p06_a4_static_ddr_freeze_manifest.json

PYTHONPATH="$PWD/src" python scripts/p07_a1_ingress.py \
  --synthetic ramp \
  --out artifacts/p07_a1_ingress_ramp_v1.bin

cc -std=c11 -Wall -Wextra -Werror -pedantic \
  software/p07/p07_a1_ingress.c software/p07/p07_a1_probe.c \
  -o /tmp/p07_a1_probe
/tmp/p07_a1_probe artifacts/p07_a1_ingress_ramp_v1.bin
```

The script refuses to overwrite an existing output. Use a **new** output
filename on rerun. It loads the actual accepted local checkpoint, verifies
pinned training hashes and the previously generated static DDR record plus
its separate manifest, recompiles the real ingress mapping, checks its
fingerprint, then emits one 2480-byte transfer. Synthetic `black`, `white`,
and `ramp` inputs are supported. `--raw-image` accepts one prechosen
784-byte validation/synthetic image only; **official MNIST TEST remains
SEALED**. No reprovisioned/retrained weights, no new DDR generator.

Host expected markers:
`P07_A1_HOST_RECORD_PASS=1` and `P07_A1_C_NATIVE_PASS=1`.
Record the emitted `P07_A1_DDR_SHA256` and exact `P07_A1_COMPILED_FINGERPRINT`
alongside user-native command output. This is a host gate only.

## Acceptance boundary

**P07-A1 completed its native user acceptance gate on 2026-10-17.**
The user verified the actual P02 static DDR digest, produced a real
compiler-bound ramp ingress record and passed the independent C probe.
All first-gate details are in `P07_A1_FINAL_CLOSEOUT.md`. No XSDB/Vivado/
Vitis run was needed for the scoped A1 host interface; those remain
mandatory for P07-A2/A3 trained physical inference. Do not treat host
validation as FPGA observation or merge without explicit authorization.
