"""Scrape current Vienna rental listings from willhaben.at.

    python -I scripts/scrape_willhaben.py raw/willhaben_rents_<date>.csv

Replaces Onur's Selenium scraper (Onur Code/Walkthrough.ipynb). Differences:
* reads the JSON the page embeds (`__NEXT_DATA__`) instead of CSS classes, so it does not
  break when the site's styling changes, and it gets fields the cards do not show;
* coordinates come from willhaben itself, with a precision flag (LOCATION_QUALITY:
  1.0 = address, 0.5 = postcode centre), so no Google geocoding and no silent
  district-centroid points;
* floor area is kept, so rent can be expressed per m^2.

Ethics / ToS: willhaben's robots.txt forbids automated access. The research team decided
to proceed for this non-commercial course project (see the paper's ethics note). To keep
the footprint small the script makes one request per results page (~60 in total), waits
6-10 s between requests, uses only plain search URLs (none of the parameters robots.txt
disallows), and stores only the listing attributes needed for a rent index: no headings,
descriptions, photos, advertiser names or contact details.
"""
import csv, json, random, re, sys, time
import urllib.request

BASE = "https://www.willhaben.at/iad/immobilien/mietwohnungen/wien?rows=90&page={page}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
KEEP = ["ADID", "COORDINATES", "LOCATION_QUALITY", "POSTCODE", "DISTRICT", "LOCATION",
        "PRICE", "RENT/PER_MONTH_LETTINGS", "ESTATE_SIZE/LIVING_AREA", "ESTATE_SIZE/USEABLE_AREA",
        "ESTATE_SIZE", "NUMBER_OF_ROOMS", "PRICE/SQUARE_METER", "PROPERTY_TYPE", "PROPERTY_TYPE_FLAT",
        "FLOOR", "FREE_AREA_TYPE_NAME", "ISPRIVATE", "PROJECT_ID", "PUBLISHED_String", "ADTYPE_ID",
        "PRODUCT_ID"]


def fetch(page):
    req = urllib.request.Request(BASE.format(page=page), headers={"User-Agent": UA,
                                                                   "Accept-Language": "de-AT,de;q=0.9"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))["props"]["pageProps"]["searchResult"]


def main(out):
    rows, seen, page, total = [], set(), 1, None
    while True:
        for attempt in range(3):
            try:
                sr = fetch(page); break
            except Exception as e:            # transient network / rate-limit errors
                print(f"page {page}: {e}; retry in 60 s", flush=True); time.sleep(60)
        else:
            print("giving up at page", page); break
        total = total or sr["rowsFound"]
        ads = sr["advertSummaryList"]["advertSummary"]
        new = 0
        for a in ads:
            at = {x["name"]: x["values"][0] for x in a["attributes"]["attribute"]}
            if at.get("ADID") in seen:
                continue
            seen.add(at.get("ADID")); new += 1
            rows.append({k: at.get(k, "") for k in KEEP})
        print(f"page {page}: {len(ads)} ads, {new} new, {len(rows)}/{total}", flush=True)
        if not ads or len(rows) >= total or page * 90 >= total + 90:
            break
        page += 1
        time.sleep(random.uniform(6, 10))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scraped_on"] + KEEP)
        w.writeheader()
        for r in rows:
            w.writerow({"scraped_on": time.strftime("%Y-%m-%d"), **r})
    print("wrote", len(rows), "listings to", out)


if __name__ == "__main__":
    main(sys.argv[1])
