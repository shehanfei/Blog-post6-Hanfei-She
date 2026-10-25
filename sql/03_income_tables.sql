-- Child income by age: JOIN person to income on the individual identifier.
DROP TABLE IF EXISTS child_income;
CREATE TABLE child_income AS
SELECT  p.person_id AS child_id,
        i.year,
        p.birth_year,
        i.year - p.birth_year AS age,
        i.earnings
FROM    person AS p
JOIN    income AS i ON i.person_id = p.person_id
WHERE   p.role = 'offspring';
CREATE INDEX idx_ci ON child_income(child_id, age);

-- Parent (family) income per child and year:
--   JOIN  parent_child -> income on parent_id
--   GROUP BY child and year, SUM() adds head + spouse earnings (aggregation across parents)
--   head_age uses MAX(CASE ...) so that only the head's birth year defines "parent age".
DROP TABLE IF EXISTS parent_family_income;
CREATE TABLE parent_family_income AS
SELECT  pc.child_id,
        i.year,
        SUM(i.earnings) AS family_earnings,
        MAX(CASE WHEN pc.parent_role = 'head' THEN i.year - pc.parent_birth END) AS head_age
FROM    parent_child AS pc
JOIN    income       AS i ON i.person_id = pc.parent_id
GROUP BY pc.child_id, i.year;
CREATE INDEX idx_pfi ON parent_family_income(child_id, head_age);
