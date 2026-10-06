# P03.2 Offline Attempt 2 — C Header Parser False Negative

**Date:** 2026-10-06  
**Phase:** P03.2 — PS-visible MMIO control/status shell  
**Result:** Static-checker false negative; RTL and inherited regressions passed.

## Observed result

The retry passed all substantive checks before the static C-header cross-check:

```text
............ [100%]
PASS: p03_ps_control_regs
PASS: P03.2a AXI-Lite control-register simulation completed successfully.
PASS: p02_page_host_arbiter_held_request
PASS: P02 held-request arbiter regression completed successfully.
PASS: p02_context_page_bank_walker
PASS: p02_axi128_burst_adapter
PASS: P02.3b1 AXI burst-adapter simulation completed successfully.
PASS: p02_ddr_backing_range_guard
PASS: P02.3b2 DDR range-guard simulation completed successfully.
```

The gate then stopped with:

```text
FAIL: P03.2 C MMIO define P03_MMIO_BASE
expected '((uintptr_t)0xA4000000u)', got None
```

## Diagnosis

The C header contained the correct definition:

```c
#define P03_MMIO_BASE ((uintptr_t)0xA4000000u)
```

The preflight parser used a Python raw regular expression containing
double-escaped whitespace tokens (`\\s`). In a raw string this matches a
literal backslash followed by `s`, not whitespace, so no `#define` lines
were recognized.

## Correction

The regex parser was removed.

The preflight now parses each C macro with:

```python
fields = stripped.split(None, 2)
```

and compares macro name/value pairs semantically. Arbitrary horizontal spacing
in the header no longer affects the gate.

No RTL, Vivado topology, MMIO address, or software register value changed.

## Acceptance impact

P03.2 remains open until the corrected complete offline preflight passes.
