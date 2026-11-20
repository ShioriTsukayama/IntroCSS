# %% [markdown]
# # Childcare accessibility and neighbourhood status in Vienna: analysis
#
# **What this notebook does.** It builds the access measures (dependent variables) from minute-by-minute travel times, attaches the status measures and controls, runs a Pennerstorfer-style OLS, and draws the analysis figures. Data preparation lives in `socioeconomic_eda.ipynb`; routing lives in `colab_routing/vienna_routing_1min_colab.ipynb`. This notebook only reads their outputs.
#
# **Fixed decisions (so the essay can state them once)**
# | Decision | Choice |
# |---|---|
# | Unit | 250 m cell, weighted by children aged 0–5 ("one row per child") |
# | **Primary access measure** | **DV2R, reliable network 2SFCA**: travel time = the time a parent can count on (90th percentile over the morning's departures) |
# | Status in regressions | **continuous**, standardised (child-weighted z-scores), one measure at a time |
# | Status in figures | **terciles** (low / middle / high), each holding about one third of children, as in Pennerstorfer |
# | Standard errors | clustered at the coarsest level of any variable in the model |
# | Travel-time catchment | Gaussian decay reaching zero at **15 min** (main); 10 and 20 min as robustness |
# | Departures | **every minute 07:30–08:29** (60 departures), walk + Wiener Linien / Wiener Lokalbahnen timetable of Tue 20 Oct 2026. The earlier 6-departure version is in `deprecated/` |

# %%
from pathlib import Path
import warnings, zipfile
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from shapely.geometry import LineString
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

warnings.filterwarnings("ignore", message=".*keep_geom_type.*")
_candidates = [Path.cwd(), *Path.cwd().parents]
ROOT = next(p for p in _candidates if (p / "Data" / "KINDERGARTENOGD.json").exists())
DATA, OUT = ROOT / "Data", ROOT / "outputs"
PROC = DATA / "socioeconomic" / "processed"
FIG = OUT / "analysis"; FIG.mkdir(parents=True, exist_ok=True)
MATRICES = OUT / "origin_destination_matrices_1min"
GRID_CRS = "EPSG:3035"
CELL_KM2 = 0.0625
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 300, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})

# Colours (validated reference palette)
BLUE = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
ORANGE = LinearSegmentedColormap.from_list("orange", ["#fdeee6", "#f9c9ad", "#f39d74", "#eb6834", "#c4501f", "#8f3a16"])
TERC = {"low": "#9ec5f4", "middle": "#3987e5", "high": "#104281"}
INK2, GRID_INK, MISSING = "#52514e", "#e6e5e0", "#ebeae6"

# %% [markdown]
# ## 1. Inputs
# * **Cells:** `grid250_analysis.gpkg` (children, status variables, controls) from the EDA notebook.
# * **Sites:** 1,682 childcare sites with under-6 places. *133 sites list no places at all.* Treating them as zero would make them invisible, so they get the **median places of their provider type** (flagged `capacity_imputed`).
# * **Travel times:** one origin × destination matrix per departure minute, 07:30–08:29 (minutes, door to door, walk + public transport; missing = over the routing cut-off or no route). Each matrix is one departure minute (`window_minutes = 1`).

# %%
grid = gpd.read_file(PROC / "grid250_analysis.gpkg")
fac = gpd.read_file(DATA / "KINDERGARTENOGD.json").to_crs(GRID_CRS)

U3 = ["KLEINKINDER_0_3", "INTEGRAT_KLEINKINDER_0_3"]
K36 = ["KDG_3_6", "HALBTAGS_KDG_3_6", "INTEGRAT_KDG_3_6", "HEILPAED_KDG_3_6"]
MIX06 = ["FAMILIE_0_6", "INTEGRAT_FAMILIE_0_6", "FAMILIE_2_6", "INTEGRAT_FAMILIE_2_6", "KINDERGRUPPE"]
MIX310 = ["FAMILIE_3_10", "INTEGRAT_FAMILIE_3_10", "HEILPAED_FAMILIE_3_10", "FAMILIE_0_10"]
HORT = ["HORT_6_10", "INTEGRAT_HORT_6_10", "HEILPAED_HORT_6_10"]
num = fac[U3 + K36 + MIX06 + MIX310].fillna(0)
fac["places_u6"] = num[U3 + K36 + MIX06].sum(axis=1) + 0.5 * num[MIX310].sum(axis=1)
fac["public"] = fac["TXTATT1"].eq("Öffentlich")
fac["capacity_imputed"] = fac[U3 + K36 + MIX06 + MIX310 + HORT].fillna(0).sum(axis=1) == 0
med = fac[~fac.capacity_imputed & (fac.places_u6 > 0)].groupby("public")["places_u6"].median()
fac.loc[fac.capacity_imputed, "places_u6"] = fac.loc[fac.capacity_imputed, "public"].map(med)
print(fac.groupby("public").agg(sites=("places_u6", "size"), places=("places_u6", "sum"),
                                imputed=("capacity_imputed", "sum")).rename(index={True: "public", False: "private"}))

mats = sorted(MATRICES.glob("*.npz"))
DEPARTURES = [m.stem.split("_")[1] for m in mats]
tt = np.empty((len(mats), len(grid), len(fac)), dtype=np.float32)      # (departure, cell, site), filled in place to save memory
for k, m in enumerate(mats):
    with np.load(m, allow_pickle=True) as z:          # written by our own routing notebook
        assert np.array_equal(z["origin_ids"].astype(str), grid["origin_id"].astype(str).to_numpy())
        assert int(z["window_minutes"]) == 1
        tt[k] = z["travel_times"]
MINS = np.array([int(d[:2]) * 60 + int(d[2:]) for d in DEPARTURES])
hhmm = lambda m: f"{m // 60:02d}:{m % 60:02d}"
print(f"{len(DEPARTURES)} departures {hhmm(MINS[0])}–{hhmm(MINS[-1])} | matrix {tt.shape}, {tt.nbytes / 1e9:.1f} GB")

S_all = fac["places_u6"].to_numpy(float)
PUB = fac["public"].to_numpy()
D = grid["children_u6"].fillna(0).to_numpy(float)

