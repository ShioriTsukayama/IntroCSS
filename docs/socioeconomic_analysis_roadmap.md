# From description to explanation: socio-economic analysis of childcare accessibility in Vienna

*Prepared 12 Nov 2026, updated 20 Nov 2026. Paths are relative to the project folder (`analysis/` in the shared repository, `'My' Code/` locally).*

> **Status, 20 Nov 2026.** Phases 1–4 are done; robustness is mostly done; writing has not started.
>
> **Pipeline** (each notebook only reads what the ones before it saved):
> 1. `routing.ipynb`: walk + public transport times from 6,950 cells to 1,682 sites, **every minute 07:30–08:29** (60 departures). Routed once (17 Nov, 3.3 h); the matrices are on the repository release.
> 2. `socioeconomic_eda.ipynb`: children per cell, the four status measures and the controls.
> 3. `accessibility_analysis.ipynb`: the access measures, the models (A, B, robustness) and analysis figures 1–9.
> 4. `access_maps.ipynb`: presentation maps (travel time, DV2R, reliability shift, public vs private, access × status).
>
> **Outcomes.** The **primary outcome is DV2R, the reliable network 2SFCA**: each cell–site pair uses its 90th-percentile travel time across the 60 departures (the time a parent can count on 9 mornings in 10). DV2 (2SFCA averaged over departures) is the comparison, DV3 (share of access lost at an unlucky departure) is the reliability outcome, and DV1 is the Euclidean Pennerstorfer replication.
>
> **Key results**
> * Higher status goes with more DV2R access, net of density and controls: β ≈ +0.08 to +0.10 SD per SD of status for all four status measures (p ≤ 0.01). In places: about +4 places per 100 children per SD (mean 80). DV1 gives the same direction (β +0.06 to +0.09; income p = 0.06).
> * **Private sites drive this** (β ≈ +0.19 to +0.28); **public sites lean towards lower-status areas** (β ≈ −0.06 to −0.15; income n.s.).
> * Higher-status areas also lose *less* access at an unlucky departure (DV3: β ≈ −0.08 to −0.10, income n.s.).
> * Requiring reliability cuts the cell–site pairs within 15 min by 19% (97,432 → 78,560), but **redistributes** rather than reduces access: a 2SFCA hands out all of the city's places, so the child-weighted mean is 80.3 places per 100 children under every measure. About a third of children gain more than 3 places per 100 and a third lose more than 3 (`access_maps.ipynb` map 2).
> * DV1 and DV2R rank cells quite differently (Spearman 0.72; 32% of children move more than 25 percentiles), and the shift is itself patterned by status (higher-status areas gain about 2–3 percentiles per SD of status under DV2R, p ≤ 0.01).
> * The nearest site is saturated: 96.8% of children's nearest-site time never changes over the hour, and practically every child has a site within 15 min. Access differences come from capacity and competition, not distance.
> * Reach falls slightly over the hour (≈ 2% fewer pairs within 15 min by 08:29) because the **timetable thins after the peak**: scheduled bus departures drop 12% from 07:30 to 08:29, trams and U-Bahn barely change. Status gaps are constant across departure minutes (analysis Fig. 5). The GTFS covers Wiener Linien and Wiener Lokalbahnen only (no ÖBB S-Bahn): a limitation.
> * Robustness: 10- and 20-min catchments, 80th / 95th percentiles, a share-of-departures weighting and a Gemeindebau control all keep the signs and significance (Gemeindebau moves status coefficients by a median of 8%).
>
> **Still open:** spatial error model at Zählbezirk level (`explanatory_models_primer.md` §5); the under-3 / 3–5 age split; the essay and slides.

---

## 1. Data inventory

Downloaded files are in `Data/socioeconomic/raw/`. The EDA notebook writes the joined, analysis-ready tables to `Data/socioeconomic/processed/`. Which files are used, and which are in the shared repository, is in `data_inventory.md`.

