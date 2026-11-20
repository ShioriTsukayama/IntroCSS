# The housing-cost status measure: how it is built, and how it compares

*Written 16 Nov 2026, checked 20 Nov 2026. Companion to `data_inventory.md` and `methods_primer.md`. Documents the fourth neighbourhood status measure, `rent_eur_m2_std` ("asking rent per m² for a standard flat, per Zählsprengel"), and compares it with Pennerstorfer & Pennerstorfer's (2021) house prices, Onur's earlier scrape, and the simple alternative of average rent per room per district.*

**Contents**
1. Summary table
2. Step-by-step comparison: Pennerstorfer vs ours
3. Toy example: every step on 15 made-up listings
4. The real pipeline in detail
5. Onur's approach, step by step
6. The simple alternative: average rent per room per district
7. Maps (EDA notebook §3e)
8. What to say in the paper
9. Files and how to re-run

---

## 1. Summary table

| | **Pennerstorfer & Pennerstorfer (2021)** | **Onur (Oct 2026)** | **Simple alternative** | **Ours (16 Nov 2026)** |
|---|---|---|---|---|
| Measures | Estimated **purchase price** per m² | Asking rent per listing (in our EDA: per room) | Asking rent per room | Asking **rent per m²** |
| Source | DataScience GmbH (proprietary model) | willhaben, browser scrape | willhaben (either scrape) | willhaben, embedded page data |
| Year | 2015 | Oct 2026 | — | 16 Nov 2026 |
| Location of listings | n/a (modelled) | Google geocoding of text address; ~1/3 at district centres | Postcode → district (no coordinates needed) | willhaben's own coordinates; postcode-only listings dropped |
| Floor area | yes | no | not used | yes |
| Adjusts for the kind of flat | yes ("standardised apartment") | no | no | yes (hedonic model) |
| Unit | ~1,364 Zählsprengel centroids | 250 Zählbezirke (≥ 5 listings) | 23 districts | 1,368 Zählsprengel centroids |
| Errors clustered at | Zählsprengel | — (descriptive only) | district | Zählbezirk |
| Effort | none for the authors (bought) | high (browser, Google API) | very low | moderate (two scripts) |

**Our design goal:** get as close as free data allow to Pennerstorfer's *"estimated purchase price of a standardized apartment located at the centroid of the SED"* (2021, §4.2).

---

## 2. Step-by-step comparison: Pennerstorfer vs ours

Pennerstorfer did not build the measure; DataScience did, with the hedonic method of Brunauer, Feilmayr & Wagner (*Der österreichische Wohnimmobilienpreisindex*, Statistik Austria / OeNB). Their column below therefore mixes what the paper states (**stated**) and what the cited method does in general (*method*). We cannot inspect DataScience's actual model or data.

