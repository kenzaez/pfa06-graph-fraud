import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import calibration_curve
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from src.features import SPLITS, matrice, population, prepare

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "configs" / "e0.json").read_text())
OUT = ROOT / "reports" / "e0"
MODELS = ROOT / "models"
KS = SPLITS["alert_budget"]["K"]


def sous_echantillonner(X, y, taux, seed):
    pos = np.flatnonzero(y.values == 1)
    neg = np.flatnonzero(y.values == 0)
    n_neg = min(len(neg), int(round(len(pos) * (1 - taux) / taux)))
    rng = np.random.default_rng(seed)
    idx = np.concatenate([pos, rng.choice(neg, n_neg, replace=False)])
    rng.shuffle(idx)
    return X.iloc[idx], y.iloc[idx]


def entrainer_xgb(Xtr, ytr, Xva, yva, depth, lr, spw):
    m = xgb.XGBClassifier(
        n_estimators=CFG["n_estimators_max"],
        max_depth=depth,
        learning_rate=lr,
        subsample=CFG["subsample"],
        scale_pos_weight=spw,
        tree_method="hist",
        eval_metric="aucpr",
        early_stopping_rounds=CFG["early_stopping_rounds"],
        random_state=CFG["seed"],
        n_jobs=-1,
    )
    t0 = time.perf_counter()
    m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    return m, time.perf_counter() - t0


def selection(Xtr, ytr, Xva, yva, grille=None):
    grille = grille or CFG
    rows, best = [], None
    for strat in grille["desequilibre"]:
        if strat["taux_cible"] is None:
            Xs, ys = Xtr, ytr
            spw = float((ytr == 0).sum() / max((ytr == 1).sum(), 1))
        else:
            Xs, ys = sous_echantillonner(Xtr, ytr, strat["taux_cible"], CFG["seed"])
            spw = 1.0
        for depth in grille["max_depth"]:
            for lr in grille["learning_rate"]:
                m, t = entrainer_xgb(Xs, ys, Xva, yva, depth, lr, spw)
                ap = average_precision_score(yva, m.predict_proba(Xva)[:, 1])
                row = {"desequilibre": strat["nom"], "taux_cible": strat["taux_cible"], "lignes_train": len(ys),
                       "max_depth": depth, "learning_rate": lr, "scale_pos_weight": spw,
                       "n_arbres": int(m.best_iteration + 1), "ap_val": ap, "temps_fit_s": t}
                rows.append(row)
                if best is None or ap > best[0]["ap_val"]:
                    best = (row, m)
    return pd.DataFrame(rows).sort_values("ap_val", ascending=False), best[0], best[1]


def refit(Xtr, ytr, Xva, yva, params):
    if params["taux_cible"] is None:
        Xs, ys = Xtr, ytr
        spw = float((ytr == 0).sum() / max((ytr == 1).sum(), 1))
    else:
        Xs, ys = sous_echantillonner(Xtr, ytr, params["taux_cible"], CFG["seed"])
        spw = 1.0
    return entrainer_xgb(Xs, ys, Xva, yva, params["max_depth"], params["learning_rate"], spw)


def signed_log(X):
    return np.sign(X) * np.log1p(np.abs(X))


def entrainer_lr(Xtr, ytr):
    m = make_pipeline(SimpleImputer(strategy="median"), FunctionTransformer(signed_log), StandardScaler(),
                      LogisticRegression(class_weight="balanced", max_iter=1000))
    t0 = time.perf_counter()
    m.fit(Xtr.values, ytr.values)
    return m, time.perf_counter() - t0


def taille_ko(m, chemin):
    if isinstance(m, xgb.XGBClassifier):
        m.save_model(chemin)
    else:
        joblib.dump(m, chemin)
    return Path(chemin).stat().st_size / 1024


def scores(m, X):
    return m.predict_proba(X.values if not isinstance(m, xgb.XGBClassifier) else X)[:, 1]


def seuil_budget(s_val, days_val, K):
    n = min(len(s_val), K * days_val.nunique())
    return float(np.sort(s_val)[::-1][n - 1])


def ordre_alertes(g):
    o = np.lexsort((g.index.values, -g.score.values))
    return g.iloc[o]


