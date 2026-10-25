---
title: "Matching Parents and Children with SQL in Python"
---

# Matching Parents and Children with SQL in Python: A Tutorial on the Intergenerational Elasticity and Life-Cycle Bias

## Why this tutorial?

How much of a child's economic success is "inherited" from their parents? The standard summary is the **intergenerational elasticity (IGE)**: the slope in a regression of log child income on log parent income. An IGE of 0.4 means that children whose parents earned 10% more tend to earn about 4% more themselves.

Estimating it takes two steps that are easy to underrate. First, you need to **match each child to their parents** in a longitudinal dataset where people are rows, years are rows, and families change over time. This is a data-wrangling problem, and SQL is the natural tool for it. Second, you need to decide **which income to use**. Income in a single year is a noisy and age-dependent snapshot of someone's long-run economic status, and that choice can change the estimate by a factor of two. I will show that with data.

This post is a tutorial: every SQL query below is in the repository and runs from Python, and you can follow along with basic Python and SQL knowledge.

**A note on the data.** The real workhorse for this question is the Panel Study of Income Dynamics (PSID), but it requires registration and cannot be redistributed. I therefore **simulate a PSID-style dataset** with the same structure (an individual ID, a family ID, and annual earnings) and a known data-generating process. This has an advantage: since I know the permanent-income slope built into the simulation (0.455), I can check how far each estimate is from the truth. The numbers below illustrate the method, not the actual US IGE. The code works unchanged on real data with the same columns (see the README).

## The data

Two tables, as you would build from PSID files:

| Table | Columns | Meaning |
|---|---|---|
| `person` | `person_id`, `origin_family_id`, `role`, `birth_year`, `sex` | one row per individual; `role` is `head`, `spouse`, or `offspring` in the childhood family |
| `income` | `person_id`, `year`, `earnings` | one row per person-year |

There are 29,981 people, 14,797 of them children, and 291,767 person-year income records covering a short **10-year panel, 2010-2019**. Incomes are missing in some waves for children, as in a real panel.

A short panel changes the design in one useful way. Nobody is followed for decades, so the children we observe in 2010 are of **different ages** (born between 1970 and 1992, so aged roughly 18 to 40 in 2010). Comparing children of different ages in the same calendar year is how we will trace out life-cycle bias. Throughout, **2010 is the base year**: the "single-year" estimates use 2010 income, and the "multi-year" estimates average income over 2010 and the years after it. The identifier logic is the key idea: `person_id` identifies *an individual*, and `origin_family_id` identifies *the family unit they grew up in*, so a child and their parents share the second identifier but not the first.

## Setup: SQL inside Python

SQLite is built into Python, so no server is needed. The pattern used throughout is: load the CSVs into a database, keep each query in a `.sql` file, and run it with `pandas.read_sql`.

```python
import sqlite3, pandas as pd

con = sqlite3.connect("data/processed/panel.db")
pd.read_csv("data/raw/persons.csv").to_sql("person", con, index=False)
pd.read_csv("data/raw/income.csv").to_sql("income", con, index=False)

def run_sql(con, name, **params):          # run a .sql file with named parameters
    return pd.read_sql(open(f"sql/{name}").read(), con, params=params)
```

Keeping SQL in separate files has two benefits: the queries stay readable, and named parameters (`:child_age`) let one query serve many specifications without string-pasting.

## Step 1: SELECT, FROM, WHERE

`SELECT` chooses columns, `FROM` chooses the table, and `WHERE` filters rows. For example, children born after 1965:

```sql
SELECT person_id, origin_family_id, birth_year
FROM   person
WHERE  role = 'offspring' AND birth_year > 1965;
```

Everything else in this tutorial builds on these three clauses.

## Step 2: JOIN to match children to parents

The match is a **self-join**: the same `person` table appears twice, once as the child (`c`) and once as the parent (`p`), connected by the family identifier. The `role` column picks the right generation.

