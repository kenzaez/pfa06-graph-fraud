import numpy as np
import pandas as pd

FENETRE = 24

NOMS = [
    "g_orig_sortant_n", "g_orig_sortant_somme", "g_orig_entrant_n", "g_orig_entrant_somme",
    "g_orig_sortant_n24", "g_orig_entrant_n24", "g_orig_contreparties_dist", "g_orig_ecart_dernier",
    "g_dest_entrant_n", "g_dest_entrant_somme", "g_dest_sortant_n", "g_dest_sortant_somme",
    "g_dest_entrant_n24", "g_dest_sortant_n24", "g_dest_contreparties_dist", "g_dest_ecart_dernier",
    "g_paire_n", "g_orig_a_historique", "g_dest_a_historique",
]


def table_cumulee(acct, step, valeurs):
    d = pd.DataFrame({"acct": acct, "step": step, **valeurs})
    g = d.groupby(["acct", "step"], sort=False).sum().reset_index().sort_values(["step", "acct"], kind="stable")
    cols = list(valeurs)
    g[cols] = g.sort_values(["acct", "step"], kind="stable").groupby("acct")[cols].cumsum().reindex(g.index)
    return g.sort_values("step", kind="stable").reset_index(drop=True)


def avant(acct, t, table, cols):
    gauche = pd.DataFrame({"acct": acct, "t": t})
    r = pd.merge_asof(gauche, table, left_on="t", right_on="step", by="acct", allow_exact_matches=False)
    return {c: r[c].to_numpy() for c in cols}


def caracteristiques(df):
    e = df[["step", "nameOrig", "nameDest", "amount"]].copy()
    codes, _ = pd.factorize(pd.concat([e.nameOrig, e.nameDest], ignore_index=True))
    n = len(e)
    o, d = codes[:n].astype(np.int64), codes[n:].astype(np.int64)
    step = e.step.to_numpy().astype(np.int64)
    amount = e.amount.to_numpy().astype(float)
    ordre = np.argsort(step, kind="stable")
    inv = np.empty(n, dtype=np.int64)
    inv[ordre] = np.arange(n)
    o, d, step, amount = o[ordre], d[ordre], step[ordre], amount[ordre]
    un = np.ones(n)

    sortant = table_cumulee(o, step, {"n": un, "s": amount})
    entrant = table_cumulee(d, step, {"n": un, "s": amount})
    pair = o * (codes.max() + 1) + d
    pairs_premiere = pd.DataFrame({"pair": pair, "step": step, "o": o, "d": d}).groupby("pair", sort=False).agg(
        step=("step", "min"), o=("o", "first"), d=("d", "first")).reset_index()
    dist_o = table_cumulee(pairs_premiere.o.to_numpy(), pairs_premiere.step.to_numpy(), {"n": np.ones(len(pairs_premiere))})
    dist_d = table_cumulee(pairs_premiere.d.to_numpy(), pairs_premiere.step.to_numpy(), {"n": np.ones(len(pairs_premiere))})
    tab_pair = table_cumulee(pair, step, {"n": un})
    tous = pd.concat([pd.DataFrame({"acct": o, "step": step}), pd.DataFrame({"acct": d, "step": step})])
    tous = tous.groupby("acct").step.agg(list)
    derniere = pd.concat([pd.DataFrame({"acct": o, "step": step}), pd.DataFrame({"acct": d, "step": step})])
    derniere = derniere.groupby(["acct", "step"], sort=False).size().reset_index(name="c")
    derniere["dernier"] = derniere["step"]
    derniere = derniere.sort_values("step", kind="stable").reset_index(drop=True)

    def val(acct, t, tab, c):
        v = avant(acct, t, tab, [c])[c]
        return np.nan_to_num(v, nan=0.0)

    f = {}
    for role, acct in [("orig", o), ("dest", d)]:
        f[f"g_{role}_sortant_n"] = val(acct, step, sortant, "n")
        f[f"g_{role}_sortant_somme"] = val(acct, step, sortant, "s")
        f[f"g_{role}_entrant_n"] = val(acct, step, entrant, "n")
        f[f"g_{role}_entrant_somme"] = val(acct, step, entrant, "s")
        f[f"g_{role}_sortant_n24"] = f[f"g_{role}_sortant_n"] - val(acct, step - FENETRE, sortant, "n")
        f[f"g_{role}_entrant_n24"] = f[f"g_{role}_entrant_n"] - val(acct, step - FENETRE, entrant, "n")
        f[f"g_{role}_contreparties_dist"] = val(acct, step, dist_o if role == "orig" else dist_d, "n")
        dern = avant(acct, step, derniere, ["dernier"])["dernier"]
        f[f"g_{role}_ecart_dernier"] = step - dern
        f[f"g_{role}_a_historique"] = (f[f"g_{role}_sortant_n"] + f[f"g_{role}_entrant_n"] > 0).astype(float)
    f["g_paire_n"] = val(pair, step, tab_pair, "n")
    out = pd.DataFrame({k: f[k][inv] for k in NOMS}, index=df.index)
    return out


def ajouter(df):
    g = caracteristiques(df)
    return pd.concat([df.drop(columns=[c for c in NOMS if c in df.columns]), g], axis=1)