# %% [markdown]
# ## 2. Dependent variables
#
# All are **2SFCA scores in places per 100 children**: step 1 divides each site's places by the (distance-weighted) children who can reach it; step 2 sums those ratios over the sites a cell can reach. Only the *weighting* differs.
#
# | | Name | Weight of a site for a cell | Role |
# |---|---|---|---|
# | **DV1** | Euclidean 2SFCA | straight-line distance d ≤ 500 m, weight d⁻² (d floored at 125 m) | Replicates Pennerstorfer |
# | **DV2R** | **Reliable network 2SFCA** | Gaussian on the **reliable travel time**: the 90th percentile of the 60 one-minute departures (weight 1 at 0 min → 0 at 15 min) | **Primary measure** |
# | DV2 | Average network 2SFCA | same Gaussian, computed **per departure** and averaged over the 60 | What a family gets on a typical morning; comparison for DV2R |
# | **DV3** | Reliability loss | **1 − (access at a bad departure ÷ average access)**, "bad" = 10th percentile of the 60 per-departure scores | How much access a family loses by leaving at an unlucky minute |
#
# **Why DV2R is primary.** A parent dropping a child off before work has to plan for the slow mornings, not the average one. The 90th-percentile time is what transport-reliability work calls *planning time*: leave that much time and you arrive on time at 9 of 10 departure minutes. A site that is 8 min away on average but 16 min at some departures counts as a 16-min site. DV2R therefore penalises unreliable connections, while DV2 averages them away. The 90th percentile is the 55th-fastest of the 60 departures; a pair with no route at more than 6 departures gets weight 0.
#
# *Robustness for DV2R:* catchment 10 and 20 min; a binary version weighting each site by the **share of departures that reach it within 15 min** (the "reliable 2SFCA" in `methods_primer.md` §2d); the 80th and 95th percentiles. *Capacity:* Pennerstorfer counted groups; we count places (group sizes are not in the data).

# %%
def two_step(W, supply, demand):
    """W: (cells, sites) weights. Returns places per child for each cell."""
    pull = demand @ W                                   # weighted children reaching each site
    R = np.divide(supply, pull, out=np.zeros_like(supply), where=pull > 0)
    return W @ R

def gaussian(t, t0):
    t = np.nan_to_num(np.asarray(t, dtype=float), nan=np.inf)
    with np.errstate(invalid="ignore", over="ignore"):
        g = (np.exp(-0.5 * (t / t0) ** 2) - np.exp(-0.5)) / (1 - np.exp(-0.5))
    return np.where(t <= t0, g, 0.0)

print("Gaussian weights at 0/5/10/15 min:", gaussian(np.array([0, 5, 10, 15.]), 15).round(2))

def sup(mask=None):
    return S_all if mask is None else np.where(mask, S_all, 0)

# DV1: Euclidean, Pennerstorfer
cxy = np.c_[grid.geometry.centroid.x, grid.geometry.centroid.y]
sxy = np.c_[fac.geometry.x, fac.geometry.y]
W1 = np.zeros((len(grid), len(fac)))
for i, js in enumerate(cKDTree(sxy).query_ball_point(cxy, r=500)):
    if js:
        d = np.maximum(np.hypot(*(sxy[js] - cxy[i]).T), 125)
        W1[i, js] = d ** -2.0
grid["dv1_euclid"] = two_step(W1, S_all, D) * 100

# Reliable travel time per cell-site pair: a percentile over departures (no route = infinitely slow), in chunks to save memory
def time_percentile(q, chunk=500):
    out = np.empty(tt.shape[1:], dtype=np.float32)
    for s in range(0, tt.shape[1], chunk):
        x = tt[:, s:s + chunk]
        out[s:s + chunk] = np.quantile(np.where(np.isnan(x), np.inf, x), q, axis=0, method="higher")
    return out

T90 = time_percentile(0.90)
T_MED = time_percentile(0.50)

# DV2R: reliable network 2SFCA (primary), provider splits and robustness
W_rel = gaussian(T90, 15)
grid["dv2_reliable"] = two_step(W_rel, sup(), D) * 100
grid["dv2r_public"] = two_step(W_rel, sup(PUB), D) * 100
grid["dv2r_private"] = two_step(W_rel, sup(~PUB), D) * 100
grid["dv2r_t10"] = two_step(gaussian(T90, 10), sup(), D) * 100
grid["dv2r_t20"] = two_step(gaussian(T90, 20), sup(), D) * 100
grid["dv2r_p80"] = two_step(gaussian(time_percentile(0.80), 15), sup(), D) * 100
grid["dv2r_p95"] = two_step(gaussian(time_percentile(0.95), 15), sup(), D) * 100
share15 = np.zeros(tt.shape[1:], dtype=np.float32)
for k in range(len(tt)):
    share15 += np.nan_to_num(tt[k], nan=np.inf) <= 15
grid["dv2r_share15"] = two_step(share15 / len(tt), sup(), D) * 100
del W_rel, share15

# DV2: average of the per-departure network 2SFCA; also the input for DV3 and the departure-time figures
A_t = np.stack([two_step(gaussian(tt[k], 15), sup(), D) for k in range(len(tt))]) * 100      # (departure, cell)
grid["dv2_network"] = A_t.mean(axis=0)

# DV3: share of average access lost at a bad (10th percentile) departure
p10 = np.percentile(A_t, 10, axis=0)
grid["dv3_reliability_loss"] = np.where(grid["dv2_network"] > 0, 1 - p10 / grid["dv2_network"], np.nan)

# Descriptive: time to the nearest site at each departure (cap 31 = none within the cut-off)
nearest = np.stack([np.nanmin(np.where(np.isnan(tt[k]), 31, tt[k]), axis=1) for k in range(len(tt))])   # (departure, cell)
grid["nearest_sd_min"] = nearest.std(axis=0)
grid["nearest_p90_min"] = np.quantile(nearest, .9, axis=0, method="higher")
grid["access_sd"] = A_t.std(axis=0)

def wmean(x, w=None):
    w = D if w is None else w; m = ~np.isnan(x) & (w > 0); return np.average(x[m], weights=w[m])
print("Child-weighted means (places per 100 children): " + ", ".join(f"{c} {wmean(grid[c].to_numpy()):.1f}" for c in
      ["dv1_euclid", "dv2_reliable", "dv2_network", "dv2r_public", "dv2r_private", "dv2r_share15"]),
      f"| DV3 {wmean(grid['dv3_reliability_loss'].to_numpy()):.3f}")
print(f"reliable vs average network access: child-weighted mean ratio DV2R/DV2 = "
      f"{wmean((grid.dv2_reliable / grid.dv2_network.where(grid.dv2_network > 0)).to_numpy()):.3f}")
print(f"cell–site pairs within 15 min: median time {(T_MED <= 15).sum():,}, 90th-percentile time {(T90 <= 15).sum():,}")
print("Total places per 100 children (city):", round(S_all.sum() / D.sum() * 100, 1))