```sql
CREATE VIEW parent_child AS
SELECT  c.person_id        AS child_id,
        p.person_id        AS parent_id,
        c.origin_family_id AS family_id,
        c.birth_year       AS child_birth,
        p.role             AS parent_role,
        p.birth_year       AS parent_birth
FROM    person AS c
JOIN    person AS p ON c.origin_family_id = p.origin_family_id
WHERE   c.role = 'offspring'
  AND   p.role IN ('head', 'spouse');
```

A plain `JOIN` (an inner join) returns a row only when the key matches on both sides. Each child therefore appears once per parent, so a child with two parents in the data gets two rows. We use that in the next step.

Inner joins silently drop non-matches, so it is good practice to **audit** what you lose. A `LEFT JOIN` keeps every child and shows `NULL` where no parent was found:

```sql
SELECT COUNT(DISTINCT c.person_id) AS children_without_parent_record
FROM   person AS c
LEFT JOIN person AS p
       ON  c.origin_family_id = p.origin_family_id
       AND p.role IN ('head', 'spouse')
WHERE  c.role = 'offspring' AND p.person_id IS NULL;
```

Result: of 14,797 children, **14,056 (95.0%) match to at least one parent and 741 (5.0%) do not**. In real PSID data the loss is usually larger and not random (for example, children who left home early are harder to link), which matters for how representative the final sample is.

## Step 3: GROUP BY and aggregation

We now need each child's **parental income**. Parents are on separate rows, and a household's income is the sum of the head's and spouse's earnings. This is exactly what `GROUP BY` and an aggregate function do: collapse many rows into one per group.

```sql
CREATE TABLE parent_family_income AS
SELECT  pc.child_id,
        i.year,
        SUM(i.earnings) AS family_earnings,
        MAX(CASE WHEN pc.parent_role = 'head' THEN i.year - pc.parent_birth END) AS head_age
FROM    parent_child AS pc
JOIN    income       AS i ON i.person_id = pc.parent_id
GROUP BY pc.child_id, i.year;
```

Reading it from the bottom: the second `JOIN` attaches each parent's earnings by `person_id`; `GROUP BY child_id, year` makes one output row per child-year; `SUM` adds the head's and spouse's earnings within each group; and `MAX(CASE ...)` is a trick for picking out the head's age (the `CASE` is `NULL` for the spouse, and `MAX` ignores `NULL`s). The aggregate functions you will use most are `SUM`, `AVG`, `COUNT`, `MIN`, and `MAX`.

Children's own income is a simple join of `person` and `income` on `person_id`, with age computed as `year - birth_year` (see `sql/03_income_tables.sql`).

### One year versus several years

Here is the key design choice. To use a **single year**, we take one calendar year of income (`:year`, here 2010) for both generations. We select children by their *age in that year*, so everyone in the sample is at a similar life-cycle stage:

```sql
SELECT c.child_id, c.earnings AS child_income, pf.family_earnings AS parent_income
FROM   child_income AS c
JOIN   parent_family_income AS pf
         ON  pf.child_id = c.child_id AND pf.year = c.year
WHERE  c.year = :year
  AND  (:year - c.birth_year) BETWEEN :a_lo AND :a_hi
  AND  c.earnings > 0 AND pf.family_earnings > 0;
```

To use **multi-year averages**, we `GROUP BY` the child again, this time averaging over the years from `:y_lo` to `:y_hi`. `HAVING` filters *groups* (just as `WHERE` filters rows), so we can require a minimum number of observed years:

```sql
WITH c AS (
    SELECT child_id, AVG(earnings) AS child_income
    FROM   child_income
    WHERE  year BETWEEN :y_lo AND :y_hi
      AND  (:base_year - birth_year) BETWEEN :a_lo AND :a_hi
    GROUP BY child_id
    HAVING COUNT(*) >= :min_c
),
p AS (
    SELECT child_id, AVG(family_earnings) AS parent_income
    FROM   parent_family_income
    WHERE  year BETWEEN :y_lo AND :y_hi
    GROUP BY child_id
    HAVING COUNT(*) >= :min_p
)
SELECT c.child_id, c.child_income, p.parent_income
FROM   c JOIN p ON p.child_id = c.child_id
WHERE  c.child_income > 0 AND p.parent_income > 0;
```

