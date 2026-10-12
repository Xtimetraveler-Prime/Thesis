# P03.3b3 — Physical FPGA spike packets and dirty-context page roundtrips

**State:** code prepared on `agent/v3-p03-autonomous-runtime`; **independent
native/Vitis/physical verification pending**. Do not merge to main.
**Predecessors physically verified:** P03.2c, P03.3b2. **P03.3b1
host-native regression verified.**

## 1. The first actual multi-logical-core hardware test

P03.3b2 proved the board-local scheduler, MMIO transport and FPGA execution
work together for **one core, two timesteps, no packets**. It did not
verify output packet encoding, cross-core routing or dirty context save.

P03.3b3 deliberately uses **two logical cores and just one resident slot**.
The workload uses real P03 packed-memory core images (NOT mock-spike
injection from the PC):

```
One physical HLS engine + ONE selected resident slot (slot 0)
                 timestep 0              timestep 1
core0            1 input axon10          no input; (reloaded from DDR)
    |                    |                            |
    |                    v                            |
    |        emits packet -> core1 axon11 t1           |
    |                    |                            |
    |         core1 is NONRESIDENT                    |
    |          NEXT event1 written to DDR            |
    v                                                v
  page-out core0 --> page-in core1 --> page-out core1 --> page-in core0
                                    (event1 preserved)
                                  --> page-out core0 --> page-in core1
                                                    |
                                          core1 consumes axon11
                                                    |
                                          emits packet -> core0
                                                   axon20 t2
                                                    |
                                          core0 NONRESIDENT
                                          NEXT event0 written DDR
```

The initial `core0.event0[0]` is **axon10**; after core1 emits a packet
at timestep1, the same backing word must become **axon20**. This prevents
an unchanged DDR fixture from spuriously passing packet routing.

The intended real HLS packet ABI is the accepted
`pack_output_packet()` format from `hardware_p03.py`:

```text
bits  0.. 6: destination core
bits  7..18: destination axon
bits 19..28: source compartment
bits 29..60: target timestep
bit      61: packet valid
bits 62..63: reserved zero
```

Expected packets:

| Source operation | Expected physical 64-bit packet | Destination |
|---|---|---|
| Core0 dispatch at timestep0 | `0x2000000020000581` | Core1, axon11, NEXT timestep1 |
| Core1 dispatch at timestep1 | `0x2000000040000A00` | Core0, axon20, NEXT timestep2 |

The directed model fixture sets a low spike threshold `1` and
synapse weight `3`, with a single input event `axon10` for core0.
Core0 has bindings for axons 10 **and 20** so the returned packet
targets a valid sparse axon. Core1 has binding axon11. The FPGA must
generate BOTH output packets; neither is simulated by the real
standalone A53 probe.

## 2. Physical DDR and memory ownership

The accepted P02.1 record layout remains unmodified:

| Logical core | DDR backing record | Initial event |
|---|---|---|
| Core0 | `0x40000000..0x4007FFFF` | Event0[0] = axon10 |
| Core1 | `0x40080000..0x400FFFFF` | No initial events |
| Result mailbox | `0x43FF0000..0x43FF007F` | 128-byte zeroed result |

Each complete record is **512 KiB**. A full page-in transfers
438,272 bytes; each dirty mutable-only page-out writes **106,496
bytes** (104 KiB) without rewriting the static config/synapse/route
images. Resident event debug bank IDs are **6 (event0)** and **9
(event1)**; DDR event offsets are `0x54000` and `0x58000`.
Host packet debug bank is 8.

The Cortex-A53 hardware adapter must:
1. Inject no algorithmic control from the PC after launching.
2. Page in core0; verify its resident event0 word.
3. Dispatch core0, read a real packet from resident bank8, and compare
   to the exact encoded expected word **before routing**.
4. Write axon11 into nonresident core1's DDR NEXT event1 bank using
   the adapter's cache-ordered store.
5. Page out dirty core0, load core1, and run its timestep0 with CURRENT
   bank0 (no input). Its NEXT event1 must remain intact.
6. Page out dirty core1, load core0 and dispatch timestep1, then page out
   dirty core0 and **reload core1**. This is the explicit roundtrip that
   must preserve core1.event1[0].
7. Dispatch core1 at timestep1 consuming its event1[0]=11, read
   the **second real HLS packet**, and route axon20 into nonresident
   core0's DDR NEXT event0[0].
8. Confirm the resulting DDR/core1 resident bytes, counters, and clean
   global status before writing the pass mailbox.

Expected board-local counters:

| Counter | Expected |
|---|---:|
| Logical dispatches | 4 |
| Barriers/timesteps | 2 |
| Real packets routed | 2 |
| Initial page-ins | 1 |
| Replacement page-ins | 3 |
| Dirty page-outs | 3 |
| FPGA total page operations | 7 |
| Final resident core | 1 |
| Final current bank | 0 |

**Note on assumptions:** The packet values follow the accepted P03
hardware ABI and the compiled directed fixture; they are **physical
expectations**, not previously observed hardware data. A failing
physical test is diagnostic evidence, not proof of a successful packet
pipeline. The original P03.2c data read smoke and P03.3b2 zero-packet
run cannot establish these claims.

## 3. Source and verification implementation

- `scripts/p03_3b3_packet_fixture.py` generates two model-backed
  512-KiB records, a C header and a JSON golden manifest.
