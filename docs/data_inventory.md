# Data inventory: what we keep, and why

*13 Nov 2026. Paths are relative to `'My' Code/Data/`. Nothing has been deleted; files marked UNNECESSARY can be removed or ignored.*

*16 Nov 2026: rent rebuilt from a new scrape. Full step-by-step method, and how it differs from Onur's scrape and Pennerstorfer's house prices: `rent_measure_reference.md`.*

**Legend**
✅ **CORE**: the analysis depends on it.
🟡 **SUPPORTING**: used for a specific check, split or robustness test (reason given).
⚠️ **USE WITH CARE**: has a known problem.
❌ **UNNECESSARY**: superseded or unused.

## Supply and routing
| File | Status | Why |
|---|---|---|
| `KINDERGARTENOGD.json` (1,682 sites) | ✅ | Locations, places by group type, public/private, operator name |
| `gtfs.zip`, `austria-*.osm.pbf` | ✅ | Routing inputs (timetable, street network) |
| `../outputs/origin_destination_matrices_1min/*.npz` | ✅ | **Current travel times:** 60 one-minute departures 07:30–08:29 (Tue 20 Oct 2026), 6,950 cells × 1,682 sites each, from `colab_routing/vienna_routing_1min_colab.ipynb`. All access measures come from these |
| `../outputs/origin_destination_matrices/*.npz` | ❌ | Old 6 departures (07:30–08:20, 10-min windows); only used by `deprecated/accessibility_analysis_6departures.ipynb` |
| `../outputs/gtfs_stop_departures_5min.csv`, `gtfs_route_lines_vienna.gpkg` | 🟡 | Caches built from `gtfs.zip` by the analysis notebook: scheduled departures per 5 min (Fig. 5) and route lines for maps (Fig. 9) |
| `OGDEXT_RASTER_1_..._L000250_LAEA.zip` | ✅ | The 250 m grid (routing origins) |
| `BEZIRKSGRENZEOGD.json` | 🟡 | District boundaries, maps only |

## Demand (children)
| File | Status | Why |
|---|---|---|
| `socioeconomic/raw/statistik_inspire/` (Zählsprengel 5-year ages + 100 m residents) | ✅ | **The child counts.** Official 0–4 and 5–9 per ZSP, placed with official 100 m residents |
| `socioeconomic/raw/statistik_zsp_boundaries_2026/` | ✅ | ZSP polygons |
| `socioeconomic/raw/ZAEHLBEZIRKOGD.json` | ✅ | ZBZ polygons, the main area unit |
| `socioeconomic/raw/zbz_births_since2015.csv` | 🟡 | Only source for the **under-3 vs 3–5 split** (births of the last 3 years ≈ under-3s); also a cross-check |
| `statistik_inspire/.../pd_popreg_1km_*` (1 km age grid) | 🟡 | Robustness: lets us weight children by local age structure within a ZSP |
| `socioeconomic/raw/bez_pop_age5_birthcountry_since2002.csv` | ❌ | Was used to calibrate the births proxy; superseded by official ZSP ages |
| `socioeconomic/raw/ghsl_pop_2025_100m/` (72 MB) | ❌ | Modelled population; superseded by the official 100 m grid. Keep only if you want the "phantom children" comparison in the paper |
| `socioeconomic/raw/zbz_pop_projection_2018_2028.csv` | ❌ | Only for a "future demand" extension, out of scope |

## Neighbourhood status (SES) and controls
| File | Level | Status | Why / caveat |
|---|---|---|---|
| `zbz_pop_birthcountry_agegroups_since2008.csv` | ZBZ | ✅ | % born abroad: closest free match to Pennerstorfer's country-of-birth control (Austria vs abroad only) |
| `eurostat_census_grid_2021/` | 1 km | 🟡 | The only free source splitting **EU vs non-EU born**; also employed persons. Robustness / control |
| `statistik_inspire/.../pd_aest_zsp_*` (employed by sector) | ZSP | 🟡 | Finest status-like data we have; an occupational proxy, not income (see answers in chat / roadmap) |
| `bez_education_since2008.csv` | district | ✅ | Pennerstorfer's main status measure, but only 23 values |
| `bez_income_since2011.csv` | district | ✅ | Pennerstorfer's second measure; 23 values. `AVERAGE_NETINCOME`: **mean** (not median) net income of employees, both sexes |
| `bez_income_since2002.csv` | district | ❌ | Older duplicate of the above |
| `bez_unemployment_since2002.csv` | district | 🟡 | Extra status measure, 23 values |
| `zbz_pop_nationality_agegroups_since2008.csv` | ZBZ | ❌ | Citizenship duplicates the birthplace information; keep one (birthplace matches Pennerstorfer) |
| `GEMBAUTENFLOGD.json` (municipal housing) | estate | ✅ control | `gemeindebau_per_100_res` per Zählbezirk (EDA §2g, §3g). Housing-tenure context, **not** a clean low-income proxy (income caps are high). ⚠️ The file lists big complexes once per address, each with the whole complex's dwelling count (302,579 listed vs ~207,000 real); deduplicated in the EDA, then split by footprint area. Not in the main specification; robustness check in `accessibility_analysis.ipynb` §5b (status coefficients move by a median of 10%, no significance changes) |
| `socioeconomic/raw/willhaben_rents_2026-11-16.csv` (5,347 listings) | points | ✅ | **New scrape, 16 Nov 2026** (`scripts/scrape_willhaben.py`). willhaben's own coordinates with a precision flag, plus floor area, rooms, floor, outdoor space. ⚠️ willhaben's robots.txt forbids automated access; scraped deliberately at low rate (61 requests), listing attributes only. State this in the ethics note |
| `socioeconomic/processed/zsp_rent_index.csv` | ZSP | ✅ | **4th status IV** `rent_eur_m2_std`: € per m² for a standard 65 m² flat, hedonic-adjusted, Gaussian kernel over the 20 nearest listings at each ZSP centre (`scripts/build_rent_index.py`). 4,071 listings kept; median bandwidth 502 m |
| `../../Onur Code/Willhaben_rent_prices (1).csv` | points | ❌ | Superseded by the new scrape. 37% of listings were geocoded to district centres; no floor area. Its per-room median correlates only ρ = 0.05 with the new index |

## Missing (no free source found)
| Variable | Pennerstorfer level | Best free level |
|---|---|---|
| Education | 250 m cell | district (23) |
| Country of birth (Austria / EU / non-EU) | 250 m cell | ZBZ (Austria vs abroad), 1 km (EU / non-EU) |
| Female employment rate | 250 m cell | none (only total employment, ZSP / 1 km) |
| House prices | ZSP (proprietary) | asking rents, kernel-smoothed to ZSP centres (done 16 Nov) |
