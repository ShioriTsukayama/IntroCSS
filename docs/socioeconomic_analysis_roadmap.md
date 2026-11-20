# Childcare accessibility and neighbourhood status in Vienna: project overview

*Prepared 12 November 2026; revised 20 November 2026. Paths are relative to the project folder (`analysis/` in the shared repository, `'My' Code/` in the authors' local copy).*

**Contents**
1. Research question and hypotheses
2. Current status and principal results
3. Analytical pipeline
4. Data
5. Measures and models
6. Work plan
7. Scope decisions
8. Development of the measures (13–18 November)
9. Limitations

---

## 1. Research question and hypotheses

The project asks whether access to childcare by walking and public transport in Vienna differs with neighbourhood socio-economic status. It replicates the design of Pennerstorfer & Pennerstorfer (2021), who measured access with a straight-line two-step floating catchment area (2SFCA), and extends it in two respects: travel times are derived from the public-transport timetable rather than from straight-line distance, and access is evaluated by the travel time that can be relied upon across the morning, not only on an average departure.

The methodological contribution can be summarised as a comparison of three measurement choices: straight-line catchments, timetable-based 2SFCA, and reliability-adjusted 2SFCA. The question is which children change position between them, and whether that change is patterned by status. Measurement choices of this kind have distributional consequences.

**Hypotheses**
* **H1.** Network-based, competition-adjusted access is lower in lower-status neighbourhoods, net of population density.
* **H2.** Lower-status neighbourhoods are more exposed to timetable unreliability than their median travel times suggest.
* **H3.** Public provision is distributed more evenly across neighbourhood status than private (predominantly non-profit) provision, as reported by Pennerstorfer & Pennerstorfer.

---

## 2. Current status and principal results

*As of 20 November 2026.* Routing, variable construction, the descriptive analysis and the main models are complete. Robustness analysis is largely complete. The written report has not yet been started.

**Outcome measures.** The primary outcome is **DV2R, the reliable network 2SFCA**: for each cell–site pair, the 90th-percentile travel time across the 60 departures (the time on which a parent can rely at nine of ten departures) enters a Gaussian distance-decay function. DV2 (the network 2SFCA averaged over departures) serves as the comparison, DV3 (the share of access lost at an unfavourable departure) as the reliability outcome, and DV1 (straight-line 2SFCA) as the replication of Pennerstorfer & Pennerstorfer.

**Principal results**
* Higher neighbourhood status is associated with greater DV2R access, net of density and controls: β ≈ +0.08 to +0.10 standard deviations per standard deviation of status for all four status measures (p ≤ 0.01), or approximately +4 places per 100 children (mean 80). DV1 yields the same direction (β +0.06 to +0.09; for income p = 0.06). This is consistent with H1.
* The association is driven by **private** sites (β ≈ +0.19 to +0.28). Access to **public** sites is oriented towards lower-status areas (β ≈ −0.06 to −0.15; not significant for income), consistent with H3.
* Higher-status areas also lose less access at an unfavourable departure (DV3: β ≈ −0.08 to −0.10; not significant for income), consistent with H2.
* Requiring reliability reduces the number of cell–site pairs within 15 minutes by 19% (from 97,432 to 78,560) but **redistributes** rather than reduces access. Because a 2SFCA allocates all places among the children who can reach them, the child-weighted mean is 80.3 places per 100 children under every measure. Approximately one third of children gain more than 3 places per 100 and one third lose more than 3 (`access_maps.ipynb`, map 2).
* DV1 and DV2R rank cells quite differently (Spearman ρ = 0.72; 32% of children move by more than 25 percentiles). The shift is itself patterned by status: higher-status areas gain approximately 2–3 percentiles per standard deviation of status under DV2R (p ≤ 0.01).
* Travel time to the nearest site is saturated: for 96.8% of children it does not change across the hour, and practically all children have a site within 15 minutes. Differences in access therefore arise from capacity and competition rather than from distance.
* Reach declines slightly over the hour (approximately 2% fewer pairs within 15 minutes by 08:29), because the timetable thins after the peak: scheduled bus departures fall by 12% between 07:30 and 08:29, while tram and U-Bahn services change little. Status gradients are constant across departure minutes (analysis Fig. 5).
* The results are robust to 10- and 20-minute catchments, to the 80th and 95th percentiles, to a share-of-departures weighting, and to a control for municipal housing (status coefficients change by a median of 8%, with no change in significance).

**Outstanding:** a spatial error model at Zählbezirk level; the under-3 / 3–5 age split; the report and presentation.

---

## 3. Analytical pipeline

Each notebook reads only what the preceding notebooks have saved. Notebooks are generated from scripts in `Data/socioeconomic/scripts/*_source.py`.

| Step | Notebook | Content | Output |
|---|---|---|---|
| 1 | `routing.ipynb` | Walking and public-transport travel times from 6,950 cells to 1,682 sites, every minute from 07:30 to 08:29 (r5py 1.1.7). Routed once on 17 November (3.3 hours) | `outputs/origin_destination_matrices_1min/`, `outputs/routing_origins.csv`, `outputs/nearest_site_time_by_cell.csv` |
| 2 | `socioeconomic_eda.ipynb` | Children aged 0–5 per cell; the four status measures; controls | `Data/socioeconomic/processed/grid250_analysis.gpkg` |
| 3 | `accessibility_analysis.ipynb` | Access measures DV1, DV2R, DV2, DV3; Models A and B; robustness; analysis figures 1–9 | `Data/socioeconomic/processed/grid250_access_measures.csv`, `outputs/analysis/` |
| 4 | `access_maps.ipynb` | Presentation maps | `outputs/maps/` |

---

## 4. Data

All sources are open data, with the exception of the rent index, which is constructed from scraped advertisements. The full list, with the status and location of every file, is in `data_inventory.md`; sources and merging procedures are documented in `data_sources_and_merging_guide.md`.

| Dataset | Spatial level | Reference date | Use |
|---|---|---|---|
| Childcare sites (`KINDERGARTENOGD`) | 1,682 sites | current | Capacity by age group; public vs private provider (`TXTATT1`) |
| Population by 5-year age group (Statistik Austria) | 1,368 Zählsprengel | 1 Jan 2026 | Children aged 0–5 (demand and regression weight) |
| Official resident grid (Statistik Austria) | 100 m | 1 Jan 2026 | Dasymetric allocation of children to cells |
| Employed residents by sector (Statistik Austria) | Zählsprengel | 31 Oct 2024 | Status measure (knowledge-sector share); employment-rate control |
| Education of 25–64-year-olds (MA 23) | 23 districts | 2023 | Status measure (% with tertiary degree) |
| Employee net income (MA 23) | 23 districts | 2023 | Status measure (mean net income) |
| Asking rents (willhaben, own scrape) | Zählsprengel centroids | 16 Nov 2026 | Status measure (rent per m² of a standard flat; `rent_measure_reference.md`) |
| Population by birthplace (MA 23) | 250 Zählbezirke | 1 Jan 2026 | Control (% born abroad) |
| Live births (MA 23) | Zählbezirke | 2015–2025 | Under-3 / 3–5 split |
| Municipal housing estates (Wiener Wohnen) | 1,776 estates | current | Robustness control |
| Timetable (GTFS) and street network (OpenStreetMap) | — | Oct 2026 | Routing |

**Data not available from open sources**
* **Education, country of birth and female employment at 250 m resolution**, as used by Pennerstorfer & Pennerstorfer. Statistik Austria supplies these as paid extracts (approximately €350 per order plus a per-variable fee, scaled by area); the Austrian Micro Data Center (AMDC) offers access to accredited researchers. Child counts no longer require purchase, since the open Zählsprengel age table provides them. The cell-level joins in the EDA notebook would accept such variables without modification (`data_sources_and_merging_guide.md` §1d).
* **Observed transit delays.** The GTFS feed describes the timetable, so the reliability measured here is **schedule-based variability** (waiting for the next service and missed connections), not delay or crowding. Observed delays would require Wiener Linien real-time data logged over several weeks.
* **Opening hours and vacancies.** The site register lists authorised places, not available ones; 133 sites report no capacity.

---

## 5. Measures and models

Definitions, toy examples and code are given in `methods_primer.md` (accessibility measures, dasymetric mapping, inequality measures, spatial statistics) and `explanatory_models_primer.md` (model choice).

**Accessibility measures.** Nearest-site travel time is reported descriptively only, as it is saturated in Vienna. The analysis uses the 2SFCA family in its enhanced form, with a Gaussian weight that declines from 1 at 0 minutes to 0 at 15 minutes. The reliability-adjusted variant (DV2R) evaluates each pair at its 90th-percentile travel time. This corresponds to *planning time* in the transport-reliability literature. Robustness variants use the 80th and 95th percentiles and a weighting by the share of departures within 15 minutes.

**Inequality measures.** All summaries are weighted by the number of children per cell. Equity gradients by child-weighted status tercile (analysis Figs. 3 and 7) and concentration curves and indices (Fig. 8) describe the distribution of access. Local indicators of spatial association (LISA) were considered and not pursued; the maps in `access_maps.ipynb` show the spatial pattern.

**Models.** Model A is an ordinary least squares regression on 250 m cells, weighted by children, with one standardised status measure at a time, controls for child density, the share of foreign-born residents, the employment rate and the presence of a U-Bahn station, and standard errors clustered at the coarsest level of any variable in the model. This follows Pennerstorfer & Pennerstorfer. Model B repeats Model A separately for public and private sites. A spatial error model at Zählbezirk level is planned as a robustness check.

**Unit of analysis.** The 250 m cell weighted by children is the unit of analysis, with each status variable assigned from its native level. The Zählbezirk (n = 250) is used for the spatial error model and for the bivariate map.

---

## 6. Work plan

| Phase | Tasks | Status (20 Nov) | Contribution to the report |
|---|---|---|---|
| 0. Scope | Age group, provider set, thresholds, time window (§7) | Completed 13 Nov | Research question and hypotheses |
| 1. Outcomes | Routing every minute 07:30–08:29; DV1, DV2, DV2R, DV3; DV2R by provider type | Completed 17–18 Nov | Methods: accessibility measures; analysis Fig. 6; maps 1–6 |
| 2. Demand and status | Official child counts on the 100 m grid; four status measures; controls | Completed 13–16 Nov | Data section; descriptive table |
| 3. Descriptive inequality | Equity gradients; concentration curves and indices; maps | Completed 18 Nov | Analysis Figs. 3, 7, 8; maps 4, 6, 7 |
| 4. Explanatory models | Models A and B | Completed 18 Nov | Regression table; analysis Fig. 4 |
| 5. Robustness | Catchments, percentiles, share-of-departures weighting, municipal-housing control (completed); spatial error model and age split (outstanding) | Largely completed | Appendix or robustness paragraph |
| 6. Report and presentation | Report of approximately 5,000 words with 2–6 figures; slides. Theory sections: Shiori | Not started | Report and presentation |

**Further research questions supported by the data**
1. How many children under six cannot *reliably* reach a site within 10, 15 or 20 minutes, and where do they live?
2. How far does the 500 m straight-line measure overstate or understate access, and in which neighbourhoods are children misclassified?
3. How much access is lost if only public sites, or only sites with places for the relevant age group (0–3 or 3–6), are counted?
4. Are rapidly growing new-build areas under-supplied relative to their child population, independently of status?
5. Does the status–access relationship vary across the city, for example north and south of the Danube (geographically weighted regression; outside the present scope)?

---

## 7. Scope decisions

*Agreed 13 November 2026.*
1. **Provider set.** All sites, with public and private provision compared throughout. Private providers are predominantly non-profit, since for-profit providers are not eligible for municipal funding. The report must state that the register covers all childcare provision.
2. **Age group.** All children under six in the main analysis; under-3 and 3–5 as a sensitivity analysis, following Pennerstorfer & Pennerstorfer (Appendix B), with mixed-age groups split one third to two thirds.
3. **Trip.** Home to childcare, morning departures only.
4. **Outcome.** A 2SFCA comparable to Pennerstorfer & Pennerstorfer, extended with timetable-based travel times and reliability.
5. **Data budget.** Open data only. Access to 250 m education data through CEU or the AMDC may be requested.
6. **Team.** Analysis: Stash. Theory sections: Shiori.

---

## 8. Development of the measures (13–18 November)

This section records the first descriptive analysis, which used six 10-minute departure windows and a binary 2SFCA. It is retained because it motivated the move from nearest-site travel time to a competition-adjusted, reliability-based measure. Its figures are archived locally; their successors are analysis Figs. 6–8.

* **Demand model.** On 13 November the child counts were rebuilt from official Zählsprengel age data allocated over the official 100 m resident grid. The earlier estimate (births combined with the modelled JRC GHSL population grid) matched the city total but placed approximately 2,400 children in 196 uninhabited cells. Because these cells lay mostly far from sites, the earlier estimate inflated the share of children with a median trip above 15 minutes (1.4% rather than 0.4%; `data_sources_and_merging_guide.md` §4). The episode illustrates how the spatial assumptions of a demand model can determine a headline result.
* **Saturation of nearest-site time.** Approximately 0.4% of the 111,600 children aged 0–5 lived in cells whose median trip to any site exceeded 15 minutes, and fewer than 0.1% lived within 500 m of a site that could not be reached within 15 minutes. With 1,682 sites in a dense city, nearest-site time offers almost no variation for a regression to explain.
* **Capacity and competition.** The number of reachable places and the 2SFCA score varied widely across the city, with the outer districts (10, 11, 21, 22, 23) and the urban fringe standing out.
* **Public sites.** Approximately 2.1% of children had no public site within a 15-minute median trip, which links the analysis to the public versus non-profit argument of Pennerstorfer & Pennerstorfer.
* **Confounding by density.** Zählbezirke with more foreign-born residents had *shorter* trips (ρ ≈ −0.58), because they are dense and central. After adjustment for competition, the 2SFCA correlated positively with the share of tertiary-educated residents (ρ ≈ +0.32). Any model therefore requires density controls.
* **Spatial clustering.** Moran's I was 0.27 for travel time, 0.18 for the 2SFCA and 0.80 for education (all p = 0.001), so unadjusted OLS standard errors would be too small. This motivated clustered standard errors and the planned spatial error model.

---

## 9. Limitations

* **Child counts.** Counts are official register counts per Zählsprengel (1 January 2026), but their placement within a Zählsprengel is modelled: children are assumed to live where residents of all ages live (official 100 m grid) and are then allocated to 250 m cells by area. Age 5 is approximated as one fifth of the 5–9 band, and the under-3 / 3–5 split uses Zählbezirk birth shares.
* **Ecological inference.** Status is measured at area level, so associations describe neighbourhoods, not households. Education and income are available for 23 districts only and carry correspondingly little information.
* **Capacity.** Capacity refers to authorised places, not vacancies; 133 sites report none, and their capacity is imputed from the median of their provider type.
* **Reliability.** Reliability is timetable-based variability, not observed delay.
* **Network coverage.** The timetable covers Wiener Linien and Wiener Lokalbahnen only; ÖBB S-Bahn services are not included.
* **Causality.** All associations are observational. Households choose where to live, partly in response to childcare provision, as Pennerstorfer & Pennerstorfer also note.
