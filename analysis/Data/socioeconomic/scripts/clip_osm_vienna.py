"""Clip the Austria OSM extract to the Vienna routing area, keeping crossing ways complete.

    python clip_osm_vienna.py <austria.osm.pbf> <vienna.osm.pbf>      (needs: pip install osmium)

Box = all GTFS stops (lat 48.00-48.30, lon 16.20-16.55) + ~2-3 km, more than a 30-min walk, so every
trip the 30-minute routing can find stays inside it. Like `osmium extract --strategy complete_ways`:
1. collect the ids of nodes inside the box;
2. keep every way with at least one such node, plus *all* of that way's nodes (no cut-off streets);
3. keep relations (turn restrictions, routes) whose members are kept;
4. write nodes, ways, relations.
"""
import sys
import osmium

SRC, DST = sys.argv[1], sys.argv[2]
LAT0, LAT1, LON0, LON1 = 47.97, 48.34, 16.15, 16.60


def inside(loc):
    return loc.valid() and LAT0 <= loc.lat <= LAT1 and LON0 <= loc.lon <= LON1


nodes_in = set()
for n in osmium.FileProcessor(SRC, osmium.osm.NODE):
    if inside(n.location):
        nodes_in.add(n.id)
print(f"pass 1: {len(nodes_in):,} nodes inside the box", flush=True)

ways, nodes_needed = set(), set(nodes_in)
for w in osmium.FileProcessor(SRC, osmium.osm.WAY):
    refs = [r.ref for r in w.nodes]
    if any(r in nodes_in for r in refs):
        ways.add(w.id)
        nodes_needed.update(refs)
print(f"pass 2: {len(ways):,} ways kept; {len(nodes_needed):,} nodes needed", flush=True)

rels = set()
for r in osmium.FileProcessor(SRC, osmium.osm.RELATION):
    if any((m.type == "w" and m.ref in ways) or (m.type == "n" and m.ref in nodes_needed) for m in r.members):
        rels.add(r.id)
print(f"pass 3: {len(rels):,} relations kept", flush=True)

with osmium.SimpleWriter(DST, overwrite=True) as out:
    for o in osmium.FileProcessor(SRC):
        if (o.is_node() and o.id in nodes_needed) or (o.is_way() and o.id in ways) or (o.is_relation() and o.id in rels):
            out.add(o)
print("written", DST)
