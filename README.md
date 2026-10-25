# Matching Parents and Children with SQL in Python (RStudio project)

A tutorial on building a parent-child match in longitudinal data with SQL (SQLite, run from Python), then using it to estimate the intergenerational elasticity (IGE) of income and to show life-cycle bias.

Blog post: [`blog/blog_post_6.md`](blog/blog_post_6.md)

## Structure
```
ige-sql.Rproj        open this in RStudio
code/                01_simulate_data.py, 02_build_database.py, 03_estimate_ige.py,
                     ige.py (helpers), config.py, run_all.R, run_all.py
sql/                 all SQL, one idea per file (indexes, match, income tables, estimation samples)
data/raw/            persons.csv, income.csv (+ truth.csv, simulation benchmark only)
data/processed/      panel.db (SQLite database; rebuilt by the pipeline, git-ignored)
results/figures/     fig1-fig3 (PNG)
results/tables/      headline IGE table and age-profile tables (CSV)
blog/                tutorial post
```

## Data
The data are **simulated** with a structure that mirrors the PSID: a `person` table (`person_id`, `origin_family_id`, `role`, `birth_year`, `sex`) and a person-year `income` table (`person_id`, `year`, `earnings`). The real PSID requires registration and cannot be redistributed. The simulation builds in a permanent-income IGE of 0.45, age-dependent returns to permanent income (the source of life-cycle bias) and AR(1) transitory shocks (the source of attenuation bias). Details are in `code/01_simulate_data.py`.

**To use real data**, create `data/raw/persons.csv` and `data/raw/income.csv` with the same columns (`role` takes the values `head`, `spouse`, `offspring`), skip step 01, and run steps 02 and 03. `truth.csv` is only used for the benchmark line in the figures; delete the benchmark code if you have real data.

## Replication
Requires Python 3 with `pandas`, `numpy`, `matplotlib` (`pip install -r requirements.txt`). SQLite ships with Python.

From RStudio: open `ige-sql.Rproj`, then run
```r
source("code/run_all.R")
```
(Set `Sys.setenv(PYTHON = "path/to/python")` first if R cannot find Python.) Or from a terminal: `python code/run_all.py`. The random seed is fixed, so the results are identical across runs.

## Methods
1. SQL self-join of `person` on `origin_family_id` (with `role`) builds the parent-child match; a LEFT JOIN audits unmatched children.
2. JOIN + GROUP BY + SUM aggregates head and spouse earnings into family income per child-year; GROUP BY + AVG + HAVING builds multi-year averages.
3. IGE = slope of log child income on log parent income (OLS, HC1 robust SEs), for single-year and multi-year income, across ages of measurement.
