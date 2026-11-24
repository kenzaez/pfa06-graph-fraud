import json
from pathlib import Path

import pandas as pd

from src import e0, graphe_causal
from src.features import prepare

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "e1"
MODELS = ROOT / "models" / "e1"


def main(df, params_b=None, grille=None):
    OUT.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    ancien = (e0.OUT, e0.MODELS)
    e0.OUT, e0.MODELS = OUT, MODELS
    try:
        d = graphe_causal.ajouter(prepare(df))
        r = e0.evaluer(d, "E1", "population_principale", params=params_b, grille=grille)
        r2 = e0.evaluer(d, "E1", "population_secondaire", params=r["params"])
    finally:
        e0.OUT, e0.MODELS = ancien
    tab = pd.concat([r["metriques"], r2["metriques"]])
    first = ["modele", "scenario", "population", "partition"]
    tab = tab[first + [c for c in tab.columns if c not in first]]
    tab.to_csv(OUT / "resultats_e1.csv", index=False)
    pd.concat([r["par_jour"], r2["par_jour"]]).to_csv(OUT / "ap_par_jour_test_e1.csv", index=False)
    (OUT / "config_choisie_e1.json").write_text(json.dumps(r["params"], indent=2, default=float))
    return tab, r["params"]