| # | Step | Pennerstorfer (via DataScience) | Ours | Why we differ / what it changes |
|---|---|---|---|---|
| 1 | **Raw data** | *Method:* property transactions and/or offers with price, size, characteristics and location | 5,347 willhaben rental adverts, scraped once | We have no purchase data. Rent is a flow, price a stock; both capitalise location value |
| 2 | **Price concept** | **Stated:** purchase price per m² | Monthly asking rent ÷ living area | Rents are partly regulated in Vienna (*Richtwert*); prices are not. Rent captures the *current* entry cost to a neighbourhood |
| 3 | **Locating each observation** | *Method:* address-level geocodes | willhaben's coordinates; precision flag `LOCATION_QUALITY`; only address/street-precise kept (622 postcode-only dropped) | Same principle: an observation must sit where the flat is, not at an area centre |
| 4 | **Cleaning** | Not described | Explicit rules (§4.2): plausible area and €/m², 1–99th percentile trim, duplicate adverts removed → 4,071 | Adverts contain typos and multi-agent duplicates that transaction registers don't |
| 5 | **Removing the flat mix (standardisation)** | **Stated:** "standardized apartment". *Method:* hedonic regression on size, age, condition, floor, outdoor space, etc. | Hedonic OLS of log €/m² on size, rooms, floor, outdoor space, new-build, private vs agency, flat type (R² = 0.25) | Same idea. We have fewer traits (no building age or condition), so some flat quality remains in our location signal |
| 6 | **Separating location from flat** | *Method:* location enters the hedonic model directly (smooth spatial terms / area effects) | Location is what the hedonic model leaves over (the residual), averaged in space in step 7 | Two-stage instead of one model. Simpler and transparent; slightly less efficient |
| 7 | **Spatial unit and smoothing** | **Stated:** value per SED (Zählsprengel); *method:* the model borrows strength across space | Gaussian kernel over the **20 nearest listings** at each Zählsprengel's interior point; k chosen by leave-one-out error; median radius 502 m | Both borrow strength from neighbours; ours does it openly, with a bandwidth you can report |
| 8 | **Evaluation point** | **Stated:** centroid of the Zählsprengel | Representative interior point of the Zählsprengel (always inside the polygon) | Same; ours avoids centroids falling outside oddly shaped units |
| 9 | **Output** | € per m² purchase price of a standard flat, per Zählsprengel | € per m² monthly rent of a standard flat (65 m², 2 rooms, 1st–2nd floor, no outdoor space, not new-build, agency advert), per Zählsprengel | Same structure, different price concept |
| 10 | **To grid cells** | **Stated:** each cell takes its Zählsprengel's value | Same (`zsp_id` join) | Identical |
| 11 | **Timing** | **Stated:** 2015 values used for all years 2007–14 | Nov 2026 snapshot; matches the 2026 child counts | Ours is contemporaneous; theirs was not |
| 12 | **In the regression** | **Stated:** one status measure at a time; terciles in figures | Same; child-weighted z-score | Identical design |
| 13 | **Standard errors** | **Stated:** clustered at SED (Zählsprengel) | Clustered at **Zählbezirk** | Our kernel shares listings between neighbouring Zählsprengel, so their errors are correlated; clustering one level up is the honest choice |

**In one sentence:** the same target (location value of a standard flat at each Zählsprengel centre, given to every cell inside it), built with an open two-stage method on current asking rents instead of a proprietary one-stage model on purchase prices.

---

## 3. Toy example: every step on 15 made-up listings

Script: `Data/socioeconomic/scripts/rent_index_toy_example.py`. All numbers below are its real output.

### 3.1 The set-up

A 1,200 m street with three Zählsprengel: **A** (0–400 m), **B** (400–800 m) and **C** (800–1,200 m). We *know* the truth, because we made the data:

* A standard 65 m² old flat costs **A €15.0, B €16.5, C €18.0** per m².
* New-builds cost **+30%** per m². Every +10% of floor area costs **−1.5%** per m² (larger flats are cheaper per m²).
* There is small random noise (±3%).

Zählsprengel B contains a new-build project. C has a single good listing.

| id | x (m) | ZSP | area m² | new-build | rent € | note |
|---|---|---|---|---|---|---|
| 1–5 | 40–340 | A | 50–85 | id 5 only | 909–1,237 | |
| 6–9 | 430–580 | B | 48–60 | yes | 1,097–1,366 | new-build project |
| 10, 11 | 640, 720 | B | 55, 80 | no | 949, 1,254 | |
| 12 | 1,000 | C | 75 | no | 1,308 | the only listing in C |
| 13 | 520 | B | 60 | yes | 1,366 | **same flat as id 8**, second agent |
| 14 | 600 | B | 65 | no | 1,072 | **postcode-centre location only** |
| 15 | 900 | C | 66 | no | 11,880 | **typo**: annual rent typed as monthly |

### 3.2 Step 2: cleaning

| Rule | Removes | Why |
|---|---|---|
| `LOCATION_QUALITY` < 0.75 | id 14 | Its point is a postcode centre, not the flat |
| € per m² outside 5–60 | id 15 (€180/m²) | A typo |
| Same position, area and rent | id 13 | Duplicate advert of id 8 |

12 listings remain: **A 5, B 6, C 1**.

### 3.3 What the simple approaches would say

