#!/usr/bin/env python3
"""
build_data.py
Generates settlements.json from source CSV/XLSX/SQLite files.
Run from the KnowledgeGraph/ directory:
    python website/build_data.py
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent  # KnowledgeGraph/

# ── helpers ──────────────────────────────────────────────────────────────────

RAILWAY_COMPANY_MAP = {
    # Connection_Detail codes → display label
    "CPR": "CPR",
    "CNR": "CNR",
    "CN":  "CNR",
    "GTP": "GTP",
    "QLL&S": "Other",
    "Other": "Other",
    "10_Other_Minor_Railways": "Other",
}

RAILWAY_LINE_KEYWORDS = {
    "CPR": "CPR",
    "CNoR": "CNR",
    "GTPR": "GTP",
    "QLSRSC": "Other",
    "M&NW": "Other",
    "M&NWR": "Other",
}

def classify_railway(railway_lines_str):
    """Return list of distinct railway company codes from the XLSX Railway_lines field."""
    if not isinstance(railway_lines_str, str):
        return []
    found = []
    for key, label in RAILWAY_LINE_KEYWORDS.items():
        if key in railway_lines_str and label not in found:
            found.append(label)
    return found or ["Other"]

def primary_railway(railways):
    """Pick the single 'primary' railway for dot color purposes."""
    priority = ["CPR", "CNR", "GTP", "Other"]
    for p in priority:
        if p in railways:
            return p
    return "Other"

def normalize_coord_name(raw):
    """'Battleford, T-V' → 'Battleford'"""
    return re.sub(r",\s*(T-V|T|C|VL|RM|SV|SC|IRI).*$", "", raw).strip()

def safe_int(val):
    try:
        v = int(val)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None

def safe_float(val):
    try:
        v = float(val)
        import math
        return None if math.isnan(v) else v
    except (ValueError, TypeError):
        return None

def safe_year(val):
    y = safe_float(val)
    if y is None:
        return None
    yi = int(y)
    return yi if 1800 <= yi <= 2000 else None

def nonempty(val):
    if not isinstance(val, str):
        return None
    s = val.strip()
    return s if s else None

# ── load coordinates ─────────────────────────────────────────────────────────

def load_coords():
    df = pd.read_csv(BASE_DIR / "settlement_coordinates.csv")
    coords = {}
    for _, row in df.iterrows():
        name = normalize_coord_name(str(row["settlement"]))
        coords[name] = (float(row["lat"]), float(row["lon"]))
    return coords

# ── load timelines ────────────────────────────────────────────────────────────

def load_timelines():
    df = pd.read_csv(BASE_DIR / "settlement_timelines.csv")
    timelines = {}
    for _, row in df.iterrows():
        name = str(row["Settlement"]).strip()
        year = safe_year(row["Year"])
        event = str(row["Event"]).strip()
        if not name or year is None or not event:
            continue
        if name not in timelines:
            timelines[name] = []
        timelines[name].append({"year": year, "event": event})
    # sort each timeline by year
    for name in timelines:
        timelines[name].sort(key=lambda e: e["year"])
    return timelines

# ── load connections ──────────────────────────────────────────────────────────

def load_connections():
    df = pd.read_csv(BASE_DIR / "settlement_connections.csv")
    connections = {}  # name → {type → [entries]}
    for _, row in df.iterrows():
        s1 = str(row["Settlement_1"]).strip()
        s2 = str(row["Settlement_2"]).strip()
        ctype = str(row["Connection_Type"]).strip()
        detail = str(row["Connection_Detail"]).strip()
        strength = str(row["Strength"]).strip()

        # Map company codes for Railway_Company connections
        display_detail = RAILWAY_COMPANY_MAP.get(detail, detail) if ctype == "Railway_Company" else detail

        entry = {"name": s2, "detail": display_detail, "strength": strength}

        for name in (s1, s2):
            if name not in connections:
                connections[name] = {
                    "Railway_Company": [],
                    "Railway_Corridor": [],
                    "Proximity": [],
                    "Institutional_Timing": [],
                }
            other = s2 if name == s1 else s1
            e = {"name": other, "detail": display_detail, "strength": strength}
            connections[name][ctype].append(e)

    # Deduplicate and cap at 30 per type
    for name in connections:
        for ctype in connections[name]:
            seen = set()
            deduped = []
            for e in connections[name][ctype]:
                if e["name"] not in seen:
                    seen.add(e["name"])
                    deduped.append(e)
            connections[name][ctype] = deduped[:30]

    return connections

# ── load documents ────────────────────────────────────────────────────────────

def load_canadiana_docs():
    """Return {settlement_name: [{title, url}]} top 5 per settlement."""
    db_path = BASE_DIR / "canadiana_rankings.db"
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT ds.settlement_name, d.canadiana_id, d.title, d.weighted_score
        FROM document_settlements ds
        JOIN documents d ON ds.canadiana_id = d.canadiana_id
        ORDER BY ds.settlement_name, d.weighted_score DESC
    """)
    rows = cur.fetchall()
    conn.close()

    docs = {}
    counts = {}
    for settlement, cid, title, score in rows:
        if settlement not in docs:
            docs[settlement] = []
            counts[settlement] = 0
        if counts[settlement] >= 5:
            continue
        # Canadiana URL: strip year suffix from id, e.g. sru.00001_1929_1930 → sru.00001
        base_id = re.sub(r'_\d{4}.*$', '', cid)
        url = f"https://www.canadiana.ca/view/{base_id}"
        docs[settlement].append({"title": title, "source": "Canadiana", "url": url})
        counts[settlement] += 1
    return docs

