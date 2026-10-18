# P07-A4.2c — Persistent 128-image primary physical-to-physical acceptance

**User crosscheck ACCEPTED 2026-10-17.** **A4.2c remains OPEN** pending
an independent reboot/repeat physical run, its full-journal and full-trace
byte equality, and larger predeclared validation reliability gates.
The canonical t10k MNIST TEST remains **SEALED**.

The user independently ran the `scripts/p07_a4_2_crosscheck.py` command
against the previously created **one-launch** persistent 128-frame
TRAIN-derived validation journal/selected trace and the original eight
accepted physical P07-A3.3 16-image PRIMARY mailboxes.
The supplied exact terminal output was:

```text
P07_A4_2C_CROSSCHECK_OLD_PHYSICAL_BATCHES=8/8
P07_A4_2C_CROSSCHECK_PRIMARY_FRAMES=128/128
P07_A4_2C_CROSSCHECK_FIRST_TRACE_BYTE_EXACT=1
P07_A4_2C_CROSSCHECK_ALL_FRAME_SPIKES_ROUTES_EXACT=1
P07_A4_2C_CROSSCHECK_OLD_REPORT_MAILBOX_SHA_PASS=1
P07_A4_2C_PRIOR_AND_PERSISTENT_PHYSICAL_MATCH=1
P07_A4_OFFICIAL_TEST=SEALED
```

The strict crosscheck decodes the new complete physical 1MiB
`P07A4R01` journal (requires `status=0x600D600D`,
`completed=128`, all indexed record CRCs), checks the complete
new 64KiB trace, validates staged input SHA256/original source-index
order, verifies the original P07-A3.3 physical report's accepted
per-mailbox SHA256 digests, and compares **every** of the 128
physical output spike histories (26×10), class counts/ties,
silence flags, routed/dropped hidden NEXT packets, external
event counts and exact original P07A1 input bytes. The
overlapping physical frame-0 full 26×42 trace is byte-exact
to the original A3.3 first-batch hardware trace.

The user's current message contains this crosscheck console,
**not** the full primary run's separate `P07_A4_2C_FULL_PHYSICAL_GATE_PASS`
console or a readback of its original `verify.log`, so that
specific independent software-oracle verification is not
re-attested separately by this conversation turn. The user's
statement is that the primary run passed; the new **repeat
aggregate gate will explicitly require** the original
primary `verify.log` physical oracle markers and original
staging/provision/program/run logs. Do not invent the
primary evidence directory path or SHA256 of its physical
journal/trace; both remain on the user's PC.

The comparison does **not** show 128 independent full
compartment traces: only original first selected trace
overlaps across firmwares; other images have exact
recorded 26×10 physical output spikes and routes.
This remains TRAIN-derived validation—not a canonical
official TEST measurement. The accepted immutable
persistent A53 ELF is unchanged:
`dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.

**Next prespecified gate:** separate physical reboot and
`persistent_val128_repeat`, independently run the same
new ELF on the same 128 images, verify software oracle and
old P07-A3.3 physical evidence again; require full 1MiB
persistent journal and 64KiB selected trace byte-exact to
primary, with immutable distinct physical run provenance.
After this, A4.2c still requires predeclared larger TRAIN
validation and fault-handling gates before official unseal.
See `P07_A4_2C_VALIDATION128_PROTOCOL.md`.
