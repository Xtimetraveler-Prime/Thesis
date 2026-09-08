from pathlib import Path

path = Path(__file__).resolve().parents[1] / "Neuromorphic Digital Twin" / "src" / "neuromorphic_twin" / "fpga_characterization.py"
text = path.read_text(encoding="utf-8")
old = '''        expected = {
            "case_id", "case_name", "tick", "cycles",
            "external_events", "recurrent_events", "routed_events",
        }
        if set(reader.fieldnames or ()) != expected:
'''
new = '''        expected = (
            "case_id", "case_name", "tick", "cycles",
            "external_events", "recurrent_events", "routed_events",
        )
        if tuple(reader.fieldnames or ()) != expected:
'''
if old not in text:
    raise SystemExit("M12.5 cycle-header anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
