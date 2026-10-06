# P02.4b Physical Attempt 6 — Held Debug Request Re-arms Stale Response

**Date:** 2026-10-05  
**Result:** Root cause isolated; RTL fix requires a new routed shell before physical acceptance.

## Evidence

The full workload reached a mutable eviction of logical core 0 from resident
slot 2. Static resident data verified immediately before the page-out:

```text
P02_4B_EVICT_PRECHECK logical_core=0 slot=2
PASS: P02.4b resident static image verified logical_core=0 slot=2
```

The first debug read immediately after page-out reported:

```text
P02_4B_EVICT_POSTCHECK logical_core=0 slot=2
P02.4b mismatch resident config core=0 slot=2:
actual=0x0
expected=0x14001000
```

Without rebooting or reprogramming the FPGA, an attach-only probe then read the
same resident slot five times:

```text
config0=0x14001000
route0=0x581
state0=0x0
```

on every attempt.

Therefore the zero postcheck was not resident-URAM corruption.

## Root cause

`p02_page_host_arbiter` tracked one active transaction but allowed a new
transaction to arm whenever the selected request level remained high.

The VIO/Tcl debug requester intentionally holds `debug_req` high until it
observes ACK. That interval spans many PL clock cycles.

After the first transaction ACK:

1. `transaction_active` cleared;
2. `debug_req` could still be high;
3. the arbiter could re-arm on that same request level;
4. the accepted P05 memory fabric could still expose the previous ACK/RVALID
   response until a genuinely new request edge was accepted;
5. the arbiter could therefore surface stale response data as a phantom second
   debug completion.

This explains the intermittent zero reads observed throughout earlier P02.4b
attempts while later reads showed correct memory.

## RTL correction

The arbiter now enters a `wait_request_low` fence after every completed
transaction.

While fenced:

- the selected request is not forwarded to the memory fabric;
- no new transaction ownership is armed;
- debug/page busy remains asserted;
- the fence clears only after the requester returns its request level low.

Only a subsequent request assertion can start another transaction.

## Regression

A dedicated simulation now deliberately holds:

- `debug_req` high after completion;
- the prior fabric ACK/RVALID/data response visible for multiple clocks.

Acceptance requires exactly one debug completion and no re-forwarding until the
request returns low.

Files:

```text
rtl/tb/test_p02_page_host_arbiter_held_request.v
rtl/run_p02_page_host_arbiter_held_request_sim.sh
```

The regression is included in both P02.3b2 and P02.4b preflight gates.

## Next gate

Because `p02_page_host_arbiter.v` changed, the previously accepted P02.3b2
bitstream/probe fingerprints are no longer the verification candidate.

The next gate is:

1. run the complete offline preflight including the held-request regression;
2. route a new P02 DDR shell;
3. confirm nonnegative setup/hold timing and unchanged topology/resource
   constraints;
4. freeze the new bitstream/probe fingerprints;
5. rerun P02.4b physical acceptance using those new artifacts.
