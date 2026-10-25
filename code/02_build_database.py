"""Load the CSVs into SQLite and run the SQL files that build the parent-child match."""
import sqlite3
import pandas as pd
from config import *

if DB_PATH.exists():
    DB_PATH.unlink()
con = sqlite3.connect(DB_PATH)

pd.read_csv(RAW / "persons.csv").to_sql("person", con, index=False)
pd.read_csv(RAW / "income.csv").to_sql("income", con, index=False)

# Run the .sql files in order (each is plain SQL, readable on its own)
for f in sorted(SQL.glob("0[1-3]_*.sql")):
    print("Running", f.name)
    con.executescript(f.read_text())
con.commit()

# Quick diagnostics ---------------------------------------------------------------------------
q = lambda s: pd.read_sql(s, con)
print(q("SELECT COUNT(*) AS n_children FROM person WHERE role = 'offspring'"))
print(q("SELECT COUNT(DISTINCT child_id) AS matched_children FROM parent_child"))
print(q((SQL / "04_check_unmatched.sql").read_text()))
con.close()
