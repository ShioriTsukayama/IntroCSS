"""Download the large inputs that are too big for git, from this repository's GitHub release.

    python get_data.py              # travel-time matrices only (enough to re-run every notebook)
    python get_data.py --routing    # also the timetable and street network (only needed to redo the routing)

Files land where the notebooks expect them, under analysis/.
"""
import sys, urllib.request, zipfile
from pathlib import Path

RELEASE = "https://github.com/ShioriTsukayama/IntroCSS/releases/download/data-v1/"
HERE = Path(__file__).resolve().parent / "analysis"
FILES = {  # asset name: (where it goes, unzip?)
    "origin_destination_matrices_1min.zip": (HERE / "outputs", True),
}
ROUTING = {
    "gtfs.zip": (HERE / "Data", False),
    "vienna-261020.osm.pbf": (HERE / "Data", False),
}

def fetch(name, dest_dir, unzip):
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / name
    if unzip and (dest_dir / Path(name).stem).is_dir():
        print(f"{name}: already unpacked, skipping"); return
    if not unzip and target.exists():
        print(f"{name}: already present, skipping"); return
    print(f"downloading {name} …")
    urllib.request.urlretrieve(RELEASE + name, target)
    if unzip:
        with zipfile.ZipFile(target) as z:
            z.extractall(dest_dir)
        target.unlink()
    print(f"  → {dest_dir.relative_to(HERE.parent)}")

if __name__ == "__main__":
    todo = {**FILES, **(ROUTING if "--routing" in sys.argv else {})}
    for name, (dest, unzip) in todo.items():
        fetch(name, dest, unzip)
