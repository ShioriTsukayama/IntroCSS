"""Stream-parse Statistik Austria INSPIRE population GML (inside zip) and keep Vienna only.

Usage: python -I parse_inspire.py <zip> <out_csv> <kind>
kind = zsp  -> keep spatial codes starting with '9' (Vienna Zählsprengel)
kind = grid -> keep grid cells inside Vienna bbox (EPSG:3035)
Output: long table  unit_id, dim, value   (dim = TOTAL / male / female / 0-5 / ... / NACE letter)
"""
import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

ZIP, OUT, KIND = sys.argv[1], sys.argv[2], sys.argv[3]
PD = "{http://inspire.ec.europa.eu/schemas/pd/4.0}"
XL = "{http://www.w3.org/1999/xlink}href"
# Vienna bbox in EPSG:3035 with ~2 km margin (Vienna approx N 2,786,000-2,820,000 ; E 4,778,000-4,820,000)
N0, N1, E0, E1 = 2_780_000, 2_826_000, 4_772_000, 4_826_000
cell_re = re.compile(r"RES(\d+)mN(\d+)E(\d+)")


def keep(code):
    if KIND == "zsp":
        return code.startswith("9")
    m = cell_re.search(code)
    n, e = int(m.group(2)), int(m.group(3))
    return N0 <= n <= N1 and E0 <= e <= E1


n_in = n_out = 0
with zipfile.ZipFile(ZIP) as z, open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["unit_id", "dim", "value", "status"])
    name = z.namelist()[0]
    with z.open(name) as fh:
        for ev, el in ET.iterparse(fh, events=("end",)):
            if el.tag == PD + "areaOfDissemination":
                el.clear()  # drop the big coverage polygon
            if el.tag != PD + "StatisticalValue":
                continue
            n_in += 1
            sp = el.find(f"{PD}dimensions/{PD}Dimensions/{PD}spatial")
            href = sp.get(XL)
            code = href.rstrip("/").split("/")
            # zsp: .../AreaStatisticalUnit/<code>/<date> ; grid: .../StatisticalGridCell/<cellcode>
            code = code[-2] if KIND == "zsp" else code[-1]
            if keep(code):
                th = el.find(f"{PD}dimensions/{PD}Dimensions/{PD}thematic/{PD}ClassificationItem/{PD}type")
                dim = th.get(XL).rstrip("/").split("/")[-1] if th is not None else "TOTAL"
                v = el.find(PD + "value")
                val = v.text.strip() if v is not None and v.text and v.text.strip() else ""
                st = el.find(PD + "specialValue")
                status = st.get(XL).split("/")[-1] if st is not None else ""
                w.writerow([code, dim, val, status])
                n_out += 1
            el.clear()
print(f"{ZIP.split('/')[-1]}: {n_in:,} values read, {n_out:,} kept -> {OUT}")
