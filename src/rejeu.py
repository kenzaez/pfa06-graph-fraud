import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from src import e0
from src.audit import sha256
from src.features import SPLITS, prepare

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "e0"
POPS = ["population_principale", "population_secondaire"]


def hash_fichier(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def manifeste(chemin_donnees):
    import sklearn
    import xgboost
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        commit = None
    sortie = {
        "python": sys.version.split()[0],
        "plateforme": platform.platform(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "commit_git": commit,
        "donnees_sha256": sha256(chemin_donnees),
        "graine": e0.CFG["seed"],
        "configs_sha256": {n: hash_fichier(ROOT / "configs" / n) for n in ["splits.json", "variables.json", "e0.json"]},
        "sorties_sha256": {},
    }
    for p in sorted(list(OUT.glob("predictions_*.csv.gz")) + list(OUT.glob("*.csv")) + list((ROOT / "models").glob("e0_*"))):
        sortie["sorties_sha256"][str(p.relative_to(ROOT))] = hash_fichier(p)
    (ROOT / "reports" / "manifest_e0.json").write_text(json.dumps(sortie, indent=2))
    return sortie


def charger_predictions():
    res = {}
    for p in OUT.glob("predictions_*.csv.gz"):
        res[p.name.replace("predictions_", "").replace(".csv.gz", "")] = pd.read_csv(p)
    return res


def topk_quotidien(preds):
    lignes = []
    for nom, d in preds.items():
        scen, pop = nom.split("_", 1)
        for part, g in d.groupby("partition"):
            nb_steps = g.groupby("day").step.nunique()
            for lab in ["XGBoost", "RegLog"]:
                dd = g.assign(score=g[f"score_{lab}"]).set_index("idx")
                for K in e0.KS:
                    t = e0.topk_par_jour(dd[["day", "y", "score"]], K)
                    t["steps_observes"] = t.day.map(nb_steps).values
                    t["jour_partiel"] = t.steps_observes < 24
                    t["jour_sans_negatif"] = t.transactions == t.fraudes_jour
                    t.insert(0, "partition", part)
                    t.insert(0, "modele", lab)
                    t.insert(0, "population", pop)
                    t.insert(0, "scenario", scen)
                    lignes.append(t)
    out = pd.concat(lignes)
    out.to_csv(OUT / "topk_quotidien.csv", index=False)
    return out


def agreger_topk(tq, sans_jour_sans_negatif=False):
    d = tq[~tq.jour_sans_negatif] if sans_jour_sans_negatif else tq
    g = d.groupby(["scenario", "population", "modele", "partition", "K"]).agg(
        alertes=("alertes", "sum"), tp=("fraudes_detectees", "sum"), fraudes=("fraudes_jour", "sum"),
        jours=("day", "nunique"), jours_budget_depasse=("budget_depasse", "sum")).reset_index()
    g["precision"] = g.tp / g.alertes
    g["rappel"] = g.tp / g.fraudes
    return g


def sans_un_jour(preds):
    lignes = []
    for nom, d in preds.items():
        scen, pop = nom.split("_", 1)
        t = d[d.partition == "test"]
        for lab in ["XGBoost", "RegLog"]:
            lignes.append({"scenario": scen, "population": pop, "modele": lab, "jour_retire": "aucun",
                           "ap": average_precision_score(t.y, t[f"score_{lab}"])})
            for j in sorted(t.day.unique()):
                u = t[t.day != j]
                lignes.append({"scenario": scen, "population": pop, "modele": lab, "jour_retire": int(j),
                               "ap": average_precision_score(u.y, u[f"score_{lab}"])})
    out = pd.DataFrame(lignes)
    out.to_csv(OUT / "ap_sans_un_jour_test.csv", index=False)
    return out


def calibration_resume(preds):
    lignes = []
    for nom, d in preds.items():
        scen, pop = nom.split("_", 1)
        for part, g in d.groupby("partition"):
            for lab in ["XGBoost", "RegLog"]:
                s = g[f"score_{lab}"]
                lignes.append({"scenario": scen, "population": pop, "modele": lab, "partition": part,
                               "score_moyen": s.mean(), "taux_observe": g.y.mean(),
                               "ecart": s.mean() - g.y.mean(), "n": len(g)})
    out = pd.DataFrame(lignes)
    out.to_csv(OUT / "calibration_resume.csv", index=False)
    return out


def alertes_au_seuil(preds, resultats):
    lignes = []
    for nom, d in preds.items():
        scen, pop = nom.split("_", 1)
        for lab in ["XGBoost", "RegLog"]:
            seuil = resultats[(resultats.scenario == scen) & (resultats.population == pop) & (resultats.modele == lab)
                              & (resultats.partition == "val")].seuil.iloc[0]
            for part, g in d.groupby("partition"):
                a = g[g[f"score_{lab}"] >= seuil].groupby("day").size().reindex(sorted(g.day.unique()), fill_value=0)
                lignes.append({"scenario": scen, "population": pop, "modele": lab, "partition": part,
                               "seuil": seuil, "alertes_total": int(a.sum()), "alertes_par_jour_moyenne": a.mean(),
                               "alertes_jour_min": int(a.min()), "alertes_jour_max": int(a.max())})
    out = pd.DataFrame(lignes)
    out.to_csv(OUT / "alertes_au_seuil_gele.csv", index=False)
    return out


def diagnostics():
    preds = charger_predictions()
    resultats = pd.read_csv(OUT / "resultats_e0.csv")
    tq = topk_quotidien(preds)
    return {"topk_quotidien": tq, "topk_agrege": agreger_topk(tq), "topk_hors_jour_sans_negatif": agreger_topk(tq, True),
            "sans_un_jour": sans_un_jour(preds), "calibration": calibration_resume(preds),
            "alertes_seuil": alertes_au_seuil(preds, resultats)}


def rejouer(df, dossier_temp):
    dossier = Path(dossier_temp)
    (dossier / "models").mkdir(parents=True, exist_ok=True)
    ancien = (e0.OUT, e0.MODELS)
    e0.OUT, e0.MODELS = dossier, dossier / "models"
    try:
        d = prepare(df)
        choix = json.loads((OUT / "config_choisie.json").read_text())
        for scen in ["A", "B"]:
            for pop in POPS:
                e0.evaluer(d, scen, pop, params=choix[scen])
    finally:
        e0.OUT, e0.MODELS = ancien
    lignes = []
    for scen in ["A", "B"]:
        for pop in POPS:
            a = pd.read_csv(OUT / f"predictions_{scen}_{pop}.csv.gz")
            b = pd.read_csv(dossier / f"predictions_{scen}_{pop}.csv.gz")
            assert (a.idx.values == b.idx.values).all()
            for lab in ["XGBoost", "RegLog"]:
                c = f"score_{lab}"
                ecart = float(np.abs(a[c].values - b[c].values).max())
                for part in ["val", "test"]:
                    m = (a.partition == part).values
                    lignes.append({"scenario": scen, "population": pop, "modele": lab, "partition": part,
                                   "ecart_max_score": ecart,
                                   "ap_initial": average_precision_score(a.y[m], a[c][m]),
                                   "ap_rejeu": average_precision_score(b.y[m], b[c][m])})
    out = pd.DataFrame(lignes)
    out["identique"] = (out.ap_initial - out.ap_rejeu).abs() < 1e-9
    out.to_csv(OUT / "rejeu_e0.csv", index=False)
    return out
