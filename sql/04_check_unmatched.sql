-- LEFT JOIN keeps every child; children with no parent record show NULL in p.person_id.
-- This is the standard way to audit how many observations the match loses.
SELECT  COUNT(DISTINCT c.person_id) AS children_without_parent_record
FROM    person AS c
LEFT JOIN person AS p
          ON  c.origin_family_id = p.origin_family_id
          AND p.role IN ('head', 'spouse')
WHERE   c.role = 'offspring'
  AND   p.person_id IS NULL;
