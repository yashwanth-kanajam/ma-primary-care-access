-- Exactly one row per county. Provider observations are heads, not FTEs.
CREATE TABLE county_metrics AS
SELECT a.fips, w.county, a.population, a.population_moe,
       w.pcp_2023, w.pcp_2022, w.md_2023, w.do_2023,
       100000.0*w.pcp_2023/NULLIF(a.population,0) AS pcp_per_100k,
       100000.0*w.pcp_2022/NULLIF(a.population,0) AS pcp_2022_per_100k,
       a.age65, a.age65_moe, 100.0*a.age65/NULLIF(a.population,0) AS age65_pct,
       a.poverty_population, a.poverty_population_moe, a.poverty, a.poverty_moe,
       100.0*a.poverty/NULLIF(a.poverty_population,0) AS poverty_pct
FROM acs a JOIN workforce w USING (fips)
ORDER BY a.fips;
