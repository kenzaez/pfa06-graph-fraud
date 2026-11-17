import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPLITS = json.loads((ROOT / "configs" / "splits.json").read_text())
SEUIL_REGIME = 200_000


def label_partition(step, bornes):
    (_, t1), (_, v1), _ = bornes
    return pd.Series(np.select([step <= t1, step <= v1], ["train", "val"], "test"), index=step.index)


def bornes_ref():
    return [SPLITS["train"], SPLITS["val"], SPLITS["test"]]


def bornes_volume(df, q1=0.6, q2=0.8):
    cum = df.groupby("step").size().cumsum() / len(df)
    s1 = int(cum[cum >= q1].index[0])
    s2 = int(cum[cum >= q2].index[0])
    smax = int(df.step.max())
    return [[1, s1], [s1 + 1, s2], [s2 + 1, smax]]


def table_jour(df):
    df = df.assign(day=(df.step - 1) // 24 + 1)
    sc = df.type.isin(SPLITS["scoring_types"])
    tous = df.groupby("day").isFraud.agg(tx_tous="size", fraudes_tous="sum")
    scor = df[sc].groupby("day").isFraud.agg(tx_scoring="size", fraudes_scoring="sum")
    t = tous.join(scor, how="left").fillna(0).astype(int)
    t["taux_tous_pct"] = t.fraudes_tous / t.tx_tous * 100
    t["taux_scoring_pct"] = t.fraudes_scoring / t.tx_scoring.replace(0, np.nan) * 100
    part = label_partition(df.step, bornes_ref())
    parts = part.groupby(df.day).agg(lambda s: "/".join(sorted(s.unique(), key=["train", "val", "test"].index)))
    t.insert(0, "partition", parts)
    t["regime"] = np.where(t.tx_tous >= SEUIL_REGIME, "charge", "calme")
    med = t.taux_scoring_pct.median()
    t["atypique"] = (t.taux_scoring_pct >= 100) | (t.taux_scoring_pct > 10 * med)
    for k in SPLITS["alert_budget"]["K"]:
        t[f"budget_{k}_depasse"] = t.tx_scoring < k
    return t.reset_index().rename(columns={"day": "jour"})


def table_partitions(df, bornes, nom):
    sc = df.type.isin(SPLITS["scoring_types"])
    part = label_partition(df.step, bornes)
    rows = []
    for pop, m in [("tous_types", pd.Series(True, index=df.index)), ("transfer_cashout", sc)]:
        for p, (a, b) in zip(["train", "val", "test"], bornes):
            mm = m & (part == p)
            n, f = int(mm.sum()), int(df.loc[mm, "isFraud"].sum())
            rows.append({
                "decoupage": nom, "population": pop, "partition": p,
                "steps": f"{a} a {b}", "transactions": n, "fraudes": f,
                "taux_pct": f / n * 100 if n else np.nan,
            })
    out = pd.DataFrame(rows)
    out["ap_hasard"] = out.taux_pct / 100
    return out


def test_sans_jour31(df):
    te = df[(df.step >= SPLITS["test"][0]) & ((df.step - 1) // 24 + 1 < 31)]
    sc = te.type.isin(SPLITS["scoring_types"])
    rows = []
    for pop, d in [("tous_types", te), ("transfer_cashout", te[sc])]:
        rows.append({"population": pop, "transactions": len(d), "fraudes": int(d.isFraud.sum()),
                     "taux_pct": d.isFraud.mean() * 100})
    return pd.DataFrame(rows)


def figure(t, path):
    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    ax1.bar(t.jour, t.tx_tous, color="lightsteelblue", label="transactions (tous types)")
    ax1.set_ylabel("transactions")
    ax2 = ax1.twinx()
    ax2.plot(t.jour, t.fraudes_tous, color="crimson", marker="o", label="fraudes")
    ax2.set_ylabel("fraudes", color="crimson")
    ax3.plot(t.jour, t.taux_tous_pct, marker="o", label="tous types")
    ax3.plot(t.jour, t.taux_scoring_pct, marker="s", label="TRANSFER + CASH_OUT")
    ax3.set_yscale("log")
    ax3.set_ylabel("taux de fraude (%) echelle log")
    ax3.set_xlabel("jour simule")
    ax3.legend()
    for ax in (ax1, ax3):
        for s in (SPLITS["train"][1], SPLITS["val"][1]):
            ax.axvline(s / 24 + 0.5, ls="--", color="gray")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


def main(df):
    tab = ROOT / "reports" / "tables"
    figs = ROOT / "reports" / "figures"
    tab.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    t = table_jour(df)
    t.to_csv(tab / "prevalence_par_jour.csv", index=False)
    ref = table_partitions(df, bornes_ref(), "heures_60_20_20_reference")
    ref.to_csv(tab / "prevalence_par_partition.csv", index=False)
    sens = pd.concat([
        ref,
        table_partitions(df, SPLITS["sensibilite_diagnostique"]["heures_70_15_15"], "heures_70_15_15_diagnostic"),
        table_partitions(df, bornes_volume(df), "volume_60_20_20_diagnostic"),
    ])
    sens.to_csv(tab / "sensibilite_decoupage.csv", index=False)
    sj = test_sans_jour31(df)
    sj.to_csv(tab / "test_sans_jour31.csv", index=False)
    figure(t, figs / "prevalence_par_jour.png")
    return t, ref, sens, sj


if __name__ == "__main__":
    from src.audit import load

    res = main(load(sys.argv[1]))
    for r in res:
        print(r.to_string(index=False))
        print()
