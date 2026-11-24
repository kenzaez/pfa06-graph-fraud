import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score

from src import e0
from src.features import SPLITS, VARS, population, prepare

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "configs" / "ablation.json").read_text())


def colonnes(df, groupe):
    X = pd.DataFrame(index=df.index)
    for t in SPLITS["history_types"]:
        X[f"type_{t}"] = (df.type.astype(str) == t).astype(float)
    X["amount"] = df.amount
    if groupe in ("solde", "solde_derivees"):
        X["oldbalanceOrg"] = df.oldbalanceOrg
    if groupe == "solde_derivees":
        X["ecart_montant_solde"] = df.oldbalanceOrg - df.amount
        X["ratio_montant_solde"] = df.amount / (df.oldbalanceOrg + 1)
    return X


def lancer(df, dossier=None):
    d = prepare(df)
    sub = population(d, "population_principale")
    y = sub.isFraud
    tr, va, te = (sub.partition == p for p in ["train", "val", "test"])
    Xs, ys = e0.sous_echantillonner(colonnes(sub, "type_montant")[tr], y[tr], CFG["taux_cible"], CFG["seed"])
    idx = Xs.index
    lignes = []
    for groupe in CFG["groupes"]:
        X = colonnes(sub, groupe)
        m = xgb.XGBClassifier(n_estimators=CFG["n_estimators_max"], max_depth=CFG["max_depth"],
                              learning_rate=CFG["learning_rate"], subsample=CFG["subsample"], tree_method="hist",
                              eval_metric="aucpr", early_stopping_rounds=CFG["early_stopping_rounds"],
                              random_state=CFG["seed"], n_jobs=-1)
        m.fit(X.loc[idx], y.loc[idx], eval_set=[(X[va], y[va])], verbose=False)
        for part, mask in [("val", va), ("test", te), ("test_sans_jour31", te & (sub.day < 31))]:
            s = m.predict_proba(X[mask])[:, 1]
            ap = average_precision_score(y[mask], s)
            lignes.append({"groupe": groupe, "partition": part, "ap": ap, "taux": y[mask].mean(),
                           "ratio_ap_taux": ap / y[mask].mean(), "n_arbres": int(m.best_iteration + 1),
                           "n_variables": X.shape[1]})
    out = pd.DataFrame(lignes)
    dossier = Path(dossier) if dossier else ROOT / "reports" / "e0"
    out.to_csv(dossier / "ablation_solde.csv", index=False)
    return out
