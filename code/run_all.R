# Run the whole pipeline from RStudio (open ige-sql.Rproj first):  source("code/run_all.R")
# Python does the SQL work; R is the project shell. Needs Python 3 with pandas, numpy, matplotlib.
py <- Sys.getenv("PYTHON", unset = if (.Platform$OS.type == "windows") "python" else "python3")
for (s in c("01_simulate_data.py", "02_build_database.py", "03_estimate_ige.py")) {
  message("\n=== ", s, " ===")
  status <- system2(py, file.path("code", s))
  if (status != 0) stop("Step failed: ", s, call. = FALSE)
}
