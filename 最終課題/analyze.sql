
SELECT COUNT(*) AS n FROM observations;


SELECT
  time,
  COUNT(*) AS n,
  AVG(value) AS avg_value,
  MIN(value) AS min_value,
  MAX(value) AS max_value
FROM observations
WHERE value IS NOT NULL
GROUP BY time
ORDER BY time
LIMIT 50;


SELECT
  area,
  COUNT(*) AS n,
  AVG(value) AS avg_value
FROM observations
WHERE value IS NOT NULL
  AND area IS NOT NULL
  AND area <> ''
GROUP BY area
ORDER BY avg_value DESC
LIMIT 20;
