"""Read limited ANSI/non-ANSI Verilog module port declarations WITHOUT elaboration.

Vendor wrappers commonly use Verilog-1995 names-only module headers and
input/output declarations inside the module body. Do not treat a module
name-only header as no AXI ports. Report unresolved parameter widths as
unknown, NEVER invent packed widths.
"""
from __future__ import annotations
import re

_NAME = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z_0-9$]*)\b")
_DECL = re.compile(
    r"\b(input|output|inout)\b\s*"
    r"(?:(?:wire|logic|reg|signed|unsigned|tri|var)\s+)*"
    r"(?:\[\s*([^\]\n]+)\]\s*)?"
    r"([A-Za-z_][A-Za-z_0-9$]*)", re.I,
)
AXI = re.compile(r"(?:S0[0-3]|M00)_AXI_", re.I)


def _strip_comments(text: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/",
                  lambda m: "".join("\n" if c == "\n" else " " for c in m[0]),
                  text, flags=re.S)


def _group(text: str, begin: int) -> tuple[str, int]:
    if begin >= len(text) or text[begin] != "(":
        raise ValueError("expected module parenthesized group")
    depth = 0
    for pos in range(begin, len(text)):
        if text[pos] == "(":
            depth += 1
        elif text[pos] == ")":
            depth -= 1
            if depth == 0:
                return text[begin + 1:pos], pos + 1
    raise ValueError("unbalanced Verilog group")


def _declarations(text: str) -> list[dict]:
    result = []
    seen: set[str] = set()
    for m in _DECL.finditer(text):
        direction, bits, name = m.groups()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        width = 1
        if bits is not None:
            expr = bits.split(":")
            if len(expr) == 2 and all(
                    re.fullmatch(r"\s*\d+\s*", x) for x in expr):
                width = abs(int(expr[0]) - int(expr[1])) + 1
            else:
                width = None
        result.append({
            "direction": direction.lower(),
            "name": name,
            "packed_width": width,
            "width_status": ("EXACT_LITERAL" if width is not None
                             else "UNRESOLVED_PARAMETER_EXPRESSION"),
        })
    return result


def module_port_contracts(verilog: str) -> list[dict]:
    """Parse declaration-only facts, not a stand-in for XSim HDL elaboration."""
    source = _strip_comments(verilog)
    contracts = []
    for found in _NAME.finditer(source):
        cur = found.end()
        while cur < len(source) and source[cur].isspace():
            cur += 1
        if cur < len(source) and source[cur] == "#":
            cur += 1
            while cur < len(source) and source[cur].isspace():
                cur += 1
            try:
                _, cur = _group(source, cur)
            except ValueError:
                continue
        while cur < len(source) and source[cur].isspace():
            cur += 1
        try:
            ports_header, end = _group(source, cur)
        except ValueError:
            continue
        semicolon = re.match(r"\s*;", source[end:])
        if semicolon is None:
            continue
        body_end = source.find("endmodule", end)
        if body_end < 0:
            continue
        ansi = _declarations(ports_header)
        if ansi:
            ports = ansi
            style = "ANSI"
        else:
            ports = _declarations(source[end + semicolon.end():body_end])
            style = "NON_ANSI"
        contracts.append({
            "module": found.group(1),
            "declaration_style": style,
            "axi_ports": [p for p in ports if AXI.search(p["name"])],
            "other_ports": [p for p in ports if not AXI.search(p["name"])],
        })
    return contracts
