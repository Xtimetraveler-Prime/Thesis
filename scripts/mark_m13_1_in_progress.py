from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "MILESTONES.md"
text = path.read_text(encoding="utf-8")

summary_old = "| M13 | Cross-validate and audit against Catalyst N1 | Planned | — | — |"
summary_new = "| M13 | Cross-validate and audit against Catalyst N1 | In progress | 2026-09-08 | — |"
if summary_old not in text:
    raise SystemExit("M13 summary row anchor not found")
text = text.replace(summary_old, summary_new, 1)

header_old = """## M13 — Cross-validate and audit against Catalyst N1

**Status:** Planned
"""
header_new = """## M13 — Cross-validate and audit against Catalyst N1

**Status:** In progress
**Started:** 2026-09-08
**Repository evidence:** current work on branch `agent/m13-1-pin-catalyst-methodology`
"""
if header_old not in text:
    raise SystemExit("M13 header anchor not found")
text = text.replace(header_old, header_new, 1)

m131_old = """### M13.1 — Pin Catalyst N1 and freeze the comparison methodology

**Status:** Planned

#### Core goal
"""
m131_new = """### M13.1 — Pin Catalyst N1 and freeze the comparison methodology

**Status:** In progress
**Started:** 2026-09-08
**Repository evidence:** branch `agent/m13-1-pin-catalyst-methodology`

#### Current implementation boundary

M13.1 freezes provenance and comparison rules before any cross-implementation behavioral judgment is allowed to influence the M12-closed baseline. The project-under-audit is pinned to M12 merge `80a502ec6dfc4c8d61372089b08c9a584ad65f85`. Catalyst N1 is pinned to tag `v2.3-paper` / equivalent tag `n1-final` at commit `1806bb4b4114d7671e5648fa75b7b83b3a8d5543`; Brian2Loihi is pinned to project dependency/tag `0.5.2` / `v0.5.2` at commit `d54676cb113e48dc886615a0b589bb0e4bccbca4`; and the initial published-Loihi set is anchored by stable DOI references.

The branch adds a versioned machine-readable reference manifest, exact Git-blob verification for key Catalyst source/document/tooling boundaries, a clean detached-checkout fetch gate, a native Catalyst RTL-regression runner that preserves the pinned source unchanged, and explicit evidence/independence/discrepancy/change-control terminology. Behavioral normalization, four-way feature comparison, project baseline changes, performance comparison, and K26 Catalyst reproduction remain outside M13.1 and are deferred to later M13 sub-milestones.

#### Core goal
"""
if m131_old not in text:
    raise SystemExit("M13.1 anchor not found")
text = text.replace(m131_old, m131_new, 1)

path.write_text(text, encoding="utf-8")
