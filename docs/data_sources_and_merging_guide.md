# Data sources and how to merge them: Vienna childcare accessibility

*Last updated 20 Nov 2026 (content mostly 13 Nov). Paths are relative to the project folder (`analysis/` in the shared repository, `'My' Code/` locally). This complements `socioeconomic_analysis_roadmap.md`; which files are used now is in `data_inventory.md`.*

---

## 1. What Pennerstorfer et al. used

### 1a. [Pennerstorfer & Pennerstorfer (2021)](https://doi.org/10.1017/S0047279419000990), *Journal of Social Policy*: years 2007–2014

The paper names four levels of geography: 250 m grid cells, 1,364 Zählsprengel (statistical enumeration districts), 250 Zählbezirke and 23 districts.

| Variable | Source | Geography | Year | How it reached each child |
|---|---|---|---|---|
| Children under 6 | Statistik Austria, **paid** | 250 m cell | 1 Jan, each year | Native. Age is only given for cells with more than 30 residents (to 2011) or more than 3 (from 2011); about 0.3% of people were lost |
| Childcare sites (capacity, group type, provider) | City of Vienna (MA 23 / MA 10) | Zählbezirk, then geocoded addresses | Oct, each year | Address geocoded, site placed at its 250 m cell's centre |
| Education (% with a university degree) | Statistik Austria, **paid** | 250 m cell | 2011 only | Native. One year used for all years |
| Income (average net income) | Vienna OGD on data.gv.at, **free** | 23 districts | annual | Every cell takes its district's value |
| House prices | DataScience Service GmbH, **proprietary** | 1,364 Zählsprengel | 2015 | Price of a standard flat at the Zählsprengel's centre, given to every cell inside it |
| Controls: born in Austria / EU / outside EU; female employment rate | Statistik Austria, **paid** | 250 m cell | 2007 | Native |
| U-Bahn station in cell (0/1) | data.gv.at, free | point | — | Point in cell |

Standard errors are clustered at the level each status variable is measured: cell for education, district for income. The 2SFCA uses straight-line distance within 500 m. Children and sites are placed at cell centres, and children in the same cell as a site are treated as 125 m away.

### 1b. [Pennerstorfer, Pennerstorfer & Neumayr (2025)](https://doi.org/10.1177/00420980241258298), *Urban Studies*: 2020 cross-section

- Children under 6 per 250 m cell in 2020 (118,520 in total), split into under 3 and 3–5.
- Education per cell for 2018: share of residents aged 15+ with a degree.
- "Neighbourhood" is the **average over all cells whose centres are within 500 m**, i.e. a moving window, not an administrative area.
- Same controls (country of birth, female employment, public transport), measured within 500 m.
- Childcare prices and services from their own phone/email survey (71% of centres responded).

### 1c. Did they merge geometries?

Not formally. Lower-resolution variables were attached to cells by **simple assignment**: each cell takes the value of the larger area containing it. Neither paper says how cells crossing a boundary were handled; presumably by cell centre. The 2025 paper avoids the issue by keeping all status variables on the grid. The only adjustment for mixed resolution is in the statistics: standard errors clustered at the variable's own level.

### 1d. Implications for a data request