Both versions return the same three columns, so the estimation code does not care which one produced the data. Note that I average income in levels and then take logs, so a year with zero earnings still contributes to the average; averaging logs would require dropping those years.

## Step 4: Estimating the IGE

The estimation is a regression of `log(child_income)` on `log(parent_income)`; the slope is the IGE. I wrote a small OLS function with heteroskedasticity-robust (HC1) standard errors, equivalent to `statsmodels`' `OLS(...).fit(cov_type="HC1")`.

```python
def estimate_ige(df):
    y = np.log(df["child_income"]); x = np.log(df["parent_income"])
    X = np.column_stack([np.ones(len(x)), x])
    ...  # OLS with HC1 robust standard errors; returns slope, se, n
```

### Headline result

| Specification | IGE | 95% CI | N |
|---|---|---|---|
| Single year (2010), children aged 25-29 | 0.229 | [0.205, 0.252] | 3,787 |
| Single year (2010), children aged 30-34 | 0.251 | [0.226, 0.276] | 3,882 |
| Single year (2010), children aged 35-39 | 0.295 | [0.256, 0.334] | 2,255 |
| 5-year average (2010-2014), children aged 30-34 | 0.365 | [0.338, 0.392] | 4,015 |
| 10-year average (2010-2019), children aged 30-34 | 0.404 | [0.377, 0.432] | 4,080 |
| 10-year average (2010-2019), children aged 35-39 | 0.445 | [0.403, 0.487] | 2,358 |
| *Benchmark: permanent-income slope in the simulation* | *0.455* | | |

The same simulated data and regression method produce headline estimates from **0.229 to 0.445**, depending on the child's age at the 2010 baseline and the income measurement window. For children aged 25–29, the one-year estimate is 0.229 (95% CI: 0.205–0.252); for children aged 35–39, averaging income over 2010–2019 gives 0.445 (95% CI: 0.403–0.487). The latter is near the simulated permanent-income benchmark of **0.455**, whereas the former is roughly half as large. These specifications differ in both age group and averaging window, so Figures 1 and 2 below examine those dimensions more systematically.

## Life-cycle bias

Why do single-year estimates depend so strongly on *when* we measure income? Because **annual income at a given age is not a clean proxy for lifetime income**. Two forces are at work.

1. **Life-cycle (age) bias.** People with high lifetime earnings tend to have *steeper* age-earnings profiles. A future lawyer and a future cashier may earn similar amounts at 23, and diverge by 40. At young ages, current income therefore understates the gap in permanent income. Haider and Solon (2006) call this the heterogeneous growth problem. In the simulation, the weight of permanent income in current income rises from 0.5 at age 22 to 1.0 at age 40.
2. **Attenuation bias.** Annual income also contains transitory shocks (bonuses, job loss, a bad year). Noise in the *explanatory* variable shrinks the OLS slope toward zero (classical measurement error). Noise in the dependent variable does not bias the slope, but it makes the estimate less precise.

Under a simplified version of the simulation, the OLS slope behaves like this:

IGE estimate ≈ true IGE × (λ_child × λ_parent × σ²_θ) / (λ²_parent × σ²_θ + σ²_u)

where λ is how strongly permanent income shows up in income at the age we measure, σ²_θ is the variance of permanent income, and σ²_u is the variance of transitory shocks. Small child λ (measuring children young) shrinks the estimate; large σ²_u (using a single year) shrinks it as well.

### Evidence: the child's age at measurement

Because the panel is short, we cannot follow one person from age 23 to 43. But we can compare children of different ages **in the same year**. Figure 1 estimates the IGE separately for overlapping five-year groups of children aged 24–28, 25–29, ..., 35–39 in 2010 (labeled by their central ages, 26 through 37), once with 2010 income and once with average income over 2010–2019 for both generations.

