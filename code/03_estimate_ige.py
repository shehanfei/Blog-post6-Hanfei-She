"""Estimate the IGE with single-year (BASE_YEAR) and multi-year income; save tables and figures."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import *
from ige import connect, run_sql, estimate_ige

con = connect()
B = BASE_YEAR

truth = pd.read_csv(RAW / "truth.csv").dropna()
bench = np.polyfit(truth["theta_parent"], truth["theta_child"], 1)[0]
print(f"Benchmark: permanent-income slope in the simulation = {bench:.3f}")


def single(a_lo, a_hi):
    return run_sql(con, "single_year.sql", year=B, a_lo=a_lo, a_hi=a_hi)


def multi(a_lo, a_hi, n_years):
    y_hi = B + n_years - 1
    return run_sql(con, "multi_year.sql", base_year=B, y_lo=B, y_hi=y_hi, a_lo=a_lo, a_hi=a_hi,
                   min_c=max(1, int(0.8 * n_years)), min_p=max(1, int(0.8 * n_years)))


# ---------------- Table 1: headline comparison ----------------
rows = []
for lab, df in [
    (f"Single year ({B}), children aged 25-29", single(25, 29)),
    (f"Single year ({B}), children aged 30-34", single(30, 34)),
    (f"Single year ({B}), children aged 35-39", single(35, 39)),
    (f"5-year average ({B}-{B+4}), children aged 30-34", multi(30, 34, 5)),
    (f"10-year average ({B}-{B+9}), children aged 30-34", multi(30, 34, 10)),
    (f"10-year average ({B}-{B+9}), children aged 35-39", multi(35, 39, 10)),
]:
    r = estimate_ige(df); r["spec"] = lab; rows.append(r)
t1 = pd.DataFrame(rows)[["spec", "ige", "se", "n"]]
t1["ci_low"] = t1["ige"] - 1.96 * t1["se"]; t1["ci_high"] = t1["ige"] + 1.96 * t1["se"]
t1.round(3).to_csv(TABLES / "ige_headline.csv", index=False)
print(t1.round(3).to_string(index=False))

# ---------------- Figure 1: life-cycle bias = IGE by child's age in the base year ----------------
res = []
for a in range(26, 38):
    s = estimate_ige(single(a - 2, a + 2))
    m = estimate_ige(multi(a - 2, a + 2, 10))
    res.append({"child_age": a, "single_ige": s["ige"], "single_se": s["se"], "single_n": s["n"],
                "multi_ige": m["ige"], "multi_se": m["se"], "multi_n": m["n"]})
r1 = pd.DataFrame(res); r1.round(4).to_csv(TABLES / "ige_by_child_age.csv", index=False)

fig, ax = plt.subplots(figsize=(7.5, 4.5))
for k, lab, c in [("single", f"Single-year income ({B})", "tab:red"),
                  ("multi", f"10-year average income ({B}-{B+9})", "tab:blue")]:
    ax.plot(r1["child_age"], r1[f"{k}_ige"], color=c, label=lab, lw=2)
    ax.fill_between(r1["child_age"], r1[f"{k}_ige"] - 1.96 * r1[f"{k}_se"],
                    r1[f"{k}_ige"] + 1.96 * r1[f"{k}_se"], color=c, alpha=0.15)
ax.axhline(TRUE_IGE, color="k", ls="--", lw=1, label=f"Built-in permanent-income IGE = {TRUE_IGE}")
ax.set_xlabel(f"Child's age in {B} (center of a 5-age group)"); ax.set_ylabel("Estimated IGE")
ax.set_title("Life-cycle bias: children observed young give a lower IGE")
ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)
fig.savefig(FIGS / "fig1_ige_by_child_age.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------------- Figure 2: averaging more years (children aged 35-39 in base year) ----------------
rel = []
for k in [1, 2, 3, 5, 7, 10]:
    r = estimate_ige(multi(35, 39, k)); r["years_averaged"] = k; rel.append(r)
r2 = pd.DataFrame(rel)[["years_averaged", "ige", "se", "n"]]
r2.round(4).to_csv(TABLES / "ige_by_years_averaged.csv", index=False)
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.errorbar(r2["years_averaged"], r2["ige"], yerr=1.96 * r2["se"], marker="o", capsize=3, color="tab:blue")
ax.axhline(TRUE_IGE, color="k", ls="--", lw=1)
ax.set_xlabel(f"Years of income averaged (starting {B}), both generations")
ax.set_ylabel("Estimated IGE"); ax.set_title("Averaging more years reduces attenuation bias")
ax.grid(alpha=0.3)
fig.savefig(FIGS / "fig2_ige_by_years_averaged.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print(r2.round(3).to_string(index=False))
print(r1.round(3).to_string(index=False))
con.close()
