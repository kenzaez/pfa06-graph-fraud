import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import graphe_causal as g


def jeu(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    step = np.sort(rng.integers(1, 744, n))
    return pd.DataFrame({
        "step": step,
        "nameOrig": [f"C{x}" for x in rng.integers(0, 400, n)],
        "nameDest": [f"M{x}" if x % 3 else f"C{x}" for x in rng.integers(0, 400, n)],
        "amount": np.exp(rng.normal(8, 1.5, n)),
        "isFraud": rng.integers(0, 2, n),
    })


def egal(a, b):
    pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-9, atol=1e-9)


def test_evenement_futur_sans_effet_sur_le_passe():
    df = jeu()
    complet = g.caracteristiques(df)
    for T in [100, 445, 594]:
        coupe = df[df.step <= T]
        egal(g.caracteristiques(coupe), complet.loc[coupe.index])


def test_frontieres_partitions():
    df = jeu()
    complet = g.caracteristiques(df)
    for premier in [446, 595]:
        avant_ = df[df.step < premier]
        a_partir = df[df.step >= premier]
        recalcul = g.caracteristiques(pd.concat([avant_, a_partir[a_partir.step == a_partir.step.min()]]))
        lignes = a_partir[a_partir.step == a_partir.step.min()].index
        egal(recalcul.loc[lignes], complet.loc[lignes])


def test_permutation_des_lignes_et_meme_step():
    df = jeu()
    base = g.caracteristiques(df)
    melange = df.sample(frac=1, random_state=5)
    egal(g.caracteristiques(melange).sort_index(), base.sort_index())


def test_etiquettes_jamais_utilisees():
    df = jeu()
    base = g.caracteristiques(df)
    autre = df.assign(isFraud=1 - df.isFraud)
    egal(g.caracteristiques(autre), base)
    egal(g.caracteristiques(df.drop(columns=["isFraud"])), base)


def test_compte_nouveau_sans_historique_et_arete_cible_exclue():
    df = pd.DataFrame({"step": [5], "nameOrig": ["C1"], "nameDest": ["C2"], "amount": [100.0]})
    f = g.caracteristiques(df)
    assert (f.drop(columns=["g_orig_ecart_dernier", "g_dest_ecart_dernier"]) == 0).all().all()
    assert f[["g_orig_ecart_dernier", "g_dest_ecart_dernier"]].isna().all().all()


def test_petite_trajectoire_a_la_main():
    df = pd.DataFrame({
        "step": [1, 2, 2, 30, 30],
        "nameOrig": ["A", "A", "B", "A", "C"],
        "nameDest": ["B", "B", "A", "B", "A"],
        "amount": [10.0, 20.0, 5.0, 40.0, 7.0],
    })
    f = g.caracteristiques(df)
    assert f.loc[0, "g_orig_sortant_n"] == 0
    assert f.loc[1, "g_orig_sortant_n"] == 1 and f.loc[1, "g_orig_sortant_somme"] == 10
    assert f.loc[1, "g_paire_n"] == 1
    assert f.loc[2, "g_orig_entrant_n"] == 1 and f.loc[2, "g_orig_entrant_somme"] == 10 and f.loc[2, "g_orig_sortant_n"] == 0
    assert f.loc[2, "g_dest_sortant_n"] == 1
    assert f.loc[3, "g_orig_sortant_n"] == 2 and f.loc[3, "g_orig_sortant_somme"] == 30
    assert f.loc[3, "g_orig_entrant_n"] == 1 and f.loc[3, "g_orig_entrant_somme"] == 5
    assert f.loc[3, "g_orig_sortant_n24"] == 0 and f.loc[3, "g_orig_entrant_n24"] == 0
    assert f.loc[3, "g_orig_ecart_dernier"] == 28
    assert f.loc[3, "g_orig_contreparties_dist"] == 1
    assert f.loc[3, "g_paire_n"] == 2
    assert f.loc[4, "g_orig_a_historique"] == 0 and f.loc[4, "g_dest_entrant_n"] == 1
