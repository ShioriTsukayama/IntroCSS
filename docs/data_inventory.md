# Data inventory: what we keep, and why

*Updated 20 Nov 2026. Paths are relative to the project folder: `analysis/` in the shared repository, `'My' Code/` in Stash's local copy. The rent method, and how it differs from Onur's scrape and Pennerstorfer's house prices, is in `rent_measure_reference.md`.*

**Legend**
✅ **CORE**: the analysis depends on it.
🟡 **SUPPORTING**: used for a specific check, split, map or robustness test (reason given).
⚠️ **USE WITH CARE**: has a known problem.
❌ **UNNECESSARY**: superseded or unused. Kept locally only, not in the shared repository.

**Where files live in the shared repository:** in git, unless marked *release* (download with `python get_data.py`; add `--routing` for the routing inputs) or *local only* (not shared; reason given).

## Pipeline
`routing.ipynb` → `socioeconomic_eda.ipynb` → `accessibility_analysis.ipynb` → `access_maps.ipynb`. Each notebook only reads what the ones before it saved.

## Supply and routing
| File | Status | Why |
|---|---|---|
| `Data/KINDERGARTENOGD.json` (1,682 sites) | ✅ | Locations, places by group type, public/private (`TXTATT1`), operator name |
| `Data/gtfs.zip` (*release*) | ✅ | Timetable for routing (Wiener Linien + Wiener Lokalbahnen; no ÖBB S-Bahn) |
| `Data/vienna-261020.osm.pbf` (*release*) | ✅ | Street network for routing: the Geofabrik Austria extract of 20 Oct 2026, cut to a box around all GTFS stops plus 2–3 km (`Data/socioeconomic/scripts/clip_osm_vienna.py`) |
| `Data/austria-261020.osm.pbf` (776 MB, *local only*) | ❌ | Source of the Vienna extract above; not needed once clipped |
| `Data/OGDEXT_RASTER_1_..._L000250_LAEA.zip` (*release*) | ✅ | The Statistik Austria 250 m grid: routing origins, built by `routing.ipynb` §2 |
| `outputs/routing_origins.csv`, `routing_destinations.csv` | ✅ | The 6,950 cells (`origin_id` o0…, cell code, routing point) and 1,682 sites, written by `routing.ipynb`. **Row order of every cell table and matrix** |
| `outputs/origin_destination_matrices_1min/*.npz` (85 MB, *release*) | ✅ | **The travel times:** 60 one-minute departures 07:30–08:29 (Tue 20 Oct 2026), 6,950 cells × 1,682 sites each, from `routing.ipynb`. All access measures come from these |
| `outputs/nearest_site_time_by_cell.csv` | 🟡 | Time to the nearest site per cell over the 60 departures (median, p90, SD, share within 15 min), from `routing.ipynb` §4. Used by the maps |
| `outputs/gtfs_stop_departures_5min.csv`, `gtfs_route_lines_vienna.gpkg`, `gtfs_stops_vienna.csv` | 🟡 | Caches built from `gtfs.zip`: scheduled departures per 5 min (analysis Fig. 5), route lines and stops for maps |
| `outputs/vienna_natural_water.geojson`, `vienna_donau_rivers.geojson` | 🟡 | Water layers for maps (OpenStreetMap via OSMnx) |
| `Data/BEZIRKSGRENZEOGD.json` | 🟡 | District boundaries: routing mask, maps |
| `outputs/origin_destination_matrices/*.npz`, `outputs/accessibility_metrics.csv` (*local only*) | ❌ | The October 6-departure routing (10-min windows) and its per-cell summary. Superseded by the 1-minute routing; `routing_origins.csv` replaces the ids the EDA used to read from `accessibility_metrics.csv` |

## Demand (children)
| File | Status | Why |
|---|---|---|
| `Data/socioeconomic/raw/statistik_inspire/vienna_extracts/` (Zählsprengel 5-year ages + employment, 100 m and 1 km residents) | ✅ | **The child counts.** Official 0–4 and 5–9 per ZSP, placed with official 100 m residents |
| `Data/socioeconomic/raw/statistik_zsp_boundaries_2026/` | ✅ | ZSP polygons |
| `Data/socioeconomic/raw/ZAEHLBEZIRKOGD.json` | ✅ | ZBZ polygons, the main area unit |
| `Data/socioeconomic/raw/zbz_births_since2015.csv` | 🟡 | Only source for the **under-3 vs 3–5 split** (births of the last 3 years ≈ under-3s); also a cross-check |
| `.../vienna_extracts/pd_popreg_1km_*` (1 km age grid) | 🟡 | Robustness: would let us weight children by local age structure within a ZSP (not used yet) |
| `Data/socioeconomic/raw/bez_pop_age5_birthcountry_since2002.csv` (*local only*) | ❌ | Was used to calibrate the births proxy; superseded by official ZSP ages |
| `Data/socioeconomic/raw/ghsl_pop_2025_100m/` (72 MB, *local only*) | ❌ | Modelled population; superseded by the official 100 m grid. Keep only for the "phantom children" comparison (`data_sources_and_merging_guide.md` §4) |
| `Data/socioeconomic/raw/zbz_pop_projection_2018_2028.csv` (*local only*) | ❌ | Only for a "future demand" extension, out of scope |

