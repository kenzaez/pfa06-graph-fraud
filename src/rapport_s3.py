import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
E0 = ROOT / "reports" / "e0"
SPLITS = json.loads((ROOT / "configs" / "splits.json").read_text())
CFG = json.loads((ROOT / "configs" / "e0.json").read_text())
KS = SPLITS["alert_budget"]["K"]


def f(x, n=3):
    return "n/a" if pd.isna(x) else f"{x:.{n}f}".replace(".", ",")


def pct(x, n=3):
    return "n/a" if pd.isna(x) else f"{x:.{n}f} %".replace(".", ",")


def tableau(df, cols, noms):
    lignes = ["| " + " | ".join(noms) + " |", "|" + "---|" * len(noms)]
    for _, r in df.iterrows():
        lignes.append("| " + " | ".join(c(r) if callable(c) else str(r[c]) for c in cols) + " |")
    return "\n".join(lignes)


def bloc_metriques(t):
    cols = ["modele", "scenario", lambda r: f(r.ap), lambda r: pct(r.taux_pct), lambda r: f(r.ratio_ap_taux, 1)]
    noms = ["Modele", "Scenario", "AP", "Taux de fraude", "AP / taux"]
    for K in KS:
        cols += [lambda r, K=K: f(r[f"P@{K}"]), lambda r, K=K: f(r[f"R@{K}"])]
        noms += [f"P@{K}", f"R@{K}"]
    cols += [lambda r: f(r.f1), lambda r: f(r.brier, 4)]
    noms += ["F1 au seuil", "Brier"]
    return tableau(t.sort_values(["scenario", "modele"], ascending=[True, False]), cols, noms)


def concordance_resume():
    p = ROOT / "reports" / "tables" / "concordance.csv"
    if not p.exists():
        return "Le tableau de concordance n'a pas encore ete genere (notebook 02)."
    c = pd.read_csv(p)
    ok = (c.statut == "OK").sum()
    txt = f"{ok} indicateurs sur {len(c)} concordent entre le rapport et le code."
    ec = c[c.statut != "OK"]
    if len(ec):
        txt += " Ecarts : " + ", ".join(f"{r.indicateur} (rapport {r.rapport}, code {r.code})" for r in ec.itertuples()) + "."
    return txt


def lecture(res):
    t = res[(res.population == "population_principale") & (res.partition == "test")].set_index(["modele", "scenario"])
    pts = []
    xa, xb = t.loc[("XGBoost", "A")], t.loc[("XGBoost", "B")]
    pts.append(f"Avec le solde de l'emetteur (scenario A), XGBoost obtient une AP de {f(xa.ap)} sur le test, contre {f(xb.ap)} sans solde (scenario B). L'ecart de {f(xa.ap - xb.ap)} mesure le poids du raccourci montant egal au solde. C'est une propriete du simulateur, pas une preuve de detection realiste.")
    for s in ["A", "B"]:
        x, l = t.loc[("XGBoost", s)], t.loc[("RegLog", s)]
        sens = "au dessus de" if x.ap > l.ap else "au niveau ou en dessous de"
        pts.append(f"Scenario {s} : XGBoost ({f(x.ap)}) est {sens} la regression logistique ({f(l.ap)}).")
    pts.append(f"Dans le scenario B, l'AP de XGBoost vaut {f(xb.ratio_ap_taux, 1)} fois le hasard. C'est la reference que E1 et E2 devront depasser grace a l'information relationnelle.")
    s31 = res[(res.population == "population_principale") & (res.partition == "test_sans_jour31") & (res.modele == "XGBoost")].set_index("scenario")
    for s in ["A", "B"]:
        pts.append(f"Sans le jour 31, l'AP de XGBoost en scenario {s} passe de {f(t.loc[('XGBoost', s)].ap)} a {f(s31.loc[s].ap)} (taux de fraude {pct(s31.loc[s].taux_pct)}).")
    return "\n".join(f"{i}. {p}" for i, p in enumerate(pts, 1))


