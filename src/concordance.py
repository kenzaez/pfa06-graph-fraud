import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def compare(outputs, expected):
    rows = []
    for key, spec in expected["valeurs"].items():
        att = spec["attendu"]
        if key not in outputs:
            rows.append((key, spec["section"], att, None, "ABSENT"))
            continue
        val = outputs[key]
        if isinstance(att, str):
            ok = val == att
            shown = val
        elif "decimales" in spec:
            shown = round(val, spec["decimales"])
            ok = abs(shown - att) < 10 ** -(spec["decimales"] + 3)
        else:
            shown = val
            ok = val == att
        rows.append((key, spec["section"], att, shown, "OK" if ok else "ECART"))
    return pd.DataFrame(rows, columns=["indicateur", "section", "rapport", "code", "statut"])


def main():
    outputs = json.loads((ROOT / "reports" / "audit_outputs.json").read_text())
    expected = json.loads((ROOT / "configs" / "report_values.json").read_text())
    table = compare(outputs, expected)
    dest = ROOT / "reports" / "tables"
    dest.mkdir(parents=True, exist_ok=True)
    table.to_csv(dest / "concordance.csv", index=False)
    return table


if __name__ == "__main__":
    t = main()
    print(t.to_string(index=False))
    print(t.statut.value_counts().to_string())
