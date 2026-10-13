# P05.1 first checkpoint — Versioned PS regression deployment contract

**Status:** Host C11/Python deployment contract independently
reported PASS, followed by successful separate P05 Cortex-A53
Vitis ELF build and two independently accepted physical KV260
workloads on 2026-10-12. P05.1 functional subphase is
**COMPLETE**. Historical host-only checkpoint expectations
below were recorded before board execution and are retained
as reproducible instructions, not current acceptance blockers.
See `docs/P05_1_TRIANGLE_ACCEPTANCE.md`. P03 remains intact.

## Why this checkpoint comes before the new PS executable

The accepted P03.4/P03.5 application (`software/p03/p03_finish_run.c`)
intentionally accepts a fixed 5-core ring with 7 or 100 timesteps.
P05.1 needs a reusable, safe and replayable way to describe a range
of test workloads with varying core count, deterministic service
order, external spike trains, and diagnostic checkpoints. The
resulting **deployment contract** must be independently checked
before building a Cortex-A53 application that reads untrusted
DDR data and drives real FPGA MMIO.

This checkpoint adds:

- `scripts/p05_deployment.py`: Python generator for workload
  specifications and immutable initial DDR records. Produces
  `p05_header.bin` (256 B), `p05_payload.bin` (bounded),
  `coreN_initial.bin` files and a manifest with checksums
  and full SHA-256 artifact identities. Includes a `from-p03`
  converter to reproduce the accepted P03 five-core workload
  without changing the original P03 oracle or fixture.
- `software/p05/include/p05_deployment.h` and
  `software/p05/p05_deployment.c`: standalone portable C11
  **read-only** validator; shares no heap, Python/BSP dependency
  or MMIO side effects. Rejects malformed size/count/offset,
  CRC, duplicate logical IDs, dangerous physical ranges,
  events for unregistered input axons, incorrect order, per
  timestep/core event overflows and invalid/duplicate checkpoints.
- `tests/test_p05_1_deployment.py`: Python/C contract
  roundtrips and fail-closed negative cases, including mutations
  with **recalculated valid CRCs** to prove that checksums
  alone are not treated as semantic correctness.

This format is **new P05 ABI v1**, not a rewrite or extension of
the frozen P03 256-byte manifest. Nothing currently loads this
P05 ABI onto a Cortex-A53; connecting it to a separate P05
ELF with physical callbacks is the next development gate.

## Fixed DDR reservation and explicit bounds

This diagnostic workload format occupies only the project-approved
64 MiB board-reserved window and does not overlap existing records
or the result mailbox.

| Address | Size/capacity | Purpose |
|---|---|---|
| `0x40000000` | max 126 × `0x80000` (512 KiB each) | Logical-core backing records, with ID `0..125` |
| `0x43F00000` | at most `0xE0000` (896 KiB) | Packed P05 core rows + ingress vectors + requested checkpoints |
| `0x43FE0000` | 256 B | Immutable P05 header |
| `0x43FF0000` | 256 B currently reserved | Future P05 result mailbox; not used by this checkpoint |

Physical addresses use little-endian, four-byte unsigned words.
A record for core ID `k` is physically located at
`0x40000000 + k * 0x80000`, *not* service-rank order;
the descriptor array order determines **service order**.

**Physical safety:** an A53 must not trust the unsigned header
and its CRC until it checks all offsets, counts and physical
bounds. CRC32 is for accidental corruption, *not* authentication.
The accepted P03 adapter remains unchanged. The planned
P05 A53 device-side integration must verify the same memory
boundaries before accessing MMIO or performing paging. No
new host-controlled dispatch loop is allowed.

The fixed header contains 64 unsigned 32-bit words
(`P05G`, `0x47353050`, version 1):

| Word(s) | Value |
|---|---|
| 0–3 | Magic, version 1, header size 256, diagnostic mode 0/1 |
| 4–7 | Timesteps 1–10000, core count 1–126, slots 1–min(3, cores), one engine |
| 8–11 | Backing base `0x40000000`, record stride `0x80000`, payload base `0x43F00000`, payload capacity `0xE0000` |
| 12–15 | Actual payload byte count, number of external events, number of checkpoints, repeated core-descriptor count |
| 16–18 | Core table start offset (=0), event table start offset, checkpoint table start offset |
| 19–20 | Future mailbox `0x43FF0000`, required algorithmic dispatch count (=timesteps × cores) |
| 21 | Must be zero |
| 22 | CRC32 of **exact** packed payload, no padding |
| 23 | CRC32 of all 256 header bytes with **word 23 temporarily zeroed** |
| 24–63 | Must be zero; reserved for a future version, not ignored |

Payload rows concatenate with no gaps or padding:

