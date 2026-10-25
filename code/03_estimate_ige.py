"""Estimate the IGE with single-year and multi-year income; save tables and figures."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import *
from ige import connect, run_sql, estimate_ige

con = connect()

# Benchmark from the simulation's latent truth (not available with real data)
truth = pd.read_csv(RAW / "truth.csv").dropna()
b = np.polyfit(truth["theta_parent"], truth["theta_child"], 1)[0]
print(f"Benchmark: permanent-income slope in the simulation = {b:.3f}")

# ---------------- Table 1: headline comparison ----------------
rows = []
def add(label, df):
    r = estimate_ige(df); r["spec"] = label; rows.append(r)

add("Single year: child age 28, parent (head) age 40",
    run_sql(con, "single_year.sql", child_age=28, parent_age=40))
add("Single year: child age 35, parent (head) age 45",
    run_sql(con, "single_year.sql", child_age=35, parent_age=45))
add("Single year: child age 40, parent (head) age 50",
    run_sql(con, "single_year.sql", child_age=40, parent_age=50))
add("5-year averages: child ages 33-37, parent ages 43-47",
    run_sql(con, "multi_year.sql", c_lo=33, c_hi=37, min_c=4, p_lo=43, p_hi=47, min_p=4))
add("Long-run: child ages 30-45, parent ages 40-55",
    run_sql(con, "multi_year.sql", c_lo=30, c_hi=45, min_c=12, p_lo=40, p_hi=55, min_p=12))

t1 = pd.DataFrame(rows)[["spec", "ige", "se", "n"]]
t1["ci_low"] = t1["ige"] - 1.96 * t1["se"]
t1["ci_high"] = t1["ige"] + 1.96 * t1["se"]
t1.round(3).to_csv(TABLES / "ige_headline.csv", index=False)
print(t1.round(3).to_string(index=False))

# ---------------- Life-cycle bias, figure 1: vary the CHILD's age ----------------
# Parent side held fixed in each line; only the age at which the child is observed changes.
res = []
for a in range(23, 44):
    s = estimate_ige(run_sql(con, "single_year.sql", child_age=a, parent_age=45))
    m = estimate_ige(run_sql(con, "multi_year.sql", c_lo=a - 2, c_hi=a + 2, min_c=4,
                             p_lo=40, p_hi=55, min_p=12))
    res.append({"child_age": a, "single_ige": s["ige"], "single_se": s["se"],
                "multi_ige": m["ige"], "multi_se": m["se"]})
r1 = pd.DataFrame(res); r1.round(4).to_csv(TABLES / "ige_by_child_age.csv", index=False)

fig, ax = plt.subplots(figsize=(7.5, 4.5))
for k, lab, c in [("single", "Single-year income (parents at age 45)", "tab:red"),
                  ("multi", "Multi-year average (child: 5-yr window; parents: ages 40-55)", "tab:blue")]:
    ax.plot(r1["child_age"], r1[f"{k}_ige"], color=c, label=lab, lw=2)
    ax.fill_between(r1["child_age"], r1[f"{k}_ige"] - 1.96 * r1[f"{k}_se"],
                    r1[f"{k}_ige"] + 1.96 * r1[f"{k}_se"], color=c, alpha=0.15)
ax.axhline(TRUE_IGE, color="k", ls="--", lw=1, label=f"Built-in permanent-income IGE = {TRUE_IGE}")
ax.set_xlabel("Child's age when income is measured"); ax.set_ylabel("Estimated IGE")
ax.set_title("Life-cycle bias: measuring children too young understates the IGE")
ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)
fig.savefig(FIGS / "fig1_ige_by_child_age.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------------- Life-cycle bias, figure 2: vary the PARENT's age ----------------
res = []
for a in range(32, 57):
    s = estimate_ige(run_sql(con, "single_year.sql", child_age=38, parent_age=a))
    m = estimate_ige(run_sql(con, "multi_year.sql", c_lo=33, c_hi=43, min_c=8,
                             p_lo=a - 2, p_hi=a + 2, min_p=4))
    res.append({"parent_age": a, "single_ige": s["ige"], "single_se": s["se"],
                "multi_ige": m["ige"], "multi_se": m["se"]})
r2 = pd.DataFrame(res); r2.round(4).to_csv(TABLES / "ige_by_parent_age.csv", index=False)

fig, ax = plt.subplots(figsize=(7.5, 4.5))
for k, lab, c in [("single", "Single-year parent income (child at age 38)", "tab:red"),
                  ("multi", "5-year average parent income (child: ages 33-43 average)", "tab:blue")]:
    ax.plot(r2["parent_age"], r2[f"{k}_ige"], color=c, label=lab, lw=2)
    ax.fill_between(r2["parent_age"], r2[f"{k}_ige"] - 1.96 * r2[f"{k}_se"],
                    r2[f"{k}_ige"] + 1.96 * r2[f"{k}_se"], color=c, alpha=0.15)
ax.axhline(TRUE_IGE, color="k", ls="--", lw=1, label=f"Built-in permanent-income IGE = {TRUE_IGE}")
ax.set_xlabel("Parent (head) age when income is measured"); ax.set_ylabel("Estimated IGE")
ax.set_title("Life-cycle bias also arises when parents are measured early")
ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.3)
fig.savefig(FIGS / "fig2_ige_by_parent_age.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------------- Figure 3: why averaging helps (attenuation) ----------------
rel = []
for n_years in [1, 3, 5, 10, 15]:
    lo = 40; hi = lo + n_years - 1
    df = run_sql(con, "multi_year.sql", c_lo=36, c_hi=44, min_c=7,
                 p_lo=lo, p_hi=hi, min_p=n_years)
    r = estimate_ige(df); r["years_averaged"] = n_years; rel.append(r)
r3 = pd.DataFrame(rel)[["years_averaged", "ige", "se", "n"]]
r3.round(4).to_csv(TABLES / "ige_by_years_averaged.csv", index=False)
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.errorbar(r3["years_averaged"], r3["ige"], yerr=1.96 * r3["se"], marker="o", capsize=3, color="tab:blue")
ax.axhline(TRUE_IGE, color="k", ls="--", lw=1)
ax.set_xlabel("Number of years of parent income averaged (starting at head age 40)")
ax.set_ylabel("Estimated IGE"); ax.set_title("Averaging more years reduces attenuation bias")
ax.grid(alpha=0.3)
fig.savefig(FIGS / "fig3_ige_by_years_averaged.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print(r3.round(3).to_string(index=False))
con.close()
