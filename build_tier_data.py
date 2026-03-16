#!/usr/bin/env python3
"""
build_tier_data.py
Generates tier_settlements.json for the economic hierarchy map.
Run from the KnowledgeGraph/ directory:
    python website/build_tier_data.py

Sources:
  - website/settlements.json                      (coordinates, population, railways)
  - analysis/tier_structural_correlates.xlsx       (commercial tier)
  - website/industry_data.json                     (top 5 industries per settlement, from Neo4j)
"""

import json
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent

def normalize_name(raw):
    """'Alameda, T-V' → 'Alameda'"""
    return re.sub(r",\s*(T-V|T|C|VL|RM|SV|SC|IRI).*$", "", str(raw)).strip()

def main():
    print("Loading commercial tiers from xlsx...")
    tier_df = pd.read_excel(
        BASE_DIR / "analysis" / "tier_structural_correlates.xlsx",
        sheet_name="Settlement Roster",
        usecols=["Settlement", "Commercial Type", "Tier"],
    )
    tiers = {}
    for _, row in tier_df.iterrows():
        plain = normalize_name(row["Settlement"])
        tiers[plain] = {
            "tier": str(row["Tier"]).strip(),
            "commercialType": str(row["Commercial Type"]).strip(),
        }
    print(f"  {len(tiers)} tier records")

    print("Loading top industries from industry_data.json...")
    with open(BASE_DIR / "website" / "industry_data.json", encoding="utf-8") as f:
        raw_industries = json.load(f)
    # Normalize census names ("Saskatoon, C") to plain names ("Saskatoon")
    local_industries = {normalize_name(k): v for k, v in raw_industries["bySettlement"].items()}
    print(f"  {len(local_industries)} settlements with industry data")

    print("Loading settlements.json...")
    with open(BASE_DIR / "website" / "settlements.json", encoding="utf-8") as f:
        settlements = json.load(f)
    print(f"  {len(settlements)} settlement records")

    out = {}
    missing_tier = []

    for name, s in settlements.items():
        tier_info = tiers.get(name)
        if tier_info is None:
            missing_tier.append(name)
            tier_info = {"tier": "SSC", "commercialType": "Small Service Centre"}

        out[name] = {
            "name": name,
            "lat": s.get("lat"),
            "lon": s.get("lon"),
            "population": s.get("population"),
            "railways": s.get("railways", []),
            "primaryRailway": s.get("primaryRailway", "Other"),
            "tier": tier_info["tier"],
            "commercialType": tier_info["commercialType"],
            "localIndustries": local_industries.get(name, []),
        }

    print(f"\nBuilt {len(out)} entries")
    if missing_tier:
        print(f"WARNING: {len(missing_tier)} settlements had no tier match (defaulted to SSC): {missing_tier}")

    out_path = BASE_DIR / "website" / "tier_settlements.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} ({size_kb:.0f} KB)")

if __name__ == "__main__":
    main()
