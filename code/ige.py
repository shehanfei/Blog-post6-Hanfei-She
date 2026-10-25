"""Helpers: run the parameterized SQL files and estimate the IGE by OLS."""
import sqlite3
import numpy as np
import pandas as pd
from config import *


def connect():
    return sqlite3.connect(DB_PATH)


def run_sql(con, name, **params):
    return pd.read_sql((SQL / name).read_text(), con, params=params)


def estimate_ige(df):
    """OLS of log(child income) on log(parent income) with HC1 robust standard errors.
    (Equivalent to statsmodels: sm.OLS(y, sm.add_constant(x)).fit(cov_type='HC1').)"""
    y = np.log(df["child_income"].to_numpy())
    x = np.log(df["parent_income"].to_numpy())
    X = np.column_stack([np.ones_like(x), x])
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    meat = X.T @ (X * resid[:, None] ** 2)
    cov = XtX_inv @ meat @ XtX_inv * n / (n - k)
    return {"ige": beta[1], "se": float(np.sqrt(cov[1, 1])), "n": n}
