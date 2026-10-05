# P03 Vivado Implementation Shell

## Purpose

This stage places the C/RTL-co-simulation-verified `loihi_core_v2_tick` HLS IP
into a K26/KV260 Vivado design with an explicit physical memory fabric. It is a
physical implementation/measurement shell; it does **not** change the P02/P03
architectural contract.

Integration problems and their resolutions are tracked in
`docs/P03_INTEGRATION_CHALLENGES.md`.

## Physical boundary

The design provides:

- the K26/KV260 PS preset as a 100 MHz PL clock source;
- the packaged `loihi_core_v2_tick` HLS IP;
- a fixed-depth XPM true-dual-port memory fabric;
- a unified banked host/debug path on the second memory port;
- VIO/JTAG control/status for bring-up; and
- `p03_run_monitor.v` for physical cycle measurement and host/compute
  arbitration.

The nine external banks are:

| Memory | Depth | Width | Raw bits | Host bank |
|---|---:|---:|---:|---:|
| compartment config | 1,024 | 128 | 131,072 | 0 |
| compartment state | 1,024 | 64 | 65,536 | 1 |
| input axon table | 4,096 | 64 | 262,144 | 2 |
| synapse table | 32,768 | 64 | 2,097,152 | 3 |
| route descriptors | 1,024 | 32 | 32,768 | 4 |
| route table | 4,096 | 32 | 131,072 | 5 |
| input events | 4,096 | 32 | 131,072 | 6 |
| normalized trace | 1,024 | 256 | 262,144 | 7 |
| output packets | 4,096 | 64 | 262,144 | 8 |

Total external raw storage is `3,375,104` bits. The HLS core additionally owns
its tick-local accumulator memory.

The logical input-event payload remains a 12-bit axon ID. The physical event
word is 32 bits because the initial Vivado native-memory shell rejected the
16-bit form; bits `[11:0]` carry the axon ID and upper bits are reserved.

## HLS memory interface

HLS uses discrete `ap_memory` ports with `storage_type=ram_1p`. This keeps the
compute-memory protocol word-addressed and avoids the grouped `bram` interface
metadata problems encountered during early IP Integrator bring-up.

Port A of each physical bank belongs to HLS. Port B belongs to the host/debug
bridge:

```text
                         Port A
P03 HLS compute core  <---------->  XPM true-dual-port RAM
                                      ^
                                      |
                                      | Port B
                                      |
                              p03_memory_host_bridge
                                      ^
                                      |
                                  VIO / JTAG
```

Host requests are rejected while a compute transaction is active, and a pending
host request blocks a new compute start. Same-address dual-port collision
behavior is therefore not part of the architecture contract.

## Why the shell uses XPM

The first routed `ap_memory` shell used Block Memory Generator cells directly in
IP Integrator. A single-access version routed successfully but retained too
little memory. Adding a second host/debug port improved physical retention from
26 to 48 RAMB36E2 tiles, but the build correctly failed the memory-capacity
assertion.

The retained-shell validation log then showed the root cause: every BMG bank
reported depth `2048`, regardless of whether the requested bank depth was 1,024,
4,096, or 32,768 words. The problem therefore occurred at BMG configuration/
block-design validation, not in the Loihi-like architecture and not primarily
as post-synthesis trimming.

The current shell moves the physical banks to `xpm_memory_tdpram` instantiated
in RTL. Capacity is fixed in source through `MEMORY_SIZE`, data width, and
address width. For the P03 retention baseline each bank uses:

- `MEMORY_PRIMITIVE="block"`;
- `MEMORY_OPTIMIZATION="false"`;
- common-clock true-dual-port operation; and
- one-cycle synchronous reads.

This is intentionally conservative. Once full-capacity retention and physical
conformance are proven, the large 32,768x64 synapse bank can be evaluated for an
UltraRAM implementation without changing logical contents or resource
accounting.

## Verification flow

Before another full route, run the synthesis-only memory-fabric gate:

```bash
bash rtl/run_p03_memory_fabric_synth.sh
```

It synthesizes only the XPM fabric and host bridge and rejects a result with
fewer than 90 BRAM-tile equivalents. This catches depth/retention mistakes
without paying the full place/route cost.

The full routed gate remains:

```bash
bash vivado/run_p03_impl.sh
```

It packages the HLS IP, builds the complete K26 design, routes it, and emits:

- post-route timing summary;
- utilization and hierarchical utilization;
- clock and bus-skew reports;
- DRC and methodology reports;
- an explicit RAMB36/RAMB18/URAM primitive listing;
- routed DCP; and
- compact P03 metrics.

The routed gate retains a conservative 80-BRAM-tile assertion for the complete
design. The synthesis-only XPM gate is stricter about the external fabric alone
because its raw bit count already requires roughly 92 36-Kbit tile equivalents
before physical packing overhead.

## Accepted evidence so far

- Python/HLS C differential corpus: passed.
- HLS C/RTL co-simulation: passed.
- First routable compute shell: WNS `+1.468 ns`, WHS `+0.020 ns` at 100 MHz.
- Host-accessible 48-BRAM BMG shell: WNS `+0.953 ns`, WHS `+0.013 ns` at
  100 MHz; route completed but retention gate correctly failed.
- Host/debug bridge RTL simulation: passed.

The next accepted evidence must show that the fixed-depth XPM fabric retains the
full external image and that the complete HLS + XPM design still closes timing.
A bitstream/physical inference test follows that gate; a successful route alone
does not complete P03.