- `software/p03/p03_3b3_probe.c` links the **real**
  `p03_runtime.c`, `p03_hw_adapter.c`,
  `p03_hw_runtime_bridge.c` and `p03_hw_xilinx_io.c`.
  It hooks the packet drain only to **read and verify raw FPGA packet
  output**, then calls the original hardware adapter drain/route
  callback. It does not inject artificial packets.
- `software/p03/build_p03_3b3_probe.py` creates a fixed-source Vitis
  Cortex-A53 standalone application from the accepted FPD128 XSA.
- `scripts/build_p03_3b3_probe.sh` locks the actual FPD128 route
  metrics and XSA SHA, copies exact source/fixtures, creates a fresh
  workspace and rejects any ELF LOAD section touching the reserved
  64-MiB P02 backing region.
- `vivado/p03_3b3_xsdb_prepare.tcl` independently provisions/reads
  back both 512-KiB records plus the cleared 128-byte mailbox.
- `vivado/p03_3b3_xsdb_run.tcl` executes A53 #0 and reads 32 words
  from the result mailbox.
- `scripts/p03_3b3_verify_probe.py` independently requires the exact
  two packet words, both DDR event values, resident core1 event1,
  page/dispatch/barrier counts, no faults and AXI page-in/out activity.
- `tests/test_p03_3b3_physical_probe.py` checks fixture bytes, packet
  constants, synthetic pass/fail mailboxes and safety guards.
- The P03.3b native AXI mock has an additional two-core packetized
  run that exercises the unchanged core scheduler and adapter
  sequencing before the real board test.

**Failure evidence:** If the FPGA emits a packet with unexpected bits,
the probe records the *actual* packet low/high words in the DDR
mailbox, marks the packet mismatch, and fails closed rather than
silently discarding the sample.

## 4. Native and Vitis build

Use the same development PC, Vivado/Vitis 2025.2, and accepted FPD128
routed bitstream/XSA that passed P03.2c and P03.3b2.

```bash
cd ~/Git/Thesis
git switch agent/v3-p03-autonomous-runtime
git pull --ff-only origin agent/v3-p03-autonomous-runtime
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p03_3b3_physical_probe.py \
  tests/test_p03_3b2_physical_probe.py \
  tests/test_p03_3b_hw_adapter.py \
  tests/test_p03_3a_native_runtime.py

export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P03_3B3_BUILD_DIR="$PWD/vivado/build/p03_3b3_probe_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/build_p03_3b3_probe.sh 2>&1 | tee /tmp/v3_p03_3b3_build.log
```

Required new build marker:

```text
PASS: P03.3b3 ELF avoids 64 MiB reserved DDR fixture/mailbox window
PASS: P03.3b3 standalone A53 runtime-adapter probe build ready for board verification
```

## 5. Physical board verification

Reboot/power-cycle the KV260 and allow its **normal** PS/DDR firmware
initialization. Keep `hw_server` running. **Do not reuse a prior
A53 Linux execution context after stopping it.**

```bash
export P03_3B3_EVIDENCE_DIR="/tmp/v3_p03_3b3_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_3b3_probe.sh "$P03_3B3_EVIDENCE_DIR" \
  2>&1 | tee /tmp/v3_p03_3b3_physical.log
cat "$P03_3B3_EVIDENCE_DIR/verify.log"
```

This **will halt running Linux, program the FPGA, overwrite the
project-designated 1-MiB backing fixture plus 128-byte mailbox,
perform page-outs and packet routing, and require a board reboot
afterward**. It must not run in any environment where those DDR
addresses are used for unrelated data. No post-boot SLCR width writes
are attempted; the FPD HPM0 width is checked read-only.

Expected marker **only if real board verification passes**:

```text
PASS: P03.3b3 physical packet/page roundtrip ps_width=128 ... page_ins=3 page_outs=3 dispatches=4 barriers=2 routed_packets=2
P03_3B3_VERIFY_EXIT=0
PASS: P03.3b3 physical Cortex-A53 two-timestep runtime-adapter probe
```

On failure, preserve the evidence directory:
`verify.log`, `ps_width.log`, `provision.log`,
`program.log`, `a53_run.log`, `artifact_identity.txt`,
and `p03_3b3_a53_mailbox.bin`. The verifier's diagnostic includes
failing fields and the initial runtime fault/phase where available.

## 6. Acceptance boundary

**This is the P03.3b3 first directed physical gate (nonresident routing
and dirty-page survival).** The resident destination **packet-delivery
branch** (`p03_hw_route_word` writing directly via MMIO while the
destination is already resident) is covered by the native mock but is
**not independently exercised by this particular physical 1-slot
scenario**. A separate resident-destination board test is still
required before accepting P03.3b as a *whole*. We deliberately do not
count normal resident event *consumption* as evidence of that distinct
direct resident *routing* path.

A **physical PASS** would establish that two actual HLS core evaluations
emit the expected packets, that the runtime routes them to
nonresident DDR-backed NEXT event banks, and that page replacement
preserves those event payloads. It does **not** yet prove:

- arbitrary five-over-three placement/eviction or the P03.4 35-dispatch test;
- broad event overflow/fault cases physically, or trace-by-trace
  normalized architecture agreement;
- SHA-256 validation and refresh of dynamically mutated DDR payloads;
- P03.3c launch/result packaging and memory/cache ownership under Linux;
- the P03.5 100-timestep golden-equivalence result.

Keep P03.3b3 open until the independent native tests, Vitis build,
physical mailbox verification and review have passed. Do **not** merge
the branch without user authorization.