| | A | B | C | Truth A / B / C |
|---|---|---|---|---|
| Raw median € per m² | 14.66 | **22.81** | 17.44 | 15.0 / 16.5 / 18.0 |
| Raw median rent per room | 412 | **561** | 436 | |
| Single district median € per m² | 17.35 | 17.35 | 17.35 | |

* **B looks 56% dearer than A**; the truth is 10%. Its listings are mostly new-builds, so the raw median measures *what is for sale there*, not the *location*. This is the flat-mix problem.
* **C rests on one listing.** Here it happens to be close, but one listing can be anything.
* **The district median** erases all differences between A, B and C.

### 3.4 Step 3: hedonic model (flat traits only)

```
log(€/m²) = a + b1·log(area) + b2·new_build + e
```

| | Estimated | Truth |
|---|---|---|
| b1 (log area) | −0.141 | −0.15 |
| b2 (new-build) | +0.331 | +0.30 |
| R² | 0.91 | |

The model has **no location variables**, so the residual `e` is "how much more or less this flat costs than a flat like it would on average": location plus noise. New-builds exist in both A (id 5) and B, so the model can tell "new-build" apart from "in B". In the real data new-builds are spread across the city, which is what makes this work.

| id | ZSP | € per m² | new-build | residual |
|---|---|---|---|---|
| 1 | A | 15.13 | 0 | −0.031 |
| 2 | A | 14.66 | 0 | −0.079 |
| 3 | A | 14.55 | 0 | −0.042 |
| 4 | A | 14.57 | 0 | −0.061 |
| 5 | A | 21.06 | **1** | −0.078 |
| 6 | B | 23.73 | **1** | +0.047 |
| 7 | B | 22.85 | **1** | −0.002 |
| 8 | B | 22.77 | **1** | +0.026 |
| 9 | B | 22.94 | **1** | +0.008 |
| 10 | B | 17.26 | 0 | +0.067 |
| 11 | B | 15.68 | 0 | +0.024 |
| 12 | C | 17.44 | 0 | +0.121 |

Id 5 costs €21 per m² but has a *negative* residual. It is expensive because it is new, not because A is a good location. Mean residual by Zählsprengel: A −0.058, B +0.028, C +0.121. The ranking is now right (A < B < C).

**Standard flat:** the model's prediction for a 65 m² old flat at an *average* location is **€15.76 per m²**. Each Zählsprengel's index = standard flat × exp(its location residual).

### 3.5 Step 4: kernel over the k nearest listings

For each Zählsprengel centre (A at 200 m, B at 600 m, C at 1,000 m):

1. Find the **k nearest listings**, from any Zählsprengel.
2. **Bandwidth** h = distance to the k-th of them.
3. **Weight** each listing: w = exp(−½ · (d / (h/2))²). Distance 0 → weight 1; the k-th listing → 0.14.
4. **Weighted mean residual** = Σ w·e / Σ w.
5. **Index** = 15.76 × exp(weighted mean residual).
6. **Effective sample size** n_eff = (Σ w)² / Σ w², how many "full-weight" listings the estimate is worth.

**Choosing k (leave-one-out):** take each listing out, predict its residual from its k nearest *other* listings, and measure the error.

| k | 2 | 4 | **6** | 11 | no location |
|---|---|---|---|---|---|
| RMSE | 0.0471 | 0.0441 | **0.0433** | 0.0536 | 0.0587 |

Too small a k chases noise; too large a k averages away real differences. k = 6 is best here.

**Result with k = 6:**

| ZSP | nearest listings (id: distance) | bandwidth | n_eff | mean residual | **index** | truth |
|---|---|---|---|---|---|---|
| A | 3:10, 4:60, 2:90, 5:140, 1:160, 6:230 m | 230 m | 4.8 | −0.054 | **14.93** | 15.0 |
| B | 9:20, 10:40, 8:80, 11:120, 7:130, 6:170 m | 170 m | 4.6 | +0.030 | **16.23** | 16.5 |
| C | 12:0, 11:280, 10:360, 9:420, 8:480, 7:530 m | 530 m | 4.1 | +0.065 | **16.82** | 18.0 |

