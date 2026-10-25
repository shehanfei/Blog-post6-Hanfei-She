"""Simulate a PSID-style longitudinal file.

WHY SIMULATE? The real PSID requires registration and a data-use agreement, so it cannot be
redistributed in a repository. This script creates two tables with the same structure you would
build from the PSID (an individual-level table with a person ID and a family ID, and a person-year
income table), so every later step works unchanged on real data.

Data-generating process (log income of person i at age a in year t):
    log y_it = mu(a) + lambda(a) * theta_i + u_it
  theta_i  : permanent (long-run) income component
  lambda(a): grows from 0.5 at age 22 to 1.0 at age 40  -> high earners have steeper age-earnings
             profiles (Haider and Solon, 2006). This is what generates life-cycle bias.
  u_it     : AR(1) transitory shock (rho = 0.5, stationary sd = 0.30) -> attenuation bias
  Child theta = TRUE_IGE * parent theta + independent noise.
"""
import numpy as np
import pandas as pd
from config import *

rng = np.random.default_rng(SEED)
SIGMA_THETA, SIGMA_U, RHO = 0.55, 0.30, 0.5


def lam(age):
    """Loading of permanent income on current income: rises from 0.5 (age 22) to 1.0 (age 40)."""
    return np.clip(0.5 + 0.5 * (age - 22) / 18, 0.5, 1.0)


def mu(age):
    """Common age-earnings profile (log dollars)."""
    a = age - 25
    return 10.2 + 0.07 * a - 0.0011 * a**2


def ar1(n_years):
    u = np.zeros(n_years)
    u[0] = rng.normal(0, SIGMA_U)
    for t in range(1, n_years):
        u[t] = RHO * u[t - 1] + rng.normal(0, SIGMA_U * np.sqrt(1 - RHO**2))
    return u


persons, income, truth = [], [], []
pid = 0
years = np.arange(PANEL_START, PANEL_END + 1)

for fam in range(1, N_FAMILIES + 1):
    head_birth = int(rng.integers(1936, 1945))
    theta_f = rng.normal(0, SIGMA_THETA)
    # Roughly 5% of families: parents never enter the data (child-only records) -> unmatched kids
    parents_observed = rng.random() > 0.05

    members = []
    if parents_observed:
        pid += 1; head_id = pid
        persons.append((head_id, fam, "head", head_birth, rng.choice(["M", "F"])))
        pid += 1; spouse_id = pid
        persons.append((spouse_id, fam, "spouse", head_birth + int(rng.integers(-3, 4)), "F"))
        members += [(head_id, "head", head_birth, theta_f), (spouse_id, "spouse", persons[-1][3], 0.8 * theta_f)]

    for _ in range(int(rng.choice([1, 2, 3], p=[0.35, 0.45, 0.20]))):
        pid += 1
        cb = head_birth + int(rng.integers(24, 31))
        persons.append((pid, fam, "offspring", cb, rng.choice(["M", "F"])))
        theta_c = TRUE_IGE * theta_f + rng.normal(0, SIGMA_THETA * np.sqrt(1 - TRUE_IGE**2))
        members.append((pid, "offspring", cb, theta_c))
        truth.append((pid, theta_f if parents_observed else np.nan, theta_c))

    for person_id, role, birth, theta in members:
        u = ar1(len(years))
        for t, yr in enumerate(years):
            age = yr - birth
            if age < 20 or age > 64:
                continue
            if role == "spouse":
                # Spouse works 70% of years; otherwise 0 earnings
                e = np.exp(mu(age) - 0.4 + lam(age) * theta + u[t]) if rng.random() < 0.7 else 0.0
            else:
                e = np.exp(mu(age) + lam(age) * theta + u[t])
            if role == "offspring" and rng.random() < 0.05:
                continue  # missing survey wave -> unbalanced panel
            income.append((person_id, int(yr), round(float(e), 2)))

pd.DataFrame(persons, columns=["person_id", "origin_family_id", "role", "birth_year", "sex"]) \
    .to_csv(RAW / "persons.csv", index=False)
pd.DataFrame(income, columns=["person_id", "year", "earnings"]).to_csv(RAW / "income.csv", index=False)
# Ground truth, used ONLY to benchmark the estimates (a real dataset would not have this file)
pd.DataFrame(truth, columns=["child_id", "theta_parent", "theta_child"]).to_csv(RAW / "truth.csv", index=False)
print(f"{len(persons)} persons, {len(income)} person-year income records")
