SELECT
  lower(trim(target)) AS target,
  COUNT(DISTINCT url) AS pages,
  MIN(TRY_CAST(incident_date AS DATE)) AS first_date,
  MAX(TRY_CAST(incident_date AS DATE)) AS last_date,
  MODE(attributed_to) AS attributed_to
FROM r6d6fab9ead2
WHERE target IS NOT NULL
GROUP BY lower(trim(target))
ORDER BY pages DESC
LIMIT 30
