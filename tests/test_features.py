import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import VARS, derivees, matrice, population, prepare


def mini():
    return pd.DataFrame({
        "step": [1, 450, 600, 730], "type": ["TRANSFER", "PAYMENT", "CASH_OUT", "TRANSFER"],
        "amount": [10.0, 5.0, 7.0, 3.0], "nameOrig": ["C1", "C2", "C3", "C4"],
        "oldbalanceOrg": [10.0, 9.0, 1.0, 3.0], "newbalanceOrig": [0.0, 4.0, 0.0, 0.0],
        "nameDest": ["C9", "M1", "C8", "C7"], "oldbalanceDest": [0.0] * 4, "newbalanceDest": [0.0] * 4,
        "isFraud": [1, 0, 0, 1], "isFlaggedFraud": [0] * 4,
    })


def test_derivees_seulement_depuis_le_scenario():
    for s, cols in VARS["scenarios"].items():
        for d in derivees(s):
            assert set(VARS["derivees"][d]["depend_de"]) <= set(cols)


def test_scenario_b_sans_derivee_de_solde():
    assert derivees("B") == []


def test_matrice_sans_variable_interdite():
    df = prepare(mini())
    interdit = set(VARS["excluded"]) | {"nameOrig", "nameDest", "day", "partition"}
    for s in VARS["scenarios"]:
        X = matrice(df, s)
        assert not interdit & set(X.columns)
        assert not any("balance" in c for c in X.columns) or s == "A"


def test_partitions_et_jours():
    df = prepare(mini())
    assert list(df.partition) == ["train", "val", "test", "test"]
    assert list(df.day) == [1, 19, 25, 31]


def test_population_principale_sans_payment():
    df = prepare(mini())
    assert set(population(df, "population_principale").type) == {"TRANSFER", "CASH_OUT"}
