"""Clean the willhaben scrape and build a location rent index per Zählsprengel.

    python -I scripts/build_rent_index.py raw/willhaben_rents_<date>.csv

Run from Data/socioeconomic. Reads the raw adverts and three raw files that are in the repository
(Zählsprengel boundaries, Zählsprengel residents, Zählbezirk boundaries). Writes
* processed/willhaben_listings_clean.gpkg   one row per kept listing (+ hedonic residual)
* processed/zsp_rent_index.csv              one row per Zählsprengel: rent index + sample size
* processed/rent_index_cleaning_log.csv     how many listings each rule removed

Method (mirrors Pennerstorfer & Pennerstorfer 2021, who gave every cell the price of a
*standard flat at its Zählsprengel's centre*):
1. Clean: Vienna only, address-precise coordinates, plausible size and rent, duplicates dropped.
2. Hedonic model: log(rent per m2) on flat traits only. The residual is the part of the rent
   explained by location (plus noise).
3. Adaptive kernel: at each Zählsprengel centroid, average the residuals of the k nearest
   listings (Gaussian weights, bandwidth = distance to the k-th listing). k is chosen by
   leave-one-out prediction error. Adding back the hedonic intercept for a standard flat
   gives "EUR per m2 for a standard flat here".
"""
import sys
import numpy as np, pandas as pd, geopandas as gpd
import statsmodels.formula.api as smf
from scipy.spatial import cKDTree

CRS = "EPSG:3035"


def zaehlsprengel():
    """Zählsprengel polygons with residents (1 Jan 2026) and the Zählbezirk holding most of their area.

    Built from raw files only. Zählsprengel codes do not contain the Zählbezirk, so the two boundary sets
    are overlaid, as in socioeconomic_eda.ipynb §3a.
    """
    zsp = gpd.read_file("raw/statistik_zsp_boundaries_2026/zsp_2026_vienna.geojson").to_crs(CRS)
    zsp = zsp.rename(columns={"g_id": "zsp_id"})[["zsp_id", "geometry"]]
    ages = pd.read_csv("raw/statistik_inspire/vienna_extracts/pd_popreg_zsp_7767c34f.csv", dtype={"unit_id": str})
    total = ages[ages["dim"] == "TOTAL"].set_index("unit_id")["value"]
    zsp["pop_total"] = zsp["zsp_id"].map(pd.to_numeric(total, errors="coerce"))     # NaN: no population record
    zbz = gpd.read_file("raw/ZAEHLBEZIRKOGD.json").to_crs(CRS)
    zbz["SUB_DISTRICT_CODE"] = 90000 + zbz["ZBEZ"].astype(int)                       # '0307' -> 90307
    ov = gpd.overlay(zsp, zbz[["SUB_DISTRICT_CODE", "geometry"]], how="intersection", keep_geom_type=True)
    ov["a"] = ov.area
    main = ov.sort_values("a", ascending=False).drop_duplicates("zsp_id").set_index("zsp_id")
    zsp["zbz_code"] = zsp["zsp_id"].map(main["SUB_DISTRICT_CODE"]).astype(float)
    # Zählsprengel in neither Statistik Austria table (22 without residents, such as parks and rail yards) get no
    # Zählbezirk; this only affects the descriptive Zählbezirk medians, not the index.
    emp = pd.read_csv("raw/statistik_inspire/vienna_extracts/pd_aest_zsp_77681182.csv", dtype={"unit_id": str}, usecols=["unit_id"])
    zsp.loc[~zsp["zsp_id"].isin(set(ages["unit_id"]) | set(emp["unit_id"])), "zbz_code"] = np.nan
    return zsp[["zsp_id", "zbz_code", "pop_total", "geometry"]]


src = sys.argv[1]
raw = pd.read_csv(src, dtype=str)
log = [("scraped", len(raw))]


def step(df, mask, why):
    log.append((why, int((~mask).sum())))
    return df[mask].copy()


