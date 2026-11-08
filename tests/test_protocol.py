import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = json.loads((ROOT / "configs" / "splits.json").read_text())
VARS = json.loads((ROOT / "configs" / "variables.json").read_text())


def test_partitions_dans_l_ordre_sans_chevauchement():
    tr, va, te = SPLITS["train"], SPLITS["val"], SPLITS["test"]
    assert tr[0] <= tr[1] < va[0] <= va[1] < te[0] <= te[1]


def test_partitions_contigues_et_completes():
    tr, va, te = SPLITS["train"], SPLITS["val"], SPLITS["test"]
    assert tr[0] == 1 and te[1] == 743
    assert va[0] == tr[1] + 1 and te[0] == va[1] + 1


def test_aucune_variable_exclue_dans_les_scenarios():
    for name, feats in VARS["scenarios"].items():
        assert not set(feats) & set(VARS["excluded"]), name


def test_scenario_b_sans_soldes():
    assert not any("balance" in f for f in VARS["scenarios"]["B"])


def test_cible_et_temps_jamais_en_entree():
    for feats in VARS["scenarios"].values():
        assert VARS["target"] not in feats
        assert VARS["time_column"] not in feats
