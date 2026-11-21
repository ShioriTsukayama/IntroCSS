"""Official-data child estimate per 250 m cell:
Zählsprengel 0-4 (+1/5 of 5-9 ~ age 5) spread over the official 100 m population grid (dasymetric),
then 100 m cells split onto the 250 m analysis grid by area (areal weighting).
Run from Data/socioeconomic with python -I, after build_inspire_tables.py.

Validation check (13 Nov 2026), not a step of the pipeline: socioeconomic_eda.ipynb §3b now performs the same
allocation itself, and its output (processed/grid250_children_official_2026.csv) is not read by the analysis.
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

P = "processed/"
h = pd.read_csv("raw/statistik_inspire/vienna_extracts/pd_popreg_100m_7767c33f.csv")
h["value"] = pd.to_numeric(h["value"], errors="coerce").fillna(0)
m = h.unit_id.str.extract(r"N(\d+)E(\d+)").astype(int)
# N is regex group 0, E is group 1 -> box(minx=E, miny=N, ...)
c100 = gpd.GeoDataFrame({"pop100": h.value.values, "id100": h.unit_id.values},
                        geometry=[box(e, n, e + 100, n + 100) for n, e in zip(m[0].values, m[1].values)], crs=3035)

zsp = gpd.read_file(P + "zaehlsprengel_2026_inspire.gpkg")[["zsp_id", "age_0_5", "age_5_10", "geometry"]]
zsp["kids_0_5"] = zsp.age_0_5.fillna(0) + zsp.age_5_10.fillna(0) / 5   # ~ ages 0-5 (6 years)

# step 1: each 100 m cell -> Zählsprengel by centre point
pts = c100.copy(); pts["geometry"] = c100.centroid
j = gpd.sjoin(pts, zsp[["zsp_id", "kids_0_5", "geometry"]], how="left", predicate="within")
j = j[~j.index.duplicated()]
miss = j.zsp_id.isna()
if miss.any():  # centres falling just outside (river, edge): nearest Zählsprengel
    near = gpd.sjoin_nearest(pts[miss], zsp[["zsp_id", "kids_0_5", "geometry"]], how="left")
    near = near[~near.index.duplicated()]
    j.loc[miss, ["zsp_id", "kids_0_5"]] = near[["zsp_id", "kids_0_5"]].values
c100["zsp_id"] = j.zsp_id.values
# step 2: dasymetric share of the ZSP's children
tot = c100.groupby("zsp_id").pop100.transform("sum")
kids = c100.zsp_id.map(zsp.set_index("zsp_id").kids_0_5)
c100["kids100"] = np.where(tot > 0, kids * c100.pop100 / tot, 0)
lost = zsp.kids_0_5.sum() - c100.kids100.sum()
print(f"children 0-5 official {zsp.kids_0_5.sum():,.0f}; allocated to 100 m cells {c100.kids100.sum():,.0f} "
      f"(unallocated {lost:,.0f}: Zählsprengel with no populated 100 m cell centre)")

# step 3: 100 m -> 250 m by area share
grid = gpd.read_file(P + "grid250_analysis.gpkg")[["cellcode", "children_u6", "pop_total", "geometry"]]
ov = gpd.overlay(c100[["kids100", "pop100", "geometry"]], grid[["cellcode", "geometry"]], how="intersection")
w = ov.area / 10_000.0
out = pd.DataFrame({"cellcode": ov.cellcode, "children_u6_official": ov.kids100 * w, "pop_official": ov.pop100 * w}) \
        .groupby("cellcode").sum()
res = grid.set_index("cellcode")[["children_u6", "pop_total"]].join(out).fillna(0)
res[["children_u6_official", "pop_official"]].to_csv(P + "grid250_children_official_2026.csv")
print(f"250 m grid: official children {res.children_u6_official.sum():,.0f} vs our estimate {res.children_u6.sum():,.0f}")
print("cell-level correlation (Pearson) children:", round(res.children_u6.corr(res.children_u6_official), 3),
      "| Spearman:", round(res.children_u6.corr(res.children_u6_official, method="spearman"), 3))
d = res.children_u6 - res.children_u6_official
print("abs difference per cell: median %.1f, 90th pct %.1f, max %.0f children" % (d.abs().median(), d.abs().quantile(.9), d.abs().max()))
big = res[(res.children_u6_official > 0) | (res.children_u6 > 0)]
print("cells with children in one source but ~0 (<0.5) in the other:",
      int(((big.children_u6 < .5) & (big.children_u6_official >= 5)).sum()), "(ours~0, official>=5);",
      int(((big.children_u6_official < .5) & (big.children_u6 >= 5)).sum()), "(official~0, ours>=5)")