What this shows:
* **A and B are now right** to within 2%, against a raw median that was 38% off for B.
* **The bandwidth adapts**: 170–230 m where listings are dense, 530 m in C where they are sparse.
* **C shows the price of borrowing.** With one listing of its own, C leans on its cheaper neighbours in B and is pulled down (€16.8 vs €18.0). The kernel trades a little bias for much less noise. This is the same shrinkage that makes our index *understate* extremes at the edges of expensive or cheap areas, and why we report the bandwidth and n_eff for every Zählsprengel.

---

## 4. The real pipeline in detail

Scripts are in `Data/socioeconomic/scripts/`; run them from `Data/socioeconomic` with `python -I`.

### 4.1 Collection (`scrape_willhaben.py`)

1. **URL:** `https://www.willhaben.at/iad/immobilien/mietwohnungen/wien?rows=90&page=N`, the plain Vienna rental search with 90 results per page and none of the parameters robots.txt disallows. Pages 1–61 were requested in order.
2. **Pace:** one request per page with a random pause of 6–10 s; 61 requests in about 8 minutes. Up to 3 retries per page with 60 s waits (none were needed).
3. **Parsing:** each page contains `<script id="__NEXT_DATA__" type="application/json">`, the full search result as JSON. Path: `props → pageProps → searchResult → advertSummaryList → advertSummary[]`. Each advert has a list of `{name, values}` attributes, turned into a dictionary.
4. **De-duplication across pages** by advert id (`ADID`). None occurred, so paging was stable.
5. **Fields kept:**

| Field | Meaning | Used for |
|---|---|---|
| `ADID` | advert id | de-duplication, matching in maps |
| `COORDINATES` | "lat,lon" | location |
| `LOCATION_QUALITY` | 1.0 address, 0.79 street, 0.5 postcode centre | cleaning |
| `POSTCODE`, `DISTRICT`, `LOCATION` | administrative location | checks, district alternative |
| `PRICE` | total monthly rent, € | rent |
| `ESTATE_SIZE/LIVING_AREA` (fallbacks `…/USEABLE_AREA`, `ESTATE_SIZE`) | m² | € per m² |
| `NUMBER_OF_ROOMS` | rooms | hedonic model |
| `FLOOR` | floor number | hedonic model |
| `FREE_AREA_TYPE_NAME` | balcony / terrace / loggia / garden | hedonic model |
| `PROJECT_ID` | part of a new-build project | hedonic model |
| `ISPRIVATE` | private landlord (1) vs agency (0) | hedonic model |
| `PROPERTY_TYPE` | flat, attic flat, ground-floor flat, maisonette, … | hedonic model |
| `PUBLISHED_String` | advert date | documentation |

   **Not kept:** headings, descriptions, photos, advertiser names, contact details.
6. **Output:** `raw/willhaben_rents_2026-11-16.csv`, with **5,347** of the 5,353 adverts the site reported (6 disappeared during paging).

**Ethics / ToS:** willhaben's robots.txt forbids automated access unless willhaben grants it. The team decided to proceed for this non-commercial course project, kept the footprint minimal and stored no personal data. Say so in the paper.

### 4.2 Cleaning (`build_rent_index.py`, part 1)

| Order | Rule | Removed | Left | Reason |
|---|---|---|---|---|
| | Scraped | | 5,347 | |
| 1 | Coordinates, rent and area all present | 149 | 5,198 | Can't place or normalise |
| 2 | `LOCATION_QUALITY` ≥ 0.75 | 622 | 4,576 | Postcode-centre points stack on one spot, like Onur's district centres |
| 3 | Area 15–300 m² | 35 | 4,541 | Parking spaces, storage, whole buildings, typos |
| 4 | € per m² between 5 and 60 | 13 | 4,528 | Typos (annual rent, price per m² entered as price) |
| 5 | Within the 1st–99th percentile of € per m² (€9.7–46.6) | 92 | 4,436 | Remaining extremes (short-let, luxury serviced flats) |
| 6 | Not a duplicate: same position (4 decimals of a degree ≈ 10 m), area and rent | 364 | 4,072 | The same flat advertised by several agents |
| 7 | Inside a Vienna Zählsprengel polygon | 1 | **4,071** | Edge case |

