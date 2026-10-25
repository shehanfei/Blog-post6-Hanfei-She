-- Multi-year averages over the SAME calendar years for both generations (:y_lo to :y_hi).
-- Each CTE collapses the person-year panel to one row per child:
--   GROUP BY child_id + AVG(...) averages over the window,
--   HAVING COUNT(*) >= :min_obs drops children observed in too few years.
-- Children are selected by their age in the base year (:base_year), as in single_year.sql.
WITH c AS (
    SELECT  child_id, AVG(earnings) AS child_income
    FROM    child_income
    WHERE   year BETWEEN :y_lo AND :y_hi
      AND   (:base_year - birth_year) BETWEEN :a_lo AND :a_hi
    GROUP BY child_id
    HAVING  COUNT(*) >= :min_c
),
p AS (
    SELECT  child_id, AVG(family_earnings) AS parent_income
    FROM    parent_family_income
    WHERE   year BETWEEN :y_lo AND :y_hi
    GROUP BY child_id
    HAVING  COUNT(*) >= :min_p
)
SELECT  c.child_id, c.child_income, p.parent_income
FROM    c
JOIN    p ON p.child_id = c.child_id
WHERE   c.child_income > 0 AND p.parent_income > 0;
