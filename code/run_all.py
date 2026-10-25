"""Python alternative to run_all.R:  python code/run_all.py"""
import subprocess, sys
from pathlib import Path
here = Path(__file__).parent
for s in ["01_simulate_data.py", "02_build_database.py", "03_estimate_ige.py"]:
    print(f"\n=== {s} ===")
    subprocess.run([sys.executable, str(here / s)], check=True, cwd=here)
