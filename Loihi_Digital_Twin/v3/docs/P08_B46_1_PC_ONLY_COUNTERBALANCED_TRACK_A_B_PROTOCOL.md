# P08-B4.6.1 — PC-only pre-registered Track A / Track B repeated physical study design

> **SUPERSEDED ARM SELECTION — 2026-11-05 local.** The user
> explicitly selected the independently verified original
> `authenticate-once V2` architecture for B4.6. The earlier
> draft below targeted original B4.4 per-image SHA Track B.
> Retain that draft as historical research design; **DO NOT
> execute it or label B_AUTH_ONCE as original B4.4**.
> The CURRENT primary P08-B4.6 study is instead
> original A2.1 Track A vs
> `B_AUTH_ONCE_UNPROTECTED_V2`, six new coldboot sessions
> AB / BA / AB, same original frozen 1024 TRAIN inputs,
> different 42-vs-1010-neuron workloads, explicit
> unprotected backup integrity tradeoff and numerical
> parity per own oracle. Exact source identities, PC-only
> gate, operator commands and hardware-readiness blockers:
> [P08-B4.6 selected authenticate-once runbook](P08_B46_SELECTED_AUTH_ONCE_PC_SOURCE_GATE_RUNBOOK.md).
> B4.5.5 was accepted from signed real local four-source
> quantitative synthesis JSON SHA
> `b04aa0ada133a61ce052ce40f7aa7dbf667da6958031cfdc63b99cc57354eff0`,
> Markdown SHA
> `8cd181ecedb407e04418ef5ab121e6560a8fef3a5908ac0ec39acfbdae41fef3`.
> No further destructive JTAG permission is implied.
>

**STATUS: DESIGN ONLY. NO NEW HARDWARE AUTHORIZATION.**
This is the original B4.6 next milestone after B4.5.5 independently
signed residual-latency phase reconstruction. Draft protocol must
be reviewed before any new JTAG, DDR, Linux takeover or Vivado work.

## Study question, NOT equivalent neuron-work speedup

How do the accepted, frozen single-logical-core Track A and
virtualized 27-logical-core Track B SYSTEM-level full-image-service
times differ across independent physical boot sessions for the same
original TRAIN-derived input population?

Track A: 42 artificial neurons, 26 FPGA dispatches/image.
Track B: 1010 artificial neurons, 27 virtualized cores into 3 physical
slots, 702 FPGA dispatches/image, context state reset/paging.
Consequently a B/A latency ratio is a **workload/system comparison**,
NOT a matched-network-complexity neural acceleration measure,
pure PL compute improvement, IPS/Joule or accuracy superiority.

## Proposed arms and protocol freeze

A = independently accepted original Track A frozen HDL, ELF,
SHA/checkpoint and input encoder with original complete image-service
timing boundary.

B = original independently accepted B4.2/B4.4 Track B 27-core
hardware and original 1024-source neural path, with the ORIGINAL
per-frame full 27-context SHA reset contract and complete
image-service timing. Explicitly retain baseline source SHA,
software FNV oracle and P03 XSA/bitstream identities.

**Do not relabel B4.5 V2 unprotected optimized once as B.**
If a separate reduced-integrity third arm is scientifically useful,
pre-register it as B_OPT with its distinct SHA/ELF, status, security
limits and independent approvals. It requires a separate randomized
design rather than silently replacing the original B arm.

The original B4.5 successful once/unchecked sessions are already
accepted for descriptive reset-performance comparison, not enough
to become any of the six independently randomized A/B sessions.
The prior six Track A A2.1 vs A2.2 instrumented physical runs
were WITHIN-TRACK timing studies and likewise do not qualify.

## Exactly six new and independent physical sessions

Pre-register three matched temporal pairs with counterbalanced
sequence AB / BA / AB:

| Pair | First session | Second session | Required reset |
| --- | --- | --- | --- |
| 1 | A | B | Independent cold boot before EACH |
| 2 | B | A | Independent cold boot before EACH |
| 3 | A | B | Independent cold boot before EACH |

