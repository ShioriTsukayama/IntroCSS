"""Builds vienna_routing_1min_colab.ipynb from the cells below:  python build_colab_notebook.py"""
import nbformat as nbf
from pathlib import Path

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# Minute-by-minute routing to childcare, Vienna (Google Colab)

Walking + public-transport routing from every 250 m cell to every childcare site, for **every minute** of the morning (an earlier version of the project used six 10-minute windows). The output is one origin × destination travel-time matrix per departure minute, in **exactly the format of the existing matrices** (`outputs/origin_destination_matrices/*.npz`), so `accessibility_analysis.ipynb` reads it with one changed folder path.

**What is the same as the original routing:** Tuesday 20 Oct 2026, the same GTFS feed, walk + transit with walking access and egress, 4.5 km/h, 30-minute cut-off, the same 6,950 grid origins (`o0…`) and 1,682 childcare sites (`d0…`) in the same order. The OSM street network is the same file, clipped to the Vienna area (all roads within ~2–3 km of every transit stop, more than a 30-minute walk), so that it fits in Colab's memory.

**What is different:** `departure_time_window` = **1 minute** (the original used r5py's default of 10 minutes and stored the median over those 10 minutes). Each file is therefore one real departure. Section 6 checks that the median of the ten 1-minute runs 07:30–07:39 reproduces the old 07:30 matrix.

### Before you start
1. **Upload** these five files to Google Drive as `MyDrive/vienna_routing/`: `origins.csv`, `destinations.csv`, `reference_10min_window_0730.npz` (all in this folder) and `gtfs.zip`, `vienna-261020.osm.pbf` (run `python get_data.py` in the repository root to download them).
2. **Runtime → Change runtime type → CPU**, with **High-RAM** if you have Colab Pro. A GPU does nothing for this routing (R5 is CPU-only Java), so don't pay for one. Speed scales with the number of CPU cores: free Colab has **2 cores**, which is likely *slower* than your own 8-core laptop or desktop. **Measured on the 8-core MacBook:** about 3–5 minutes per departure, so **4–5 hours for all 60**. Free Colab is likely 3–4× slower (15–20 h), longer than its ~12 h session limit, so either use Colab Pro (High-RAM CPU runtime, more cores), or split the work with `SHARD` over two or three sessions, or simply reconnect and rerun (finished minutes are kept). Cell 5 times the first departure and prints an estimate for the rest.
3. **Run all cells.** If Colab disconnects, reconnect and **run all again**: finished minutes are saved in Drive and skipped.

### Output
`MyDrive/vienna_routing/origin_destination_matrices_1min/2026-10-20_HHMM.npz`, one per minute, plus `progress.csv`. Copy the folder to `analysis/outputs/origin_destination_matrices_1min/` (or download the finished matrices with `python get_data.py`)."""),

md("## 1. Settings"),
code('''DRIVE_DIR = "/content/drive/MyDrive/vienna_routing"   # where the inputs were uploaded; outputs go here too
TRAVEL_DATE = "2026-10-20"                            # a Tuesday inside the GTFS service period (same as before)
FIRST, LAST = "07:30", "08:29"                        # every minute in this range (inclusive) = 60 departures;
                                                      # matches the period the old six 10-min windows covered
WINDOW_MINUTES = 1                                    # 1 = one real departure per file
MAX_MINUTES = 30                                      # R5 cut-off, as before
WALK_KMH = 4.5                                        # as before
ORIGIN_BATCH = 1000                                   # origins per R5 call (memory vs. overhead)

# Optional: split the departures over several Colab sessions running at the same time.
# Session k of n routes every n-th minute starting at k, e.g. SHARD = (0, 2) and (1, 2) in two notebooks.
SHARD = (0, 1)

OUT_SUBDIR = "origin_destination_matrices_1min"'''),

md("## 2. Google Drive and inputs"),
code('''from google.colab import drive
drive.mount("/content/drive")

from pathlib import Path
import shutil, os
DRIVE = Path(DRIVE_DIR)
NEEDED = ["origins.csv", "destinations.csv", "gtfs.zip", "vienna-261020.osm.pbf", "reference_10min_window_0730.npz"]
missing = [f for f in NEEDED if not (DRIVE / f).exists()]
if missing:
    raise FileNotFoundError(f"Upload these to {DRIVE}: {missing}")

# Work on Colab's local disk (much faster than reading through Drive); results are copied back to Drive.
WORK = Path("/content/work"); WORK.mkdir(exist_ok=True)
for f in NEEDED:
    if not (WORK / f).exists() or (WORK / f).stat().st_size != (DRIVE / f).stat().st_size:
        shutil.copy2(DRIVE / f, WORK / f)
    print(f"{f:36s} {(WORK / f).stat().st_size / 1e6:8.1f} MB")
OUTDIR = DRIVE / OUT_SUBDIR; OUTDIR.mkdir(exist_ok=True)'''),

md("""## 3. Java 21 and r5py
r5py 1.1.7 (the version used for the original routing) runs R5 v7, which needs **Java 21**. Colab ships without it; this installs it with `apt`, falling back to the Eclipse Temurin build if `apt` has no Java 21 package. Takes 1–2 minutes."""),
code('''import subprocess, sys, glob

def java21_home():
    for pattern in ["/usr/lib/jvm/java-21-openjdk-*", "/content/jdk-21*"]:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]

if java21_home() is None:
    r = subprocess.run("apt-get -qq update && apt-get -qq install -y openjdk-21-jdk-headless", shell=True)
    if java21_home() is None:   # fallback: Eclipse Temurin 21 from adoptium.net
        subprocess.run("cd /content && wget -q -O jdk21.tar.gz "
                       "'https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jdk/hotspot/normal/eclipse' "
                       "&& tar xzf jdk21.tar.gz && rm jdk21.tar.gz", shell=True, check=True)
JAVA_HOME = java21_home()
os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["PATH"] = f"{JAVA_HOME}/bin:" + os.environ["PATH"]
print(subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.splitlines()[0])

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "r5py==1.1.7"], check=True)'''),

md("""## 4. Memory, then build the network
The Java heap must be set **before** r5py is imported. It gets ~75% of the runtime's RAM. Building the network from the OSM and GTFS files takes a few minutes. If you change the heap, use *Runtime → Restart session* and run all cells again."""),
code('''import psutil
ram_gb = psutil.virtual_memory().total / 1024**3
heap_gb = max(4, int(ram_gb * 0.75))
if "r5py" not in sys.modules:
    sys.argv += ["--max-memory", f"{heap_gb}G"]
print(f"RAM {ram_gb:.1f} GB -> Java heap {heap_gb} GB | CPU cores: {os.cpu_count()}")

import time
from datetime import datetime, timedelta
import numpy as np, pandas as pd, geopandas as gpd
import r5py
print("r5py", r5py.__version__)

origins_df = pd.read_csv(WORK / "origins.csv")
dest_df = pd.read_csv(WORK / "destinations.csv")
assert len(origins_df) == 6950 and len(dest_df) == 1682, "unexpected number of origins / destinations"
assert (origins_df["id"] == [f"o{i}" for i in range(len(origins_df))]).all()
assert (dest_df["id"] == [f"d{i}" for i in range(len(dest_df))]).all()
origins = gpd.GeoDataFrame(origins_df[["id"]], geometry=gpd.points_from_xy(origins_df.lon, origins_df.lat), crs="EPSG:4326")
destinations = gpd.GeoDataFrame(dest_df[["id"]], geometry=gpd.points_from_xy(dest_df.lon, dest_df.lat), crs="EPSG:4326")
origin_ids = origins_df["id"].astype(str).to_numpy(dtype=object)        # same dtype as the old files
destination_ids = dest_df["id"].astype(str).to_numpy(dtype=object)
opos = {v: i for i, v in enumerate(origin_ids)}; dpos = {v: i for i, v in enumerate(destination_ids)}

t0 = time.time()
network = r5py.TransportNetwork(WORK / "vienna-261020.osm.pbf", [WORK / "gtfs.zip"])
print(f"network built in {(time.time() - t0) / 60:.1f} min")'''),

md("""## 5. Route every minute (resumable)
For each departure minute: route all origins in batches, assemble the 6,950 × 1,682 matrix (minutes; NaN = no trip within 30 min), and save it to Drive. The save writes a temporary file first and renames it once complete, so an interrupted run never leaves a half-written matrix. Minutes already in Drive are checked and skipped.

The first departure is timed, and the cell prints how long the rest will take. If that is far longer than on your own machine, stop here and run the same notebook locally instead (see the note at the end)."""),
code('''import warnings
warnings.filterwarnings("ignore", message=".*departure time window is below 5 minutes.*")   # see section 6

signature = "|".join(map(str, [TRAVEL_DATE, MAX_MINUTES, WALK_KMH, "TRANSIT+WALK_DIRECT+WALK_ACCESS_EGRESS",
                               f"window={WINDOW_MINUTES}min", "osm=vienna-261020 (clipped)",
                               (WORK / "gtfs.zip").stat().st_size, "r5py=" + r5py.__version__]))
first = datetime.strptime(f"{TRAVEL_DATE} {FIRST}", "%Y-%m-%d %H:%M")
last = datetime.strptime(f"{TRAVEL_DATE} {LAST}", "%Y-%m-%d %H:%M")
all_minutes = [first + timedelta(minutes=k) for k in range(int((last - first).total_seconds() // 60) + 1)]
k, n = SHARD
my_minutes = all_minutes[k::n]
print(f"{len(all_minutes)} departures {FIRST}–{LAST}; this session (shard {k} of {n}) routes {len(my_minutes)}")

def out_file(dep):
    return OUTDIR / f"{TRAVEL_DATE}_{dep:%H%M}.npz"

def is_complete(path):
    try:
        with np.load(path, allow_pickle=True) as z:
            return (z["travel_times"].shape == (len(origin_ids), len(destination_ids))
                    and np.array_equal(z["origin_ids"], origin_ids) and str(z["signature"]) == signature)
    except Exception:
        return False

def route(dep):
    M = np.full((len(origin_ids), len(destination_ids)), np.nan, dtype=np.float32)
    for s in range(0, len(origins), ORIGIN_BATCH):
        m = r5py.TravelTimeMatrix(
            network, origins.iloc[s:s + ORIGIN_BATCH], destinations,
            departure=dep, departure_time_window=timedelta(minutes=WINDOW_MINUTES),
            transport_modes=[r5py.TransportMode.TRANSIT, r5py.TransportMode.WALK],
            access_modes=[r5py.TransportMode.WALK], egress_modes=[r5py.TransportMode.WALK],
            speed_walking=WALK_KMH, max_time=timedelta(minutes=MAX_MINUTES),
            max_time_walking=timedelta(minutes=MAX_MINUTES))
        tt = m["travel_time"]
        tt = tt.dt.total_seconds() / 60 if pd.api.types.is_timedelta64_dtype(tt) else pd.to_numeric(tt, errors="coerce")
        M[m["from_id"].map(opos).to_numpy(), m["to_id"].map(dpos).to_numpy()] = tt.to_numpy(np.float32)
    return M

log_file = OUTDIR / f"progress_shard{k}of{n}.csv"
todo = [d for d in my_minutes if not is_complete(out_file(d))]
print(f"already done: {len(my_minutes) - len(todo)}; to route now: {len(todo)}")
times = []
for i, dep in enumerate(todo):
    t = time.time()
    M = route(dep)
    tmp_local = WORK / f"tmp_{dep:%H%M}.npz"
    np.savez_compressed(tmp_local, travel_times=M, origin_ids=origin_ids, destination_ids=destination_ids,
                        signature=signature, departure=f"{dep:%Y-%m-%d %H:%M}", window_minutes=WINDOW_MINUTES)
    tmp_drive = out_file(dep).with_suffix(".partial")
    shutil.copy2(tmp_local, tmp_drive); os.replace(tmp_drive, out_file(dep)); tmp_local.unlink()
    times.append(time.time() - t)
    pd.DataFrame([{"departure": f"{dep:%H:%M}", "seconds": round(times[-1]), "reachable_pairs": int(np.isfinite(M).sum()),
                   "finished": datetime.now().isoformat(timespec="seconds")}]).to_csv(
        log_file, mode="a", header=not log_file.exists(), index=False)
    left = (len(todo) - i - 1) * np.mean(times)
    print(f"{dep:%H:%M} done in {times[-1] / 60:.1f} min | {i + 1}/{len(todo)} | "
          f"about {left / 3600:.1f} h left (finishes ~{datetime.now() + timedelta(seconds=left):%H:%M} Colab time)", flush=True)
print("all departures of this shard are saved in", OUTDIR)'''),

md("""## 6. Checks
1. **Complete and compatible:** every minute is present, with the right shape and the same id order as the old matrices.
2. **Same routing as before:** R5's 10-minute window reports, for each pair, the **5th-fastest of the 10 one-minute departures** it contains (its "median" is the lower middle value, not the average of the 5th and 6th). So the 5th-fastest of our 1-minute matrices for 07:30–07:39 must reproduce the old 07:30 matrix (`reference_10min_window_0730.npz`) **exactly**, including which pairs are unreachable.

*Tested before handing over* (16–17 Nov, on 60 origins × all 1,682 sites, r5py 1.1.7): the clipped network reproduced the old 07:30 matrix on 100% of pairs, and the 5th-fastest of ten 1-minute runs matched it on 100% of pairs. r5py warns that windows under 5 minutes "may cause adverse effects with routing"; on this fully scheduled timetable they do not, and this check confirms it on the full output. Expect **100.00%** below; anything clearly lower means the set-up differs (wrong files, other r5py version)."""),
code('''files = {d: out_file(d) for d in all_minutes}
have = [d for d, f in files.items() if is_complete(f)]
print(f"complete: {len(have)} of {len(all_minutes)} departures")
if len(have) < len(all_minutes):
    print("missing:", [f"{d:%H:%M}" for d in all_minutes if d not in have][:20], "→ rerun section 5 (and the other shards)")

ten = [first + timedelta(minutes=j) for j in range(10)]
if all(d in have for d in ten):
    S = np.stack([np.load(files[d], allow_pickle=True)["travel_times"] for d in ten])
    fifth = np.sort(np.where(np.isnan(S), np.inf, S), axis=0)[4]          # 5th-fastest of 10 = R5's window "median"
    fifth[np.isinf(fifth)] = np.nan
    ref = np.load(WORK / "reference_10min_window_0730.npz", allow_pickle=True)
    assert np.array_equal(ref["origin_ids"], origin_ids) and np.array_equal(ref["destination_ids"], destination_ids)
    R = ref["travel_times"]
    same = (np.isnan(fifth) & np.isnan(R)) | (fifth == R)
    print(f"identical to the old 07:30 matrix on {same.mean():.2%} of all {same.size:,} pairs (expected: 100.00%)")
    print(f"reachable pairs: new {np.isfinite(fifth).sum():,} vs old {np.isfinite(R).sum():,}")
    if same.mean() < 0.999:
        d_ = (fifth - R)[np.isfinite(fifth) & np.isfinite(R)]
        print("NOT identical: differences (new − old), percentiles 1/50/99:", np.percentile(d_, [1, 50, 99]).round(2))
else:
    print("check 2 needs the ten departures 07:30–07:39; run the shard(s) that hold them first")'''),

md("## 7. A first look: how much does the timetable move access minute by minute?"),
code('''import matplotlib.pyplot as plt
rows = []
for d in have:
    M = np.load(files[d], allow_pickle=True)["travel_times"]
    nearest = np.nanmin(np.where(np.isnan(M), np.inf, M), axis=1)
    rows.append({"departure": d, "pairs_within_15": np.mean(M <= 15) * 100,
                 "median_nearest": np.median(np.where(np.isinf(nearest), MAX_MINUTES, nearest))})
summary = pd.DataFrame(rows).set_index("departure")
fig, ax = plt.subplots(1, 2, figsize=(12, 3.5))
summary["pairs_within_15"].plot(ax=ax[0], marker=".", title="% of cell–site pairs reachable within 15 min")
summary["median_nearest"].plot(ax=ax[1], marker=".", title="median minutes to the nearest site (all cells)")
for a in ax: a.set_xlabel("departure")
plt.tight_layout(); plt.show()'''),

md("""## 8. Bring the results home
The matrices are already in Drive (`MyDrive/vienna_routing/origin_destination_matrices_1min/`, ~1.7 MB each, ~100 MB for 60). Download that folder (or run the cell below for a single zip) and put it at:

`analysis/outputs/origin_destination_matrices_1min/`

Then, in `accessibility_analysis.ipynb` §1, change `OUT / "origin_destination_matrices"` to `OUT / "origin_destination_matrices_1min"`. Everything downstream (DV2, DV3, Fig. 5) then uses 60 departures, and DV3's 10th percentile becomes a true 10th percentile.

**Running locally instead:** the same notebook runs in Jupyter on your own machine. Skip cells 2–3 (set `WORK` to the folder holding the five input files, set `OUTDIR`, and make sure Java 21 is installed)."""),
code('''shutil.make_archive("/content/origin_destination_matrices_1min", "zip", OUTDIR)
from google.colab import files as colab_files
colab_files.download("/content/origin_destination_matrices_1min.zip")'''),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "colab": {"provenance": [], "machine_shape": "hm"}, "language_info": {"name": "python"}})
out = Path(__file__).with_name("vienna_routing_1min_colab.ipynb")
nbf.write(nb, out)
print("wrote", out)
