-- Indexes make JOINs on the identifiers fast (without them SQLite scans the whole table per row).
CREATE INDEX idx_person_family ON person(origin_family_id);
CREATE INDEX idx_person_id     ON person(person_id);
CREATE INDEX idx_income_person ON income(person_id, year);
