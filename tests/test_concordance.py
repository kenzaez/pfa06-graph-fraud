import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports" / "audit_outputs.json"


@pytest.mark.skipif(not OUT.exists(), reason="lancer src/audit.py d'abord")
def test_rapport_et_code_concordent():
    from src.concordance import main

    table = main()
    ecarts = table[table.statut != "OK"]
    assert ecarts.empty, ecarts.to_string(index=False)
