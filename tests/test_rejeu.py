import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import ablation, e0, rejeu


def jeu(n=24000, seed=1):
    rng = np.random.default_rng(seed)
    step = rng.integers(1, 744, n)
    type_ = rng.choice(["TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"], n, p=[.3, .3, .2, .15, .05])
    amount = np.exp(rng.normal(9, 1.5, n))
    solde = amount * rng.uniform(0.5, 3, n)
    fraude = (np.isin(type_, ["TRANSFER", "CASH_OUT"])) & (rng.random(n) < 0.05)
    solde = np.where(fraude, amount, solde)
    return pd.DataFrame({
        "step": step, "type": type_, "amount": amount, "nameOrig": [f"C{i}" for i in range(n)],
        "oldbalanceOrg": solde, "newbalanceOrig": solde - amount, "nameDest": [f"C{i % 500}" for i in range(n)],
        "oldbalanceDest": 0.0, "newbalanceDest": 0.0, "isFraud": fraude.astype(int), "isFlaggedFraud": 0,
    })


def test_topk_depart_deterministe_et_k_borne():
    d = pd.DataFrame({"day": [1] * 5 + [2] * 3, "y": [1, 0, 1, 0, 0, 1, 1, 1],
                      "score": [.5, .5, .5, .1, .1, .9, .8, .7]}, index=[10, 11, 12, 13, 14, 20, 21, 22])
    t = e0.topk_par_jour(d, 4)
    j1 = t[t.day == 1].iloc[0]
    assert j1.alertes == 4 and j1.fraudes_detectees == 2
    j2 = t[t.day == 2].iloc[0]
    assert j2.alertes == 3 and bool(j2.budget_depasse)
    d2 = d.sample(frac=1, random_state=3)
    t2 = e0.topk_par_jour(d2, 4)
    assert t.fraudes_detectees.tolist() == t2.fraudes_detectees.tolist()


def test_chaine_complete(tmp_path, monkeypatch):
    sortie = tmp_path / "e0"
    modeles = tmp_path / "models"
    sortie.mkdir()
    modeles.mkdir()
    monkeypatch.setattr(e0, "OUT", sortie)
    monkeypatch.setattr(e0, "MODELS", modeles)
    monkeypatch.setattr(rejeu, "OUT", sortie)
    monkeypatch.setattr(rejeu, "ROOT", tmp_path)
    df = jeu()
    grille = {"desequilibre": [{"nom": "naturel_spw", "taux_cible": None}, {"nom": "sous_ech_10pct", "taux_cible": 0.1}],
              "max_depth": [4], "learning_rate": [0.1]}
    tab, pj, choix = e0.main(df, grille=grille)
    tailles = tab[tab.partition == "test"].groupby(["scenario", "population", "modele"]).taille_modele_ko.first()
    assert (tailles > 0).all()
    assert tailles.loc[("B", "population_principale", "RegLog")] != tailles.loc[("B", "population_principale", "XGBoost")]
    assert len(list(sortie.glob("predictions_*.csv.gz"))) == 4
    diag = rejeu.diagnostics()
    assert set(diag) >= {"topk_quotidien", "sans_un_jour", "calibration", "alertes_seuil"}
    assert diag["topk_quotidien"].jour_partiel.any()
    rejeu_dir = tmp_path / "rejeu"
    (sortie / "config_choisie.json").write_text(__import__("json").dumps(choix, default=float))
    r = rejeu.rejouer(df, rejeu_dir)
    assert r.identique.all()


def test_ablation(tmp_path):
    out = ablation.lancer(jeu(), dossier=tmp_path)
    assert set(out.groupe) == {"type_montant", "solde", "solde_derivees"}
    assert (out.n_variables.groupby(out.groupe).first().sort_values().tolist() == [6, 7, 9])


def test_e1_chaine_et_comparaison(tmp_path, monkeypatch):
    from src import comparaison_e0_e1 as cmp, e1
    sortie0, sortie1 = tmp_path / "e0", tmp_path / "e1"
    for p in (sortie0, sortie1, tmp_path / "m0", tmp_path / "m1"):
        p.mkdir()
    monkeypatch.setattr(e0, "OUT", sortie0)
    monkeypatch.setattr(e0, "MODELS", tmp_path / "m0")
    monkeypatch.setattr(e1, "OUT", sortie1)
    monkeypatch.setattr(e1, "MODELS", tmp_path / "m1")
    monkeypatch.setattr(cmp, "E0", sortie0)
    monkeypatch.setattr(cmp, "E1", sortie1)
    monkeypatch.setattr(cmp, "OUT", tmp_path / "cmp")
    df = jeu()
    grille = {"desequilibre": [{"nom": "sous_ech_10pct", "taux_cible": 0.1}], "max_depth": [4], "learning_rate": [0.1]}
    e0.main(df, grille=grille)
    tab, params = e1.main(df, grille=grille)
    assert set(tab.scenario) == {"E1"}
    from src import graphe_causal
    from src.features import prepare
    res = cmp.main(graphe_causal.ajouter(prepare(df)))
    assert len(res["global"]) > 0 and len(res["par_jour"]) > 0 and len(res["historique"]) > 0
