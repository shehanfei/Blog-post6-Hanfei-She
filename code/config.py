"""Shared settings and paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SQL = ROOT / "sql"
FIGS = ROOT / "results" / "figures"
TABLES = ROOT / "results" / "tables"
DB_PATH = PROCESSED / "panel.db"

for p in (RAW, PROCESSED, FIGS, TABLES):
    p.mkdir(parents=True, exist_ok=True)

SEED = 20241
N_FAMILIES = 3000
TRUE_IGE = 0.45          # intergenerational elasticity of *permanent* income built into the simulation
PANEL_START, PANEL_END = 1965, 2019