# %% [markdown]
# ## 3. Status measures (IVs) and controls
#
# | Variable | Level | Role | Note |
# |---|---|---|---|
# | `pct_tertiary`: % adults with a degree | district (23) | **IV** | Pennerstorfer's main measure |
# | `net_income_eur`: mean annual net income of employees | district (23) | **IV** | Pennerstorfer's second measure (they also used the district average) |
# | `share_knowledge_JKM`: % employed in ICT, finance, professional services | Zählsprengel | **IV** (new) | occupational proxy |
# | `rent_eur_m2_std`: asking rent, € per m², for a *standard flat* | Zählsprengel centre (kernel over nearest *k* listings) | **IV** | stands in for Pennerstorfer's proprietary house prices (see §3b) |
# | `log_child_density` | cell | control | competition for places |
# | `share_foreign_born_15_64` | Zählbezirk | control | Pennerstorfer's country-of-birth control (Austria vs abroad only) |
# | `emp_rate_15_64`: employed ÷ residents 15–64 | Zählsprengel | control | stand-in for female employment |
# | `ubahn_in_cell` | cell | control | Pennerstorfer's U-Bahn control |
#
# Every continuous variable is turned into a **child-weighted z-score**, so a coefficient reads: *a 1 SD higher status is associated with β SD more access*. That makes the access measures directly comparable.
#
# ### 3b. Rent: the fourth status measure
# Pennerstorfer & Pennerstorfer (2021) used the price of a *standard flat at each Zählsprengel's centre* from a proprietary valuation model. Our free equivalent is built from current willhaben asking rents (`scripts/scrape_willhaben.py`, `scripts/build_rent_index.py`):
# 1. **Clean:** Vienna, address-precise coordinates only (postcode-centre listings dropped), 15–300 m², plausible € per m², duplicates removed.
# 2. **Hedonic adjustment:** log € per m² regressed on flat traits only (size, rooms, floor, outdoor space, new-build project, private vs agency). The residual is what location adds.
# 3. **Adaptive kernel:** at each Zählsprengel centre, a Gaussian-weighted mean of the residuals of the *k* nearest listings, *k* chosen by leave-one-out error. Adding the standard flat back gives € per m² for the same flat in each place.
#
# Raw Zählsprengel medians would rest on about 3 listings each; the kernel borrows strength from neighbours, so every Zählsprengel has a value based on *k* listings. Neighbouring Zählsprengel share listings, so errors are clustered at the Zählbezirk. *Caveats:* asking rents for flats on the market now, not sitting tenants' rents; Vienna's large municipal and cooperative stock is barely listed.

# %%
rent = pd.read_csv(PROC / "zsp_rent_index.csv", usecols=["zsp_id", "rent_eur_m2_std", "rent_n_eff", "rent_bandwidth_m"])
grid["rent_eur_m2_std"] = pd.to_numeric(grid["zsp_id"]).map(rent.set_index(pd.to_numeric(rent["zsp_id"]))["rent_eur_m2_std"])   # ids are float in the grid (NaN outside ZSPs)
print("cells with a rent value:", grid.rent_eur_m2_std.notna().sum(), "of", len(grid),
      f"| children covered: {grid.loc[grid.rent_eur_m2_std.notna(), 'children_u6'].sum():,.0f} of {D.sum():,.0f}")

ub = pd.read_csv(PROC / "ubahn_stops.csv")          # U-Bahn stops (route_type 1) extracted from gtfs.zip
ub = gpd.GeoDataFrame(ub, geometry=gpd.points_from_xy(ub.stop_lon, ub.stop_lat), crs=4326).to_crs(GRID_CRS)
grid["ubahn_in_cell"] = grid.index.isin(gpd.sjoin(grid[["geometry"]], ub[["geometry"]], predicate="contains").index).astype(int)
grid["log_child_density"] = np.log1p(grid["children_u6"] / CELL_KM2)
grid["zsp"] = grid["zsp_id"]; grid["zbz"] = grid["SUB_DISTRICT_CODE"]; grid["district"] = grid["DISTRICT_CODE"]

IVS = {"pct_tertiary": ("% with degree", "district"),
       "net_income_eur": ("Mean net income", "district"),
       "share_knowledge_JKM": ("% knowledge jobs", "zbz"),    # ZSP measure; cluster at ZBZ because foreign-born control is ZBZ
       "rent_eur_m2_std": ("Rent € per m²", "zbz")}           # ZSP kernel; neighbours share listings, so cluster at ZBZ
CONTROLS = ["log_child_density", "share_foreign_born_15_64", "emp_rate_15_64"]
DVS = {"dv1_euclid": "DV1 Euclidean 2SFCA", "dv2_reliable": "DV2R Reliable network 2SFCA",
       "dv2_network": "DV2 Average network 2SFCA", "dv3_reliability_loss": "DV3 Reliability loss"}
EXTRA_DVS = ["dv2r_public", "dv2r_private", "dv2r_t10", "dv2r_t20", "dv2r_share15", "dv2r_p80", "dv2r_p95"]
DV_LABELS = {**DVS, "dv2r_public": "DV2R public sites", "dv2r_private": "DV2R private sites",
             "dv2r_t10": "DV2R 10-min catchment", "dv2r_t20": "DV2R 20-min catchment",
             "dv2r_share15": "DV2R share of departures ≤ 15 min", "dv2r_p80": "DV2R 80th percentile", "dv2r_p95": "DV2R 95th percentile"}

cols = list(DVS) + EXTRA_DVS + list(IVS) + CONTROLS
df = grid.loc[(grid.children_u6 > 0) & grid[cols].notna().all(axis=1),
              cols + ["ubahn_in_cell", "children_u6", "zsp", "zbz", "district"]].copy()
print(f"analysis sample: {len(df):,} cells, {df.children_u6.sum():,.0f} of {D.sum():,.0f} children")

def wz(s, w):
    m = np.average(s, weights=w); return (s - m) / np.sqrt(np.average((s - m) ** 2, weights=w))
for c in cols:
    df[c + "_z"] = wz(df[c], df.children_u6)

def wtercile(s, w):
    order = s.sort_values(kind="mergesort").index
    cum = w.loc[order].cumsum() / w.sum()
    return pd.Series(np.select([cum <= 1/3, cum <= 2/3], ["low", "middle"], "high"), index=order).reindex(s.index)
for c in IVS:
    df[c + "_t3"] = pd.Categorical(wtercile(df[c], df.children_u6), ["low", "middle", "high"], ordered=True)
print(df.groupby("pct_tertiary_t3", observed=True).children_u6.sum().round(0).to_dict(), "← children per education tercile")

# %% [markdown]
# ## 4. Model A: Pennerstorfer-style OLS
# `access_z ~ status_z + controls`, weighted by children, errors clustered (see table in §3). One regression per status measure × access measure. **DV2R is the headline**; DV1 is the replication, DV2 shows what averaging over departures would conclude, DV3 is the reliability outcome.

# %%
def fit(dv, iv, cluster):
    f = f"{dv}_z ~ {iv}_z + " + " + ".join(c + "_z" for c in CONTROLS) + " + ubahn_in_cell"
    return smf.wls(f, df, weights=df.children_u6).fit(cov_type="cluster", cov_kwds={"groups": df[cluster]})