df = raw.copy()
num = lambda c: pd.to_numeric(df[c].str.replace(",", ".", regex=False), errors="coerce")
df["rent"] = num("PRICE")
df["area_m2"] = num("ESTATE_SIZE/LIVING_AREA").fillna(num("ESTATE_SIZE/USEABLE_AREA")).fillna(num("ESTATE_SIZE"))
df["rooms"] = num("NUMBER_OF_ROOMS")
df["quality"] = num("LOCATION_QUALITY")
df["floor"] = num("FLOOR")
ll = df["COORDINATES"].str.split(",", expand=True)
df["lat"], df["lon"] = pd.to_numeric(ll[0], errors="coerce"), pd.to_numeric(ll[1], errors="coerce")

df = step(df, df.lat.notna() & df.rent.notna() & df.area_m2.notna(), "missing coordinates, rent or area")
df = step(df, df.quality >= 0.75, "location only to postcode centre (LOCATION_QUALITY 0.5)")
df = step(df, df.area_m2.between(15, 300), "area outside 15-300 m2")
df["eur_m2"] = df.rent / df.area_m2
df = step(df, df.eur_m2.between(5, 60), "rent outside 5-60 EUR/m2 (typos, parking, totals)")
lo, hi = df.eur_m2.quantile([.01, .99])
df = step(df, df.eur_m2.between(lo, hi), f"outside 1st-99th pct of EUR/m2 ({lo:.1f}-{hi:.1f})")
# The same flat listed by several agents: same rounded position, area and rent
key = [df.lat.round(4), df.lon.round(4), df.area_m2.round(0), df.rent.round(0)]
df = step(df, ~pd.concat(key, axis=1).duplicated(), "duplicate listing (same place, area, rent)")

g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(CRS)
zsp = zaehlsprengel()
g = gpd.sjoin(g, zsp[["zsp_id", "zbz_code", "geometry"]], predicate="within", how="left").drop(columns="index_right")
g = step(g, g.zsp_id.notna(), "outside Vienna's Zählsprengel")

# ---- 2. Hedonic model (flat traits only, no location terms) ----
g["log_eur_m2"] = np.log(g.eur_m2)
g["log_area"] = np.log(g.area_m2)
g["rooms_c"] = g.rooms.clip(1, 5).fillna(g.rooms.median()).round().astype(int).astype(str)
g["floor_c"] = pd.cut(g.floor, [-10, 0.5, 2.5, 5.5, 100], labels=["ground", "1-2", "3-5", "6+"]).astype(object).fillna("unknown")
g["outdoor"] = g["FREE_AREA_TYPE_NAME"].fillna("").str.len().gt(0).astype(int)
g["new_project"] = g["PROJECT_ID"].fillna("").str.len().gt(0).astype(int)
g["private_ad"] = g["ISPRIVATE"].fillna("0").eq("1").astype(int)
g["ptype"] = g["PROPERTY_TYPE"].fillna("Wohnung")
rare = g.ptype.value_counts()
g.loc[g.ptype.map(rare) < 30, "ptype"] = "other"
hed = smf.ols("log_eur_m2 ~ log_area + C(rooms_c) + C(floor_c) + outdoor + new_project + private_ad + C(ptype)", g).fit()
print(hed.summary().tables[1])
print(f"hedonic R2 = {hed.rsquared:.2f} (flat traits only; the rest is location + noise)")
g["resid"] = hed.resid

# Standard flat: the sample's median area, its modal rooms/floor/type, no outdoor, not a project, agency ad
std = pd.DataFrame({"log_area": [np.log(g.area_m2.median())], "rooms_c": [g.rooms_c.mode()[0]],
                    "floor_c": [g.floor_c.mode()[0]], "outdoor": [0], "new_project": [0],
                    "private_ad": [0], "ptype": [g.ptype.mode()[0]]})
std_log = float(hed.predict(std)[0])
print(f"standard flat: {g.area_m2.median():.0f} m2, {std.rooms_c[0]} rooms -> {np.exp(std_log):.2f} EUR/m2 at an average location")

# ---- 3. Adaptive kernel; choose k by leave-one-out error ----
xy = np.c_[g.geometry.x, g.geometry.y]
tree = cKDTree(xy)
r = g.resid.to_numpy()


