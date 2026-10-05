# P00 — v3 Baseline Acceptance

**Status:** Accepted  
**Accepted:** 2026-10-05

## Accepted branch candidate

```text
branch: agent/v3-foundation-roadmap
baseline commit before acceptance-record update:
f4a7699f59d1dd8f004d847f7344ef25e1505b3b
```

The v3 tree was created from the final accepted v2 main commit:

```text
a9329caa064fee3876d69fbbe6c626ac035e67b5
Close P08 and complete FPGA-v2 roadmap
```

## Independent structural verification

The user independently verified that no accepted v2 files changed:

```text
PASS: v2 untouched
```

The inherited v3 implementation trees were compared against v2 using Git tree identities and all passed:

```text
PASS: docs identical
PASS: examples identical
PASS: hardware identical
PASS: hls identical
PASS: rtl identical
PASS: scripts identical
PASS: src identical
PASS: tests identical
PASS: vivado identical
PASS: pyproject.toml identical
PASS: .gitignore identical
```

## Independent regression verification

The inherited regression suite was executed from the v3 directory with the v3 source tree forced on `PYTHONPATH`:

```bash
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q
```

Observed terminal result:

```text
...................................................................    [100%]
```

This is 67 passing test indicators with no reported failures or errors.

## Acceptance decision

P00 is accepted.

This acceptance proves that v3 begins from the accepted v2 implementation baseline while preserving v2 unchanged and retaining the inherited software regression behavior.

It does **not** prove any new v3 board-local execution capability yet. DDR-backed virtualization, PS/PL runtime ownership, expanded physical regression, benchmark replacement, and performance/energy characterization remain follow-on work beginning with P01.
