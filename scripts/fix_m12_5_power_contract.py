from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "Neuromorphic Digital Twin" / "docs" / "M12_5_CHARACTERIZATION.md"
text = path.read_text(encoding="utf-8")
old = "Power/energy remains intentionally outside the validated M12 claim set."
new = "Power/energy is intentionally outside the validated M12 claim set."
if old not in text:
    if new in text:
        raise SystemExit(0)
    raise SystemExit("M12.5 power/energy claim-boundary sentence not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
