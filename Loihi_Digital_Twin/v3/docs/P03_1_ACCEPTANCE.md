# P03.1 Autonomous Runtime Contract Acceptance

**Phase:** P03 — Autonomous PS-resident runtime  
**Sub-milestone:** P03.1 — Autonomous runtime contract  
**Accepted:** 2026-10-06  
**Branch:** `agent/v3-p03-autonomous-runtime`

## Independent verification

The P03.1 preflight was independently rerun and the required acceptance markers
were observed:

```text
PASS: P03.1 contract/addendum static checks
PASS: P03.1 autonomous runtime contract preflight completed successfully.
```

The focused executable contract regression also completed successfully, and the
preflight included the complete inherited v3 Python regression suite.

## Accepted contract

P03.1 freezes:

- external-PC exclusion from algorithmic control after RUN/START;
- deterministic initial service/replacement policy;
- dirty victim save-before-replacement ordering;
- packet drain/commit before logical-core completion;
- all-core and no-pending-packet global barrier condition;
- global CURRENT/NEXT event-bank swap only after barrier completion;
- explicit 64 MiB DDR backing-window reservation;
- non-coherent PS/PL ownership and cache-maintenance rules;
- active-run stale-header/digest handling for mutable PL writeback;
- board-local control/inference timing boundaries;
- sticky first-fault / fail-closed recovery semantics;
- result/evidence record requirements;
- the FPGA-v3 board-local addendum to the inherited Loihi-1 target
  specification.

Primary records:

- `docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md`
- `docs/LOIHI1_TARGET_SPEC_V3_ADDENDUM.md`
- `src/loihi_twin_v2/runtime_v3.py`
- `tests/test_p03_1_runtime_contract.py`

## Claim boundary

P03.1 accepts the control semantics only.

It does not claim that a PS-visible hardware register block or Cortex-A53
runtime is implemented. Those begin at P03.2 and P03.3.