rows, models = [], {}
for dv in list(DVS) + EXTRA_DVS:
    for iv, (lab, cl) in IVS.items():
        m = models[(dv, iv)] = fit(dv, iv, cl)
        b, se = m.params[iv + "_z"], m.bse[iv + "_z"]
        rows.append(dict(dv=dv, status=lab, beta=b, se=se, lo=b - 1.96 * se, hi=b + 1.96 * se,
                         p=m.pvalues[iv + "_z"], r2=m.rsquared, clusters=df[cl].nunique()))
res = pd.DataFrame(rows)
res.to_csv(FIG / "model_A_status_coefficients.csv", index=False)
res[res.dv.isin(DVS)].round(3)

# %% [markdown]
# Full output for one model (education → DV2R), to see the controls:

# %%
print(models[("dv2_reliable", "pct_tertiary")].summary().tables[1])

# %% [markdown]
# ## 4b. Effects in real units
# In a linear model without interactions, the average marginal effect *is* the coefficient, so what readers need is a translation into **places per 100 children**. Two versions, both holding the controls constant:
# * **per 1 SD status:** β × SD(access)
# * **low → high tercile:** the per-SD effect × the gap between the average child in the low and the high tercile (in SD of status)
#
# ⚠️ Standardised β depend on how much each measure varies between cells. Compare measures in these real units, not by the size of β alone.

# %%
w = df.children_u6
def wsd(x): m = np.average(x, weights=w); return np.sqrt(np.average((x - m) ** 2, weights=w))
UNIT = {"dv3_reliability_loss": 100}      # DV3 shown in percentage points
rows = []
for dv in ["dv1_euclid", "dv2_reliable", "dv2_network", "dv2r_public", "dv2r_private", "dv3_reliability_loss"]:
    scale = wsd(df[dv]) * UNIT.get(dv, 1); mean = np.average(df[dv], weights=w) * UNIT.get(dv, 1)
    for iv, (lab, _) in IVS.items():
        t = df.groupby(iv + "_t3", observed=True).apply(lambda d: np.average(d[iv], weights=d.children_u6))
        gap_sd = (t["high"] - t["low"]) / wsd(df[iv])
        m = models[(dv, iv)]; lo, hi = m.conf_int().loc[iv + "_z"]; b = m.params[iv + "_z"]
        rows.append({"access": DV_LABELS[dv], "status": lab, "mean": mean, "per_SD": b * scale, "CI_low": lo * scale, "CI_high": hi * scale,
                     "low_to_high_tercile": b * scale * gap_sd, "as_%_of_mean": b * scale * gap_sd / mean * 100})
effects = pd.DataFrame(rows)
effects.to_csv(FIG / "effects_real_units.csv", index=False)
print("Units: places per 100 children; DV3 in percentage points of access lost")
effects.round(1)

# %% [markdown]
# ## 5. Model B: provider type, and robustness
# Same regression on DV2R, with access to **public** and to **private (non-profit)** places as separate DVs (every child counts as demand in both). Then robustness of DV2R: catchment 10 and 20 min, the binary "share of departures within 15 min" weighting, and the 80th / 95th travel-time percentiles.

# %%
res[res.dv.isin(EXTRA_DVS)].round(3)

# %% [markdown]
# ### 5b. Robustness: adding the Gemeindebau share as a control
# `gemeindebau_per_100_res` (municipal-housing dwellings per 100 residents, Zählbezirk; built and de-duplicated in the EDA notebook §2g, §3g) is not in Pennerstorfer's models, so it is **not** in the main specification. Here Model A is re-fitted with it as an extra control, on the same cells, with the same clustering. If the status coefficients barely move, the main results do not depend on housing tenure. The table also shows the Gemeindebau coefficient itself.

# %%
df["gemeindebau_per_100_res"] = grid.loc[df.index, "gemeindebau_per_100_res"]
print(f"cells without a Gemeindebau value: {df['gemeindebau_per_100_res'].isna().sum()}")
df["gemeindebau_per_100_res_z"] = wz(df["gemeindebau_per_100_res"].fillna(0), df.children_u6)

def fit_gb(dv, iv, cluster):
    f = (f"{dv}_z ~ {iv}_z + " + " + ".join(c + "_z" for c in CONTROLS)
         + " + gemeindebau_per_100_res_z + ubahn_in_cell")
    return smf.wls(f, df, weights=df.children_u6).fit(cov_type="cluster", cov_kwds={"groups": df[cluster]})

rob = []
for dv in ["dv1_euclid", "dv2_reliable", "dv2_network", "dv2r_public", "dv2r_private", "dv3_reliability_loss"]:
    for iv, (lab, cl) in IVS.items():
        m0, m1 = models[(dv, iv)], fit_gb(dv, iv, cl)
        rob.append({"access": DV_LABELS[dv], "status": lab,
                    "beta_main": m0.params[iv + "_z"], "p_main": m0.pvalues[iv + "_z"],
                    "beta_with_gb": m1.params[iv + "_z"], "p_with_gb": m1.pvalues[iv + "_z"],
                    "change_%": (m1.params[iv + "_z"] / m0.params[iv + "_z"] - 1) * 100,
                    "gb_beta": m1.params["gemeindebau_per_100_res_z"], "gb_p": m1.pvalues["gemeindebau_per_100_res_z"]})
rob = pd.DataFrame(rob)
rob.to_csv(FIG / "robustness_gemeindebau.csv", index=False)
flips = rob[(rob.p_main < .05) != (rob.p_with_gb < .05)]
print(f"status coefficients: median |change| {rob['change_%'].abs().median():.0f}%; "
      f"significance (p < 0.05) changes in {len(flips)} of {len(rob)} models")
rob.round(3)

# %% [markdown]
# ## 6. Validation: does the straight-line measure get it wrong, and is the error related to status?
# * **Agreement:** Spearman correlation of DV1 and DV2R across cells.
# * **Rank shift:** each cell's child-weighted percentile rank under DV2R minus its rank under DV1. Positive = the reliable network measure says this cell is *better* off than the straight-line measure suggests.
# * **Test:** regress the rank shift on status. If status predicts the shift, the Euclidean measure is **biased** with respect to status, not just noisy.

# %%
def wpct(s, w):
    order = s.sort_values(kind="mergesort").index
    return ((w.loc[order].cumsum() - w.loc[order] / 2) / w.sum() * 100).reindex(s.index)
df["rank_shift"] = wpct(df.dv2_reliable, df.children_u6) - wpct(df.dv1_euclid, df.children_u6)
rho = spearmanr(df.dv1_euclid, df.dv2_reliable).statistic
print(f"Spearman DV1 vs DV2R: {rho:.2f} | DV2 vs DV2R: {spearmanr(df.dv2_network, df.dv2_reliable).statistic:.2f}")
print(f"children whose rank shifts by >25 percentiles: {df.loc[df.rank_shift.abs() > 25, 'children_u6'].sum() / df.children_u6.sum():.0%}")
val = []
for iv, (lab, cl) in IVS.items():
    m = smf.wls(f"rank_shift ~ {iv}_z", df, weights=df.children_u6).fit(cov_type="cluster", cov_kwds={"groups": df[cl]})
    val.append(dict(status=lab, shift_per_sd=m.params[iv + "_z"], se=m.bse[iv + "_z"], p=m.pvalues[iv + "_z"]))