- **Core table:** `core_count × 32 B`, each eight
  `uint32_t`: logical ID, metadata low/high, initial
  `config0`, initial full-record CRC32, sole allowed
  input axon, initial event0 count, initial event1 count.
  Last two must be zero in this first revision. The
  descriptor array **is the fixed per-timestep service order**.
  Physical core IDs are unique and under 126.
- **External input:** `event_count × 16 B`; each row
  contains `timestep, logical_id, axon, reserved_zero`.
  Sorted by (timestep, **service rank**), while allowing
  repeated same-core events. At most 4096 explicit
  external input events per core/timestep.
  **Current limitation:** each core registers one valid input axon;
  arbitrary multi-axon bindings need a separately versioned
  extension before claiming generalized physical deployment.
- **Checkpoint requests:** `checkpoint_count × 16 B`;
  each row contains `completed_timestep, logical_id,
  state_class, expected_crc32`. Classes 1=state0,
  2=event0, 3=event1, 4=packet0. Rows sorted strictly
  (completed timestep, service rank, class) with no
  duplicate key. Supported **only in diagnostic mode**.
  **These are not yet real board-collected checksums.**
  Device-side capture and first-mismatch reporting must
  be added to the new P05 A53 runner.

The Python producer opens the original source records,
checks each P02/v3 ABI header, stride and logical ID, and
derives CRC32 and config0 from **actual file contents**.
It does not permit a fabricated supplied record CRC.
The output manifest deliberately states
`HOST_CONTRACT_ONLY_NOT_A53_OR_PHYSICAL_ACCEPTANCE`.

### JSON workload specification

```json
{
  "schema": "p05-regression-deployment-v1",
  "timesteps": 2,
  "slot_count": 1,
  "mode": "diagnostic",
  "cores": [
    {
      "id": 0,
      "metadata": "0x0000000000000080",
      "input_axon": 10,
      "record": "/absolute/or/relative/path/to/core0_initial.bin"
    }
  ],
  "events": [
    {"timestep": 0, "core": 0, "axon": 10},
    {"timestep": 1, "core": 0, "axon": 10}
  ],
  "checkpoints": []
}
```

The `metadata` field above is illustrative; it is **not a
substitute for generating an actual complete Loihi-compatible
network record**. The generator checks the record ABI but
does not independently prove that embedded axon/synapse/route
tables match the declared metadata. P05.1 must tighten this
for board admission while producing valid varied test networks.

## First independent checkpoint: run on Ubuntu host

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q tests/test_p05_1_deployment.py

# Protect the accepted P03 and frozen P02 Python model:
python -m pytest -q \
  tests/test_p03_finish_autonomy.py \
  tests/test_p03_3b_hw_adapter.py \
  tests/test_p03_3a_native_runtime.py \
  tests/test_p02_4b_ring_fixture.py
```

For a positive real P03-derived workload smoke (still **host-only**):

```bash
export P05_1_HOST_SMOKE=/tmp/v3_p05_1_contract_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$P05_1_HOST_SMOKE"

python scripts/p03_finish_fixture.py --timesteps 7 \
  --output-dir "$P05_1_HOST_SMOKE/p03_golden"
python scripts/p05_deployment.py from-p03 \
  --fixture-dir "$P05_1_HOST_SMOKE/p03_golden" \
  --output-spec "$P05_1_HOST_SMOKE/p05_spec.json"
python scripts/p05_deployment.py build \
  --spec "$P05_1_HOST_SMOKE/p05_spec.json" \
  --output-dir "$P05_1_HOST_SMOKE/p05_artifacts"

cat "$P05_1_HOST_SMOKE/p05_artifacts/p05_manifest.json"
```

Expected host contract profile: five core descriptors, 7 timesteps,
35 inputs and **35 required future dispatches**, independent SHA256s
and CRC32 fields. This **does not** imply 35 actual FPGA dispatches
occurred — the P03 physical evidence already proves that for the
separate P03 runner.

### Next work after independent checkpoint

Implement `software/p05/p05_regression_run.c` and a new fixed Vitis
build script with a **new P05-specific ELF signature**. The new
A53 app will need a bounded payload reader, physical record-header/
CRC admission, generalized sparse axon registration, per-dispatch
ingress from the vector table, packet routing, checkpoint capture,
fail-closed result/evidence and final dirty writeback. Reuse the
accepted `p03_runtime` and `p03_hw_adapter` interfaces and
the accepted FPD128 bitstream first. Make every physical change
subject to an independent gate; never replace a P03-accepted
bitstream or claim a mocked result is physical evidence.

After at least two independently validated board-local profiles
and real diagnostic checkpoint results are accepted, transition
to the broader directed physical testing of **P05.2**.
