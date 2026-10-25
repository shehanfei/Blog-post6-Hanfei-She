-- Multi-year averages. Each CTE collapses a person-year panel to one row per child:
--   GROUP BY child_id + AVG(...) gives the average over the age window,
--   HAVING COUNT(*) >= :min_obs drops children observed in too few years.
WITH c AS (
    SELECT  child_id, AVG(earnings) AS child_income
    FROM    child_income
    WHERE   age BETWEEN :c_lo AND :c_hi
    GROUP BY child_id
    HAVING  COUNT(*) >= :min_c
),
p AS (
    SELECT  child_id, AVG(family_earnings) AS parent_income
    FROM    parent_family_income
    WHERE   head_age BETWEEN :p_lo AND :p_hi
    GROUP BY child_id
    HAVING  COUNT(*) >= :min_p
)
SELECT  c.child_id, c.child_income, p.parent_income
FROM    c
JOIN    p ON p.child_id = c.child_id
WHERE   c.child_income > 0 AND p.parent_income > 0;