pd.DataFrame(val).round(3)

# %% [markdown]
# ## 6b. Reliability: which measure?
# Timetable variation can enter at three points:
# 1. **Time to the nearest site.** Almost always walkable, so it does not depend on the timetable (see the share of zeros below).
# 2. **The catchment.** Further sites are reached by transit; their time, and so their decay weight, moves with departure time. Most variation lives here, so reliability is measured on the 2SFCA.
# 3. **Competition.** A tram gap that cuts a site off from one cell usually cuts it off from neighbours too, so fewer children compete and the site's ratio rises. 2SFCA-based measures capture this net effect; raw travel-time SDs cannot.
#
# Because of the Gaussian decay, a site swinging 14 → 16 min barely matters (weight ≈ 0.05 → 0), while one swinging 8 → 12 min does (≈ 0.67 → 0.30).
#
# | Measure | Definition |
# |---|---|
# | **DV2R** (primary) | access with the 90th-percentile time: reliability *built into* access |
# | **DV3 P10 loss** | 1 − 10th-percentile access ÷ mean access: reliability as its own outcome |
# | DV2R ÷ DV2 | share of average access that is also reliable |
# | CV | SD ÷ mean of access across departures |
# | SD of access | SD across departures, places per 100 children (tied to access level) |
# | SD of nearest-site minutes | SD across departures of time to the closest site (description only) |

# %%
cell_idx = grid.index.get_indexer(df.index)
df["rel_ratio"] = df.dv2_reliable / df.dv2_network.where(df.dv2_network > 0)
df["rel_cv"] = A_t[:, cell_idx].std(axis=0) / df.dv2_network
df["rel_sd"] = A_t[:, cell_idx].std(axis=0)
df["nearest_sd"] = grid.loc[df.index, "nearest_sd_min"]
REL = {"dv3_reliability_loss": "DV3 P10 loss", "rel_ratio": "DV2R ÷ DV2", "rel_cv": "CV of access", "rel_sd": "SD of access",
       "nearest_sd": "SD of nearest-site minutes"}
print(f"children whose nearest-site time never changes over 60 departures: {w[df.nearest_sd == 0].sum() / w.sum():.1%}")
rel_rows = []
for c, lab in REL.items():
    df[c + "_z"] = wz(df[c].fillna(df[c].median()), w)
    m = fit(c, "pct_tertiary", "district")
    rel_rows.append({"measure": lab, "spearman_with_DV2R": spearmanr(df[c], df.dv2_reliable, nan_policy="omit").statistic,
                     "spearman_with_DV3": spearmanr(df[c], df.dv3_reliability_loss, nan_policy="omit").statistic,
                     "education_beta": m.params["pct_tertiary_z"], "p": m.pvalues["pct_tertiary_z"]})
pd.DataFrame(rel_rows).round(3)

# %% [markdown]
# ## 7. Figures
# ### Fig. 1: where the two measures disagree (rank shift map)
# Compares **capacity- and competition-adjusted** access under the straight-line measure (DV1) and the reliable network measure (DV2R), so it can differ everywhere.

# %%
dist = gpd.read_file(DATA / "BEZIRKSGRENZEOGD.json").to_crs(GRID_CRS)
g = grid.join(df[["rank_shift"]])
fig, ax = plt.subplots(figsize=(7, 6))
g.dropna(subset=["rank_shift"]).plot("rank_shift", ax=ax, cmap="RdBu", vmin=-60, vmax=60, legend=True,
    legend_kwds={"label": "Percentile rank under DV2R minus DV1", "shrink": .6})
dist.boundary.plot(ax=ax, color="k", lw=.4)
ax.set_title("Fig. 1  Blue: better off than the straight-line measure says. Red: worse off", fontsize=9); ax.set_axis_off()
fig.savefig(FIG / "fig1_rank_shift_map.png", bbox_inches="tight")

# %% [markdown]
# ### Fig. 2: agreement between the measures

# %%
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, (x, xl) in zip(axes, [("dv1_euclid", "DV1 Euclidean 2SFCA"), ("dv2_network", "DV2 average network 2SFCA")]):
    hb = ax.hexbin(df[x] + 1, df.dv2_reliable + 1, C=df.children_u6, reduce_C_function=np.sum,
                   xscale="log", yscale="log", gridsize=45, cmap=BLUE, mincnt=1)
    lim = [1, max(df[x].max(), df.dv2_reliable.max()) + 1]; ax.plot(lim, lim, color=INK2, lw=.7, ls="--")
    ax.set(xlabel=f"{xl} (+1, log)", ylabel="DV2R reliable network 2SFCA (+1, log)",
           title=f"Spearman ρ = {spearmanr(df[x], df.dv2_reliable).statistic:.2f}")
fig.colorbar(hb, ax=axes, label="children", shrink=.8)
fig.suptitle("Fig. 2  DV2R against the straight-line and the average network measure", x=.01, ha="left")
fig.savefig(FIG / "fig2_dv1_vs_dv2.png", bbox_inches="tight")

# %% [markdown]
# ### Fig. 3: equity gradient by status tercile (z-scores)
# Child-weighted mean access (z-score) per tercile. The error bars on DV2 show the **range across the 60 departures**: how much the tercile's average moves depending on when families leave.

# %%
A_df = pd.DataFrame(A_t.T, index=grid.index, columns=DEPARTURES).loc[df.index]
LINES3 = [("dv1_euclid", "s", "#2a78d6"), ("dv2_reliable", "o", "#eb6834"), ("dv2_network", "^", "#1baf7a")]
fig, axes = plt.subplots(1, len(IVS), figsize=(3.4 * len(IVS), 3.6), sharey=True)
for ax, (iv, (lab, _)) in zip(axes, IVS.items()):
    t3 = df[iv + "_t3"]
    for dv, mk, col in LINES3:
        y = df.groupby(t3, observed=True).apply(lambda d: np.average(d[dv + "_z"], weights=d.children_u6))
        if dv == "dv2_network":
            mu, sd = np.average(df.dv2_network, weights=df.children_u6), np.sqrt(np.cov(df.dv2_network, aweights=df.children_u6))
            per = A_df.groupby(t3, observed=True).apply(lambda d: ((d - mu) / sd).apply(lambda c: np.average(c, weights=df.loc[d.index, "children_u6"])))
            ax.errorbar(range(3), y, yerr=[y - per.min(axis=1), per.max(axis=1) - y], marker=mk, color=col, capsize=3, label=DVS[dv])
        else:
            ax.plot(range(3), y, marker=mk, color=col, label=DVS[dv])
    ax.set(xticks=range(3), xticklabels=["low", "middle", "high"], title=lab, xlabel="status tercile")
    ax.axhline(0, color="grey", lw=.5)
