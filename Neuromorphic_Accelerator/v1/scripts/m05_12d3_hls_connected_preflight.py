"""M05.12d.3: reauthenticate accepted ORIGINAL signed32 HLS before Vivado.

A genuine Vitis RTL artifact is mandatory. Never copy, generate or stub HLS.
This is a read-only gate; it does not validate the future Vivado graph.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from m05_12d3_real_hls_contract import attest

CONTRACT_PREFIX = "neuromorphic_v1_m05_12d3_real_hls_contract_"
SOURCE_SHA = "24c4de87b5557cd536b33fe518595d56133e2ac737786bdf0d6fdbc53a687073"


def preflight(contract: Path, cpp: Path) -> Path:
    proof = contract.resolve(strict=True)
    if not proof.is_dir() or not proof.name.startswith(CONTRACT_PREFIX):
        raise ValueError("accepted original M05.12d.3 HLS contract folder required")
    if (proof / "result.txt").read_text().strip() != "exit_status=0":
        raise ValueError("original contract result was not exit_status=0")
    report = (proof / "01_original_hls_contract.txt").read_text()
    if not report.endswith("\n") or not report.startswith(
            "META|scope|ORIGINAL_SIGNED32_GENERATED_RTL_ATTESTATION_NO_BD\n"):
        raise ValueError("unexpected original HLS attestation scope")
    lines = report.splitlines()
    fields = {}
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) == 3 and parts[0] == "META":
            if parts[1] in fields:
                raise ValueError("duplicate original HLS metadata")
            fields[parts[1]] = parts[2]
    if fields.get("ps_pl_integration") != "NOT_RUN":
        raise ValueError("original source-only attestation claims a BD run")
    if fields.get("physical_board") != "NOT_AUTHORIZED":
        raise ValueError("original HLS proof claims physical authorization")
    if fields.get("part") != "xck26-sfvc784-2LV-c" or fields.get("top") != "m05_rolling_replay":
        raise ValueError("original HLS part/top mismatch")
    if f"SOURCE_SHA256|{SOURCE_SHA}|hls/m05_rolling/m05_rolling.cpp" not in lines:
        raise ValueError("original signed32 source hash not authenticated")
    xsim_path = fields.get("xsim_evidence")
    if not xsim_path or not Path(xsim_path).is_absolute():
        raise ValueError("original M05.11c evidence reference missing")
    # Recompute independent original HLS SOURCE+RTL+REGMAP attestation; exact
    # UTF-8 record comparison catches every changed generated .v byte.
    expected = attest(Path(xsim_path), cpp)
    if expected != report:
        raise ValueError("external original HLS source/RTL/regmap changed since accepted attestation")
    impl_path = fields.get("impl_evidence")
    if not impl_path or not Path(impl_path).is_absolute():
        raise ValueError("original Vitis implementation path missing")
    rtl = Path(impl_path).resolve(strict=True) / "work/hls/syn/verilog"
    if not (rtl / "m05_rolling_replay.v").is_file():
        raise ValueError("actual HLS top missing")
    return rtl


def require_new_preflight_output(output: Path) -> None:
    """Allow only a fresh current-stage artifact, never accepted evidence."""
    parent = output.parent.resolve(strict=True)
    allowed_prefixes = (
        "neuromorphic_v1_m05_12d3_hls_connected_",
        "neuromorphic_v1_m05_12d3_native_axis_",
        "neuromorphic_v1_m05_12d3_addr_validate_",
    )
    if (not parent.is_dir()
            or not any(parent.name.startswith(prefix) for prefix in allowed_prefixes)
            or output.name != "01_hls_preflight.txt"
            or output.exists()):
        raise ValueError(
            "preflight output must be a NEW file in an authorized "
            "M05.12d.3 integration evidence folder"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contract-evidence", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        rtl = preflight(a.contract_evidence, a.source)
        # Both integration runners use this genuine original HLS gate.
        # Validate unique new report target before any write.
        require_new_preflight_output(a.output)
        with a.output.open("x", encoding="utf-8") as f:
            f.write("PASS|ORIGINAL_SIGNED32_HLS_SOURCE_RTL_REGMAP_MATCH\n")
            f.write(f"RTL_DIRECTORY|{rtl}\n")
            f.write("META|physical_board|NOT_AUTHORIZED\n")
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"ERROR: M05.12d.3 integrated HLS preflight: {exc}", file=sys.stderr)
        return 2
    print("PASS: M05.12d.3 authentic ORIGINAL generated HLS input accepted for offline BD candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