- **Worth requesting** (250 m cell, Vienna only, latest year): **education**, **country of birth (Austria / EU / outside EU)** and **female employment rate**. Children by age are no longer needed; see §2.
- **Not in their paper at grid level:** income. Check the `reg.data` catalogue for whether Statistik Austria now offers it.
- **No need to buy:** district income is free and already downloaded. House prices were proprietary, so use the scraped Willhaben rents.
- **Where to order:** geoinformation@statistik.gv.at. A Vienna-only extract is quoted below the Austria-wide list price; ask for research terms. [Price list PDF](https://www.statistik.at/fileadmin/pages/454/RegionalstatistischeRasterDatenPreise.pdf).

---

## 2. Free data: what exists and at what geography

### 2a. New: Statistik Austria's free downloads (verified 13 Nov 2026)

These are Statistik Austria's INSPIRE downloads (an EU open-data standard), published free on its [download service](https://www.statistik.at/gs-inspire/www/inspire2/download/download-service.xml). Boundaries are CC BY 4.0 via [data.statistik.gv.at](https://data.statistik.gv.at/web/meta.jsp?dataset=OGDEXT_ZSP_1).

| Dataset | Unit | Reference date | Content | Vienna extract |
|---|---|---|---|---|
| Population by Zählsprengel | 1,345 populated Zählsprengel (1,368 polygons) | 1 Jan 2026 | Total, by sex, by **5-year age groups (0–4, 5–9, … 100+)** | `processed/zaehlsprengel_2026_inspire.csv/.gpkg` |
| Population by economic characteristics, by Zählsprengel | same | 31 Oct 2024 | Residents (TOTAL) and **employed residents by workplace sector** (NACE A–U) | merged into the same file (`emp_*`, `share_*`) |
| Population, 100 m grid | populated 100 m cells | 1 Jan 2026 | Total population | `processed/grid250_pop_official_2026.csv` (split onto our 250 m grid) |
| Population, 1 km grid | 1 km cells | 1 Jan 2026 | Total, sex, 5-year age groups (about 6% of values withheld for confidentiality) | `raw/statistik_inspire/vienna_extracts/` |
| Zählsprengel boundaries | polygons | 1 Jan 2026 | Through Statistik Austria's map server (WFS) | `raw/statistik_zsp_boundaries_2026/` |

**Validation checks run on these files:**
- Zählsprengel population summed to Zählbezirke **equals** the Vienna statistics department's 2026 totals exactly: 2,040,914 people.
- Zählsprengel codes do **not** contain the Zählbezirk code. The first five digits are the district code (90101 = 1st district). Zählsprengel were linked to Zählbezirke by overlap: median 99.8% of each one's area lies in a single Zählbezirk, 88% have at least 99%, and 7 have less than 90%.
- **Our births-based child estimate** compared with official ages 0–5 (0–4 plus one fifth of 5–9):
  - Vienna total: 111,847 vs 113,331.
  - Zählbezirk level: r = 0.97, median ratio 0.99, middle half of Zählbezirke between 0.91 and 1.07.
  - **250 m cell level:** r = 0.83 (rank correlation 0.90); the median cell differs by 1.5 children.
  - **196 cells** get at least 5 children from us but have about zero residents officially. GHSL, the satellite-based population grid we used, puts people on land where nobody lives.
- **Conclusion:** rebuild the demand side as official Zählsprengel ages 0–5, spread over the official 100 m population grid. The files are ready: `processed/grid250_children_official_2026.csv`. This removes the births proxy and GHSL, and leaves only one modelling assumption.

### 2b. Everything else free, by geography

| Geography (number in Vienna) | Variables | Source | Already downloaded? |
|---|---|---|---|
| **District (23)** | Education 25–64 (9 levels); average net income; unemployment; population by 5-year age × 4 origin groups (AUT / EEA / REU / TCN); household types | Vienna statistics (MA 23) on data.gv.at | yes, except household types |
| District (23) | Statistik Austria employment statistics, municipal results (Vienna's districts count as municipalities) | data.statistik.gv.at `OGDEXT_AEST_GEMTAB_1` | no |
| District (23) | Pupils with a home language other than German (school statistics) | Vienna integration monitoring, ÖIF reports | no (PDF/HTML tables) |
| **Zählbezirk (250)** | Population by 3 age groups × born in Austria/abroad; × citizenship; births; population projection | MA 23 on data.gv.at | yes |
| **Zählsprengel (about 1,360)** | 5-year age groups, sex; employed residents by sector | Statistik Austria INSPIRE | **yes (new)** |
| 1 km grid | Census 2021: age bands, employed, born in other EU / outside EU, moved in last year | Eurostat GISCO | yes |
| 1 km grid | 5-year age groups, 2026; employed by sector | Statistik Austria INSPIRE | yes (age) |
| 100 m grid | Official population, 2026 | Statistik Austria INSPIRE | **yes (new)** |
| 100 m grid | Modelled population (satellite-based) | JRC GHSL | yes (now superseded) |
| Points / polygons | Childcare sites; municipal housing estates; U-Bahn and stops (GTFS); schools; parks; land use; building heights | Vienna OGD (data.wien.gv.at) | sites, housing, GTFS: yes |
| Points | Asking rents | willhaben (own scrape, 16 Nov 2026; replaced Onur's October scrape) | yes, aggregated to `processed/zsp_rent_index.csv` (`rent_measure_reference.md`) |
| Zone maps (PDF) | Rent location surcharge zones; no surcharge in about 70% of census areas, a marker of historically poorer housing stock | MA 25 / wohnberatung-wien.at | no |

### 2c. Origin and language

- **Country of birth / citizenship.** From the population register, published by MA 23. Zählbezirk level is only binary (Austria vs abroad), in 3 age groups. District level has 4 groups. For EU vs outside EU at fine scale, use the Eurostat 1 km census grid (2021).
- **Language.** There are **no residential language data**. The 2001 census was the last to ask about everyday language; since 2011 the census is built from registers that do not record it. The only proxy is pupils' home language at schools, published by district: about 49% non-German in Vienna, over two thirds in Favoriten, Ottakring and Simmering. Neither Pennerstorfer paper used language.

### 2d. Status proxies now possible at Zählsprengel level (free)

The employment file lets us build, per Zählsprengel:
- `share_knowledge_JKM`: share of employed residents working in information/communication (J), finance (K) or professional and scientific services (M). Strongly linked to education.
- `share_lowwage_IN`: share working in accommodation and food (I) or administrative and support services, which includes cleaning and security (N).
- `emp_rate_15_64`: employed residents divided by residents aged 15–64. Approximate, because the numerator includes workers over 65 and the two files have different dates.

These are new and validated only by construction. Correlate them with district education before relying on them.

---

## 3. Standard procedure for merging data across geographies

### 3a. Before any join
1. **One projection, equal-area.** Use EPSG:3035 (Europe-wide equal-area projection, metres), which is our grid's native system. Zählsprengel arrive in EPSG:31287 (Austrian Lambert) and must be reprojected.
2. **Clean geometries.** Run `make_valid()`; dissolve multipart duplicates.
3. **Check IDs and coverage.** Do not assume codes nest (see §2a). Check totals before and after every step.

### 3b. Counts vs rates
| Type | Examples | Moving to **smaller** units | Moving to **larger** units |
|---|---|---|---|
| **Count** (extensive) | children, residents, places, dwellings | **Split** (by area or an ancillary layer) | **Sum** |
| **Rate / average** (intensive) | % with a degree, average income, rent per m², 2SFCA score | **Assign** the parent's value | **Weighted mean**, using the right denominator (e.g. % with a degree weighted by adults, not by area or by unit) |

Assigning a *count* to smaller units multiplies it; summing *rates* is meaningless. Most merging errors are one of these two.

### 3c. Methods, from simplest to most demanding

| Situation | Method | Assumption to state | Python |
|---|---|---|---|
| Units nest (Zählsprengel → Zählbezirk → district) | Join on ID, then sum or weighted mean | Correct nesting (verify!) | `pandas.groupby` |
| Large → small, **rate** | **Simple assignment / centroid join** (what Pennerstorfer did for income and house prices) | Value is the same everywhere inside the parent | `geopandas.sjoin(cells.centroid, polys)` |
| Large → small, **count**, no helper layer | **Areal weighting**: split in proportion to overlapping area | People are spread evenly. Bad in cities with parks, rail yards and the Danube | `geopandas.overlay` + area share; `tobler.area_weighted.area_interpolate` |
| Large → small, **count**, with helper layer | **Dasymetric**: split in proportion to population, buildings or residential land | Target variable is distributed like the helper (e.g. children like total population) | `overlay` + weights; `tobler.dasymetric` |
| Cells crossing boundaries | Centre-point assignment, or splitting by overlap share | Small edge error. Report how many cells are affected (we had 319 edge cells) | `sjoin` / `sjoin_nearest`; `overlay` |
| Point data (rents, sites) → areas | Point-in-polygon, then median or count | Sample represents the area; check how many points each area has | `sjoin` |
| Smoothed neighbourhoods (Pennerstorfer et al. 2025) | Moving window / kernel: average over cells within *r* metres | Residents experience the area within *r* | `libpysal.weights.DistanceBand` + spatial lag |
| Raster → polygons (GHSL, land use) | Zonal statistics (sum or mean of pixels) | Pixel values are accurate at that resolution | `rasterstats.zonal_stats` |

Advanced options, rarely needed here: pycnophylactic interpolation (smooth surfaces that preserve totals), and regression- or kriging-based downscaling.

### 3d. Consequences for inference
- **Effective sample size.** A variable measured for 23 districts carries 23 values of information, whatever the number of cells. Cluster standard errors at that level, or use a multilevel model (cells within Zählsprengel within districts).
- **Ecological fallacy.** Area-level associations do not describe individual families. Say so.
- **MAUP** (the modifiable areal unit problem: results can change with the size and shape of units). Re-run the key model at a second scale (cells and Zählsprengel) and report both.
- **Spatial autocorrelation.** Neighbouring units resemble each other (Moran's I for travel time is 0.36 and for education 0.80), so use spatial-error models or cluster-robust standard errors.

### 3e. What to put in the paper
One table, one row per variable:

| Variable | Original unit | Year | How it reached the analysis unit | Assumption |
|---|---|---|---|---|
| Children 0–5 | Zählsprengel | 2026 | Dasymetric via official 100 m population, then areal weighting to 250 m | Children are distributed like residents within a Zählsprengel |
| % tertiary | district (or 250 m if purchased) | 2023 | Assignment | Same within district |
| … | | | | |

---

## 4. The pipeline as implemented

Scripts are in `Data/socioeconomic/scripts/`. Run them from `Data/socioeconomic` with `python -I`. They produced the files in `raw/statistik_inspire/vienna_extracts/` and `processed/`; the national INSPIRE zips they read (0.15–0.8 GB) are not in the repository.

1. `parse_inspire.py <zip> <out.csv> zsp|grid` reads the GML (the EU's XML format for map data) directly from the zip and keeps Vienna only. Extracted, the full files are 0.15–0.8 GB each, so do not unzip them.
2. `build_inspire_tables.py`:
   - turns the files into Zählsprengel tables, adds employment shares and the overlap link to Zählbezirke;
   - spreads 100 m population onto the 250 m grid by area;
   - prints the validation results.
3. `official_children_250.py`:
   - takes Zählsprengel ages 0–5;
   - spreads them over 100 m cells in proportion to population (each cell assigned to a Zählsprengel by its centre);
   - splits those onto 250 m cells by area;
   - writes `processed/grid250_children_official_2026.csv` and the comparison with our estimate.

**Done 13 Nov 2026:** `socioeconomic_eda.ipynb` now builds `children_u6` this way inside the notebook (§3b since the 16 Nov restructure, which also dropped the births × GHSL comparison column), and every downstream measure uses it: underserved counts, 2SFCA, gradients, Moran's I, concentration curves. The old estimate was kept as `children_u6_births_ghsl` until the 16 Nov restructure removed it. Effects at the time (6 departures, binary 2SFCA):

| Measure | Births × GHSL (before) | Official (after) |
|---|---|---|
| Children aged 0–5 in routed grid | 111,847 | 111,638 |
| Median trip > 15 min | 1,607 (1.4%) | 404 (0.4%) |
| At least 1 of 6 departures > 15 min | 1,669 (1.5%) | 490 (0.4%) |
| Public site median > 15 min | 3,888 (3.5%) | 2,343 (2.1%) |
| < 25 competition-adjusted places per 100 (2SFCA) | 4.3% | 2.4% |
| Child-weighted mean 2SFCA | 75.7 | 75.9 |
| Moran's I, travel time (Zählbezirke) | 0.36 | 0.27 |

Most of the children previously classified as underserved had been allocated to uninhabited peripheral cells. This is a concrete example of the point in §3d: a demand model's spatial assumptions can drive a headline result.