* Rent per m² = `PRICE` ÷ area, where area is living area, else usable area, else total area.
* Coordinates are projected to EPSG:3035 (metres) and joined to Zählsprengel polygons (`processed/zaehlsprengel_2026_inspire.gpkg`) by point-in-polygon.
* The log is saved to `processed/rent_index_cleaning_log.csv`.

### 4.3 Hedonic model (`build_rent_index.py`, part 2)

```
log(€/m²) = a + b·log(area) + rooms + floor band + outdoor + new_project + private_ad + property type + e
```

| Variable | Coding | Reference category |
|---|---|---|
| `log_area` | log m² | — |
| `rooms_c` | 1, 2, 3, 4, 5+ (missing → median) | 1 room |
| `floor_c` | ground, 1–2, 3–5, 6+, unknown (27% missing) | 1–2 |
| `outdoor` | 1 if any balcony / terrace / loggia / garden | — |
| `new_project` | 1 if advert belongs to a new-build project | — |
| `private_ad` | 1 if private landlord | — |
| `ptype` | property type; types with < 30 adverts pooled as "other" | attic flat (alphabetically first) |

Estimates (OLS, n = 4,071, R² = 0.25), as % effect on € per m² (≈ exp(b) − 1):

| Trait | Effect |
|---|---|
| +10% floor area | −1.7% |
| 2 rooms (vs 1) | −6%; 4 rooms +9%; 5+ rooms +15% (at equal area, more rooms = better-divided flats) |
| Floor 3–5 / 6+ (vs 1–2) | +4% / +26% |
| Ground floor | +5% (unexpected sign; not investigated, possibly garden flats) |
| Floor unknown | +5% |
| Outdoor space | +11% |
| New-build project | +7% |
| Private landlord | −11% |
| Ground-floor flat / regular flat (vs attic flat) | −8% / −3% |

**Standard flat** = median area (65 m²), modal rooms (2), modal floor band (1–2), modal type (regular flat), no outdoor space, not new-build, agency advert. Prediction at an average location: **€18.80 per m²**.

**Why these traits:** they are what the listing data reliably contain and what determines price independently of location. **Missing:** building age, condition and fittings. Where these cluster in space (e.g. *Gründerzeit* stock in the inner districts), they remain in the location signal.

### 4.4 Spatial kernel (`build_rent_index.py`, part 3)

For every Zählsprengel *z* with interior point p_z, and listings *i* with hedonic residual e_i:

```
d_i   = distance from p_z to listing i (metres)
h_z   = distance to the k-th nearest listing          (adaptive bandwidth)
w_i   = exp(−½ · (d_i / (h_z/2))²)  for the k nearest, 0 otherwise
m_z   = Σ w_i·e_i / Σ w_i                              (local location effect, log scale)
index = exp(standard-flat prediction + m_z)            (€ per m², standard flat)
n_eff = (Σ w_i)² / Σ w_i²                              (effective number of listings)
```

**Choice of k** by leave-one-out RMSE of the log residual:

| k | 10 | 15 | 20 | 30 | 40 | 60 | 80 | 120 | 160 | 200 | no location |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RMSE | 0.1977 | **0.1974** | 0.1979 | 0.1992 | 0.2004 | 0.2020 | 0.2035 | 0.2056 | 0.2069 | 0.2078 | 0.2336 |

The curve is flat from 10 to 20, so we use **k = 20** (the script sets a minimum of 20): equally accurate, but each estimate rests on more listings.

**Location explains** 1 − (0.1979 / 0.2336)² ≈ **28%** of the residual variance, on top of the 25% explained by flat traits.

**Granularity achieved:**

| | Value |
|---|---|
| Populated Zählsprengel | 1,345 |
| Own listings per Zählsprengel | median 1; 30% none; 53% 1–4; 11% 5–9; 6% ≥ 10 |
| Bandwidth at Zählsprengel centres | median **502 m** (90th percentile 1,365 m, outskirts) |
| Effective listings per estimate | median **15.2** |
| Index, population-weighted median | **€17.98** per m² (range €13.7–28.8) |

