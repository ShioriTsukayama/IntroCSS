# Methods primer: terms, measures and Python

*A plain-language reference for the childcare accessibility project. Each entry says **what it is**, **why we use it**, and gives a **toy example**. All code was run; the printed results are shown as comments. Checked against the project on 20 Nov 2026.*

**Contents**
1. Basic terms
2. Accessibility measures (nearest time, cumulative, 2SFCA and variants)
3. Moving data between geographies (dasymetric, areal weighting)
4. Describing inequality (weighted means, gradients, concentration index)
5. Spatial statistics (Moran's I, LISA)
6. Regression issues (clustered errors, ecological fallacy, MAUP)

---

## 1. Basic terms

| Term | Meaning |
|---|---|
| **SES** | *Socio-economic status*: a person's or area's position in terms of education, income, occupation. We only have **area-level** SES ("neighbourhood status"), never individual. Pennerstorfer used three: % with a degree, average income, house prices. |
| **Zählsprengel (ZSP)** | Census tract. 1,368 in Vienna, ~1,500 residents each. Our finest official unit. |
| **Zählbezirk (ZBZ)** | Statistical sub-district. 250 in Vienna, groups of ZSPs. |
| **Bezirk** | One of 23 districts. |
| **Cell** | A 250 m × 250 m square of the Statistik Austria grid. Our routing origin. |
| **Catchment** | The area around a site (or a child) inside which a trip counts as "reachable", e.g. 500 m or 15 min. |
| **Supply / demand** | Supply = childcare places. Demand = children who might use them. |
| **OD matrix** | *Origin–destination* matrix: travel time from every cell (row) to every site (column). Ours is 6,950 × 1,682 per departure, for **60 one-minute departures** (07:30–08:29). |
| **GTFS** | The public-transport timetable format. Our routing uses the timetable, so "reliability" = timetable variability (waiting, transfers), not real delays. |
| **Child-weighted** | Averages where each cell counts by how many children live there, so empty parks don't count. |
| **NACE** | EU classification of economic sectors (A = agriculture … U = extraterritorial). |

---

## 2. Accessibility measures

### 2a. Nearest travel time
Minutes to the closest site. Simple, but ignores **capacity** (a 10-place site counts like a 200-place one) and **competition** (how many other children want the same places). In Vienna it is saturated: almost every child has some site within 15 min.

### 2b. Cumulative opportunities
Number of places reachable within a threshold (e.g. 15 min). Captures choice and capacity, but not competition.

### 2c. 2SFCA (two-step floating catchment area)
The standard way to combine **distance, capacity and competition**. It answers: *"How many places per child can this child reach, given that other children compete for them?"*

* **Step 1 – each site:** `R_site = places ÷ children who can reach this site`
* **Step 2 – each child/cell:** `A_cell = sum of R_site over all sites the cell can reach`

`A × 100` reads as "places per 100 children". If supply exactly matches demand everywhere, A = 1 for everyone.

```python
import numpy as np
dist = np.array([[100, 900],      # rows = 3 cells, cols = 2 sites, metres
                 [300, 400],
                 [800, 200]])
children = np.array([50, 30, 20])
places   = np.array([40, 10])

inside = dist <= 500               # 0/1 catchment
demand = children @ inside         # step 1: children who can reach each site -> [80 50]
R = places / demand                # places per child per site              -> [0.5 0.2]
A = inside @ R                     # step 2: sum over reachable sites
print(A * 100)                     # [50. 70. 20.] places per 100 children
```
Cell 2 scores highest because it reaches *both* sites; cell 3 lowest because it reaches only the small site.

**Is it hard?** No. With an OD matrix it is the four lines above. It is in `accessibility_analysis.ipynb` §2 (with Gaussian distance decay).

### 2d. Variants
| Variant | What changes | Use for us |
|---|---|---|
| **Pennerstorfer's version** | 500 m straight line; **distance decay** f(d) = d⁻² (closer children count more); capacity = **number of groups**, not places | Direct replication (straight-line distances between cell centres and sites are trivial to compute) |
| **E2SFCA** (enhanced) | Catchment split into bands (0–5, 5–10, 10–15 min) with falling weights | We use its continuous form: a **Gaussian** weight falling from 1 at 0 min to 0 at 15 min |
| **Reliable 2SFCA, DV2R** (our primary measure) | Use each cell–site pair's **90th-percentile travel time** across departures in the Gaussian weight | A site counts as far away as it is on a bad morning (1 in 10). See 2e |
| Share-of-departures 2SFCA (robustness) | Replace 0/1 "reachable" with **share of departures within threshold** | A site reachable on only half the departures counts half |
| **MM2SFCA** (multi-modal) | Demand split by travel mode (e.g. car owners vs transit users), each with its own catchment | Probably out of scope: needs car routing + car ownership data; trip here is walk/transit |
| **3SFCA / M2SFCA** | Corrections for demand being counted at several sites | Mention as limitation only |

Pennerstorfer's decay version:
```python
f = np.where(dist <= 500, dist.astype(float) ** -2, 0)   # weight falls fast with distance
R_p = 1 / (children @ f)                                  # their R_d
A_p = f @ (places * R_p)
print(A_p.round(3))   # [0.75  0.174 0.364]
```
(Their children in the *same* cell as a site get distance 125 m to avoid dividing by zero.)

Share-of-departures version (robustness check):
```python
p_ok = np.array([[1.0, 0.0],      # share of morning departures within 15 min
                 [0.5, 1.0],
                 [0.0, 0.8]])
R_r = places / (children @ p_ok)
A_r = p_ok @ R_r
print(A_r * 100)                  # [61.5 52.5 17.4]
```

### 2e. Reliable vs average access (DV2R vs DV2), and why the average does not change
* **DV2, average:** compute the 2SFCA separately at each departure minute, then average the 60 scores.
* **DV2R, reliable (primary):** for each cell–site pair, take the **90th-percentile** travel time over the departures (the time you can count on 9 times in 10; transport research calls it *planning time*), then compute one 2SFCA. A pair with no route at more than 10% of departures gets weight 0.

Toy: 3 cells, 2 sites (40 places each), 10 departures. Cell 3 reaches site B by a bus: 6 min normally, but 17 min at the 3 departures that just miss it.
```python
def gauss(t, t0=15):                       # weight 1 at 0 min -> 0 at 15 min
    t = np.asarray(t, float); g = (np.exp(-0.5*(t/t0)**2) - np.exp(-0.5)) / (1 - np.exp(-0.5))
    return np.where(t <= t0, g, 0.0)
def two_step(W, S, D):
    pull = D @ W; R = np.divide(S, pull, out=np.zeros_like(S), where=pull > 0); return W @ R

tt = np.array([[[4, 12], [9, 9], [14, 6]]] * 10, float)   # (departure, cell, site), minutes
tt[[2, 5, 8], 2, 1] = 17                                 # cell 3 -> site B misses the bus 3 times
children, places = np.array([50., 30., 20.]), np.array([40., 40.])

A = np.stack([two_step(gauss(tt[k]), places, children) for k in range(10)]) * 100
t90 = np.quantile(tt, 0.9, axis=0, method="higher")      # cell 3 -> site B: 17 min
dv2  = A.mean(0)                                         # [84.7  90.5  52.5]
dv2r = two_step(gauss(t90), places, children) * 100      # [93.3 107.0   6.3]
np.average(dv2, weights=children), np.average(dv2r, weights=children)   # 80.0, 80.0
```
* On an average morning cell 3 has 52.5 places per 100 children. Counting only what it can **rely on**, it has 6.3, because its main site is outside the 15-min catchment 3 mornings in 10.
* **The child-weighted average is the same (80.0 = 80 places ÷ 100 children).** A 2SFCA always hands out all places among the children who can reach them, so as long as every site is reached by someone, Σ children × access = Σ places. Requiring reliability **moves** access from badly connected cells (cell 3) to the cells that still reach the site (cells 1 and 2, which now compete with fewer children). In Vienna: DV2 and DV2R both average 80.3, but the cell–site pairs within 15 min fall by 19%.
* So DV2R is an *inequality* measure: it does not say Vienna has fewer places, it says who can count on them. Map 2 in `access_maps.ipynb` shows where access moves: about a third of children gain more than 3 places per 100, a third lose more than 3.

**What 2SFCA needs, and what we have**

| Input | Have it? | Quality |
|---|---|---|
| Site locations | ✅ 1,682 | exact |
| Capacity | ✅ places by group type | 133 sites missing capacity |
| Provider type | ✅ public / private (+ operator name) | good |
| Children per cell | ✅ official ZSP counts, placed with official 100 m residents | real totals, modelled placement (§3) |
| Travel times | ✅ OD matrices from `routing.ipynb` (60 departures) | timetable-based |

So **yes, we can do a Pennerstorfer-style 2SFCA**. The weak point is not the 2SFCA but the **SES variables** we regress it on.

---

## 3. Moving data between geographies

### 3a. Counts vs rates
* **Counts** (children, residents, places) can be **split** into smaller units and **summed** into larger ones.
* **Rates** (% with a degree, average income) can only be **copied** down to smaller units and **weighted-averaged** up.

### 3b. Dasymetric mapping
Spread an area's count to its sub-units in proportion to a helper layer showing where people live.

```python
zone_children = 100
residents = pd.Series([0, 300, 700], index=["park", "c1", "c2"])
zone_children * residents / residents.sum()   # park 0, c1 30, c2 70
# naive equal split would give 33 each, putting 33 children in the park
```
**Is it sound?** Yes, it's the standard method, and our version is about as good as free data allows:
* the **totals** are official register counts per ZSP (not estimates);
* the helper layer is the **official** 100 m resident grid (not modelled);
* the only assumption is that *within one ZSP*, children live where residents live. A ZSP has on average only ~2–3 populated 250 m cells, so little is being "spread".

What it can get wrong: a ZSP with a family-heavy new estate and an elderly block will smear children evenly over both. Real 250 m child counts would fix that; we can **test sensitivity** by also weighting with the 1 km age grid.

### 3c. Areal weighting
Split by overlapping area, assuming even spread. Only acceptable at very fine scale (we use it for 100 m → 250 m, where errors are tiny).

---

## 4. Describing inequality

### 4a. Child-weighted mean
```python
cells = pd.DataFrame({"minutes": [5, 25, 10], "children": [90, 10, 50]})
cells["minutes"].mean()                                     # 13.3 – counts the empty-ish cell equally
np.average(cells["minutes"], weights=cells["children"])     # 8.0  – what the typical child experiences
```

### 4b. Spearman correlation (ρ)
Correlation of **ranks**, so one outlier can't dominate and the relation needn't be linear. Range −1 … +1.
```python
from scipy.stats import spearmanr, pearsonr
x = [1, 2, 3, 4, 100]; y = [2, 4, 6, 8, 10]
pearsonr(x, y)[0]    # 0.72 – dragged by the outlier
spearmanr(x, y)[0]   # 1.0  – perfectly monotone
```

### 4c. Equity gradient
Rank areas into 5 groups (**quintiles**) by an SES variable and show the outcome per group. Pennerstorfer used high / middle / low status thirds.

### 4d. Concentration index (CI)
Rank areas from most to least disadvantaged; compare the cumulative share of children with the cumulative share of access. Range −1 … +1. **CI > 0 = access favours advantaged areas; CI = 0 = equal.**
```python
d = pd.DataFrame({"disadv_rank": [1, 2, 3, 4],   # 1 = most disadvantaged
                  "access":      [20, 40, 60, 80],
                  "children":    [1, 1, 1, 1]}).sort_values("disadv_rank")
cw = d.children.cumsum() / d.children.sum()
cv = (d.access * d.children).cumsum() / (d.access * d.children).sum()
1 - 2 * np.trapezoid(np.r_[0, cv], np.r_[0, cw])   # 0.25 -> favours advantaged
```

---

## 5. Spatial statistics

### 5a. Moran's I
Measures **spatial autocorrelation**: do neighbouring areas have similar values? ≈ 0 for a random pattern, towards +1 when similar values cluster. "Neighbours" are defined by a **weights matrix W** (here *Queen*: sharing an edge or corner).
```python
import geopandas as gpd
from shapely.geometry import box
from libpysal.weights import Queen
from esda.moran import Moran
sq = gpd.GeoDataFrame(geometry=[box(i, j, i+1, j+1) for i in range(6) for j in range(6)])
clustered = np.array([i for i in range(6) for j in range(6)], float)   # values rise west -> east
random = np.random.default_rng(0).permutation(clustered)
W = Queen.from_dataframe(sq, use_index=False); W.transform = "r"
Moran(clustered, W).I   # 0.82 – strongly clustered
Moran(random, W).I      # 0.08 – no pattern
```
**Why it matters:** if both access and SES are clustered, an ordinary regression treats 250 neighbouring areas as 250 independent facts when they are not → p-values too small.

### 5b. LISA (local Moran)
Splits Moran's I by location to map **clusters**: *High-High* (high values surrounded by high), *Low-Low*, and outliers (*High-Low*, *Low-High*). Answers "where are the underserved pockets?" with a significance test. `esda.moran.Moran_Local(y, W)`. *Not used in the final analysis (dropped 16 Nov).*

---

## 6. Regression issues

### 6a. Clustered standard errors
If an SES variable is measured per district, all cells in a district share the same value. You really have **23 observations of it**, not 6,950. Clustering tells the regression this.
```python
import statsmodels.formula.api as smf
# 23 districts × 30 cells; education is a district value
naive = smf.ols("acc ~ edu", df).fit()
cl    = smf.ols("acc ~ edu", df).fit(cov_type="cluster", cov_kwds={"groups": df["district"]})
naive.bse["edu"], cl.bse["edu"]   # 0.047 vs 0.167 – honest uncertainty is 3.5× larger
```
This is exactly what Pennerstorfer did ("residuals clustered at grid cell / SED / district").

### 6b. Ecological fallacy
Area-level patterns don't describe individuals. "Children in high-education areas have more access" ≠ "children of graduates have more access".

### 6c. MAUP (modifiable areal unit problem)
Results can change with the size and shape of the units. Check key results at two scales (e.g. cell and ZBZ).

### 6d. Uniform granularity is **not** required
Mixing levels is normal (Pennerstorfer mixed 250 m cells, ZSPs and districts). The rules: assign coarse values down (§3a), cluster errors at the coarse level (§6a), and don't over-interpret coarse variables.
