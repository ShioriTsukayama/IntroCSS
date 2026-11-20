# Explanatory models: options, what Pennerstorfer did, and what fits a 5,000-word essay

*Companion to `methods_primer.md`. Code below was run on a toy dataset (100 areas in 4 "districts", access driven by density and SES plus spatially clustered noise). Status of each model in the project: §5 (updated 20 Nov 2026).*

---

## 1. What Pennerstorfer & Pennerstorfer (2021) actually estimated

`Access_child,year = α + β·SES + controls·θ + year effects + error`, estimated by **OLS**:

* **One row per child** (each child gets its cell's accessibility), 2007–2014.
* **SES** one at a time: education (cell), income (district), house prices (Zählsprengel).
* **Controls:** % born in Austria / EU / outside EU, female employment rate (all per cell, 2011), U-Bahn station in cell.
* **Standard errors clustered** at the level where the SES variable is measured.
* Separate regressions per **provider type** (public vs non-profit), and an **age split** (under 3 vs 3–5; mixed groups counted ⅓ toddlers, ⅔ older).
* Robustness: semi-parametric version, 1 km catchment, gentler distance decay.

No spatial-econometric models: they handled spatial dependence through clustering. That is a defensible choice for us too.

---

## 2. The menu, simplest first

| Model | Question it answers | Effort | Recommended? |
|---|---|---|---|
| **A. OLS, child-weighted, clustered SE** | Is access higher where SES is higher, net of density? | low | Yes: **core model** (Pennerstorfer replication) |
| **B. Same, by provider type** | Do public and non-profit sites differ in where they locate relative to SES? | low | Yes: **core** (the public–private comparison) |
| **C. Logistic regression** | Which areas are more likely to be "underserved" (a yes/no outcome)? | low | optional; few underserved children, so weak |
| **D. Spatial error model (SEM)** | Same as A, but correcting for spatially clustered unexplained variation | medium | Yes: **one robustness check** at Zählbezirk level |
| **E. Spatial lag model (SAR)** | Does access in one area depend on access in neighbouring areas? | medium | No: conceptually inappropriate, since the 2SFCA already incorporates neighbouring supply |
| **F. Multilevel / random intercepts** | How much variation is between districts vs within them? | medium | optional; clustering (A) does most of the job |
| **G. GWR / MGWR** | Does the SES–access relationship differ across the city? | high | No: out of scope; noted as future work |

---

## 3. Code (toy data)

### A/B. OLS, child-weighted, clustered (Pennerstorfer style)
```python
import statsmodels.formula.api as smf
m = smf.wls("access ~ ses + density", data, weights=data["children"]) \
       .fit(cov_type="cluster", cov_kwds={"groups": data["district"]})
m.params    # ses 0.089, density 2.83
m.bse       # standard errors that respect clustering
```
* `wls` with child weights = "one row per child" without duplicating rows.
* For B, swap `access` for `access_public` / `access_private` (separate 2SFCA scores).
* **Density control is essential**: in our data, density and SES are correlated with access in opposite directions.

### D. Is spatial correction needed? Then the spatial error model
```python
from libpysal.weights import Queen
from spreg import OLS, ML_Error
W = Queen.from_dataframe(zbz_gdf); W.transform = "r"
ols = OLS(y, X, w=W, spat_diag=True)       # y: (n,1) array, X: (n,k) without constant
ols.lm_error   # (11.2, p=0.001) -> spatial error present
ols.lm_lag     # (0.7,  p=0.40)  -> no lag needed
sem = ML_Error(y, X, w=W)
sem.betas      # constant, ses, density, lambda
```
**Reading it:** the *Lagrange Multiplier (LM) tests* say which spatial problem exists. If only LM-error is significant, use SEM. **λ (lambda)** measures how strongly unexplained access spills over between neighbouring areas.

### C. Logistic
```python
smf.logit("underserved ~ ses + density", data).fit(cov_type="cluster", cov_kwds={"groups": data["district"]})
```

### F. Multilevel
```python
smf.mixedlm("access ~ ses + density", data, groups=data["district"]).fit()
```

---

## 4. Unit of analysis: how the levels fit together

* **Accessibility** is computed per **250 m cell** (the routing origin). There is no need to aggregate it.
* **Model A** runs on **cells, weighted by children**, with each SES variable copied down from its own level and errors clustered at that level. This is exactly Pennerstorfer's set-up and avoids choosing one "true" unit.
* **Model D** needs areas with neighbours, so run it on **Zählbezirke** (cell values aggregated with child weights). Zählbezirk is the finest level where we have country of birth and social housing; the rent index is at Zählsprengel level and aggregates up.
* District variables (education, income) enter as context with district-clustered errors; with 23 values they can show direction, not much more.

---

## 5. Scope for the essay (≈ 5,000 words), and where it stands

| Part | Status (20 Nov 2026) |
|---|---|
| 1. **Descriptives:** maps of 2SFCA (all / public / private), equity gradients, concentration indices | Done: analysis Figs. 3, 6–8; `access_maps.ipynb` |
| 2. **Model A** for each status measure, all sites; then **Model B** by provider type. One regression table | Done: `accessibility_analysis.ipynb` §4–5 |
| 3. **Reliability:** DV2R (reliable network 2SFCA) is the headline outcome, DV2 (average over departures) the comparison, DV3 (access lost at a bad departure) the reliability outcome | Done: §2, §6b |
| 4. **Robustness:** catchment 10 / 20 min, 80th / 95th percentiles, share-of-departures weighting, Gemeindebau control | Done: §5, §5b |
| 4b. **Robustness:** SEM at Zählbezirk level | Open |
| 4c. **Robustness:** under-3 vs 3–5 split (Pennerstorfer Appendix B) | Open (`children_u3`, `children_3_5` are already in `grid250_analysis.gpkg`) |
| ~~Child counts official vs births-based~~ | dropped: the births × GHSL estimate was replaced on 13 Nov (`data_sources_and_merging_guide.md` §4) |

That is a full, comparable analysis without GWR, multilevel or lag models.
