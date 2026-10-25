-- One year of child income at a given age, one year of parent income at a given head age.
SELECT  c.child_id,
        c.earnings          AS child_income,
        pf.family_earnings  AS parent_income
FROM    child_income AS c
JOIN    parent_family_income AS pf ON pf.child_id = c.child_id
WHERE   c.age = :child_age
  AND   pf.head_age = :parent_age
  AND   c.earnings > 0
  AND   pf.family_earnings > 0;