## Neighbourhood status (SES) and controls
| File | Level | Status | Why / caveat |
|---|---|---|---|
| `zbz_pop_birthcountry_agegroups_since2008.csv` | ZBZ | ✅ | % born abroad: closest free match to Pennerstorfer's country-of-birth control (Austria vs abroad only) |
| `.../vienna_extracts/pd_aest_zsp_*` (employed by sector) | ZSP | ✅ | **3rd status IV** `share_knowledge_JKM` and the `emp_rate_15_64` control. An occupational proxy, not income |
| `bez_education_since2008.csv` | district | ✅ | Pennerstorfer's main status measure, but only 23 values |
| `bez_income_since2011.csv` | district | ✅ | Pennerstorfer's second measure; 23 values. `AVERAGE_NETINCOME`: **mean** (not median) net income of employees, both sexes |
| `GEMBAUTENFLOGD.json` (municipal housing) | estate | 🟡 control | `gemeindebau_per_100_res` per Zählbezirk (EDA §2g, §3g). Housing-tenure context, **not** a clean low-income proxy (income caps are high). ⚠️ The file lists big complexes once per address, each with the whole complex's dwelling count (302,579 listed vs ~207,000 real); deduplicated in the EDA, then split by footprint area. Not in the main specification; robustness check in `accessibility_analysis.ipynb` §5b (status coefficients move by a median of 8%, no significance changes) |
| `Data/socioeconomic/processed/zsp_rent_index.csv` | ZSP | ✅ | **4th status IV** `rent_eur_m2_std`: € per m² for a standard 65 m² flat, hedonic-adjusted, Gaussian kernel over the 20 nearest listings at each ZSP centre (`scripts/build_rent_index.py`). 4,071 listings kept; median bandwidth 502 m |
| `Data/socioeconomic/raw/willhaben_rents_2026-11-16.csv` (5,347 listings, *local only*) | points | ✅ | **The rent scrape, 16 Nov 2026** (`scripts/scrape_willhaben.py`): willhaben's own coordinates with a precision flag, plus floor area, rooms, floor, outdoor space. ⚠️ willhaben's robots.txt forbids automated access; scraped deliberately at low rate (61 requests), listing attributes only. State this in the ethics note. Not shared (third-party adverts with street-level locations); only the aggregated index is |
| `Data/socioeconomic/processed/willhaben_listings_clean.gpkg` (*local only*) | points | 🟡 | The 4,071 clean listings with model residuals; only used for the EDA listing maps. Not shared, for the same reason |
| `bez_unemployment_since2002.csv` (*local only*) | district | ❌ | Extra status measure, 23 values; not used in the current analysis |
| `eurostat_census_grid_2021/` (*local only*) | 1 km | ❌ | The only free source splitting **EU vs non-EU born**; not used in the current analysis. Candidate robustness control |
| `bez_income_since2002.csv` (*local only*) | district | ❌ | Older duplicate of `bez_income_since2011.csv` |
| `zbz_pop_nationality_agegroups_since2008.csv` (*local only*) | ZBZ | ❌ | Citizenship duplicates the birthplace information; birthplace matches Pennerstorfer |
| `Onur Code/Willhaben_rent_prices (1).csv` (*local only*) | points | ❌ | Onur's earlier scrape, superseded. 37% of listings were geocoded to district centres; no floor area. Its per-room median correlates only ρ = 0.05 with the new index. Used only for the comparison map in EDA §3e |

## Missing (no free source found)
| Variable | Pennerstorfer level | Best free level |
|---|---|---|
| Education | 250 m cell | district (23) |
| Country of birth (Austria / EU / non-EU) | 250 m cell | ZBZ (Austria vs abroad), 1 km (EU / non-EU) |
| Female employment rate | 250 m cell | none (only total employment, ZSP / 1 km) |
| House prices | ZSP (proprietary) | asking rents, kernel-smoothed to ZSP centres (done 16 Nov) |