A ~500 m radius is the same neighbourhood size Pennerstorfer, Pennerstorfer & Neumayr (2024) use for their moving-window status variables.

### 4.5 Validation

| Check | Result |
|---|---|
| Spearman with raw Zählsprengel median (≥ 5 own listings, n = 225) | 0.74 |
| Spearman with raw Zählbezirk median | 0.67 |
| Median level: raw Zählsprengel medians vs index | €21.5 vs €18.1. Raw medians are pushed up by new-builds, outdoor space and small flats |
| Spearman across cells with children: % with degree / % knowledge jobs / district income / % foreign-born | 0.52 / 0.42 / 0.32 / 0.18 |
| Spearman with Onur-based `rent_per_room_median` | 0.05 |

### 4.6 Output: `processed/zsp_rent_index.csv`

| Column | Meaning |
|---|---|
| `zsp_id`, `zbz_code`, `pop_total` | Zählsprengel id, its Zählbezirk, residents |
| `rent_eur_m2_std` | **The index**: € per m² per month, standard flat |
| `rent_index_log` | Same, log scale |
| `rent_bandwidth_m` | Kernel bandwidth h_z |
| `rent_n_eff` | Effective number of listings |
| `rent_n_in_zsp`, `rent_raw_median_zsp` | Own listings and their raw median € per m² |
| `rent_n_in_zbz`, `rent_raw_median_zbz` | The same for the Zählbezirk |

`processed/willhaben_listings_clean.gpkg` holds the 4,071 clean listings with all model variables and residuals (for maps).

### 4.7 Into the analysis (`accessibility_analysis_source.py` → `accessibility_analysis.ipynb` §3b)

1. Each 250 m cell takes its Zählsprengel's `rent_eur_m2_std` via `zsp_id`. This covers 6,631 of 6,950 cells and 111,479 of 111,638 children; the analysis sample is unchanged (3,735 cells, 110,822 children).
2. Child-weighted z-score, as for all status measures.
3. Same OLS and controls as the other three status measures, **clustered by Zählbezirk** (248 clusters).
4. Child-weighted terciles for Fig. 3; fourth panel in Figs. 3 and 4.

Results (18 Nov 2026: 60 one-minute departures; **DV2R, the reliable network 2SFCA, is the primary measure**, see `methods_primer.md` §2e):

| Access measure | β (SD access per SD rent) | 95% CI | p |
|---|---|---|---|
| DV1 straight-line 2SFCA | +0.078 | 0.035 to 0.122 | < 0.001 |
| **DV2R reliable network 2SFCA** | **+0.082** | **0.032 to 0.132** | **0.001** |
| DV2 average network 2SFCA | +0.070 | 0.021 to 0.118 | 0.005 |
| DV2R public sites | −0.111 | −0.171 to −0.051 | < 0.001 |
| DV2R private sites | +0.219 | 0.154 to 0.285 | < 0.001 |
| DV3 reliability loss | −0.103 | −0.155 to −0.050 | < 0.001 |

For comparison, DV2R with the other status measures: % with degree +0.099, mean net income +0.094, % knowledge jobs +0.101 (all p ≤ 0.01).

---

## 5. Onur's approach, step by step

Source: `Onur Code/Walkthrough.ipynb` cells 0–15; output `Onur Code/Willhaben_rent_prices (1).csv` (3,616 rows).

