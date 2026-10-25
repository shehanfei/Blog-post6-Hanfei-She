-- Self-join: the person table plays two roles, c (child) and p (parent).
-- The family identifier links them; the role column picks the right generation.
-- INNER JOIN keeps only children who have at least one parent record.
DROP VIEW IF EXISTS parent_child;
CREATE VIEW parent_child AS
SELECT  c.person_id        AS child_id,
        p.person_id        AS parent_id,
        c.origin_family_id AS family_id,
        c.birth_year       AS child_birth,
        p.role             AS parent_role,
        p.birth_year       AS parent_birth
FROM    person AS c
JOIN    person AS p
          ON c.origin_family_id = p.origin_family_id
WHERE   c.role = 'offspring'
  AND   p.role IN ('head', 'spouse');
