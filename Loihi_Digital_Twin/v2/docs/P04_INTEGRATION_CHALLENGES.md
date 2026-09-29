# P04 Integration Challenges and Resolution Log

## Purpose

P04 is the first v2 phase that carries two Loihi-compatible compute endpoints,
inter-core packet routing, destination-side event delivery, and a global
algorithmic-timestep barrier through source-level differential testing, routed
Vivado implementation, and automated execution on the physical K26. This file
records the integration problems encountered while closing that path, why they
occurred, and how they were resolved.

These issues are intentionally documented separately from
`LOIHI1_TARGET_SPEC.md`. The target specification defines the modeled Loihi-1
architecture; this log records FPGA resource constraints, Vivado/HLS interface
behavior, board bring-up diagnostics, and implementation choices made to realize
that architecture on the K26.

## Accepted P04 baseline

P04 preserves the full logical Loihi-like per-core limits defined by v2 while
using a smaller physical validation allocation for the directed two-endpoint
corpus. The accepted physical fixture provides, per endpoint:

```text
compartments        16
input axons         64
synapse entries     256
output routes       64
input events        64
output packets      64
```

This does **not** redefine the logical core. The Python/specification boundary
continues to enforce 1,024 compartments, 4,096 input axon IDs, 4,096 output
route slots, and the project-defined 128 KiB synaptic fan-in budget. Addresses
outside the physical P04 fixture are rejected and cannot alias into lower
physical locations. Transparent storage/scheduling of multiple full logical
contexts remains the P05 virtualization problem.

The final P04 architecture contains two unchanged P03-compatible HLS compute
engines, two guarded endpoint memory fabrics, a packet-memory streamer for each
core, a two-source packet router with per-destination queues, explicit local vs.
remote packet accounting, next-timestep destination event writes, and a barrier
that advances only after both compute egress paths and all routed traffic are
quiescent.

## Challenge / resolution history

| Challenge | Observation | Resolution / final status |
|---|---|---|
| Two literal P03 memory shells do not fit the K26 | The accepted P03 shell uses `96.5 / 144` BRAM tiles. Two full copies would require about `193` BRAM tiles before adding router/barrier storage. | **Resolved architecturally without shrinking Loihi capacities:** P04 uses two genuine compute endpoints with resource-scaled physical validation memories. Logical limits remain unchanged and are still enforced by the Python/specification layer. P05 is responsible for transparent full-context storage/scheduling. |
| Packet-memory streamer completion survived into the next tick | Repeated-timestep controller testing exposed a stale sticky `done` condition in the packet-memory streamer, allowing completion state from one drain to contaminate the next drain. | **Resolved:** the streamer completion handshake was corrected and the repeated-timestep controller regression was retained. Corrected XSim and the consolidated P04 preflight passed. |
| Initial board reset investigation produced ambiguous symptoms | The first physical attempts programmed the K26 and discovered VIO successfully, but the free-running reset-dependent heartbeat remained zero. Early reset-polarity fixes were therefore insufficient to distinguish a stopped PL clock from an asserted reset output. | **Resolved diagnostically:** a temporary reset-debug build exposed a reset-independent PL0 counter plus `proc_sys_reset/peripheral_aresetn`. The raw counter advanced while `peripheral_aresetn` remained `0`, proving the PL clock was running and the functional reset path was holding the design down. |
| `proc_sys_reset` remained asserted after input-polarity fixes | The P04 board preset resolved both `C_EXT_RESET_HIGH=1` and `C_AUX_RESET_HIGH=1`. The auxiliary reset source was first corrected to inactive-low, but the physical diagnostic still showed `peripheral_aresetn=0` after the VIO external reset request was released. | **Resolved by removing the opaque functional dependency:** P04 now uses `p04_reset_conditioner`, a source-controlled synchronous reset conditioner driven directly by the VIO reset request and PL0. `1` asserts reset; after release the conditioner holds reset for 16 PL clocks, then emits active-high `reset` for HLS and active-low `resetn` for RTL. The canonical physical run verifies release with a heartbeat before proceeding. |
| Candidate reset integration repeatedly failed Vivado block-design validation | The first candidate Tcl used the wrong `disconnect_bd_net` form. The next attempt exposed incorrect module-reference reset polarity inference and asynchronous-reset warnings. Attempts to write reset `POLARITY`/`ASSOCIATED_RESET` properties also produced read-only warnings. | **Resolved:** the reset module carries explicit Xilinx interface metadata; the candidate flow creates an isolated project copy, refreshes the module reference, verifies the read-only inferred properties (`reset=ACTIVE_HIGH`, `resetn=ACTIVE_LOW`, `ASSOCIATED_RESET=reset:resetn`), rewires only the functional reset endpoints, and then routes the final design. The canonical flow promotes this conditioned design rather than the staging `proc_sys_reset` artifact. |
| First physical multicore tick never started after reset was fixed | With the replacement reset path, the heartbeat advanced and both endpoint memory preflights passed, but `completed_ticks` remained zero at the first feed-forward tick. The controller required `core0_ready && core1_ready` before asserting `ap_start`. Under the packaged `ap_ctrl_hs` behavior, `ap_ready` is not a valid prerequisite for beginning an idle transaction, producing a circular condition. The existing RTL testbench had hidden the bug by tying both ready inputs permanently high. | **Resolved:** `ap_ready` was removed from the controller's initial start-admission condition. The controller still exposes the signals for observability, but tick admission depends on epoch validity, host inactivity, fixture capacity, and controller idle state. The controller regression now deliberately holds both ready inputs low before start so this hardware-only deadlock cannot silently return. |
| Candidate and canonical bitstream provenance became important during reset debugging | A failed board run can be meaningless if it used a stale `.bit`/`.ltx`, so reset fixes could not be accepted until commit, routed metrics, timestamps, and artifact hashes were reconciled. | **Resolved procedurally:** the implementation flow removes/rebuilds its output directory, reports reset strategy and logical-capacity invariants, and the final canonical `run_p04_impl.sh` publishes the reset-conditioned `p04_two_core.bit/.ltx`. The physical harness archives the tested artifacts and their identities only after `result=PASS`. |
| Hardware-only failures were not represented in the source-level regression suite | The source-level router/controller/HLS differential tests passed before physical bring-up, yet reset and HLS-start behavior still failed on the board. | **Resolved as a verification-policy lesson:** physical heartbeat/reset release, endpoint-memory preflight, low-`ap_ready` startup, both router service orders, and archived physical conformance are treated as required evidence rather than inferred from source-level success. |