![IGE by child age](results/figures/fig1_ige_by_child_age.png)

*Figure 1. Estimated IGE by the central age of an overlapping five-year child-age group in 2010. Red: single-year income in 2010. Blue: average income in 2010–2019 for both generations. Shaded bands show approximate 95% confidence intervals; the dashed line marks the simulated permanent-income benchmark (0.455, displayed as 0.45 in the chart legend).*

The red line (single-year income) rises from **0.227** at central age 26 to **0.295** at central age 37, with modest fluctuations across intervening age groups. The blue line (ten-year averages for both generations) rises from **0.343** to **0.445** over the same age-group centers. The blue series is consistently above the red series: at age 26 the difference is about 0.116, and at age 37 it is about 0.150. For the oldest group, the ten-year estimate of 0.445 is close to the 0.455 simulation benchmark; its approximate 95% confidence interval is 0.403–0.487. These age-related patterns are consistent with life-cycle bias in this simulation, where younger workers' current earnings are a weaker proxy for permanent earnings.

Two cautions matter. First, **the age gradient is consistent with the life-cycle mechanism**, but the graph alone cannot establish that age causes the differences: age groups in a ten-year panel also differ by birth cohort and potentially by sample composition. The simulated data-generating process is what gives the life-cycle interpretation here. Second, even for the oldest group the single-year estimate (0.295) remains substantially below 0.455, consistent with continuing attenuation from noisy annual income and potentially other measurement effects. The chart itself does not separately identify the contributions of those mechanisms. In this simulation, parents are observed later in their careers; the particularly important age variation is on the children's side.

## Why averaging over several years helps

Averaging solves the attenuation problem directly. If transitory shocks are only partly correlated from year to year, they partly cancel when we average, while permanent income does not change. The noise-to-signal ratio in the regressor falls, and the slope moves back toward the truth. Averaging over a *range* of years also dampens life-cycle bias a little, because it mixes years when the age-earnings profile is steep with years when it is flatter, although it cannot fully remove it for children who start young (the blue line in Figure 1).

Figure 2 holds the baseline child-age group fixed at 35–39 in 2010 and progressively lengthens the income averaging window for both generations, starting in 2010. This makes the pattern consistent with reduced transitory-income noise, though the sample and the ages covered by the measurement window also change.

![IGE by years averaged](results/figures/fig2_ige_by_years_averaged.png)

*Figure 2. Estimated IGE against the number of income years averaged for both generations (children aged 35–39 in 2010). Error bars show approximate 95% confidence intervals; the dashed line is the 0.455 simulation benchmark (rounded to 0.45 in the chart).*

| Years of income averaged | Estimated IGE | Robust SE | N |
|---|---:|---:|---:|
| 1 | 0.2953 | 0.0198 | 2,255 |
| 2 | 0.3384 | 0.0210 | 2,373 |
| 3 | 0.3652 | 0.0213 | 2,354 |
| 5 | 0.4047 | 0.0214 | 2,319 |
| 7 | 0.4288 | 0.0212 | 2,370 |
| 10 | 0.4450 | 0.0214 | 2,358 |

The estimate rises from **0.2953** with one income year to **0.3652** with three years (an increase of 0.0699), then to **0.4450** with ten years (a total increase of 0.1497). The increments diminish as the window lengthens. The ten-year estimate is close to 0.455, and its approximate 95% confidence interval (0.403–0.487) includes that benchmark. This pattern is consistent with averaging reducing transitory-income noise, but it does not isolate measurement-error attenuation perfectly: the longer windows cover later ages and may change the set of people who meet the data requirements. Indeed, the sample size **does not shrink monotonically** in these results: N is 2,255 with one year and 2,358 with ten years, varying between 2,319 and 2,373 for the intermediate multi-year windows. The practical lesson, in line with Solon (1992) and Mazumder (2005), is to use well-motivated multi-year income measures and appropriate ages, while checking how each specification changes sample composition.