1. **Browser automation:** Selenium opens Firefox at the Vienna rental search. Cookies are rejected by hand and the page is switched to its mobile layout in the inspector.
2. **Paging:** 153 pages × 30 listings, using a URL with room filters, `PRICE_FROM=300`, a session id `sfId` and `isNavigation=true`, all three disallowed by robots.txt. Each page is scrolled pixel by pixel, then there is a 1–1.6 s pause.
3. **Extraction by CSS class:** address and price text are read from auto-generated style classes (`.Text-sc-10o2fdq-0.iiBbPS`, `.Box-sc-wfmb7k-0.hsbsqk`). If a page doesn't yield exactly 30 of each, **the page is skipped**. These classes change when the site is rebuilt.
4. **Price cleaning:** `€` is stripped and German number formatting converted, giving `Price_Clean`, the total monthly rent.
5. **Geocoding:** each text address goes to the Google Geocoding API; the first result's coordinates are kept, and failures are dropped. **1,170 of 3,616 (32%) addresses have no street** (e.g. "1100 Wien, 10. Bezirk, Favoriten"), so Google returns the **district centre**, and those listings stack there (map 02a).
6. **Use in Onur's project:** rent heat map (2-D histogram, Gaussian blur), nearest transit stop, cluster medians. No adjustment for size or flat type.
7. **In our EDA (§6):** duplicates dropped, price €200–15,000, `rent_per_room = Price_Clean / rooms`, joined to Zählbezirke, median where ≥ 5 listings, giving `rent_per_room_median`. Marked as robustness-only.

**Problems:** a third of the points are misplaced, there is no floor area, no flat-mix adjustment, and it exists only at Zählbezirk level. Its correlation with our index is ρ = 0.05.

---

## 6. The simple alternative: average rent per room per district

Tested on the new scrape (5,045 listings with a Vienna postcode and rooms; no coordinates needed). The regressions are re-fits with the notebook's controls (density, % foreign-born, employment rate, U-Bahn), on the 18 Nov access measures (DV2R primary), errors clustered by Zählbezirk for the index and by district for the district measures.

**Pros**
* Almost no processing; postcode-only listings can be kept.
* 68–857 listings per district, so each value is stable.
* Easy to explain; same clustering as income.

**Cons**
* **It duplicates the other district measures:** ρ = 0.82 with district % with a degree.
* **It loses about half the signal:** only 54% of the child-weighted variation in our index lies between districts.
* **Per room is confounded by the flat mix.** Donaustadt (22nd) ranks 3rd most expensive (€742 per room) because of small new-builds (857 listings, median 53 m²). The toy example's B is the same problem.
* **It changes the conclusions:**

| Access measure | Zählsprengel index | District rent per room | District rent per m² |
|---|---|---|---|
| DV1 straight-line | +0.078 *** | +0.077 *** | +0.058 ** |
| DV2R reliable network | +0.082 ** | +0.103 *** | +0.094 *** |
| DV2R public sites | −0.111 *** | −0.081 (p = 0.18) | −0.006 (p = 0.93) |
| DV2R private sites | +0.219 *** | +0.224 ** | +0.145 * |
| DV3 reliability loss | −0.103 *** | +0.001 (p = 0.98) | +0.063 (p = 0.25) |

\*\*\* p < 0.001, \*\* p < 0.01, \* p < 0.05.

The public-site and reliability results exist **within** districts and disappear when status is measured per district. **Use:** district rent per m² as a robustness check, and as a MAUP illustration (the modifiable areal unit problem: results change with the size of the units).

---

## 7. Maps (EDA notebook §3e, `outputs/eda_socioeconomic/`)

| Figure | Shows |
|---|---|
| `02a_rent_listing_locations.png` | Left: Onur's listings, with street-less ones stacked at district centres (circle size = number). Right: the new scrape, coloured kept (4,071) / dropped as postcode-only (628) / dropped by other rules (648) |
| `02b_rent_listing_density_zsp.png` | Clean listings per Zählsprengel (count classes 0, 1–2, 3–4, 5–9, 10–19, 20+) and per 1,000 residents |
| `02c_rent_by_zsp.png` | Raw median € per m² where a Zählsprengel has ≥ 5 listings (227 of 1,345), next to the standard-flat index, on one colour scale |

*The kept/dropped counts in 02a differ slightly from the cleaning table: the map labels every listing with a postcode-only location as "postcode", including 6 that step 1 had already removed for missing rent or area.*

---

## 8. What to say in the paper

