# Childcare accessibility in Vienna — Intro to CSS final project

Does access to childcare places by public transport differ with neighbourhood status in Vienna? We replicate and extend Pennerstorfer & Pennerstorfer (2021) with a timetable-based, reliability-adjusted 2SFCA (60 one-minute departures, 07:30–08:29).

**Status (18 Nov 2026):** routing and the main analysis are done. The primary outcome is **DV2R**, the reliable network 2SFCA (90th-percentile travel time across departures). See the status box at the top of `docs/socioeconomic_analysis_roadmap.md` for the key results so far.

## Where to start

| Read this | For |
|---|---|
| `docs/socioeconomic_analysis_roadmap.md` | Overview, current results, open to-dos |
| `docs/methods_primer.md` | Plain-language glossary: 2SFCA, dasymetric mapping, concentration index, MAUP … |
| `docs/explanatory_models_primer.md` | Which regression models we use and why |
| `docs/data_inventory.md` | Every dataset, whether it is core, supporting or unused |
| `docs/data_sources_and_merging_guide.md` | Where the data came from and how geographies were merged |
| `docs/rent_measure_reference.md` | How the rent-based status measure was built |

## Layout

```
docs/                         analysis documents (above)
analysis/
  accessibility_analysis.ipynb   main analysis: access measures, models, figures
  socioeconomic_eda.ipynb        builds the status measures and controls (EDA)
  Data/socioeconomic/scripts/    source .py for both notebooks + data-building scripts
  Data/socioeconomic/processed/  analysis-ready tables (grid, Zählsprengel, Zählbezirk)
  outputs/analysis/              final figures (fig1–fig9) and result tables
  outputs/eda_socioeconomic/     EDA figures
  colab_routing/                 the Colab notebook that produced the travel-time matrices
```

The docs refer to `'My' Code/…`; in this repo that folder is `analysis/`.

## Not in this repo

Left out on purpose (too large for git, superseded, or not ours to republish):

- **Large raw inputs:** OSM extract (`austria-261020.osm.pbf`), GTFS timetable (`gtfs.zip`), the 60 travel-time matrices (`origin_destination_matrices_1min/`, 85 MB), and the raw downloads in `Data/socioeconomic/raw/`. Sources and download details are in `docs/data_inventory.md` and `docs/data_sources_and_merging_guide.md`. Ask Stash for a copy.
- **Scraped rental listings** (raw willhaben scrape and listing-level file). Only the aggregated per-Zählsprengel index (`zsp_rent_index.csv`) is included.
- **Superseded work:** the 6-departure analysis, the October notebooks and figures, Onur's earlier code, early experiments.
- **Papers / readings** (copyrighted PDFs).