## Pitfalls and limitations

- **Simulated data.** The patterns here follow from the data-generating process I chose, so the magnitudes (0.23, 0.30, and so on) should not be read as estimates of actual IGEs. The *direction* of the biases, however, matches what the literature documents for real data.
- **Match selection.** 5.0% of children had no parent record. In real data, who is matched is rarely random.
- **Changing samples.** Observation requirements, age groups, and positive-income restrictions can alter who enters each regression. Within the fixed 35–39 baseline-age comparison in Figure 2, N varies from 2,255 to 2,373 across specifications and is 2,358 in the ten-year case; it does not decrease monotonically.
- **Zeros and logs.** Dropping non-positive incomes is common but has consequences, and averaging in levels versus logs gives different answers.
- **Short panel.** With ten years of data we compare children of different ages in the same year rather than following people over their lives. That mixes age with birth cohort, so the age gradient in Figure 1 could partly reflect cohort differences in real data (in the simulation there are none).
- **Family income versus individual earnings.** I used the sum of both parents' earnings for parents and individual earnings for children; other choices (household income, sons only, father-only) give different elasticities.
- **Standard errors.** Siblings share parents, so errors are probably correlated within families. Clustering by `origin_family_id` would be the next refinement.

## Takeaway

SQL does two jobs in this workflow. `JOIN` builds the link between generations from person and family identifiers, with a `LEFT JOIN` audit to show what the match loses. `GROUP BY` with `SUM`, `AVG`, and `HAVING` turns a person-year panel into one analysis row per child, whether we want a single year or an average over many. Both steps are explicit, reproducible, and easy to check, which is much harder when the match is buried in a long script of data-frame edits.

The substantive lesson is that the measured IGE depends strongly on how and when income is observed. In these simulated data, the single-year estimate for children aged 25–29 is **0.229**, while the ten-year average for children aged 35–39 gives **0.445**, close to the **0.455** benchmark. Figure 1 shows higher estimates for older baseline-age groups, and Figure 2 shows higher estimates as more income years are averaged for a fixed baseline-age group. The patterns are consistent with both life-cycle effects and attenuation from noisy annual earnings, but these plots do not by themselves assign a precise share of the bias to each mechanism. Without attention to age, averaging windows, and sample composition, a study may misstate the degree of intergenerational income persistence.

For readers doing their own work, the checklist is short: match on identifiers and audit the loss; build income measures in SQL with explicit age windows; average over as many years as possible; measure people in mid-career; and always plot the estimate against age at measurement (even in a short panel, by comparing age groups in the same year), because a visible slope is a warning that the single-year number is unreliable.

## Replication

All code is in the repository; see `README.md`. In RStudio, open the project folder as an RStudio project (use **File → New Project → Existing Directory** if there is no `.Rproj` file), configure a Python environment with `pandas`, `numpy`, and `matplotlib`, then run `source("code/run_all.R")` from the project root. If using `reticulate`, you can point the runner at the configured Python first:

```r
library(reticulate)
py_require(c("pandas", "numpy", "matplotlib"))
python_path <- py_config()$python
Sys.setenv(PYTHON = python_path)
source("code/run_all.R")
```

The script regenerates the input simulation, SQLite tables, results CSVs, and both figures. The figures referenced above are `results/figures/fig1_ige_by_child_age.png` and `results/figures/fig2_ige_by_years_averaged.png`.

## References

- Haider, S., and Solon, G. (2006). Life-Cycle Variation in the Association between Current and Lifetime Earnings. *American Economic Review*, 96(4), 1308-1320.
- Mazumder, B. (2005). Fortunate Sons: New Estimates of Intergenerational Mobility in the United States Using Social Security Earnings Data. *Review of Economics and Statistics*, 87(2), 235-255.
- Solon, G. (1992). Intergenerational Income Mobility in the United States. *American Economic Review*, 82(3), 393-408.
- Panel Study of Income Dynamics, Institute for Social Research, University of Michigan (the real dataset this simulation imitates).
