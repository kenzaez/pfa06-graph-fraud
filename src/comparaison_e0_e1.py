from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[1]
E0 = ROOT / "reports" / "e0"
E1 = ROOT / "reports" / "e1"
OUT = ROOT / "reports" / "comparaison"


def charger(pop="population_principale"):
    a = pd.read_csv(E0 / f"predictions_B_{pop}.csv.gz")
    b = pd.read_csv(E1 / f"predictions_E1_{pop}.csv.gz")
    assert (a.idx.values == b.idx.values).all() and (a.y.values == b.y.values).all()
    return a, b


def ap_global(pop="population_principale"):
    a, b = charger(pop)
    lignes = []
    for part in ["val", "test"]:
        m = (a.partition == part).values
        for lab in ["XGBoost", "RegLog"]:
            lignes.append({"population": pop, "partition": part, "modele": lab,
                           "ap_E0_B": average_precision_score(a.y[m], a[f"score_{lab}"][m]),
                           "ap_E1": average_precision_score(b.y[m], b[f"score_{lab}"][m])})
        if True:
            sans = m & (a.day.values < 31)
            if part == "test":
                for lab in ["XGBoost", "RegLog"]:
                    lignes.append({"population": pop, "partition": "test_sans_jour31", "modele": lab,
                                   "ap_E0_B": average_precision_score(a.y[sans], a[f"score_{lab}"][sans]),
                                   "ap_E1": average_precision_score(b.y[sans], b[f"score_{lab}"][sans])})
    t = pd.DataFrame(lignes)
    t["gain"] = t.ap_E1 - t.ap_E0_B
    return t


def par_jour(pop="population_principale"):
    a, b = charger(pop)
    t = a[a.partition == "test"].index
    lignes = []
    for j in sorted(a.loc[t, "day"].unique()):
        m = ((a.partition == "test") & (a.day == j)).values
        if a.y[m].sum() == 0 or a.y[m].sum() == m.sum():
            ap0 = ap1 = np.nan
        else:
            ap0 = average_precision_score(a.y[m], a.score_XGBoost[m])
            ap1 = average_precision_score(b.y[m], b.score_XGBoost[m])
        lignes.append({"day": int(j), "transactions": int(m.sum()), "fraudes": int(a.y[m].sum()), "ap_E0_B": ap0, "ap_E1": ap1,
                       "gain": ap1 - ap0})
    return pd.DataFrame(lignes)


def selon_historique(df_graphe_test, pop="population_principale"):
    a, b = charger(pop)
    g = df_graphe_test.loc[a.idx.values].reset_index(drop=True)
    m = (a.partition == "test").values
    lignes = []
    for nom, masque in [("emetteur sans historique", g.g_orig_a_historique.values == 0),
                        ("emetteur avec historique", g.g_orig_a_historique.values == 1),
                        ("beneficiaire sans historique", g.g_dest_a_historique.values == 0),
                        ("beneficiaire avec historique", g.g_dest_a_historique.values == 1)]:
        k = m & masque
        if a.y[k].sum() == 0:
            continue
        lignes.append({"groupe": nom, "transactions": int(k.sum()), "fraudes": int(a.y[k].sum()),
                       "ap_E0_B": average_precision_score(a.y[k], a.score_XGBoost[k]),
                       "ap_E1": average_precision_score(b.y[k], b.score_XGBoost[k])})
    return pd.DataFrame(lignes)


def main(df_graphe=None):
    OUT.mkdir(parents=True, exist_ok=True)
    g = ap_global()
    g.to_csv(OUT / "ap_E0B_contre_E1.csv", index=False)
    j = par_jour()
    j.to_csv(OUT / "ap_par_jour_E0B_contre_E1.csv", index=False)
    res = {"global": g, "par_jour": j}
    if df_graphe is not None:
        h = selon_historique(df_graphe)
        h.to_csv(OUT / "ap_selon_historique.csv", index=False)
        res["historique"] = h
    return res