axes[0].set_ylabel("access (child-weighted z-score)"); axes[0].legend(fontsize=7, frameon=False)
fig.suptitle("Fig. 3  Access by neighbourhood status", y=1.03); fig.savefig(FIG / "fig3_equity_gradient.png", bbox_inches="tight")

# %% [markdown]
# ### Fig. 4: coefficient plot (Model A and B)
# One dot per regression: the status coefficient and its 95% interval. If DV1 and DV2R dots sit apart, the access measure changes the conclusion.

# %%
order = ["dv1_euclid", "dv2_reliable", "dv2_network", "dv2r_public", "dv2r_private", "dv3_reliability_loss"]
fig, axes = plt.subplots(1, len(IVS), figsize=(3.4 * len(IVS), 3.4), sharey=True)
for ax, (iv, (lab, _)) in zip(axes, IVS.items()):
    r = res[(res.status == lab) & res.dv.isin(order)].set_index("dv").loc[order[::-1]]
    cols4 = ["#eb6834" if d == "dv2_reliable" else "#2a78d6" for d in r.index]
    for yy, (d, rr) in enumerate(r.iterrows()):
        ax.errorbar(rr.beta, yy, xerr=[[rr.beta - rr.lo], [rr.hi - rr.beta]], fmt="o", capsize=3, color=cols4[yy])
    ax.axvline(0, color="grey", lw=.6); ax.set_title(lab); ax.set_xlabel("β (SD access per SD status)")
axes[0].set_yticks(range(len(order))); axes[0].set_yticklabels([DV_LABELS[o] for o in order[::-1]])
fig.suptitle("Fig. 4  Status coefficients, child-weighted OLS, clustered 95% CI (orange = primary measure)", y=1.03)
fig.savefig(FIG / "fig4_coefficients.png", bbox_inches="tight")

# %% [markdown]
# ### Fig. 5: access by departure minute
# **Top left:** share of all cell–site pairs reachable within 10, 15 and 20 min at each departure minute (07:30 = 100). **Top right:** scheduled stop departures at Vienna stops per 5 minutes, by mode, from the same GTFS timetable (07:30 = 100). Together they show that reach falls slightly after the peak because the timetable thins out, mostly buses. **Bottom:** child-weighted average network 2SFCA at each departure minute for low-, middle- and high-status children, one panel per status measure. Flat lines mean departure time does not matter; lines that diverge would mean unreliability falls unevenly.

# %%
pairs = pd.DataFrame({f"≤ {t} min": [(np.nan_to_num(tt[k], nan=99) <= t).sum() for k in range(len(tt))] for t in (10, 15, 20)}, index=MINS)