def load_ia_docs():
    """Return {settlement_name: [{title, url, creator, date}]} top 5 per settlement."""
    db_path = BASE_DIR / "internetarchive_rankings.db"
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT ds.settlement_name, d.identifier, d.title, d.creator, d.date, ds.weight
        FROM document_settlements ds
        JOIN documents d ON ds.identifier = d.identifier
        ORDER BY ds.settlement_name, ds.weight DESC
    """)
    rows = cur.fetchall()
    conn.close()

    docs = {}
    counts = {}
    for settlement, identifier, title, creator, date, weight in rows:
        if settlement not in docs:
            docs[settlement] = []
            counts[settlement] = 0
        if counts[settlement] >= 5:
            continue
        year = date[:4] if isinstance(date, str) and len(date) >= 4 else None
        docs[settlement].append({
            "title": title,
            "source": "Internet Archive",
            "url": f"https://archive.org/details/{identifier}",
            "creator": creator,
            "year": year,
        })
        counts[settlement] += 1
    return docs

# ── build XLSX event rows ─────────────────────────────────────────────────────

XLSX_EVENT_FIELDS = [
    ("Founded",               "Founded"),
    ("Incorporated",          "Incorporated"),
    ("Railway_arrives",       "Railway Arrives"),
    ("First_post_office",     "First Post Office"),
    ("First_church",          "First Church"),
    ("First_school",          "First School"),
    ("First_cemetery",        "First Cemetery"),
    ("First_newspaper",       "First Newspaper"),
    ("Medical",               "Medical Facility"),
    ("Justice_system",        "Justice System"),
    ("Colonization_companies","Colonization Company"),
    ("Land_office_established","Land Office"),
]

def extract_xlsx_events(row):
    """Return sorted list of {year, event} from the master XLSX row."""
    events = []
    for col, label in XLSX_EVENT_FIELDS:
        y = safe_year(row.get(col))
        if y is not None:
            events.append({"year": y, "event": label})
    events.sort(key=lambda e: e["year"])
    return events

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading coordinates...")
    coords = load_coords()
    print(f"  {len(coords)} settlements with coordinates")

    print("Loading timelines...")
    timelines = load_timelines()
    print(f"  {len(timelines)} settlements with timeline events")

    print("Loading connections...")
    connections = load_connections()
    print(f"  {len(connections)} settlements with connections")

    print("Loading Canadiana documents...")
    canadiana = load_canadiana_docs()
    print(f"  {len(canadiana)} settlements with Canadiana docs")

    print("Loading Internet Archive documents...")
    ia_docs = load_ia_docs()
    print(f"  {len(ia_docs)} settlements with IA docs")

    print("Loading master XLSX...")
    df = pd.read_excel(BASE_DIR / "JJack_Urban_Sask_Knowledge_Graph_Feb_2026.xlsx")
    print(f"  {len(df)} settlement rows")

    settlements = {}
    missing_coords = []

    for _, row in df.iterrows():
        name = str(row["PR_CD_CSD"]).strip()
        if not name:
            continue

        # Coordinates
        if name in coords:
            lat, lon = coords[name]
        else:
            # Try partial match (some names may differ slightly)
            match = next((k for k in coords if k.startswith(name) or name.startswith(k)), None)
            if match:
                lat, lon = coords[match]
            else:
                missing_coords.append(name)
                lat, lon = None, None

        railways = classify_railway(row.get("Railway_lines"))

        # Merge XLSX events with timeline CSV events (deduplicate by year+event)
        xlsx_events = extract_xlsx_events(row)
        csv_events = timelines.get(name, [])
        seen = set()
        merged_events = []
        for e in xlsx_events + csv_events:
            key = (e["year"], e["event"])
            if key not in seen:
                seen.add(key)
                merged_events.append(e)
        merged_events.sort(key=lambda e: e["year"])

        # Documents: merge Canadiana + IA
        docs = canadiana.get(name, []) + ia_docs.get(name, [])

        # Context fields (rich text from XLSX)
        context = {}
        for col, label in [
            ("Founded_context", "Founded"),
            ("Incorporated_context", "Incorporated"),
            ("Railway_lines", "Railway Lines"),
            ("Post_office_context", "Post Office"),
            ("First_church_context", "First Church"),
            ("First_school_context", "First School"),
            ("Cemeteries_context", "Cemeteries"),
            ("Newspapers", "Newspapers"),
            ("Medical_context", "Medical"),
            ("Justice_system_context", "Justice System"),
            ("Colonization_companies_context", "Colonization Companies"),
            ("Residential_school", "Residential School"),
            ("Digital_local_history_source", "Local History Source"),
        ]:
            v = nonempty(str(row.get(col, "")))
            if v and v != "nan":
                context[label] = v

        csd_type_raw = str(row.get("CSD_TYPE", "")).strip()
        type_labels = {"T": "Town", "C": "City", "VL": "Village", "TV": "Town-Village"}
        csd_label = type_labels.get(csd_type_raw, csd_type_raw)

        settlements[name] = {
            "name": name,
            "type": csd_type_raw,
            "typeLabel": csd_label,
            "population": safe_int(row.get("POP_TOT_1921")),
            "lat": lat,
            "lon": lon,
            "censusId": str(row.get("V1T27_1921", "")).strip(),
            "railways": railways,
            "primaryRailway": primary_railway(railways),
            "events": merged_events,
            "connections": connections.get(name, {
                "Railway_Company": [],
                "Railway_Corridor": [],
                "Proximity": [],
                "Institutional_Timing": [],
            }),
            "context": context,
            "documents": docs,
        }

    print(f"\nBuilt {len(settlements)} settlement entries")
    if missing_coords:
        print(f"WARNING: {len(missing_coords)} settlements missing coordinates: {missing_coords[:10]}")

    out_path = Path(__file__).parent / "settlements.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(settlements, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = out_path.stat().st_size / 1024
    print(f"\nWrote {out_path} ({size_kb:.0f} KB, {len(settlements)} settlements)")

if __name__ == "__main__":
    main()
