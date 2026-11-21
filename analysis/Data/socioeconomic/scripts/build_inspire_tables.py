"""Validation check (13 Nov 2026), not a step of the pipeline: the analysis does not read its outputs.

Turns the Vienna INSPIRE extracts into wide Zählsprengel tables and compares the official counts with the
births-based child estimate used before the official data were available (agreement at Zählbezirk level:
r = 0.97; see docs/data_sources_and_merging_guide.md §2a). Writes processed/zaehlsprengel_2026_inspire.*
and processed/grid250_pop_official_2026.csv for reference.

It reads processed/grid250_analysis.gpkg and zaehlbezirke_analysis.*, so it can only run after
socioeconomic_eda.ipynb. Run from Data/socioeconomic with: python -I scripts/build_inspire_tables.py
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

X = "raw/statistik_inspire/vienna_extracts/"
P = "processed/"

# ---------- 1. Zählsprengel population by 5-year age (1 Jan 2026) ----------
z = pd.read_csv(X + "pd_popreg_zsp_7767c34f.csv", dtype={"unit_id": str})
print("ZSP status values:", z.status.value_counts(dropna=False).to_dict())
z["value"] = pd.to_numeric(z["value"], errors="coerce")
zw = z.pivot_table(index="unit_id", columns="dim", values="value", aggfunc="first")
conf = z[z.status == "confidential"].groupby("unit_id").dim.apply(list)
age_cols = [c for c in zw.columns if c[0].isdigit()]
age_cols = sorted(age_cols, key=lambda c: int(c.split("-")[0].rstrip("+")))
zw = zw[["TOTAL", "male", "female"] + age_cols]
zw.columns = ["pop_total", "pop_male", "pop_female"] + ["age_" + c.replace("-", "_").replace("+", "plus") for c in age_cols]
zw.index.name = "zsp_id"
zw["zbz_code"] = zw.index.str[:5].astype(int)
zw["n_confidential_cells"] = conf.reindex(zw.index).str.len().fillna(0).astype(int)
print(f"ZSP units: {len(zw)}; total pop {zw.pop_total.sum():,.0f}; age 0-4 {zw.age_0_5.sum():,.0f} "
      f"({zw.age_0_5.isna().sum()} units with 0-4 suppressed)")

# ---------- 2. Zählsprengel employed residents by workplace sector (31 Oct 2024) ----------
a = pd.read_csv(X + "pd_aest_zsp_77681182.csv", dtype={"unit_id": str})
a["value"] = pd.to_numeric(a["value"], errors="coerce")
aw = a.pivot_table(index="unit_id", columns="dim", values="value", aggfunc="first")
aw.columns = ["pop_total_2024" if c == "TOTAL" else f"emp_nace_{c}" for c in aw.columns]
aw.index.name = "zsp_id"
nace = [c for c in aw.columns if c.startswith("emp_nace_")]
aw["emp_total"] = aw[nace].sum(axis=1, min_count=1)  # TOTAL in the file = all residents
print(f"AEST: residents {aw.pop_total_2024.sum():,.0f}; employed (sum of sectors) {aw.emp_total.sum():,.0f}")
# simple sector-mix status proxies (share of employed residents)
aw["share_knowledge_JKM"] = aw[["emp_nace_J", "emp_nace_K", "emp_nace_M"]].sum(axis=1) / aw.emp_total
aw["share_lowwage_IN"] = aw[["emp_nace_I", "emp_nace_N"]].sum(axis=1) / aw.emp_total
aw["share_public_OPQ"] = aw[["emp_nace_O", "emp_nace_P", "emp_nace_Q"]].sum(axis=1) / aw.emp_total

zsp = zw.join(aw, how="outer")
zsp["district_gkz"] = zsp.index.str[:5].astype(int)   # 90101 = 1st district (Gemeindekennziffer)
pop1564 = zsp[[f"age_{a}_{a+5}" for a in range(15, 65, 5)]].sum(axis=1, min_count=1)
zsp["emp_rate_15_64"] = zsp.emp_total / pop1564   # approx: numerator includes 65+ workers

# ---------- 3. boundaries + spatial link to Zählbezirke (codes do NOT nest) ----------
g = gpd.read_file("raw/statistik_zsp_boundaries_2026/zsp_2026_vienna.geojson").to_crs(3035)
g = g.rename(columns={"g_id": "zsp_id"})[["zsp_id", "geometry"]]
zbg = gpd.read_file(P + "zaehlbezirke_analysis.gpkg")[["SUB_DISTRICT_CODE", "geometry"]].to_crs(3035)
ov = gpd.overlay(g, zbg, how="intersection", keep_geom_type=True)
ov["a"] = ov.area
ov = ov.sort_values("a", ascending=False)
share = ov.groupby("zsp_id").a.transform(lambda s: s / s.sum())
ov["share"] = share
best = ov.drop_duplicates("zsp_id").set_index("zsp_id")
nest = best["share"]
print(f"ZSP->ZBZ nesting: {len(nest)} ZSP; share of area in its main ZBZ: median {nest.median():.4f}, "
      f">=0.99: {(nest >= 0.99).mean():.1%}, <0.9: {(nest < 0.9).sum()} units")
zsp["zbz_code"] = best["SUB_DISTRICT_CODE"].reindex(zsp.index)
zsp["zbz_overlap_share"] = nest.reindex(zsp.index)
zsp.to_csv(P + "zaehlsprengel_2026_inspire.csv")
gz = g.merge(zsp.reset_index(), on="zsp_id", how="left")
gz.to_file(P + "zaehlsprengel_2026_inspire.gpkg", driver="GPKG")
print(f"boundaries: {len(g)} polygons, {gz.pop_total.isna().sum()} without population record")

# ---------- 4. compare with births proxy at Zählbezirk level ----------
zb = pd.read_csv(P + "zaehlbezirke_analysis.csv")
agg = zsp.groupby("zbz_code")[["pop_total", "age_0_5", "age_5_10"]].sum().add_prefix("zsp_")
cmp = zb.set_index("SUB_DISTRICT_CODE")[["pop_total", "pop_0_14", "children_u6_proxy", "children_u6"]].join(agg, how="inner")
print(f"ZBZ matched: {len(cmp)}; MA23 pop {cmp.pop_total.sum():,.0f} vs ZSP-sum {cmp.zsp_pop_total.sum():,.0f}")
print(f"children_u6 (ours) {cmp.children_u6.sum():,.0f}; official 0-4 {cmp.zsp_age_0_5.sum():,.0f}; "
      f"official 0-4 + 1/5 of 5-9 (approx 0-5) {(cmp.zsp_age_0_5 + cmp.zsp_age_5_10/5).sum():,.0f}")
cmp["zsp_age_0_5yrs_approx"] = cmp.zsp_age_0_5 + cmp.zsp_age_5_10 / 5
r = (cmp.children_u6 / cmp.zsp_age_0_5yrs_approx)
print("ratio ours/official per ZBZ: median %.3f, IQR %.3f-%.3f, min %.2f max %.2f" % (r.median(), r.quantile(.25), r.quantile(.75), r.min(), r.max()))
print("ZBZ comparison columns:", cmp.columns.tolist())
num = cmp.select_dtypes("number")
print(num.corr(method="pearson").loc[["zsp_age_0_5"]].round(3).T.to_string())

# ---------- 5. 100 m official population -> 250 m analysis grid (areal weighting) ----------
h = pd.read_csv(X + "pd_popreg_100m_7767c33f.csv")
h["value"] = pd.to_numeric(h["value"], errors="coerce")
m = h.unit_id.str.extract(r"N(\d+)E(\d+)").astype(int)
h["N"], h["E"] = m[0], m[1]
cells100 = gpd.GeoDataFrame(h[["value"]], geometry=[box(e, n, e + 100, n + 100) for n, e in zip(h.N, h.E)], crs=3035)
grid = gpd.read_file(P + "grid250_analysis.gpkg")[["cellcode", "geometry"]]
ov = gpd.overlay(cells100, grid, how="intersection")
ov["pop_part"] = ov.value * ov.area / 10_000.0
pop250 = ov.groupby("cellcode").pop_part.sum().rename("pop_official_2026")
pop250.to_csv(P + "grid250_pop_official_2026.csv")
g250 = gpd.read_file(P + "grid250_analysis.gpkg").set_index("cellcode")
gcols = [c for c in g250.columns if c.startswith(("pop", "ghsl", "children", "u6"))]
both = g250[gcols].join(pop250, how="left").fillna({"pop_official_2026": 0})
print(f"100m -> 250m: Vienna grid total {pop250.sum():,.0f}")
print(both.select_dtypes("number").corr().loc[["pop_official_2026"]].round(3).T.to_string())

# ---------- 6. 1 km age grid (for reference) ----------
k = pd.read_csv(X + "pd_popreg_1km_7767c345.csv")
print("1km dims:", sorted(k.dim.unique())[:6], "... confidential share:",
      round((k.status == "confidential").mean(), 3))
