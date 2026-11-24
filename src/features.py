import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPLITS = json.loads((ROOT / "configs" / "splits.json").read_text())
VARS = json.loads((ROOT / "configs" / "variables.json").read_text())


def derivees(scenario):
    base = set(VARS["scenarios"][scenario])
    return [k for k, v in VARS["derivees"].items() if set(v["depend_de"]) <= base]


def colonnes_brutes(scenario):
    return list(VARS["scenarios"][scenario])


def prepare(df):
    tr, va = SPLITS["train"], SPLITS["val"]
    out = df.copy()
    out["day"] = (out.step - 1) // 24 + 1
    out["partition"] = np.select([out.step <= tr[1], out.step <= va[1]], ["train", "val"], "test")
    return out


def population(df, nom):
    types = SPLITS[SPLITS[nom]]
    return df[df.type.isin(types)]


def matrice(df, scenario):
    cols = colonnes_brutes(scenario)
    X = pd.DataFrame(index=df.index)
    for c in cols:
        if c == "type":
            cats = pd.Categorical(df.type.astype(str), categories=SPLITS["history_types"])
            for t in SPLITS["history_types"]:
                X[f"type_{t}"] = (cats == t).astype(np.int8)
        else:
            X[c] = df[c].astype(float)
    for d in derivees(scenario):
        if d == "ecart_montant_solde":
            X[d] = df.oldbalanceOrg - df.amount
        elif d == "ratio_montant_solde":
            X[d] = df.amount / (df.oldbalanceOrg + 1)
    if scenario == "E1":
        gcols = [c for c in df.columns if c.startswith("g_")]
        assert gcols, "colonnes du graphe absentes : appeler graphe_causal.ajouter(df) avant"
        for c in gcols:
            X[c] = df[c].astype(float)
    interdit = set(VARS["excluded"]) | {VARS["target"], VARS["time_column"]} | set(VARS["graph_ids"])
    assert not interdit & set(X.columns)
    return X
