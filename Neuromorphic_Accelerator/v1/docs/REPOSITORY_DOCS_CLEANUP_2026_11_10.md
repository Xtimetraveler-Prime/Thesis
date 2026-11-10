# Documentation cleanup review — November 10, 2026

**Status: draft documentation-only proposal.** This change must remain unmerged until explicitly approved. M01–M06 acceptance status, source code, Vivado evidence and archived research history are unchanged.

## What changed

The top-level README, accelerator umbrella README, v1 README and v1 roadmap had accumulated chronological "LATEST" notes, repeated milestone statements and, in some places, outdated instructions claiming previously completed milestones were still open. This branch replaces them with **reader-first** descriptions and points to existing primary acceptance and design records.

| Page | Purpose after cleanup | Original size | New size (approx.) |
| --- | --- | ---: | ---: |
| Repository README | Thesis motivation, research questions, version lineage, current boundaries and safe navigation | 9.7 KB | 7.1 KB |
| Neuromorphic_Accelerator README | Short workspace overview and where to start | 2.9 KB | 3.2 KB |
| Neuromorphic_Accelerator/v1 README | Current architecture, implemented milestones, tests, source map and M07 handoff | 33.8 KB | 8.5 KB |
| Neuromorphic_Accelerator/v1 roadmap | Current M01–M09 objectives, accepted gates, complete future M07–M09 experimental plan, scientific/safety contract | 202.6 KB | 17.6 KB |

No previously accepted original AMD/HLS/fault/parity ZIP was deleted or altered. This branch modifies Markdown only. **The historical narrative is still in Git history**, not newly re-added as large duplicate archives. Readers looking for the detailed failure-by-failure reports can open the exact prior version instead of scrolling through obsolete notes on the current landing page.

## Pre-cleanup frozen sources — exact commit

Original snapshot: commit **33916fffd4f5935aac9ec060a0e62d92977b3c05** (main after M06 merge and closeout documentation). These SHA-pinned links are safe even after subsequent commits and make the removed text retrievable.

- [Root README before cleanup](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/README.md)
- [Accelerator umbrella README before cleanup](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/README.md)
- [v1 README with complete M05 chronology](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/README.md)
- [v1 roadmap with extensive historical M01–M06 development notes](https://github.com/Xtimetraveler-Prime/Thesis/blob/33916fffd4f5935aac9ec060a0e62d92977b3c05/Neuromorphic_Accelerator/v1/roadmap.md)

To inspect locally without replacing the cleaned branch:

~~~bash
cd ~/Git/Thesis
git show 33916fffd4f5935aac9ec060a0e62d92977b3c05:README.md | less
git show 33916fffd4f5935aac9ec060a0e62d92977b3c05:Neuromorphic_Accelerator/README.md | less
git show 33916fffd4f5935aac9ec060a0e62d92977b3c05:Neuromorphic_Accelerator/v1/README.md | less
git show 33916fffd4f5935aac9ec060a0e62d92977b3c05:Neuromorphic_Accelerator/v1/roadmap.md | less
~~~

## Preserved source-of-truth references

- [Current M01–M09 milestone status and future acceptance gates](../roadmap.md).
- [Authoritative new-chat M07 handoff: research context, accepted M05/M06 evidence, GitHub branch/CI/owner workflow and first implementation steps](M07_NEXT_CHAT_HANDOFF_2026_11_10.md).
- [M01 architecture choices and reversible baseline](M01_ARCHITECTURE_OPTIONS.md).
- [M02 reference numerical contract](M02_PROVISIONAL_LIF_CONTRACT.md).
- [M03 matched workload and traffic contract](M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md).
- [M04 original engine audit and reuse decision](M04_HLS_ENGINE_AUDIT.md).
- [M05 formal accepted offline HLS/RTL evidence](M05_ACCEPTANCE_REVIEW_2026_11_09.md).
- [M06 formal accepted original AMD/HLS parity/fault/recovery evidence with five genuine owner ZIP hashes and physical nonclaims](M06_ACCEPTANCE_REVIEW_2026_11_10.md).
- [M05 engine optimization timeline](M05_EVALUATION_ENGINE_EVOLUTION.md).
- [M06 G4 detailed original-owner verification history](M06_G4_REMAINING_CONNECTED_OWNER_GATES_2026_11_10.md).

The original frozen Loihi-inspired v3 files, its A/B test records, previous design context, prior-art attribution, old failure evidence and physical safety boundaries are all retained.

## Nonclaims and review checklist

This cleanup **does not** mark M07 started, edit accepted hardware/software behavior, perform a physical action, reclassify M06 as physical DDR, unlock the official MNIST TEST, or retroactively claim vendor, JTAG, power or hardware timing verification. M06 acceptance remains OFFLINE simulation only, with real original HLS and AMD simulation libraries and a privately controlled 64 KiB scratch image.

Before requesting merge, check that Markdown links resolve, current milestone statuses are consistent, original versioned histories remain accessible, changes touch no executable files, and host-only CI passes. User review is required for merge; no approval is implied by preparing this branch.

## Reproduce the review locally

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch docs/neuromorphic-v1-reader-cleanup-2026-11-10
git pull --ff-only origin docs/neuromorphic-v1-reader-cleanup-2026-11-10
git status --short
git diff --stat main...HEAD
git diff main...HEAD -- README.md Neuromorphic_Accelerator/README.md Neuromorphic_Accelerator/v1/README.md Neuromorphic_Accelerator/v1/roadmap.md
~~~
