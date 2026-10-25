-- Single-year estimation sample: ONE calendar year (:year) of income for both generations.
-- Children are selected by their age in the base year, so every row of the sample is a child
-- observed at the same life-cycle stage.
SELECT  c.child_id,
        c.earnings          AS child_income,
        pf.family_earnings  AS parent_income
FROM    child_income AS c
JOIN    parent_family_income AS pf
          ON  pf.child_id = c.child_id
          AND pf.year     = c.year
WHERE   c.year = :year
  AND   (:year - c.birth_year) BETWEEN :a_lo AND :a_hi
  AND   c.earnings > 0
  AND   pf.family_earnings > 0;