def main():
    res = pd.read_csv(E0 / "resultats_e0.csv")
    choix = json.loads((E0 / "config_choisie.json").read_text())
    pj = pd.read_csv(E0 / "ap_par_jour_test.csv")
    prin = res[res.population == "population_principale"]
    sec = res[res.population == "population_secondaire"]

    hp = pd.DataFrame([{"scenario": s, **p} for s, p in choix.items()])
    t_hp = tableau(hp, ["scenario", "desequilibre", lambda r: str(int(r.lignes_train)), lambda r: str(int(r.max_depth)), lambda r: f(r.learning_rate, 2),
                        lambda r: f(r.scale_pos_weight, 1), lambda r: str(int(r.n_arbres)), lambda r: f(r.ap_val)],
                   ["Scenario", "Desequilibre", "Lignes d'entrainement", "Profondeur", "Taux d'apprentissage",
                    "scale_pos_weight", "Arbres", "AP validation"])

    sel = []
    for s in ["A", "B"]:
        d = pd.read_csv(E0 / f"selection_{s}_population_principale.csv")
        g = d.groupby("desequilibre").ap_val.max().reset_index().assign(scenario=s)
        sel.append(g)
    t_sel = tableau(pd.concat(sel), ["scenario", "desequilibre", lambda r: f(r.ap_val)],
                    ["Scenario", "Strategie", "Meilleure AP validation"])

    shap = []
    for s in ["A", "B"]:
        sh = pd.read_csv(E0 / f"shap_{s}_population_principale.csv", index_col=0).iloc[:, 0]
        sh = sh[sh > 0].head(5)
        shap.append(f"* Scenario {s} : " + ", ".join(f"{k} ({f(v)})" for k, v in sh.items()))

    pjp = pj[pj.population == "population_principale"]
    jours = pjp.groupby(["scenario", "modele"]).ap.agg(["min", "median", "max"]).reset_index()
    t_jours = tableau(jours, ["scenario", "modele", lambda r: f(r["min"]), lambda r: f(r["median"]), lambda r: f(r["max"])],
                      ["Scenario", "Modele", "AP min", "AP mediane", "AP max"])
    piv = pjp[pjp.modele == "XGBoost"].pivot_table(index=["day", "transactions", "fraudes", "taux_pct"], columns="scenario", values="ap").reset_index()
    t_piv = tableau(piv, [lambda r: str(int(r.day)), lambda r: str(int(r.transactions)), lambda r: str(int(r.fraudes)), lambda r: pct(r.taux_pct, 2), lambda r: f(r.get("A")), lambda r: f(r.get("B"))],
                    ["Jour", "Transactions", "Fraudes", "Taux", "AP XGBoost A", "AP XGBoost B"])

    couts = prin[prin.partition == "test"]
    t_couts = tableau(couts.sort_values(["scenario", "modele"]), ["modele", "scenario", lambda r: f(r.temps_fit_s, 1),
                                                                   lambda r: f(r.latence_ms_1000tx, 2), lambda r: f(r.taille_modele_ko, 0) if r.modele == "XGBoost" else "n/a"],
                      ["Modele", "Scenario", "Entrainement (s)", "Latence pour 1000 tx (ms)", "Taille (Ko)"])

    seuils = prin[prin.partition == "test"].sort_values(["scenario", "modele"])
    t_conf = tableau(seuils, ["modele", "scenario", lambda r: f(r.seuil, 4), "tp", "fp", "fn", "tn", lambda r: f(r.precision), lambda r: f(r.rappel)],
                     ["Modele", "Scenario", "Seuil (fixe sur validation)", "VP", "FP", "FN", "VN", "Precision", "Rappel"])

    txt = f"""# Note d'avancement S3 : reference E0 (XGBoost transactionnel)

PFA 06, Kenza EZZAHED et Oumnia EL FATIMI, encadrant Pr. Mohammed MESTARI. Genere le {date.today().strftime('%d/%m/%Y')} par `src/rapport_s3.py` a partir des sorties du notebook `03_e0_xgboost.ipynb`.

## 1. Objet

Cette semaine couvre les recommandations R4 (deux scenarios de variables tires d'un contrat unique) et R5 (baseline E0 competitive). Elle s'appuie sur le protocole gele en fin de S2 (`docs/fiche_protocole.md`).

Controle de l'audit (R1) : {concordance_resume()}

## 2. Protocole applique

* Population principale : TRANSFER et CASH_OUT. Population secondaire : tous les types, avec les memes hyperparametres.
* Decoupage : steps 1 a 445 (entrainement), 446 a 594 (validation), 595 a 743 (test). Le test n'a ete utilise qu'une fois, apres le choix des hyperparametres et du seuil.
* Scenario A : `type`, `amount`, `oldbalanceOrg`, plus deux variables derivees declarees dans `configs/variables.json` et calculees uniquement a partir de ces colonnes (`oldbalanceOrg - amount` et `amount / (oldbalanceOrg + 1)`). Scenario B : `type` et `amount`. Aucun solde posterieur, ni `step`, ni `isFlaggedFraud`, ni identifiant de compte (verifie par `tests/test_features.py`).
* Desequilibre : quatre strategies comparees sur la validation, soit le ratio naturel avec `scale_pos_weight`, soit un sous echantillonnage des transactions normales de l'entrainement jusqu'a 1 %, 5 % ou 10 % de fraudes (graine {CFG['seed']}). On n'a jamais combine les deux. La validation et le test gardent leur distribution naturelle.
* Grille : profondeur {CFG['max_depth']}, taux d'apprentissage {CFG['learning_rate']}, jusqu'a {CFG['n_estimators_max']} arbres avec arret precoce ({CFG['early_stopping_rounds']} tours) sur l'AP de validation, subsample {CFG['subsample']}.
* Reference simple : regression logistique (log signe, standardisation, `class_weight="balanced"`) sur les memes variables.
* Seuil : choisi sur la validation pour produire en moyenne {CFG['budget_seuil_K']} alertes par jour, puis gele pour le test.
* Budget d'alertes : K = {', '.join(map(str, KS))} alertes par jour simule. P@K et R@K sont agreges sur les jours de la partition.

## 3. Hyperparametres retenus (validation)

{t_hp}

Meilleure AP de validation par strategie de desequilibre :

{t_sel}

## 4. Resultats principaux : TRANSFER et CASH_OUT

### Test (jour 31 inclus, resultat principal)

{bloc_metriques(prin[prin.partition == 'test'])}

### Validation

{bloc_metriques(prin[prin.partition == 'val'])}

### Matrices de confusion sur le test, au seuil fixe sur la validation

{t_conf}

## 5. Resultats diagnostiques

### Test sans le jour 31

{bloc_metriques(prin[prin.partition == 'test_sans_jour31'])}

### Population secondaire (tous les types), test

{bloc_metriques(sec[sec.partition == 'test'])}

## 6. Stabilite jour par jour sur le test

{t_jours}

{t_piv}

Les jours sans fraude ou sans transaction normale (comme le jour 31) n'ont pas d'AP definie.

## 7. Variables qui pesent dans le score

Moyenne des valeurs SHAP absolues de XGBoost sur un echantillon d'entrainement :

{chr(10).join(shap)}

Ces valeurs decrivent le modele, elles ne disent pas pourquoi une transaction est frauduleuse.

## 8. Calibration

Le score de Brier est dans les tableaux, et les courbes de fiabilite sont dans `reports/e0/fiabilite_*.png`. Quand l'entrainement est sous echantillonne, les scores ne sont plus des probabilites realistes : ils surestiment le risque. Le classement (AP, P@K) n'en depend pas. Une calibration sur la validation sera etudiee a part (R11), en tenant compte du changement de taux de fraude entre validation et test.

## 9. Couts

{t_couts}

## 10. Lecture des resultats

{lecture(res)}

## 11. Limites

* PaySim est synthetique : les resultats ne disent rien de l'efficacite sur une vraie banque.
* Le scenario A repose en grande partie sur une regle du simulateur.
* L'entrainement est dans la periode chargee, la validation et le test dans la periode calme : le modele est evalue dans un autre regime que celui ou il a appris.
* Pas encore d'intervalles de confiance par blocs temporels (prevu en S8).

## 12. Suite (S4)

Construction causale du graphe historique G<t et des agregats de E1 (R6) : degres entrants et sortants, partenaires distincts, montants cumules, fenetres 24 h et 72 h, indicateur d'historique absent. Mesure des degres reellement disponibles au moment de la decision (R7).

## 13. Fichiers de preuve

* Code : `src/features.py`, `src/e0.py`, `src/rapport_s3.py`, `notebooks/03_e0_xgboost.ipynb`
* Contrat et configuration : `configs/variables.json`, `configs/e0.json`, `reports/e0/config_choisie.json`
* Modeles : `models/e0_xgb_*.json`
* Resultats : `reports/e0/resultats_e0.csv`, `reports/e0/selection_*.csv`, `reports/e0/ap_par_jour_test.csv`, `reports/e0/shap_*.csv`
* Figures : `reports/e0/pr_*.png`, `reports/e0/fiabilite_*.png`
* Tests : `tests/test_protocol.py`, `tests/test_features.py`, `tests/test_concordance.py`
"""
    dest = ROOT / "docs" / "note_s3_E0.md"
    dest.write_text(txt)
    return dest


if __name__ == "__main__":
    print(main())
