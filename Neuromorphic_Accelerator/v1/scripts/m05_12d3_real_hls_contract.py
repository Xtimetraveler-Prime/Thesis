"""M05.12d.3: read-only attestation of the ORIGINAL Vitis signed32 RTL.

This is an evidence gate, not HLS re-synthesis or a generated-IP substitute.
Only the original owner's accepted M05.11c XSim evidence may select the HLS
implementation. Do not infer real HLS ports/registers from a Python model.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import re
import sys

from m05_axis_regmap import (
    REQUIRED as REQUIRED_REGISTERS,
    find_generated_register_map,
    parse_control_verilog,
)
from m05_rtl_meminit import referenced_init_files

PART = "xck26-sfvc784-2LV-c"
TOP = "m05_rolling_replay"
IMPL_PREFIX = "neuromorphic_v1_m05_rolling_impl_"
XSIM_PREFIX = "neuromorphic_v1_m05_11c_real_hls_"
# These widths/directions were exercised by the accepted original XSim
# tb_m05_11c_real_hls_shell.sv; actual generated top MUST match all of them.
PORTS = {
    "ap_clk": ("input", 1), "ap_rst_n": ("input", 1),
    "interrupt": ("output", 1),
    "s_axi_control_AWADDR": ("input", 7),
    "s_axi_control_AWVALID": ("input", 1),
    "s_axi_control_AWREADY": ("output", 1),
    "s_axi_control_WDATA": ("input", 32),
    "s_axi_control_WSTRB": ("input", 4),
    "s_axi_control_WVALID": ("input", 1),
    "s_axi_control_WREADY": ("output", 1),
    "s_axi_control_BRESP": ("output", 2),
    "s_axi_control_BVALID": ("output", 1),
    "s_axi_control_BREADY": ("input", 1),
    "s_axi_control_ARADDR": ("input", 7),
    "s_axi_control_ARVALID": ("input", 1),
    "s_axi_control_ARREADY": ("output", 1),
    "s_axi_control_RDATA": ("output", 32),
    "s_axi_control_RRESP": ("output", 2),
    "s_axi_control_RVALID": ("output", 1),
    "s_axi_control_RREADY": ("input", 1),
}
for _name, _width, _direction in (
    ("neurons", 128, "input"),
    ("synapses", 192, "input"),
    ("external_events", 128, "input"),
    ("trace", 192, "output"),
):
    PORTS[_name + "_TDATA"] = (_direction, _width)
    PORTS[_name + "_TVALID"] = (_direction, 1)
    PORTS[_name + "_TREADY"] = (
        "output" if _direction == "input" else "input", 1
    )

MODULE_START = re.compile(r"\bmodule\s+m05_rolling_replay\s*\(", re.M)
# Actual Vitis HLS 2025.2 uses parameterized ranges, e.g.
#   input [C_S_AXI_CONTROL_ADDR_WIDTH - 1:0] s_axi_control_AWADDR;
# with parameters C_S_AXI_CONTROL_ADDR_WIDTH=7 and
# C_S_AXI_CONTROL_WSTRB_WIDTH=(32 / 8).
PORT_DECL = re.compile(
    r"^\s*(input|output)\s+(?:(?:wire|reg|logic|signed|unsigned)\s+)*"
    r"(?:\[\s*([^:\]\n]+)\s*:\s*([^\]\n]+)\s*\]\s*)?"
    r"([a-zA-Z_]\w*)\s*[,;)]", re.M
)
PARAM_DECL = re.compile(
    r"^\s*parameter\s+([a-zA-Z_]\w*)\s*=\s*([^;]+);", re.M
)


def _constant_expression(expr: str, parameters: dict[str, str],
                         stack: frozenset[str] = frozenset()) -> int:
    """Resolve only bounded integer arithmetic, never eval arbitrary Verilog.

    Supports integer literals, known parameter names, parentheses, unary +/-,
    plus, minus, multiply and exact integral division. Anything else fails.
    """
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid Verilog width expression: {expr!r}") from exc

    def visit(node: ast.AST, active: frozenset[str]) -> int:
        if isinstance(node, ast.Expression):
            return visit(node.body, active)
        if isinstance(node, ast.Constant) and type(node.value) is int:
            result = node.value
        elif isinstance(node, ast.Name):
            if node.id not in parameters or node.id in active:
                raise ValueError(f"undefined/cyclic Verilog width parameter {node.id}")
            return _constant_expression(parameters[node.id], parameters,
                                        active | frozenset((node.id,)))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = visit(node.operand, active)
            result = operand if isinstance(node.op, ast.UAdd) else -operand
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (
                ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = visit(node.left, active), visit(node.right, active)
            if isinstance(node.op, ast.Add):
                result = left + right
            elif isinstance(node.op, ast.Sub):
                result = left - right
            elif isinstance(node.op, ast.Mult):
                result = left * right
            else:
                if right == 0 or left % right:
                    raise ValueError("nonintegral/zero-divisor Verilog width parameter")
                result = left // right
        else:
            raise ValueError(f"unsupported Verilog width expression: {expr!r}")
        if not -65536 <= result <= 65536:
            raise ValueError("unreasonable Verilog width expression value")
        return result

    return visit(tree, stack)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_top_ports(source: str) -> dict[str, tuple[str, int]]:
    """Resolve actual HLS top pin directions and parameterized widths."""
    starts = list(MODULE_START.finditer(source))
    if len(starts) != 1:
        raise ValueError("exactly one generated m05_rolling_replay top required")
    body = source[starts[0].start():]
    end = re.search(r"\bendmodule\b", body)
    if end is None:
        raise ValueError("HLS top missing endmodule")
    body = body[:end.start()]
    header = re.match(
        r"module\s+m05_rolling_replay\s*\((.*?)\)\s*;",
        body, re.S
    )
    if header is None:
        raise ValueError("malformed HLS top port list")
    listed = []
    for item in header.group(1).split(","):
        name = re.search(r"([a-zA-Z_]\w*)\s*$", item.strip())
        if name is None:
            raise ValueError("malformed HLS top pin name")
        listed.append(name.group(1))
    if len(set(listed)) != len(listed):
        raise ValueError("duplicate names in HLS top port list")
    params: dict[str, str] = {}
    for match in PARAM_DECL.finditer(body):
        name, expr = match.groups()
        if name in params:
            raise ValueError(f"duplicate generated Verilog parameter {name}")
        params[name] = expr
    found: dict[str, tuple[str, int]] = {}
    for match in PORT_DECL.finditer(body):
        direction, msb, lsb, name = match.groups()
        if msb is None:
            width = 1
        else:
            high = _constant_expression(msb, params)
            low = _constant_expression(lsb, params)
            width = abs(high - low) + 1
            if width > 65536:
                raise ValueError("unreasonable generated HLS bus width")
        if name in found:
            raise ValueError(f"duplicate RTL port declaration {name}")
        found[name] = direction, width
    if not found or set(listed) != set(found):
        raise ValueError("HLS port list does not match declared top-level pins")
    return found


def verify_top_contract(source: str) -> dict[str, tuple[str, int]]:
    actual = parse_top_ports(source)
    for name, expected in PORTS.items():
        if name not in actual or actual[name] != expected:
            raise ValueError(
                f"generated HLS port {name}: got {actual.get(name)!r}, "
                f"expected {expected!r}"
            )
    # Existing XSim exercised these native plain HLS streams WITHOUT sideband
    # TLAST/TKEEP. A different HLS generated interface needs design review.
    for prefix in ("neurons", "synapses", "external_events", "trace"):
        for extra in ("TLAST", "TKEEP", "TSTRB"):
            if prefix + "_" + extra in actual:
                raise ValueError("unexpected native HLS AXIS sideband "
                                 + prefix + "_" + extra)
    return actual


def verify_original_evidence(xsim_evidence: Path, source_cpp: Path
                             ) -> tuple[Path, Path, str, dict[str, int], Path]:
    xsim = xsim_evidence.resolve(strict=True)
    if not xsim.is_dir() or not xsim.name.startswith(XSIM_PREFIX):
        raise ValueError("only original M05.11c evidence directory accepted")
    if (xsim / "result.txt").read_text().strip() != "exit_status=0":
        raise ValueError("original M05.11c XSim evidence not accepted")
    if not (xsim / "05_dma_frame_replay.log").is_file() or not (
        "PASS: M05.11c raw 256-bit RTL DMA transcript replay"
        in (xsim / "05_dma_frame_replay.log").read_text()
    ):
        raise ValueError("M05.11c independent raw-frame PASS missing")
    impl_ref = (xsim / "source_impl_evidence.txt").read_text().strip()
    if not impl_ref or "\n" in impl_ref or not Path(impl_ref).is_absolute():
        raise ValueError("original source_impl_evidence.txt must give ONE absolute path")
    impl = Path(impl_ref).resolve(strict=True)
    if not impl.is_dir() or not impl.name.startswith(IMPL_PREFIX):
        raise ValueError("referenced evidence not original signed32 HLS impl")
    for name, required in (("result.txt", "exit_status=0"),
                           ("top.txt", TOP), ("part.txt", PART)):
        if (impl / name).read_text().strip() != required:
            raise ValueError(f"original HLS {name} mismatch")
    entries = []
    for line in (impl / "source_sha256.txt").read_text().splitlines():
        bits = line.split()
        if len(bits) >= 2 and bits[1].lstrip("*") == "hls/m05_rolling/m05_rolling.cpp":
            entries.append(bits[0])
    actual_hash = sha256(source_cpp)
    if len(entries) != 1 or not re.fullmatch(r"[a-f0-9]{64}", entries[0]):
        raise ValueError("missing/ambiguous frozen signed32 HLS source hash")
    if entries[0] != actual_hash:
        raise ValueError("signed32 HLS source changed from ORIGINAL implementation")
    # M05.11c's accepted XSim runner recorded this HLS source hash too.
    # Require the independently retained XSim manifest to agree with --impl.
    xsim_hashes = []
    for row in (xsim / "source_sha256.txt").read_text().splitlines():
        bits = row.split()
        if len(bits) >= 2 and Path(bits[1]).name == "m05_rolling.cpp":
            xsim_hashes.append(bits[0])
    if len(xsim_hashes) != 1 or xsim_hashes[0] != actual_hash:
        raise ValueError("M05.11c signed32 source hash disagrees with original HLS")
    rtl = impl / "work/hls/syn/verilog"
    top = rtl / (TOP + ".v")
    if not top.is_file():
        raise ValueError("actual Vitis generated top RTL missing")
    verify_top_contract(top.read_text(encoding="utf-8"))
    rtl_files = sorted((*rtl.glob("*.v"), *rtl.glob("*.sv")))
    if len(rtl_files) < 2 or any(not p.is_file() for p in rtl_files):
        raise ValueError("original generated sibling RTL missing")
    # The accepted XSim runner preserved the exact set of tool RTL source
    # paths it compiled. The names must still match, not merely the top.
    xsim_rtl = (xsim / "generated_rtl_files.txt").read_text().splitlines()
    if len(set(xsim_rtl)) != len(xsim_rtl) or not xsim_rtl:
        raise ValueError("M05.11c original generated RTL file manifest invalid")
    if {str(p.resolve()) for p in rtl_files} != set(xsim_rtl):
        raise ValueError("original M05.11c compiled RTL file set differs")
    # Retain evidence that all tool-generated RAM init assets exist, without
    # writing, copying or backfilling the immutable original Vitis artifact.
    ram_names = referenced_init_files(rtl)
    available: dict[str, set[str]] = {name: set() for name in ram_names}
    work_root = (impl / "work").resolve(strict=True)
    for asset in work_root.rglob("*.dat"):
        if asset.name in available:
            resolved = asset.resolve(strict=True)
            if not resolved.is_relative_to(work_root) or not resolved.is_file():
                raise ValueError("original Vitis RAM asset escapes work tree")
            available[asset.name].add(sha256(resolved))
    if any(len(values) != 1 for values in available.values()):
        raise ValueError("missing or conflicting original Vitis RAM .dat assets")
    addresses, reg_source = find_generated_register_map(impl)
    # If vendor also emitted control_s_axi, require EXACT consistency with
    # any generated driver header. Never assume offsets from a testbench.
    ctrl = rtl / (TOP + "_control_s_axi.v")
    if not ctrl.is_file():
        raise ValueError("Vitis generated HLS AXI-Lite control RTL missing")
    rtl_map = parse_control_verilog(ctrl.read_text(encoding="utf-8"))
    if addresses != rtl_map:
        raise ValueError("generated HLS driver and control RTL offsets disagree")
    if set(addresses) != set(REQUIRED_REGISTERS):
        raise ValueError("incomplete native HLS AXI-Lite map")
    return impl, rtl, actual_hash, addresses, reg_source


def attest(xsim_evidence: Path, source_cpp: Path) -> str:
    impl, rtl, source_hash, offsets, reg_source = verify_original_evidence(
        xsim_evidence, source_cpp
    )
    top = rtl / (TOP + ".v")
    ports = verify_top_contract(top.read_text(encoding="utf-8"))
    lines = [
        "META|scope|ORIGINAL_SIGNED32_GENERATED_RTL_ATTESTATION_NO_BD",
        "META|part|" + PART,
        "META|top|" + TOP,
        "META|xsim_evidence|" + str(xsim_evidence.resolve()),
        "META|impl_evidence|" + str(impl),
        "SOURCE_SHA256|" + source_hash + "|hls/m05_rolling/m05_rolling.cpp",
        "GENERATED_REG_SOURCE|" + str(reg_source),
    ]
    for p in sorted((*rtl.glob("*.v"), *rtl.glob("*.sv"))):
        lines.append(f"RTL_SHA256|{sha256(p)}|{p}")
    for name in sorted(PORTS):
        direction, bits = ports[name]
        lines.append(f"PORT|{name}|{direction}|{bits}")
    for name in sorted(offsets):
        lines.append(f"REG|{name}|0x{offsets[name]:02x}")
    lines.append("META|ps_pl_integration|NOT_RUN")
    lines.append("META|physical_board|NOT_AUTHORIZED")
    return "\n".join(lines) + "\n"


def require_new_evidence_output(report: Path) -> None:
    """Never create a report inside an accepted original artifact directory."""
    parent = report.parent.resolve(strict=True)
    if (not parent.name.startswith("neuromorphic_v1_m05_12d3_real_hls_contract_")
            or report.name != "01_original_hls_contract.txt"):
        raise ValueError("report must be in a NEW D3 contract evidence directory")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xsim-evidence", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        require_new_evidence_output(args.report)
        contents = attest(args.xsim_evidence, args.source)
        with args.report.open("x", encoding="utf-8") as f:
            f.write(contents)
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"ERROR: M05.12d.3 genuine HLS attestation: {exc}",
              file=sys.stderr)
        return 2
    print("PASS: M05.12d.3 ORIGINAL generated signed32 HLS RTL "
          "port/regmap/source attestation (NO Vivado BD or hardware)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
