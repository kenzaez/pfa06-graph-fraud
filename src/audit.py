import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPLITS = json.loads((ROOT / "configs" / "splits.json").read_text())


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return pd.read_csv(path, dtype={"type": "category"})


def partition(step):
    tr, va = SPLITS["train"], SPLITS["val"]
    return pd.Series(
        np.select([step <= tr[1], step <= va[1]], ["train", "val"], "test"),
        index=step.index,
    )


def run_audit(df, path=None):
    out = {}
    if path is not None:
        out["sha256"] = sha256(path)
    out["n_transactions"] = int(len(df))
    out["n_colonnes"] = int(df.shape[1])
    out["n_fraudes"] = int(df.isFraud.sum())
    out["taux_fraude_pct"] = float(df.isFraud.mean() * 100)
    out["valeurs_manquantes"] = int(df.isnull().sum().sum())
    out["doublons"] = int(df.duplicated().sum())
    out["step_min"] = int(df.step.min())
    out["step_max"] = int(df.step.max())

    ft = df.loc[df.isFraud == 1, "type"].value_counts()
    for t in df.type.cat.categories:
        out[f"fraudes_{t}"] = int(ft.get(t, 0))

    out["emetteurs_distincts"] = int(df.nameOrig.nunique())
    out["beneficiaires_distincts"] = int(df.nameDest.nunique())
    co = df.nameOrig.value_counts()
    cd = df.nameDest.value_counts()
    out["emetteurs_vus_1_fois"] = int((co == 1).sum())
    out["beneficiaires_vus_1_fois"] = int((cd == 1).sum())
    out["beneficiaires_plus_de_10_fois"] = int((cd > 10).sum())

    out["comptes_emetteurs_et_beneficiaires"] = int(len(set(df.nameOrig) & set(df.nameDest)))
    first_dest = df.groupby("nameDest").step.min()
    seen = df.nameOrig.map(first_dest) < df.step
    out["tx_emetteur_deja_beneficiaire"] = int(seen.sum())
    out["tx_emetteur_deja_beneficiaire_pct"] = float(seen.mean() * 100)
    out["fraudes_emetteur_deja_beneficiaire"] = int(df.loc[seen, "isFraud"].sum())

    pairs = df.groupby(["nameOrig", "nameDest"]).size()
    out["paires_repetees"] = int((pairs > 1).sum())

    first_seen = pd.concat([
        df[["nameOrig", "step"]].rename(columns={"nameOrig": "acc"}),
        df[["nameDest", "step"]].rename(columns={"nameDest": "acc"}),
    ]).groupby("acc").step.min()
    age_orig = df.step - df.nameOrig.map(first_seen)
    age_dest = df.step - df.nameDest.map(first_seen)
    out["emetteur_nouveau_pct"] = float((age_orig == 0).mean() * 100)
    out["beneficiaire_nouveau_pct"] = float((age_dest == 0).mean() * 100)
    out["age_median_beneficiaire_fraude_h"] = float(age_dest[df.isFraud == 1].median())
    out["age_median_beneficiaire_normal_h"] = float(age_dest[df.isFraud == 0].median())

    div = df.groupby("nameDest").nameOrig.nunique()
    fraud_dest = df.loc[df.isFraud == 1, "nameDest"].unique()
    out["diversite_mediane_beneficiaires"] = float(div.median())
    out["diversite_mediane_beneficiaires_fraude"] = float(div.loc[fraud_dest].median())

    merch = df.nameDest.str.startswith("M")
    out["tx_vers_marchands"] = int(merch.sum())
    out["fraudes_vers_marchands"] = int(df.loc[merch, "isFraud"].sum())

    out["montant_median_fraude"] = float(df.loc[df.isFraud == 1, "amount"].median())
    out["montant_median_normal"] = float(df.loc[df.isFraud == 0, "amount"].median())
    out["fraudes_montant_10M"] = int((df.loc[df.isFraud == 1, "amount"] == 10_000_000).sum())
    out["fraudes_montant_nul"] = int((df.loc[df.isFraud == 1, "amount"] == 0).sum())

    tc = df[df.type.isin(SPLITS["scoring_types"])]
    vide = (tc.amount - tc.oldbalanceOrg).abs() < 0.01
    out["fraudes_vide_compte_pct"] = float(vide[tc.isFraud == 1].mean() * 100)
    out["normales_vide_compte_pct"] = float(vide[tc.isFraud == 0].mean() * 100)

    out["isFlaggedFraud_total"] = int(df.isFlaggedFraud.sum())
    out["isFlaggedFraud_vraies_fraudes"] = int(df.loc[df.isFlaggedFraud == 1, "isFraud"].sum())

    part = partition(df.step)
    for p in ["train", "val", "test"]:
        m = part == p
        out[f"{p}_transactions"] = int(m.sum())
        out[f"{p}_fraudes"] = int(df.loc[m, "isFraud"].sum())
        out[f"{p}_taux_pct"] = float(df.loc[m, "isFraud"].mean() * 100)

    out["scoring_transactions"] = int(len(tc))
    out["scoring_taux_pct"] = float(tc.isFraud.mean() * 100)

    day = (df.step - 1) // 24 + 1
    d31 = day == 31
    out["jour31_transactions"] = int(d31.sum())
    out["jour31_fraudes"] = int(df.loc[d31, "isFraud"].sum())
    return out


def environnement():
    import importlib

    env = {"python": sys.version.split()[0], "plateforme": platform.platform()}
    for lib in ["pandas", "numpy", "matplotlib", "sklearn", "xgboost"]:
        try:
            env[lib] = importlib.import_module(lib).__version__
        except ImportError:
            env[lib] = None
    return env


def main(path):
    df = load(path)
    out = run_audit(df, path)
    rep = ROOT / "reports"
    rep.mkdir(exist_ok=True)
    (rep / "audit_outputs.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    (rep / "environnement.json").write_text(json.dumps(environnement(), indent=2))
    return df, out


if __name__ == "__main__":
    main(sys.argv[1])