GTFS_CACHE = OUT / "gtfs_stop_departures_5min.csv"
if not GTFS_CACHE.exists():                                     # count once from gtfs.zip (≈1 min), then cache
    with zipfile.ZipFile(DATA / "gtfs.zip") as z:
        cal = pd.read_csv(z.open("calendar.txt"), dtype=str); cd = pd.read_csv(z.open("calendar_dates.txt"), dtype=str)
        DAY = "20261020"
        act = set(cal[(cal.tuesday == "1") & (cal.start_date <= DAY) & (cal.end_date >= DAY)].service_id)
        act = (act | set(cd[(cd.date == DAY) & (cd.exception_type == "1")].service_id)) - set(cd[(cd.date == DAY) & (cd.exception_type == "2")].service_id)
        trips = pd.read_csv(z.open("trips.txt"), usecols=["trip_id", "service_id", "route_id"], dtype=str)
        routes = pd.read_csv(z.open("routes.txt"), usecols=["route_id", "route_type"], dtype=str)
        trips = trips[trips.service_id.isin(act)].merge(routes, on="route_id").set_index("trip_id")["route_type"]
        stops = pd.read_csv(z.open("stops.txt"), usecols=["stop_id", "stop_lat", "stop_lon"], dtype={"stop_id": str})
        stops = gpd.GeoDataFrame(stops, geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat), crs=4326).to_crs(GRID_CRS)
        vstops = set(gpd.sjoin(stops, dist[["geometry"]], predicate="within").stop_id)
        parts = []
        for ch in pd.read_csv(z.open("stop_times.txt"), usecols=["trip_id", "departure_time", "stop_id"], dtype=str, chunksize=3_000_000):
            ch = ch[ch.trip_id.isin(trips.index) & ch.stop_id.isin(vstops)]
            m_ = ch.departure_time.str[:2].astype(int) * 60 + ch.departure_time.str[3:5].astype(int)
            ch = ch[(m_ >= 7 * 60) & (m_ < 9 * 60)]
            parts.append(pd.DataFrame({"bin": (m_[ch.index] // 5) * 5, "mode": ch.trip_id.map(trips).values}))
    sd5 = pd.concat(parts).groupby(["bin", "mode"]).size().unstack(fill_value=0)
    sd5 = sd5.rename(columns={"0": "tram", "1": "U-Bahn", "2": "rail", "3": "bus"})
    sd5.to_csv(GTFS_CACHE)
sd5 = pd.read_csv(GTFS_CACHE, index_col="bin")
sd5 = sd5.loc[(sd5.index >= MINS[0]) & (sd5.index <= MINS[-1])]

MODE_COL = {"bus": "#2a78d6", "tram": "#eb6834", "U-Bahn": "#1baf7a"}
PAIR_COL = {"≤ 10 min": "#9ec5f4", "≤ 15 min": "#3987e5", "≤ 20 min": "#104281"}
ticks = [m for m in MINS if m % 10 == 0]
fig = plt.figure(figsize=(15, 8.2))
gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.05], hspace=.45, wspace=.28)
ax = fig.add_subplot(gs[0, :2])
for c, col in PAIR_COL.items():
    ax.plot(MINS, pairs[c] / pairs[c].iloc[0] * 100, color=col, lw=2, label=c)
ax.set(title="Cell–site pairs reachable (07:30 = 100)", ylabel="index", xticks=ticks, xticklabels=[hhmm(m) for m in ticks])
ax.legend(frameon=False, fontsize=8); ax.grid(axis="y", color=GRID_INK, lw=.6)
ax = fig.add_subplot(gs[0, 2:])
for c, col in MODE_COL.items():
    if c in sd5:
        ax.plot(sd5.index + 2.5, sd5[c] / sd5[c].iloc[0] * 100, color=col, lw=2, marker="o", ms=3, label=f"{c} ({sd5[c].iloc[0]:,} per 5 min at 07:30)")
ax.set(title="Scheduled departures at Vienna stops (07:30 = 100)", ylabel="index", xticks=ticks, xticklabels=[hhmm(m) for m in ticks])
ax.legend(frameon=False, fontsize=8); ax.grid(axis="y", color=GRID_INK, lw=.6)
wv = df.children_u6.to_numpy()
for k_, (iv, (lab, _)) in enumerate(IVS.items()):
    ax = fig.add_subplot(gs[1, k_])
    for lvl, col in TERC.items():
        msk = (df[iv + "_t3"] == lvl).to_numpy()
        y = A_df.to_numpy()[msk].T @ wv[msk] / wv[msk].sum()
        ax.plot(MINS, y, color=col, lw=1.8, label=f"{lvl} status")
    ax.set(title=lab, xticks=ticks[::2], xticklabels=[hhmm(m) for m in ticks[::2]])
    ax.grid(axis="y", color=GRID_INK, lw=.6)
    if k_ == 0:
        ax.set_ylabel("average network 2SFCA\n(places per 100 children)"); ax.legend(frameon=False, fontsize=8)
fig.suptitle("Fig. 5  Access by departure minute, 07:30–08:29", x=.01, ha="left", y=.98)
fig.savefig(FIG / "fig5_by_departure.png", bbox_inches="tight")
print("reach change 07:30 → 08:29:", (pairs.iloc[-1] / pairs.iloc[0] * 100 - 100).round(1).to_dict(),
      "| scheduled departures change:", (sd5.iloc[-1] / sd5.iloc[0] * 100 - 100).round(1).to_dict())

# %% [markdown]
# ### Fig. 6: what the access measures look like
# Child-weighted analysis cells only (others white). DV1, DV2R and DV2 share one colour scale, since all are places per 100 children. The bottom row splits DV2R by provider and shows DV3, the % of access lost at a bad departure.

# %%
gm = grid[["geometry"]].join(df[["dv1_euclid", "dv2_reliable", "dv2_network", "dv2r_public", "dv2r_private", "dv3_reliability_loss"]], how="inner")
gm["dv3_pct"] = gm["dv3_reliability_loss"] * 100
hi12 = np.nanpercentile(gm[["dv1_euclid", "dv2_reliable", "dv2_network"]], 98)
panels = [("dv1_euclid", "DV1 straight-line 2SFCA", "places per 100 children", (0, hi12)),
          ("dv2_reliable", "DV2R reliable network 2SFCA (primary)", "places per 100 children", (0, hi12)),
          ("dv2_network", "DV2 average network 2SFCA", "places per 100 children", (0, hi12)),
          ("dv2r_public", "DV2R, public sites only", "places per 100 children", None),
          ("dv2r_private", "DV2R, private sites only", "places per 100 children", None),
          ("dv3_pct", "DV3 reliability loss", "% of access lost at a bad departure", None)]
fig, axes = plt.subplots(2, 3, figsize=(16, 11))
for ax, (c, title, unit, lim) in zip(axes.ravel(), panels):
    lo, hi = lim if lim else np.nanpercentile(gm[c], [2, 98])
    gm.plot(c, ax=ax, cmap=BLUE, vmin=lo, vmax=hi, edgecolor="none", legend=True, missing_kwds={"color": MISSING},
            legend_kwds={"label": unit, "orientation": "horizontal", "shrink": .7, "pad": .02, "aspect": 30})
    dist.boundary.plot(ax=ax, color=INK2, lw=.35); ax.set_axis_off(); ax.set_title(title, fontsize=10, loc="left")
fig.suptitle("Fig. 6  Access measures, 250 m cells with children", fontsize=11, x=.01, ha="left", y=1.01)
fig.tight_layout(); fig.savefig(FIG / "fig6_access_maps.png", bbox_inches="tight")

# %% [markdown]
# ### Fig. 7: equity gradients in real units
# Like Fig. 3, but in the units readers care about and for every access measure: the child-weighted mean for children in low-, middle- and high-status terciles (columns: the four status measures). The last row is the share of children with **fewer than 25 places per 100** on DV2R, the descriptive "underserved" count. The number above each panel is the high-minus-low gap. These are raw gaps; Model A's coefficients are the same comparison net of density and the controls.

# %%
UNDER = 25
df["dv2r_below"] = (df["dv2_reliable"] < UNDER).astype(float) * 100
ROWS = [("dv1_euclid", "DV1 straight-line", "places / 100 children", 1), ("dv2_reliable", "DV2R reliable network", "places / 100 children", 1),
        ("dv2r_public", "DV2R public", "places / 100 children", 1), ("dv2r_private", "DV2R private", "places / 100 children", 1),
        ("dv3_reliability_loss", "DV3 reliability loss", "% of access lost", 100),
        ("dv2r_below", f"DV2R < {UNDER} places / 100", "% of children", 1)]
grad_rows = []
fig, axes = plt.subplots(len(ROWS), len(IVS), figsize=(3.4 * len(IVS), 2.3 * len(ROWS)), sharey="row")
for r, (dv, dlab, unit, k) in enumerate(ROWS):
    for c, (iv, (ilab, _)) in enumerate(IVS.items()):
        ax = axes[r, c]
        y = df.groupby(iv + "_t3", observed=True).apply(lambda d: np.average(d[dv], weights=d.children_u6) * k).reindex(["low", "middle", "high"])
        ax.bar(range(3), y, color=list(TERC.values()), width=.7)
        for i, v in enumerate(y):
            ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=7, color=INK2)
        gap = y["high"] - y["low"]
        ax.set_title(f"{ilab}: gap {gap:+.1f}" if r == 0 else f"gap {gap:+.1f}", fontsize=8.5, loc="left")
        ax.set_xticks(range(3), ["low", "mid", "high"] if r == len(ROWS) - 1 else ["", "", ""])
        ax.grid(axis="y", color=GRID_INK, lw=.6); ax.set_axisbelow(True)
        if c == 0:
            ax.set_ylabel(f"{dlab}\n({unit})", fontsize=8)
        grad_rows.append({"access": dlab, "status": ilab, **y.round(2).to_dict(), "high_minus_low": round(gap, 2)})
fig.suptitle("Fig. 7  Child-weighted access by status tercile (raw, no controls)", fontsize=11, x=.01, ha="left", y=1.0)
fig.tight_layout(); fig.savefig(FIG / "fig7_equity_gradients_units.png", bbox_inches="tight")
grad = pd.DataFrame(grad_rows); grad.to_csv(FIG / "equity_gradients_units.csv", index=False)
grad.pivot(index="access", columns="status", values="high_minus_low").round(1)

# %% [markdown]
# ### Fig. 8: concentration curves
# Cells are ordered from **lowest to highest status**. x = cumulative share of children; y = cumulative share of the places they can reach (access × children). On the diagonal, every child gets the same access. A curve **below** it means lower-status areas get less than their share. The **concentration index** (CI, from health economics) is twice the area between curve and diagonal: **CI > 0 favours higher-status areas**, CI < 0 lower-status ones, 0 = equal. District measures have only 23 values, so cells with the same value are grouped before plotting (ties have no order).

# %%
def concentration(d, rank_col, val_col, w="children_u6"):
    t = d.groupby(rank_col).apply(lambda g: pd.Series({"w": g[w].sum(), "v": (g[val_col] * g[w]).sum()})).sort_index()
    cw = np.r_[0, t["w"].cumsum() / t["w"].sum()]; cv = np.r_[0, t["v"].cumsum() / t["v"].sum()]
    return cw, cv, 1 - 2 * np.trapezoid(cv, cw)

SERIES = {"dv1_euclid": "#2a78d6", "dv2_reliable": "#eb6834", "dv2r_public": "#1baf7a", "dv2r_private": "#eda100"}
CURVE_LABEL = {"dv1_euclid": "DV1 straight-line", "dv2_reliable": "DV2R reliable", "dv2r_public": "DV2R public", "dv2r_private": "DV2R private"}
ci_rows = []
fig, axes = plt.subplots(1, len(IVS), figsize=(3.9 * len(IVS), 4.3), sharey=True)
for ax, (iv, (ilab, _)) in zip(axes, IVS.items()):
    ax.plot([0, 1], [0, 1], color=INK2, lw=.7, ls="--")
    for dv, col in SERIES.items():
        cw_, cv_, ci = concentration(df, iv, dv)
        ax.plot(cw_, cv_, color=col, lw=2, label=f"{CURVE_LABEL[dv]}  CI {ci:+.3f}")
        ci_rows.append({"status": ilab, "access": DV_LABELS[dv], "CI": ci})
    ax.set(xlabel="cumulative share of children (low status first)", xlim=(0, 1), ylim=(0, 1), aspect="equal")
    ax.set_title(ilab, fontsize=10, loc="left"); ax.legend(fontsize=7, frameon=False, loc="upper left")
axes[0].set_ylabel("cumulative share of places reached")
fig.suptitle("Fig. 8  Concentration curves (CI > 0: access favours higher-status areas)", fontsize=11, x=.01, ha="left", y=1.02)
fig.tight_layout(); fig.savefig(FIG / "fig8_concentration_curves.png", bbox_inches="tight")
ci_tab = pd.DataFrame(ci_rows).pivot(index="access", columns="status", values="CI")
ci_tab.to_csv(FIG / "concentration_indices.csv"); ci_tab.round(3)

# %% [markdown]
# ### Fig. 9: how much does access vary with departure minute?
# Redraws the variability maps of the routing notebook (`vienna_childcare_accessibility.ipynb`, figure 2) with the 60 one-minute departures, over the transit network, water and childcare sites. **Left:** SD of the time to the nearest site (minutes): zero almost everywhere, because the nearest site is usually walkable. **Right:** SD of network 2SFCA across departures (places per 100 children): this is where the timetable matters, through sites reached by tram or bus. Colours saturate at the 95th percentile. Cells without children are not shown.

# %%
del tt, T90, T_MED                                             # the raw matrices are no longer needed; frees ~3 GB
LINES_CACHE = OUT / "gtfs_route_lines_vienna.gpkg"
if not LINES_CACHE.exists():                                   # build once from gtfs.zip shapes, then cache
    with zipfile.ZipFile(DATA / "gtfs.zip") as z:
        tr = pd.read_csv(z.open("trips.txt"), usecols=["route_id", "shape_id"], dtype=str).drop_duplicates("shape_id")
        ro = pd.read_csv(z.open("routes.txt"), usecols=["route_id", "route_type"], dtype=str)
        sh = pd.read_csv(z.open("shapes.txt"), dtype={"shape_id": str}).sort_values(["shape_id", "shape_pt_sequence"])
    lines = gpd.GeoDataFrame([{"shape_id": k, "geometry": LineString(zip(g_.shape_pt_lon, g_.shape_pt_lat))}
                              for k, g_ in sh.groupby("shape_id") if len(g_) > 1], crs=4326)
    lines = lines.merge(tr, on="shape_id").merge(ro, on="route_id").to_crs(GRID_CRS)
    lines = gpd.clip(lines, dist.union_all()).dissolve("route_type").reset_index()
    lines.to_file(LINES_CACHE, driver="GPKG")
lines = gpd.read_file(LINES_CACHE)
water = gpd.read_file(OUT / "vienna_natural_water.geojson").to_crs(GRID_CRS)
donau = gpd.read_file(OUT / "vienna_donau_rivers.geojson").to_crs(GRID_CRS)

def overlays(ax):
    lines.plot(ax=ax, color="black", lw=.5, alpha=.35, zorder=2)
    donau.plot(ax=ax, color="#3180AB", lw=1, alpha=.5, zorder=3)
    water.plot(ax=ax, color="#003153", alpha=.55, zorder=4)
    fac.plot(ax=ax, color="black", markersize=5, marker="D", alpha=.4, zorder=5)
    dist.boundary.plot(ax=ax, color="#263238", lw=.5, zorder=6)
    gpd.GeoSeries([dist.union_all()], crs=GRID_CRS).boundary.plot(ax=ax, color="#263238", lw=1.6, zorder=7)
    ax.set_axis_off()

kids = grid[grid.children_u6 > 0]
fig, axes = plt.subplots(1, 2, figsize=(20, 10))
for ax, (c, title, unit) in zip(axes, [("nearest_sd_min", "Fig. 9  Variability across the 60 departures, 07:30–08:29\n(a) SD of time to the nearest site", "minutes"),
                                       ("access_sd", "\n(b) SD of network 2SFCA", "places per 100 children")]):
    vmax = max(float(kids[c].quantile(.95)), .05)
    kids.plot(c, ax=ax, cmap=ORANGE, vmin=0, vmax=vmax, edgecolor="none", alpha=.85, zorder=1, legend=True,
              legend_kwds={"label": f"{unit} (saturates at the 95th percentile, {vmax:.2f})", "orientation": "horizontal",
                           "shrink": .6, "pad": .01, "aspect": 35, "extend": "max"})
    overlays(ax)
    share0 = np.average(kids[c] == 0, weights=kids.children_u6)
    ax.set_title(f"{title}\n{share0:.0%} of children see no variation", fontsize=11, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig9_access_variability_maps.png", bbox_inches="tight")

# %% [markdown]
# ## 8. Save

# %%
keep = ["gid", "origin_id", "dv1_euclid", "dv2_reliable", "dv2_network", "dv2r_public", "dv2r_private", "dv2r_t10", "dv2r_t20",
        "dv2r_share15", "dv2r_p80", "dv2r_p95", "dv3_reliability_loss", "nearest_sd_min", "nearest_p90_min", "access_sd",
        "ubahn_in_cell", "log_child_density", "rent_eur_m2_std"]
grid[keep].join(df[["rank_shift"]]).to_csv(PROC / "grid250_access_measures.csv", index=False)
print("saved", PROC / "grid250_access_measures.csv", "and figures in", FIG)