| Issue | Pennerstorfer | Ours | Consequence |
|---|---|---|---|
| Purchase vs rent | Purchase price | Asking rent | Both reflect location value; rent is also shaped by tenancy law, and old regulated flats are rarely advertised |
| Asking vs paid | Model estimate | Advertised price | Asking rents exceed sitting tenants' rents; the gap is larger in high-demand areas |
| Housing stock covered | Whole market (modelled) | Flats on the market now; municipal (*Gemeindebau*) and cooperative flats barely appear | The index is the **private-market price of location**, not what residents pay |
| Flat traits controlled | Rich (age, condition, …) | Size, rooms, floor, outdoor space, new-build, landlord type | Some building quality remains in our location signal |
| Smoothing | Inside the vendor's model | Explicit kernel, ~500 m, k = 20 | Slight shrinkage of extremes (toy example, Zählsprengel C); errors clustered by Zählbezirk |
| Timing | 2015 for 2007–14 | Nov 2026, matching the 2026 data | — |
| Reproducibility | Proprietary | Scripts and the aggregated index are shared; the raw adverts are kept locally, not redistributed. A re-run another day gives another sample | State the scrape date |
| Ethics | — | Scraped against willhaben's robots.txt, at low rate, no personal data | Ethics note |

**Suggested methods sentence:** *"Following Pennerstorfer and Pennerstorfer (2021), who used the estimated price of a standardised flat at each census tract's centroid, we construct a rent index from 4,071 geolocated willhaben listings (16 November 2026). A hedonic regression removes differences in flat size and type, and a Gaussian kernel over the 20 nearest listings (median radius 502 m, chosen by leave-one-out cross-validation) gives the monthly asking rent per m² of a standard 65 m² flat at each tract's centre."*

---

## 9. Files and how to re-run

Paths are relative to the project folder (`analysis/` in the shared repository, `'My' Code/` locally). Files marked *local only* are not in the shared repository: they are third-party adverts with street-level locations, and willhaben does not allow redistribution.

| File | What |
|---|---|
| `Data/socioeconomic/scripts/scrape_willhaben.py` | Collection (§4.1) |
| `Data/socioeconomic/raw/willhaben_rents_2026-11-16.csv` (*local only*) | Raw scrape, 5,347 listings |
| `Data/socioeconomic/scripts/build_rent_index.py` | Cleaning, hedonic model, kernel (§4.2–4.6) |
| `Data/socioeconomic/scripts/rent_index_toy_example.py` | Toy example (§3) |
| `Data/socioeconomic/processed/willhaben_listings_clean.gpkg` (*local only*) | 4,071 clean listings with residuals |
| `Data/socioeconomic/processed/zsp_rent_index.csv` | Index per Zählsprengel |
| `Data/socioeconomic/processed/rent_index_cleaning_log.csv` | Cleaning table |
| `Data/socioeconomic/scripts/socioeconomic_eda_source.py` → `socioeconomic_eda.ipynb` §3e | Maps (§7). The listing-location map is skipped when the local-only files are absent |
| `Data/socioeconomic/scripts/accessibility_analysis_source.py` → `accessibility_analysis.ipynb` §3b | Regressions (§4.7) |
| `access_maps.ipynb` map 7 | Access × rent index, bivariate map by Zählbezirk |

From `Data/socioeconomic` (needs the local-only raw scrape):

```bash
python -I scripts/build_rent_index.py raw/willhaben_rents_2026-11-16.csv
```

```bash
python -I scripts/rent_index_toy_example.py
```

From the project folder (notebooks are generated from their `_source.py`; edit the source, not the notebook):

```bash
python Data/socioeconomic/scripts/py_to_ipynb.py Data/socioeconomic/scripts/socioeconomic_eda_source.py socioeconomic_eda.ipynb && jupyter nbconvert --to notebook --execute --inplace socioeconomic_eda.ipynb
```

```bash
python Data/socioeconomic/scripts/py_to_ipynb.py Data/socioeconomic/scripts/accessibility_analysis_source.py accessibility_analysis.ipynb && jupyter nbconvert --to notebook --execute --inplace accessibility_analysis.ipynb
```

Re-scraping is only needed for a new snapshot. Keep the dated file name, and re-read the ToS note first.
