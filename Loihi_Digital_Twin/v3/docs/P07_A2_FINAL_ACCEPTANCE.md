# P07-A2 — Autonomous trained-classifier KV260 physical acceptance

**Status:** CLOSED — **USER-ACCEPTED 2026-10-17**.
**Development branch:** `agent/v3-p07-a-784-axon-streaming`.
**No merge to main is authorized by this acceptance.**

## Independent physical result supplied by the user

The user executed the guarded P07-A2 **physical** command on the actual
KV260 in the accepted JTAG-owned/bare-metal environment and pasted
terminal output from the resulting Vivado programming, XSDB one-shot
Cortex-A53 ELF run, and independent Python frozen-oracle comparator.

Evidence location on the user's machine:

```text
/tmp/v3_p07_a2_physical_20261017T130533/
  p07_a2_mailbox.bin
  physical_identity.txt
  ps_width.log
  provision.log
  program.log
  a53_run.log
  verify.log
  readback/
```

**The raw 64KiB mailbox and its independent SHA-256 were not uploaded
into the repository.** This record transcribes user-attested passing
logs; it is **not** a fresh re-read of the user's board or files by
the assistant. Preserve the original evidence directory and, if
archiving it, capture its raw SHA ledger without regenerating its
contents.

```text
PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released
P07-A2 standalone A53 ELF downloaded; starting ONE autonomous batch
P07_A2_MAILBOX_STATUS=0x600D600D
P07_A2_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS
P07_A2_FRAME=0 class=0 counts=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0) silent=1 routed=0 last_discard=0
P07_A2_FRAME=1 class=3 counts=(0, 0, 0, 25, 0, 0, 0, 0, 0, 0) silent=0 routed=175 last_discard=0
P07_A2_FRAME=2 class=3 counts=(1, 0, 7, 18, 0, 10, 0, 7, 0, 0) silent=0 routed=237 last_discard=0
P07_A2_PHYSICAL_TRACES_EXACT=1
P07_A2_OFFICIAL_TEST=SEALED
P07_A2_GATE_FULL_PHYSICAL_PASS=1
```

### Evidence scope and result interpretation

Three deterministic diagnostic images were run in order: black, white,
ramp, using the accepted versioned P07-A1 mapped-784-axon ingress and
P07-A2 batch descriptor. There were exactly 26 timesteps (25 input
plus one drain) per frame with board-local A53 scheduler, event-bank,
routing and memory reset ownership.

The standalone A53 reported terminal success and three complete frame
records. The independent physical verifier then compared:
- per-timestep output spike flags for **all three** frames against
  frozen P03 packed software replay;
- class totals, predictions, silence, NEXT-route totals and final-drain
  packet discard counts for **all three** frames;
- all **26 ticks × 42 compartments × 256-bit hardware trace words**
  against the independent packed replay for the selected **white frame
  (frame 1)**, including before state, synaptic accumulator, after state,
  spike bit and reserved bits.

The first nonzero tracked route counts were 175 (white) and 237 (ramp).
No physical mismatch was reported by the strict first-divergence checker.

This establishes functional **actual PL** execution for a frozen
project-trained 784→32→10 one-core SNN with autonomous A53 execution,
rather than a host-driven mock inference. It does **not** constitute
MNIST validation or official TEST accuracy, repeated-run reliability,
multi-core scaling, physical latency/throughput/power/energy, or an
Intel Loihi hardware-equivalence claim.

### Frozen identities and prior native gate

- Accepted P02 512KiB immutable master SHA-256:
  `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`
- Compiler fingerprint:
  `e612a971cda11fae3f1be215c0ca3ed7de7b2af7339446e926ce559658db2f7f`
- Accepted routed FPD128 XSA SHA-256 from native gate:
  `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`
- Corrected firmware identity enforced by guarded physical-run shell:
  `P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX`
- The **original pre-fix ELF** SHA-256
  `64601cc0ea491f9ae3e3ba8287cd9d52640b8c1d12273e8c8601c1f1aeac4c96`
  was explicitly superseded; **do not label it as the physical-run ELF
  hash**. The corrected physical-run ELF hash is held in the user's
  `physical_identity.txt`, not copied here.

## Acceptance decision / next gate

**P07-A2 CLOSED.** The terminal physical mailbox and independently
matched 26×42 selected-frame traces satisfy its declared physical
numerical-conformance gate. P07-A1 remains closed.

Next is **P07-A3: physical inference on a deterministic, preselected,
validation-only subset from the canonical TRAIN-derived held-out
10,000-image validation split**, with exact host-vs-board predictions
and diagnostic per-frame labels/accuracy measured separately. The
official canonical MNIST **test 10k stays SEALED**. A later P07-A4
test-unsealing gate requires its own precommitted full-population or
reduced-population policy before opening the test archives. P08-A
physical performance characterization remains its separate prerequisite
for scaled Track B.

Do not merge the P07 development branch without explicit user approval.