Each JTAG run is a fresh disposable Linux/A53 session with accepted
128-bit PS width/CPU halt first, independently confirmed original
P03 shell, original DDR occupancy/ownership risk acceptance,
same-session source readbacks, unique no-overwrite evidence directory,
physical power cycle/recovery after ANY destructive attempt,
independent source/ELF admission and 1024-image complete scalar/FNV
parity BEFORE timing acceptance. Six original sessions and all
failed attempts must remain in the report, no post-hoc dropping.
No test-set use, model refit, train/shard regeneration or changing
source-encoded 1024 image population.

Reconsider whether an independent real DDR/boot/DMA owner audit is
required for each destructive memory region before physical use;
accepting the experimental B4.5 reduced-security caveat does NOT
prove A/B DDR address ownership. No further hardware actions
are authorized by this planning document.

## Common timing endpoints and measurement fidelity

- One original frozen 1024-image TRAIN-derived source set per session.
- Exactly 1023 ordinary frames in each latency distribution; selected
  trace frame ordinal 1023 verified but excluded from ordinary stats.
- Same precise A53 service boundary: immediately BEFORE per-image
  restore/ingress through durable neural journal commit. A/B
  instrumentation boundaries must be independently inspected for
  identical definition; trace-sidecar emission/setup outside the timer.
- Actual per-session CNTFRQ_EL0 and 64-bit CNTVCT measured; no
  assumption of 100MHz and no conversion of PL cycle count using A53 Hz.
- Report per-session 1023 median, P95 nearest rank, min, max and
  per-image ordinal vector, plus SHA and complete FNV/spike agreement.
- Quantify instrument overhead independently if source needs extra
  probes: new instrumentation means a separately versioned arm.
- Record hardware clock, P03 bitstream/XSA and unique A53 ELF identity,
  boot state, A53 takeover, live Linux/app state, errors, session
  UTC/local date, room/board temperature if reliably available,
  host/board actions and reboot recovery.
- For Track B, report reset vs mixed 26tick virtual-core phase
  separately but do NOT call the latter pure FPGA compute.
  Track A has a smaller architecture, so direct phase-by-phase
  attribution may be structurally unmatched.

## How results will be analyzed

Each accepted physical SESSION is the independent experimental
unit; 1023 within-session image times are repeated observations
under the same boot/board state, NOT 1023 independent trials.
Calculate original A and B per-session median complete service.
For pair j, record B_session_median / A_session_median, plus
difference in ms and order; report the three paired ratios and
their geometric mean, min/max, and order sensitivity.
Do NOT present an image-level bootstrap over 1023 as if 1023
independent hardware runs. With only 3 independent session pairs,
do not claim a precise p-value/95% CI, generic runtime causality,
or energy/PL speedup. Report the descriptive spread transparently.
Predefine handling of failed/aborted sessions and replacement
sessions before running anything (no unlogged retries).

## Actual first B4.6 deliverables

B4.6.1 (THIS WORK): source-only comparison protocol and discovery
of existing original Track A/B exact source/ELF/memory/timing
identities, negative gates, and pre-registered statistical recipe.
No board.

B4.6.2 (LATER): separate exact source-pinned PC admission for BOTH
arms with independent 1024 oracle, matched complete A53 service
instrumentation, and a six-session run sheet. Native tests and
user verification before any board authorization.

B4.6.3 (LATER): user-by-user explicit physical JTAG approvals
for each of six disposable coldboot sessions, preserving immutable
raw evidence, separately rebooting the board after every attempt.

B4.6.4 (LATER): independent cross-session numerical equality and
descriptive three paired-session ratios, causal limits and
thesis-ready outcome. Preserve original B4.4/B4.5 evidence.

**Immediate operator action:** first run P08-B4.5.5 signed 4-report
comparison and inspect six-phase medians and sum-based shares.
It will identify whether additional mixed A53 paging/dispatch
instrumentation is warranted before designing B4.6.2. No
new FPGA build, JTAG or PuTTY commands are needed now.