def kernel_mean(dist, idx, k):
    h = np.maximum(dist[:, k - 1:k], 1.0)            # bandwidth: distance to k-th neighbour
    w = np.exp(-0.5 * (dist[:, :k] / (h / 2)) ** 2)  # Gaussian, h = 2 SD
    return (w * r[idx[:, :k]]).sum(1) / w.sum(1), (w.sum(1) ** 2) / (w ** 2).sum(1)


dist_loo, idx_loo = tree.query(xy, k=201)
dist_loo, idx_loo = dist_loo[:, 1:], idx_loo[:, 1:]  # drop self
cv = {k: np.sqrt(np.mean((r - kernel_mean(dist_loo, idx_loo, k)[0]) ** 2)) for k in [10, 15, 20, 30, 40, 60, 80, 120, 160, 200]}
print("leave-one-out RMSE of log rent residual by k:", {k: round(v, 4) for k, v in cv.items()},
      f"| no-location baseline {r.std():.4f}")
K = max(20, min(cv, key=cv.get))
print("chosen k =", K)

cen = zsp.copy(); cen["geometry"] = zsp.geometry.representative_point()
d, i = tree.query(np.c_[cen.geometry.x, cen.geometry.y], k=K)
m, n_eff = kernel_mean(d, i, K)
cen["rent_index_log"] = std_log + m
cen["rent_eur_m2_std"] = np.exp(cen.rent_index_log)
cen["rent_bandwidth_m"] = d[:, -1]
cen["rent_n_eff"] = n_eff
cnt = g.groupby("zsp_id").size()
cen["rent_n_in_zsp"] = cen.zsp_id.map(cnt).fillna(0).astype(int)
cen["rent_raw_median_zsp"] = cen.zsp_id.map(g.groupby("zsp_id").eur_m2.median())
zbz_med = g.groupby("zbz_code").eur_m2.median()
cen["rent_raw_median_zbz"] = cen.zbz_code.map(zbz_med)
cen["rent_n_in_zbz"] = cen.zbz_code.map(g.groupby("zbz_code").size()).fillna(0).astype(int)

out = cen.drop(columns="geometry")
out.to_csv("processed/zsp_rent_index.csv", index=False)
g.drop(columns=[c for c in ["FLOOR"] if c in g]).to_file("processed/willhaben_listings_clean.gpkg", driver="GPKG")
pd.DataFrame(log + [("kept", len(g))], columns=["step", "n"]).to_csv("processed/rent_index_cleaning_log.csv", index=False)

pop = out[out.pop_total > 0]
print("\ncleaning:", *[f"  {a}: {b}" for a, b in log], f"  kept: {len(g)}", sep="\n")
print(f"\nZSP with people: {len(pop)} | listings per ZSP: median {pop.rent_n_in_zsp.median():.0f}, "
      f"{(pop.rent_n_in_zsp == 0).mean():.0%} have none, {(pop.rent_n_in_zsp >= 10).mean():.0%} have >= 10")
print(f"listings per ZBZ: median {g.groupby('zbz_code').size().median():.0f}, min {g.groupby('zbz_code').size().min()}, "
      f"ZBZ with < 5: {(out.drop_duplicates('zbz_code').rent_n_in_zbz < 5).sum()}")
print(f"kernel bandwidth (m) at ZSP centres: median {pop.rent_bandwidth_m.median():.0f}, "
      f"p90 {pop.rent_bandwidth_m.quantile(.9):.0f}; effective n median {pop.rent_n_eff.median():.1f}")
print(f"standard-flat rent EUR/m2, pop-weighted: median {np.average(pop.rent_eur_m2_std, weights=pop.pop_total):.2f}, "
      f"range {pop.rent_eur_m2_std.min():.1f}-{pop.rent_eur_m2_std.max():.1f}")
ok = pop.rent_raw_median_zsp.notna() & (pop.rent_n_in_zsp >= 5)
print(f"Spearman index vs raw ZSP median (ZSP with >= 5 listings, n={ok.sum()}): "
      f"{pop[ok][['rent_eur_m2_std', 'rent_raw_median_zsp']].corr('spearman').iloc[0, 1]:.2f}; "
      f"vs ZBZ median: {pop[['rent_eur_m2_std', 'rent_raw_median_zbz']].corr('spearman').iloc[0, 1]:.2f}")