def topk_par_jour(d, K):
    rows = []
    for day, g in d.groupby("day"):
        g = ordre_alertes(g)
        k_d = min(K, len(g))
        top = g.head(k_d)
        rows.append({"day": day, "K": K, "transactions": len(g), "alertes": k_d,
                     "fraudes_detectees": int(top.y.sum()), "fraudes_jour": int(g.y.sum()),
                     "budget_depasse": len(g) < K,
                     "precision": top.y.sum() / k_d if k_d else np.nan,
                     "rappel": top.y.sum() / g.y.sum() if g.y.sum() else np.nan})
    return pd.DataFrame(rows)


def ap_par_jour(d):
    rows = []
    for day, g in d.groupby("day"):
        ap = average_precision_score(g.y, g.score) if 0 < g.y.sum() < len(g) else np.nan
        rows.append({"day": day, "transactions": len(g), "fraudes": int(g.y.sum()),
                     "taux_pct": g.y.mean() * 100, "ap": ap})
    return pd.DataFrame(rows)


def metriques(y, s, days, seuil, idx=None):
    y = np.asarray(y)
    pred = s >= seuil
    tp = int((pred & (y == 1)).sum())
    fp = int((pred & (y == 0)).sum())
    fn = int((~pred & (y == 1)).sum())
    tn = int((~pred & (y == 0)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    taux = y.mean()
    ap = average_precision_score(y, s)
    out = {"transactions": len(y), "fraudes": int(y.sum()), "taux_pct": taux * 100,
           "ap": ap, "ap_hasard": taux, "ratio_ap_taux": ap / taux if taux else np.nan,
           "seuil": seuil, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
           "precision": p, "rappel": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
           "brier": brier_score_loss(y, s)}
    d = pd.DataFrame({"day": np.asarray(days), "y": y, "score": s}, index=np.arange(len(y)) if idx is None else np.asarray(idx))
    for K in KS:
        t = topk_par_jour(d, K)
        out[f"P@{K}"] = t.fraudes_detectees.sum() / t.alertes.sum()
        out[f"R@{K}"] = t.fraudes_detectees.sum() / max(t.fraudes_jour.sum(), 1)
        out[f"jours_budget_depasse_{K}"] = int(t.budget_depasse.sum())
    return out


def latence_ms_pour_1000(m, X, rep=5):
    x = X.iloc[:1000]
    t = []
    for _ in range(rep):
        t0 = time.perf_counter()
        scores(m, x)
        t.append(time.perf_counter() - t0)
    return float(np.median(t) * 1000)


def shap_moyen(m, X, n=20000):
    xs = X.sample(min(n, len(X)), random_state=CFG["seed"])
    contrib = m.get_booster().predict(xgb.DMatrix(xs), pred_contribs=True)[:, :-1]
    return pd.Series(np.abs(contrib).mean(0), index=xs.columns).sort_values(ascending=False)


def figures(courbes, calib, nom):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, part in zip(axes, ["val", "test"]):
        for lab, (y, s) in courbes[part].items():
            pr, rc, _ = precision_recall_curve(y, s)
            ax.plot(rc, pr, label=f"{lab} (AP {average_precision_score(y, s):.3f})")
        ax.axhline(np.mean(y), ls="--", color="gray", label=f"hasard ({np.mean(y):.4f})")
        ax.set_title(f"{nom} : {part}")
        ax.set_xlabel("rappel")
        ax.set_ylabel("precision")
        ax.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(OUT / f"pr_{nom}.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.5, 5))
    for lab, (y, s) in calib.items():
        fp_, mp = calibration_curve(y, s, n_bins=10, strategy="quantile")
        ax.plot(mp, fp_, marker="o", label=lab)
    ax.plot([0, 1], [0, 1], ls="--", color="gray")
    ax.set_xlabel("score moyen")
    ax.set_ylabel("taux de fraude observe")
    ax.set_title(f"fiabilite {nom}")
    ax.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(OUT / f"fiabilite_{nom}.png", dpi=150)
    plt.close(fig)


def evaluer(d, scenario, pop, params=None, grille=None):
    sub = population(d, pop)
    X = matrice(sub, scenario)
    y = sub.isFraud
    parts = {p: sub.partition == p for p in ["train", "val", "test"]}
    Xtr, ytr = X[parts["train"]], y[parts["train"]]
    Xva, yva = X[parts["val"]], y[parts["val"]]
    nom = f"{scenario}_{pop}"
    res = {"nom": nom}
    if params is None:
        sel, params, m = selection(Xtr, ytr, Xva, yva, grille)
        sel.to_csv(OUT / f"selection_{nom}.csv", index=False)
        t_fit = params["temps_fit_s"]
    else:
        m, t_fit = refit(Xtr, ytr, Xva, yva, params)
    lr_m, t_lr = entrainer_lr(Xtr, ytr)
    tailles = {"XGBoost": taille_ko(m, MODELS / f"e0_xgb_{nom}.json"),
               "RegLog": taille_ko(lr_m, MODELS / f"e0_reglog_{nom}.joblib")}
    res["params"] = params
    modeles = {"XGBoost": (m, t_fit), "RegLog": (lr_m, t_lr)}
    lignes, jours, courbes, calib, preds = [], [], {"val": {}, "test": {}}, {}, {}
    for lab, (mod, tf) in modeles.items():
        s_va = scores(mod, Xva)
        seuil = seuil_budget(s_va, sub.day[parts["val"]], CFG["budget_seuil_K"])
        for part, mask in [("val", parts["val"]), ("test", parts["test"]),
                           ("test_sans_jour31", parts["test"] & (sub.day < 31))]:
            s = scores(mod, X[mask])
            row = metriques(y[mask].values, s, sub.day[mask].values, seuil, idx=X.index[mask].values)
            if part in ("val", "test"):
                preds.setdefault(part, pd.DataFrame({"idx": X.index[mask].values, "step": sub.step[mask].values,
                                                    "day": sub.day[mask].values, "partition": part,
                                                    "y": y[mask].values}))[f"score_{lab}"] = s
            row.update({"modele": lab, "scenario": scenario, "population": pop, "partition": part})
            lignes.append(row)
            if part in courbes:
                courbes[part][lab] = (y[mask].values, s)
            if part == "test":
                aj = ap_par_jour(pd.DataFrame({"day": sub.day[mask].values, "y": y[mask].values, "score": s}))
                aj.insert(0, "modele", lab)
                jours.append(aj)
            if part in ("val", "test"):
                calib[f"{lab} {part}"] = (y[mask].values, s)
        lat = latence_ms_pour_1000(mod, Xva)
        for r in lignes[-3:]:
            r["temps_fit_s"] = tf
            r["latence_ms_1000tx"] = lat
            r["taille_modele_ko"] = tailles[lab]
    figures(courbes, calib, nom)
    pd.concat(preds.values()).to_csv(OUT / f"predictions_{nom}.csv.gz", index=False, float_format="%.10g")
    shap_moyen(m, Xtr).rename("shap_moyen_abs").to_csv(OUT / f"shap_{nom}.csv")
    res["metriques"] = pd.DataFrame(lignes)
    j = pd.concat(jours)
    j.insert(0, "scenario", scenario)
    j.insert(1, "population", pop)
    res["par_jour"] = j
    return res


def main(df, grille=None):
    OUT.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    d = prepare(df)
    resultats, par_jour, choix = [], [], {}
    for scenario in ["A", "B"]:
        r = evaluer(d, scenario, "population_principale", grille=grille)
        choix[scenario] = r["params"]
        resultats.append(r["metriques"])
        par_jour.append(r["par_jour"])
        r2 = evaluer(d, scenario, "population_secondaire", params=r["params"])
        resultats.append(r2["metriques"])
        par_jour.append(r2["par_jour"])
    tab = pd.concat(resultats)
    first = ["modele", "scenario", "population", "partition"]
    tab = tab[first + [c for c in tab.columns if c not in first]]
    tab.to_csv(OUT / "resultats_e0.csv", index=False)
    pj = pd.concat(par_jour)
    pj.to_csv(OUT / "ap_par_jour_test.csv", index=False)
    (OUT / "config_choisie.json").write_text(json.dumps(choix, indent=2, default=float))
    return tab, pj, choix