## Reset diagnosis in detail

The reset issue was isolated in stages rather than accepted on the basis of
configuration assumptions.

The corrected routed metrics first established that the tested artifact really
contained:

```text
C_EXT_RESET_HIGH=1
C_AUX_RESET_HIGH=1
aux_reset_in_tied_inactive_low=1
```

A board diagnostic then observed a reset-independent counter advancing from tens
of millions of PL0 cycles to higher values while
`proc_sys_reset/peripheral_aresetn` stayed low before, during, and after the VIO
reset pulse. The result was explicitly classified as:

```text
P04 RESET DIAG RESULT=PROC_SYS_RESET_STILL_ASSERTED
```

That evidence ruled out a missing PL clock. The replacement conditioner was
therefore introduced as a controlled implementation boundary rather than another
polarity guess.

The conditioner uses a 16-bit release pipeline initialized to all ones. A high
VIO reset request refills the pipeline; after the request drops, sixteen PL0
clock edges shift zeros through the pipeline. The two outputs are complementary:

```text
reset   = |release_pipe     // active-high HLS reset
resetn  = ~reset            // active-low RTL reset
```

The final physical harness does not assume this worked merely because the design
routed. It samples the heartbeat before and after reset release and aborts before
memory or compute testing if the count does not advance.

## HLS start-handshake diagnosis in detail

Once reset release worked, the board passed write/read preflight on both P04
endpoint fabrics, proving that the control path and retained memories were live.
The first feed-forward tick nevertheless timed out waiting for
`completed_ticks=1`.

The controller's original admission expression included both HLS `ap_ready`
inputs. That made physical startup depend on a signal that the HLS block does not
need to assert before receiving `ap_start`. The source-level controller test did
not catch the problem because it instantiated:

```text
core0_ready = 1
core1_ready = 1
```

for the entire test.

The fix removes `ap_ready` from the idle-to-start gate and adds a regression in
which both ready inputs are low before start. The same physical corpus that had
previously stalled at feed-forward timestep 0 then completed every directed tick.

## Accepted canonical physical conformance

The final acceptance run used the canonical `p04_two_core.bit` and
`p04_two_core.ltx` produced by the normal P04 implementation flow, with no
candidate-artifact override. On `xck26_0` the harness verified:

- reset release by observing the heartbeat advance from `4,710,844` to
  `7,448,013`;
- write/read memory preflight on both endpoint fabrics;
- the two-timestep feed-forward scenario under both legal service priorities;
- the three-timestep recurrent local+remote multicast scenario under both legal
  service priorities;
- core state, trace data, packets, next-timestep events, spike counts, packet
  counts, router traffic counts, and error/status observations against the
  Python-generated expectations; and
- nonzero physical cycle counts for every completed tick.

The ten accepted physical ticks were:

| Scenario | Reverse priority | Timestep | PL cycles | Local packets | Remote packets |
|---|---:|---:|---:|---:|---:|
| feed_forward | 0 | 0 | 28 | 0 | 1 |
| feed_forward | 0 | 1 | 21 | 0 | 0 |
| feed_forward | 1 | 0 | 28 | 0 | 1 |
| feed_forward | 1 | 1 | 21 | 0 | 0 |
| recurrent_multicast | 0 | 0 | 33 | 2 | 2 |
| recurrent_multicast | 0 | 1 | 39 | 2 | 2 |
| recurrent_multicast | 0 | 2 | 39 | 2 | 2 |
| recurrent_multicast | 1 | 0 | 33 | 2 | 2 |
| recurrent_multicast | 1 | 1 | 39 | 2 | 2 |
| recurrent_multicast | 1 | 2 | 39 | 2 | 2 |

The generated result uses:

```text
schema=p04-physical-conformance-v1
result=PASS
```

The accepted evidence archive is:

```text
hardware/evidence/p04_physical_20260929T211309Z/
```

The cycle counts above are implementation observations for the directed
validation corpus. They are not algorithmic timesteps and are not claimed as
native Loihi timing.

## P04 closure

**P04 completed on 2026-09-29.** The multicore v2 implementation now has accepted
evidence across the Python manycore contract, standalone router/barrier RTL,
two-endpoint HLS/controller integration, routed K26 implementation, physical
reset and memory bring-up, forward and reversed legal packet service orders,
and physical Python/FPGA differential execution.

The physical validation fixture remains intentionally smaller than the full
logical Loihi core capacities. This is not an unresolved P04 correctness issue;
it is the explicit implementation boundary that motivates P05. P05 should
retain P04's packet, barrier, error-checking, reset, host-memory, and normalized
trace contracts while adding transparent logical-core context storage and
scheduling.