| Dataset | Spatial level | Year | Key variables | Status |
|---|---|---|---|---|
| Population by 3 age bands × birthplace (MA 23) | 250 Zählbezirke | annual 2008–2026 | 0–14, 15–64, 65+; born in Austria/abroad | ✅ downloaded |
| Population by 3 age bands × citizenship (MA 23) | Zählbezirke | 2008–2026 | as above, by citizenship | ✅ |
| **Population by 5-year age band (Statistik Austria, free)** | **1,368 Zählsprengel** | 1 Jan 2026 | **official 0–4 / 5–9 counts → children aged 0–5 (used in all analysis)** | ✅ (13 Nov) |
| **Employed residents by workplace sector (Statistik Austria, free)** | Zählsprengel | 31 Oct 2024 | sector shares → fine-grained status proxies | ✅ (13 Nov) |
| **Official resident grid (Statistik Austria, free)** | **100 m** | 1 Jan 2026 | residents → **dasymetric** weight | ✅ (13 Nov) |
| Live births by residence (MA 23) | Zählbezirke | 2015–2025 | births → cross-check of child counts, and the under-3 / 3–5 split | ✅ |
| Population projection 2018–28 (MA 23) | Zählbezirke | 2018–2028 | projected age bands | ✅ (for "future demand" extension) |
| Population by 5-year age bands × birthplace | 23 Bezirke | 2002–2026 | official 0–4 counts: used to validate the births proxy | ✅ |
| Education of 25–64-year-olds | Bezirke | 2008–2023 | % tertiary, % compulsory only | ✅ |
| Employee net/gross income | Bezirke | 2011–2023 | average net income | ✅ |
| Registered unemployment | Bezirke | 2002–2023 | per 1,000 residents | ✅ |
| Zählbezirk boundaries (`ZAEHLBEZIRKOGD`) | 250 polygons | 2026 | join key `9BBZZ` | ✅ |
| Municipal housing (*Gemeindebau*) | 1,776 estates (polygons) | current | dwellings per estate → housing-tenure context (robustness control) | ✅ |
| JRC GHS-POP 2025 | 100 m raster | 2025 | modelled population: **superseded** by the official 100 m grid | ❌ not used |
| Eurostat Census 2021 grid | 1 km | 2021 | <15, born outside EU, employed, recent movers | downloaded, not used |
| willhaben asking rents (own scrape, `scrape_willhaben.py`) | points → Zählsprengel index | 16 Nov 2026 | € per m², standard flat (`rent_measure_reference.md`) | ✅ (replaces Onur's Oct scrape) |
| `KINDERGARTENOGD` (already had) | 1,682 sites | current | **capacity by age group**, **public vs private** (`TXTATT1`) | already had; now used |
| Travel-time matrices (`routing.ipynb`) | 6,950 × 1,682 × **60 one-minute departures** (07:30–08:29) | Oct 2026 timetable | full travel-time matrices | ✅ routed 17 Nov |

**What is missing, and how to get it**
* **250 m grid data on education, country of birth and female employment.** This is what Pennerstorfer & Pennerstorfer used. **Child counts no longer need buying**: the free Zählsprengel age table covers them. Statistik Austria sells the grid data at about €350 per order plus a per-variable fee (prices scale with area, so a Vienna-only extract should cost much less than the Austria-wide list price). Ask your supervisors whether CEU has research access. The Austrian Micro Data Center (AMDC) also offers access for accredited researchers. If you get it, the notebook's cell-level joins already work: just add the variables. See `data_sources_and_merging_guide.md` §1d.
* **Real-world transit delays.** The GTFS feed is the *timetable*, so the "reliability" you measure is **schedule-based variability**: waiting for the next tram or bus, and missed connections. It is not delay or crowding. Name it that way in the paper. Real delays would need Wiener Linien real-time data logged over several weeks, which is out of scope.
* **Opening hours and actual vacancies.** The dataset lists *authorised* places, not free ones, and 133 sites list no capacity at all.

---

## 2. What the first EDA pass showed (13 Nov 2026, historical)

> **Superseded.** This section records the first descriptive pass, on the old 6 departures and a binary 2SFCA. Current results are in the status box at the top and in `accessibility_analysis.ipynb`. It is kept because it explains why the project moved from nearest-site time to a competition-adjusted, reliability-based measure.

> **16 Nov 2026:** the EDA notebook was restructured (setup → loading → variable construction → correlations and status terciles) and now only builds children and status variables; all access measures live in `accessibility_analysis.ipynb`. The figures cited below are archived in `outputs/eda_socioeconomic/_archive_pre_2026-11-16/`. Their successors, built on the current access measures, are in `accessibility_analysis.ipynb`: Fig. 6 (access maps), Fig. 7 (equity gradients by status tercile, in places per 100 children, incl. the share of children below 25 places) and Fig. 8 (concentration curves and indices). LISA was dropped. Gemeindebau numbers below predate the 16 Nov de-duplication of the estate file and overstate dwellings.

*Updated 13 Nov 2026: all figures now use **official child counts** (Statistik Austria Zählsprengel ages, spread over the official 100 m resident grid). The previous births × GHSL estimate agreed on totals but placed about 2,400 "phantom" children in 196 uninhabited cells (parks, rail land, edge areas). Those sat mostly far from sites, so they inflated every "underserved" count. Previous values are shown in brackets.*

1. **Nearest-site travel time barely varies where children live.** About **111,600** children aged 0–5 live in the routed grid. Only **~0.4%** of them (≈ 400 children; previously 1.4%, ≈ 1,600) live in cells where the median fastest trip to *any* site exceeds 15 min, and 0.4% have at least one of 6 departures over 15 min. A further check is the "false access" cells: within 500 m straight line, yet never reachable within 15 min. These hold under **0.1%** of children. With 1,682 sites in a dense city, "time to the nearest site" is saturated, and as the main outcome it gives the regression almost no variation to explain.
2. **Things change once you count capacity and competition.** The number of places reachable within 15 min, and the network **2SFCA** score (places per 100 children within 15 min, adjusted for how many other children can reach the same sites), vary widely across the city. The outer districts (10, 11, 21, 22, 23) and the urban fringe stand out.
3. **Access to public sites only** is worse: **~2.1%** of children (previously 3.5%) have no public site within a 15-min median trip. Public sites are only 392 of the 1,682, so this is the natural link to Pennerstorfer's public-versus-non-profit argument. Children with fewer than 25 competition-adjusted places per 100 (2SFCA) fall from 4.3% to **2.4%**. The child-weighted mean is unchanged at about 76 places per 100. The 2SFCA *ranking* of cells is almost identical (Spearman 0.99), but cell values move (Pearson 0.60), because phantom demand had diluted nearby sites.
4. **Density confounds the SES correlations.** Zählbezirke with more foreign-born residents have *shorter* trips (Spearman ρ ≈ −0.58), because they are dense and central. After adjusting for competition, the 2SFCA score correlates *positively* with the share of tertiary-educated residents (ρ ≈ +0.32), and with the new Zählsprengel-based share of residents working in ICT, finance or professional services (ρ ≈ +0.21). Pennerstorfer & Pennerstorfer found the same direction. Any model needs density or centrality controls.
   * The equity gradients (Fig. 05) run the *opposite* way to the naive expectation. Children with a trip over 15 min are concentrated in the **least** foreign-born quintile (about 2.1% vs ≤ 0.3% elsewhere; previously 7% vs ≤ 1.6%). Areas with the most hospitality and cleaning/security workers have the *shortest* trips (ρ ≈ −0.38). Long trips are in peripheral, lower-density areas, so in Vienna "underserved by time" is mainly a **periphery** story, and a small one.
   * Competition-adjusted places are spread almost evenly across children. The concentration index is about 0 when Zählbezirke are ranked by % foreign-born (−0.006), social housing (+0.009) or low-wage employment (+0.013), and +0.03 (slightly favouring advantaged areas) when ranked by district unemployment. Any SES inequality is subtle, so careful modelling and precise claims matter more than headline gaps.
5. **Everything is spatially clustered.** Moran's I is 0.27 for travel time (previously 0.36), 0.18 for 2SFCA and 0.80 for education (all p = 0.001). Ordinary least squares (OLS) p-values would therefore be over-confident, so spatial regression or robust errors are needed (see §3.4).

> These are first-pass descriptive numbers using a 15-min threshold and 6 departures. Treat them as hypotheses to test, not as results yet.

---

## 3. Spatial analysis primer (Python)

### 3.1 Core ideas you will need to explain in the paper

| Concept | Plain-language meaning | Where it bites in this project |
|---|---|---|
| **Coordinate reference system (CRS)** | How lat/long becomes metres on a flat map. | Use EPSG:3035 (the grid's own CRS) or EPSG:32633 for distances and areas. Never measure in degrees. |
| **Spatial join** | Joining tables by location (point-in-polygon) instead of by a key column. | Grid cell → Zählbezirk, facilities → Zählbezirk. |
| **MAUP (Modifiable Areal Unit Problem)** | Results change with the size and shape of the areas you aggregate to. | Report results at both the 250 m and Zählbezirk levels, and show they agree, or explain why they don't. |
| **Ecological fallacy** | Patterns between areas do not tell you what happens to individuals. | "Zählbezirke with more X have worse access" does **not** mean "X families have worse access". |
| **Dasymetric mapping** | Spreading an area total onto smaller cells using an auxiliary layer of where people actually live. | How we estimate children per 250 m cell. |
| **Spatial weights matrix W** | A table saying which units count as neighbours: shared border (Queen/Rook), *k* nearest, or within a distance. | Required by every spatial statistic below. |
| **Spatial autocorrelation** | Nearby values resemble each other (Tobler's first law). | It breaks OLS's independence assumption. |

### 3.2 Accessibility measures, from simple to rich

1. **Nearest-facility time.** Easy to interpret, but saturated in Vienna. Used for description and maps only.
2. **Cumulative opportunities.** The number of sites or *places* reachable within *T* minutes. Not used in the current analysis.
3. **Gravity / distance-decay.** Like (2), but each place is weighted by `exp(−β·t)` instead of a hard cut-off.
4. **2SFCA family** (two-step floating catchment area). Pennerstorfer used it with straight-line distance; you can now run it with network times.
   * 2SFCA with a binary catchment was the first pass; the current measures use its **E2SFCA** form (distance-decay weights inside the catchment), with a Gaussian weight falling to 0 at 15 min (DV2, DV2R).
   * **M2SFCA / MM2SFCA** correct for supply over- or under-estimation, and MM2SFCA is the multi-modal version. The papers in `Papers/MM2SFCA/` cover these.
5. **Reliability-aware measures.** These are your distinctive contribution:
   * the share of departures within *T* (`share_departures_within_15` in `nearest_site_time_by_cell.csv`; as a 2SFCA weighting: `dv2r_share15`);
   * the **buffer time** (p90 − p50 travel time), a standard transport-reliability index. For the nearest site it is zero for 99% of children (it is usually walkable), so it is not used as an outcome;
   * "**reliable** 2SFCA", which only counts a site if it is reachable in ≥ 95% of departures. *Implemented (18 Nov) as DV2R: the Gaussian 2SFCA on each pair's 90th-percentile travel time; the 80th / 95th percentiles and a share-of-departures-within-15-min weighting are robustness checks.*

   Comparing the 2SFCA "on a typical departure" with the "reliable" 2SFCA shows who loses access once reliability is taken into account.

### 3.3 Inequality and descriptive statistics

* **Child-weighted summaries.** Always weight cells by `children_u6`, otherwise empty parks count as much as housing estates.
* **Equity gradients.** Access by status tercile (analysis Figs. 3 and 7).
* **Concentration curve and concentration index.** These come from health economics (analysis Fig. 8). CI > 0 means access favours advantaged areas.
* **Gini / Lorenz curve** of accessibility across children.
* **Hot-spot analysis.** **LISA** (Local Moran's I) or **Getis-Ord Gi\*** answer "*where* are the significant clusters of poor access?" *Dropped (16 Nov): the maps in `access_maps.ipynb` show the pattern, and the essay has no room for it.*

### 3.4 Explanatory models (in order of complexity)

| Model | Use it for | Python |
|---|---|---|
| OLS with **cluster-robust SE** (by district) and controls for density and distance to the centre | Baseline; directly comparable to Pennerstorfer's eq. (3) | `statsmodels` |
| **Spatial lag (SAR)** model: `y = ρWy + Xβ + ε` | Access in one area depends on access in neighbouring areas (spillover) | `spreg.ML_Lag` / `spreg.GM_Lag` |
| **Spatial error (SEM)** model: `y = Xβ + u, u = λWu + ε` | Omitted variables that are themselves spatially clustered | `spreg.ML_Error` |
| Choosing between them | Lagrange-multiplier (LM) tests on the OLS residuals | `spreg.OLS(..., spat_diag=True, w=W)` |
| **Geographically weighted regression (GWR / MGWR)** | Does the SES–access relationship *differ* across the city, e.g. north vs south of the Danube? | `mgwr` |
| **Logistic regression** on `underserved` (cell level, child-weighted) | "Which characteristics predict a child being underserved?" | `statsmodels` (GLM Binomial with `freq_weights`) |
| **Multilevel model** (cells within Zählbezirke within districts) | When predictors exist at several levels (cell, ZBZ, district) | `statsmodels.MixedLM` |

**Unit of analysis (decided 16 Nov):** the **250 m cell, weighted by children**, with each status variable copied down from its own level and errors clustered at the coarsest level in the model. This is Pennerstorfer's set-up (`explanatory_models_primer.md` §4). The Zählbezirk (n = 250) is used for the planned spatial error model and for the bivariate map.

### 3.5 Toolset

`geopandas`, `shapely`, `pyproj` (vector data), `rasterio` (GHSL raster), `r5py`, `osmnx` (routing and networks, already in use), **PySAL**: `libpysal` (spatial weights), `esda` (Moran, LISA, Getis-Ord), `spreg` (spatial regression), `mgwr` (GWR), plus `mapclassify` (map class breaks), `statsmodels`, and optionally `contextily` (basemaps). `libpysal`, `esda` and `spreg` were installed into your Anaconda environment for this work. `mgwr` is not installed yet: `pip install mgwr`.

Python is fine for this. Everything a GIS package (QGIS/ArcGIS) does here can be done in code, and code is reproducible, which the grading rubric rewards. QGIS is still handy for eyeballing layers.

---

## 4. Explanatory research questions you can answer with the current data

**Descriptive: "who and where"**
1. How many children under 6 live where no childcare site is *reliably* reachable within 10 / 15 / 20 min by foot + public transport? Where are they (LISA clusters)?
2. How much does the straight-line 500 m measure *overstate* or *understate* access? How many children are misclassified, and in which kinds of neighbourhood?
3. How much access do families lose if only **public** sites count, or only sites with places for their child's **age group** (0–3 vs 3–6)?

**Explanatory: "how does access relate to SES"**

4. Is competition-adjusted access (network 2SFCA) lower in Zählbezirke with a higher share of foreign-born residents, more municipal housing, or lower district education and income, **after controlling for density and centrality**?
5. Is travel-time **reliability** worse in lower-SES areas, even where the median time is the same? This is your distinctive question, since the Pennerstorfer measure cannot answer it.
6. Do public and private (mostly non-profit) providers differ in how equitably they cover low-SES areas? This replicates the Pennerstorfer finding with network times rather than Euclidean distance.
7. Are fast-growing new-build areas (high 5-year population change, rising births) under-supplied relative to their children? This is a supply-lag, rather than SES, explanation for poor access.
8. Does the SES–access relationship vary across the city (GWR)? For example, is it stronger in the trans-Danube districts 21 and 22?

**The methodological contribution in one sentence:** *Euclidean catchments (Pennerstorfer) vs network-time 2SFCA vs reliability-adjusted 2SFCA: which children change category, and is that change patterned by SES?* This makes a strong CSS framing: measurement choices have distributional consequences.

---

## 5. Roadmap

| Phase | Tasks | Status (20 Nov) | Output for the paper |
|---|---|---|---|
| **0. Decide scope** | Age group, provider set, thresholds, time window (§6). | ✅ done 13 Nov | Research question and hypotheses (Intro) |
| **1. Outcomes** | (a) Route every minute 07:30–08:29 with one-minute windows (`routing.ipynb`). (b) Pennerstorfer 2SFCA (DV1: 500 m, d⁻²); network 2SFCA averaged over departures (DV2); **reliable network 2SFCA (DV2R)**; reliability loss (DV3); DV2R separately for public and private sites. | ✅ done 17–18 Nov | Methods: accessibility measures; analysis Fig. 6, maps 1–6 |
| **2. Demand and SES** | Official Zählsprengel child counts on the official 100 m grid; four status measures (education, income, knowledge jobs, rent index); controls (density, % foreign-born, employment rate, U-Bahn; Gemeindebau as robustness). | ✅ done 13–16 Nov | Data section; descriptive table (EDA §3–4) |
| **3. Descriptive inequality** | Child-weighted equity gradients by status tercile; concentration curves and indices; access maps. LISA dropped. | ✅ done 18 Nov | Analysis Figs. 3, 7, 8; maps 4, 6, 7 |
| **4. Explanatory models** | Model A (child-weighted OLS, clustered SE, one status measure at a time) and Model B (public vs private). | ✅ done 18 Nov | Regression table; analysis Fig. 4 |
| **5. Robustness** | Catchments 10/20 min, 80th/95th percentiles, share-of-departures weighting, Gemeindebau control: ✅ done. Still open: spatial error model at Zählbezirk level; under-3 / 3–5 age split. | 🟡 mostly done | Appendix or short robustness paragraph |
| **6. Write and present** | About 5,000 words, 2–6 figures; slides. Shiori: theory sections. | ⏳ not started | Paper and presentation |

**Suggested hypotheses**
* H1: Network-based, competition-adjusted access is lower in low-SES Zählbezirke, net of density.
* H2: Low-SES areas suffer more from timetable unreliability than their median travel time suggests.
* H3: Public provision is more evenly spread across SES than private/non-profit provision (Pennerstorfer replication).

---

## 6. Clarifying questions

**Answers (13 Nov 2026)**
1. Provider set: all sites, with **public vs private** compared throughout (private ≈ non-profit; for-profits can't get city funding). The essay must say the dataset covers all childcare, not only public.
2. Age group: main analysis all under-6s; under-3 / 3–5 as a sensitivity check, as in Pennerstorfer Appendix B (mixed groups split ⅓ / ⅔).
3. Trip: home → childcare only, morning.
4. Main outcome: Pennerstorfer-comparable 2SFCA, extended with network times and reliability.
5. Data budget: nothing paid. Optionally ask the professor about CEU / AMDC access to 250 m education data.
6. Compute: the minute-by-minute routing ran once on 17 Nov (3.3 h). Nobody needs to re-run `routing.ipynb`: the matrices are on the repository release.
7. Team: Stash (analysis) and Shiori (theory sections); Onur is not on the team. Sync needed.

*Original questions:*

1. **Provider set.** You wrote "public childcare locations", but the data has 392 public and 1,290 private (mostly non-profit, publicly funded) sites, and the existing routing used all of them. Should the focus be all sites, public only, or the public-versus-private comparison?
2. **Age group.** Should the study cover all under-6s, or separate 0–3 (crèche, where shortages are real) from 3–6 (kindergarten, near-universal take-up, with the final year compulsory)?
3. **Trip definition.** Is the trip home → childcare only, or home → childcare → workplace (trip chaining)? Should departures cover the morning only, or also an afternoon pick-up window? What threshold should define "accessible": 10, 15 or 20 min?
4. **Main outcome.** Given finding #1 in §2, are you happy to make capacity/competition-adjusted access (2SFCA) the headline, with nearest-time as the baseline?
5. **Data budget.** Can you, or CEU, pay for or request Statistik Austria 250 m grid data? If not, is the Zählbezirk the accepted unit of analysis?
6. **Compute.** Which machine will run the re-routing (8 GB Mac or 32 GB desktop)? This decides between a 60–90-min departure window and coarser sampling.
7. **Team split and deadline.** Who owns which phase (e.g. Onur on routing or OSM, you on SES and models), and when are the presentation and paper due?

---

## 7. Caveats to state in the paper

* Child counts are **official register counts per Zählsprengel** (1 Jan 2026), but their placement *within* a Zählsprengel is modelled: they are assumed to live where residents of all ages live (official 100 m grid), then split onto 250 m cells by area. Age 5 is approximated as one fifth of the 5–9 band, and the under-3 / 3–5 split uses Zählbezirk birth shares.
* SES is measured at the area level, so watch for the **ecological fallacy**. Education and income exist only for **23 districts**, so treat them as context or a cluster level.
* Capacity means **authorised** places, not vacancies; 133 sites have none recorded.
* Reliability is **timetable-based** variability, not observed delays.
* All associations are observational. Households choose where to live, partly because of childcare (Pennerstorfer & Pennerstorfer make the same point).
