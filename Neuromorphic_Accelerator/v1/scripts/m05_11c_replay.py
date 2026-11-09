"""Read-only postcheck of ACTUAL accepted 256-bit DMA RTL signals in XSim.

Not a real PS DMA transfer: this tool replays simulator TDATA/TKEEP/TLAST
handshakes into the existing M05.11a atomic packet validator. The input
must come from the newly run *real generated HLS Verilog + real RTL shell*
testbench. Native regression tests use SYNTHETIC transcripts separately.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_dma_frame import (
    accept_dma_frame, DMAFrameError,
)
from neuromorphic_accelerator_v1.m05_execution_abi import decode_trace

DMA = re.compile(
    r"^M05_11C_DMA run=([01]) data=([0-9a-fA-F]{64}) "
    r"last=([01]) keep=([0-9a-fA-F]{8})$"
)
ROW = re.compile(
    r"^M05_11C_ROW run=([01]) tick=(\d+) neuron=(\d+) "
    r"voltage=(-?\d+) spike=([01]) evaluated=([01]) delivered=(\d+)$"
)
FINAL = re.compile(
    r"^M05_11C_FINAL run=([01]) status=(\d+) rows=(\d+) "
    r"committed=(\d+) session=([0-9a-fA-F]{16}) tlast=1$"
)
COMMIT = re.compile(r"^M05_11C_COMMIT run=([01]) accepted_rows=(\d+)$")
PASS = "PASS: M05.11c REAL HLS RTL + AXIL shell"
SESSION_IDS = (0x0102030405060708, 0x1020304050607080)
EXPECTED_STATUS = (0, 4)
EXPECTED_ROWS = (24, 8)
EXPECTED_COMMITS = (24, 0)


def replay_real_xsim_log(log: str) -> tuple[int, int]:
    """Strict run boundaries: 2 frames, 2 footers, 2 hardware statuses."""
    if "M05_11C_FAIL" in log or "Fatal:" in log or "ERROR:" in log:
        raise ValueError("simulator reported a hardware/testbench failure")
    packets = [bytearray(), bytearray()]
    last_seen = [False, False]
    final_count = [0, 0]
    commit_count = [0, 0]
    row_marker_count = [0, 0]
    phase = 0
    pass_seen = 0
    for line in log.splitlines():
        line = line.strip()
        m = DMA.fullmatch(line)
        if m:
            run, raw, last, keep = m.groups()
            run = int(run)
            if run != phase or last_seen[run] or int(keep, 16) != 0xFFFFFFFF:
                raise ValueError("DMA beat crossed run boundary/after TLAST/bad keep")
            # Direct raw hardware TDATA, reversed into little-endian bytes.
            packets[run].extend(int(raw, 16).to_bytes(32, "little"))
            if int(last):
                last_seen[run] = True
            continue
        m = ROW.fullmatch(line)
        if m:
            run = int(m.group(1))
            marker = tuple(map(int, m.groups()[1:]))
            index = row_marker_count[run]
            if (run != phase or last_seen[run]
                    or len(packets[run]) != 32 * (index + 1)):
                raise ValueError("missing/duplicate/out-of-order XSim ROW diagnostic")
            actual = decode_trace(bytes(packets[run][-32:-8]))
            actual_fields = (
                actual.tick, actual.neuron_id, actual.voltage,
                actual.spike, actual.evaluated, actual.delivered_count,
            )
            if marker != actual_fields:
                raise ValueError("XSim ROW diagnostic disagrees with actual DMA TDATA")
            row_marker_count[run] += 1
            continue
        m = FINAL.fullmatch(line)
        if m:
            run, status, rows, committed, sid = m.groups()
            run, status, rows, committed = map(
                int, (run, status, rows, committed)
            )
            if (run != phase or final_count[run] or not last_seen[run]
                    or status != EXPECTED_STATUS[run]
                    or rows != EXPECTED_ROWS[run]
                    or committed != EXPECTED_COMMITS[run]
                    or int(sid, 16) != SESSION_IDS[run]):
                raise ValueError("missing/incorrect real hardware footer status/count")
            # XSim emits one ROW diagnostic after each neural DMA beat.
            # Synthetic host transcripts without ROW markers remain supported.
            # If any exist, require ALL rows rather than ignoring partial logs.
            if row_marker_count[run] not in (0, rows):
                raise ValueError("incomplete XSim ROW diagnostic coverage")
            # The footer must be the LAST beat in the packet.
            if len(packets[run]) != 32 * (rows + 1):
                raise ValueError("wrong 256-bit DMA beat count before footer")
            frame = accept_dma_frame(
                bytes(packets[run]), session_id=SESSION_IDS[run],
                neuron_count=2, ticks=12, hls_status=EXPECTED_STATUS[run],
                transferred_bytes=len(packets[run]),
                dma_completed=True, tlast_certified=last_seen[run],
                transport_quiescent=True,
            )
            if frame.result.accepted != (run == 0):
                raise ValueError("failed hardware run was published or success rejected")
            if len(frame.result.rows) != EXPECTED_COMMITS[run]:
                raise ValueError("DMA packet did not atomically commit correct rows")
            if frame.result.drained_rows != EXPECTED_ROWS[run]:
                raise ValueError("DMA packet lost provisional transfer(s)")
            if run == 0:
                for i, row in enumerate(frame.result.rows):
                    tick, neuron = divmod(i, 2)
                    spike = int((tick == 0 and neuron == 0)
                                or (tick == 8 and neuron == 1))
                    delivered = int(tick in (0, 8))
                    if (row.tick, row.neuron_id, row.voltage, row.spike,
                            row.evaluated, row.delivered_count) != (
                            tick, neuron, 0, spike, spike, delivered
                    ):
                        raise ValueError("actual HLS trace violated recurrent spike oracle")
            final_count[run] += 1
            continue
        m = COMMIT.fullmatch(line)
        if m:
            run, count = map(int, m.groups())
            if (run != phase or not final_count[run] or commit_count[run]
                    or count != EXPECTED_COMMITS[run]):
                raise ValueError("wrong or early simulator commit marker")
            commit_count[run] += 1
            phase += 1
            continue
        if line.startswith(PASS):
            if phase != 2 or pass_seen:
                raise ValueError("premature or duplicate simulator PASS")
            pass_seen += 1
        elif line.startswith("M05_11C_"):
            raise ValueError("unknown/malformed M05.11c simulator marker")

    if (phase != 2 or final_count != [1, 1]
            or commit_count != [1, 1] or not all(last_seen)
            or pass_seen != 1):
        raise ValueError("incomplete verified generated-HLS/RTL frame transcript")
    return EXPECTED_COMMITS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xsim-log", type=Path, required=True)
    args = parser.parse_args()
    try:
        accepted = replay_real_xsim_log(
            args.xsim_log.read_text(encoding="utf-8", errors="replace")
        )
    except (OSError, ValueError, DMAFrameError) as exc:
        print(f"ERROR: M05.11c real XSim raw DMA frame replay: {exc}",
              file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        "PASS: M05.11c raw 256-bit RTL DMA transcript replay: "
        "session0=24 trace+TLAST/footer status0 committed24; "
        "session1=8 trace+TLAST/footer status4 committed0; "
        f"accepted={accepted[0]}+{accepted[1]} (OFFLINE SIMULATOR, not PS DMA)"
    )


if __name__ == "__main__":
    main()
