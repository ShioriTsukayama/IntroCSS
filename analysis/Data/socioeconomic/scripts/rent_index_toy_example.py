"""Toy example for rent_measure_reference.md §3: every step of the rent index on 15 made-up listings.
Run: python -I scripts/rent_index_toy_example.py   (prints the numbers quoted in the doc)"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
pd.set_option("display.width", 140)

# A toy street, 1,200 m long, three Zählsprengel: A = 0-400 m, B = 400-800 m, C = 800-1,200 m.
# TRUE rent of a standard 65 m2 old flat: A 15.0, B 16.5, C 18.0 EUR/m2 (B +10%, C +20% vs A).
# New-builds cost +30% per m2; every +10% of floor area costs -1.5% per m2.
L = pd.DataFrame({
    "id":      [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    "x":       [40, 110, 190, 260, 340, 430, 470, 520, 580, 640, 720, 1000, 520, 600, 900],
    "quality": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.5, 1],
    "area":    [70, 62, 85, 74, 50, 52, 48, 60, 50, 55, 80, 75, 60, 65, 66],
    "rooms":   [3, 2, 3, 3, 2, 2, 2, 2, 2, 2, 3, 3, 2, 2, 25],
    "new":     [0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0],
    "noise":   [.02, -.03, .01, -.01, .00, .03, -.02, .01, -.01, .02, -.02, -.01, .01, 0, 0],
})
loc = np.select([L.x < 400, L.x < 800], [np.log(15.0), np.log(16.5)], np.log(18.0))
L["rent"] = (np.exp(loc + 0.30 * L.new - 0.15 * np.log(L.area / 65) + L.noise) * L.area).round(0)
L.loc[L.id == 15, "rent"] = 11880                                   # a typo: annual rent entered
L["zsp"] = pd.cut(L.x, [0, 400, 800, 1200], labels=list("ABC"))
print("== raw listings ==\n", L.drop(columns="noise").to_string(index=False))

# ---- Step 2: cleaning
L = L[L.quality >= 0.75]                                            # id 14: postcode centre only
L = L.assign(eur_m2=L.rent / L.area)
L = L[L.eur_m2.between(5, 60)]                                      # id 15: 180 EUR/m2 typo
L = L[~L.duplicated(["x", "area", "rent"])].copy()                  # id 13 = id 8 listed twice
print("\n== kept after cleaning:", sorted(L.id.tolist()), "==")

# ---- What the simple approaches give
print("\nlistings per ZSP:", L.zsp.value_counts().sort_index().to_dict())
print("raw median EUR/m2 by ZSP:", L.groupby("zsp", observed=False).eur_m2.median().round(2).to_dict(), "(truth A 15.0, B 16.5, C 18.0)")
print("raw median rent/room by ZSP:", (L.rent / L.rooms).groupby(L.zsp, observed=False).median().round(0).to_dict())
print("district (all three) median EUR/m2:", round(L.eur_m2.median(), 2))

# ---- Step 3: hedonic model, flat traits only
L["log_eur_m2"] = np.log(L.eur_m2); L["log_area"] = np.log(L.area)
h = smf.ols("log_eur_m2 ~ log_area + new", L).fit()
print("\nhedonic coefs:", h.params.round(3).to_dict(), f"R2 = {h.rsquared:.2f}  (truth: log_area -0.15, new +0.30)")
L["resid"] = h.resid
std_log = h.params.Intercept + h.params.log_area * np.log(65)       # standard flat: 65 m2, not new-build
print(f"standard flat at an average location: {np.exp(std_log):.2f} EUR/m2")
print(L[["id", "zsp", "x", "area", "new", "eur_m2", "resid"]].round(3).to_string(index=False))
print("mean residual by ZSP:", L.groupby("zsp", observed=False).resid.mean().round(3).to_dict())

# ---- Step 4: kernel at ZSP centres over the k nearest listings
X, r, ids = L.x.to_numpy(float), L.resid.to_numpy(), L.id.to_numpy()
def kernel(x0, k, skip=None):
    d = np.abs(X - x0)
    if skip is not None: d[skip] = np.inf
    o = np.argsort(d)[:k]; hbw = max(d[o][-1], 1.0)
    w = np.exp(-0.5 * (d[o] / (hbw / 2)) ** 2)
    return (w * r[o]).sum() / w.sum(), hbw, w.sum() ** 2 / (w ** 2).sum(), o, w

for k in [2, 4, 6, 11]:
    err = [r[i] - kernel(X[i], k, skip=i)[0] for i in range(len(L))]
    print(f"leave-one-out RMSE, k = {k:2d}: {np.sqrt(np.mean(np.square(err))):.4f}")
print(f"no location at all:       {r.std():.4f}")

K = 6
print(f"\n-- index with k = {K} --")
for z, x0, true in [("A", 200, 15.0), ("B", 600, 16.5), ("C", 1000, 18.0)]:
    m, hbw, neff, o, w = kernel(x0, K)
    print(f"ZSP {z} centre {x0} m: nearest ids {ids[o].tolist()}, distances {np.abs(X[o] - x0).astype(int).tolist()} m, "
          f"weights {np.round(w, 2).tolist()}, bandwidth {hbw:.0f} m, n_eff {neff:.1f}, "
          f"weighted mean resid {m:+.3f} -> index {np.exp(std_log + m):.2f} (truth {true})")
