#!/usr/bin/env python3
"""
build_industry_data.py
Generates industry_data.json — top 5 industries by % of classified workforce
for each settlement, used by the economic hierarchy map.

Run from the KnowledgeGraph/ directory:
    python website/build_industry_data.py

Filters (same as Phase 2):
  - Exclude industry STARTS WITH 'Ambiguous' or 'Non-', or = 'Unclassifiable industry'
  - Exclude occupation STARTS WITH 'Ambiguous' or 'Non-'
  - Exclude artifact industries
  - Educational services: exclude students/pupils
"""

import json
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "11069173"
TOP_N          = 5
MIN_WORKERS    = 2   # ignore industries with fewer than this many workers in a settlement

ARTIFACT_INDUSTRIES = {
    "OFFICE", "CONTRACTOR", "ODD JOBS/JOBBER", "CLERK", "MERCHANT/DEALER",
    "DRIVER", "EMPLOYEE/WORKER", "PROPRIETOR/LANDLORD/OWNER",
    "Common or General Laborer", "At Home (not housework)",
    "Lady/Man of Leisure", "Retired", "Housework at home",
    "School response (students, etc.)", "NAME OF A PLACE/TOWN",
    "STREET/AVENUE", "LINK WITH MUSIC", "WATER RELATED", "TRAVELLER",
    "War Services", "with family member", "IN TRAINING/APPRENTICE",
    "JOURNEYMAN", "NOT EMPLOYED/WORKING", "War Products",
}

BASE_DIR = Path(__file__).parent.parent

print("Querying Neo4j...")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

rows = []
with driver.session() as s:
    result = s.run("""
        MATCH (p:Person)-[:ENUMERATED_IN]->(s:Settlement)
        WHERE p.industry IS NOT NULL
          AND p.occupation IS NOT NULL
          AND NOT p.industry STARTS WITH 'Ambiguous'
          AND NOT p.industry STARTS WITH 'Non-'
          AND NOT p.industry = 'Unclassifiable industry'
          AND NOT p.occupation STARTS WITH 'Ambiguous'
          AND NOT p.occupation STARTS WITH 'Non-'
        OPTIONAL MATCH (s)-[:IS_TYPE]->(ct:SettlementType)
        RETURN s.census_name AS settlement,
               ct.name       AS tier,
               p.industry    AS industry,
               p.occupation  AS occupation
    """)
    for r in result:
        rows.append(dict(r))

driver.close()
print(f"  {len(rows):,} person-records loaded")

df = pd.DataFrame(rows)

# Exclude artifact industries
df = df[~df["industry"].isin(ARTIFACT_INDUSTRIES)].copy()

# Exclude students from Educational services
import re
student_pattern = re.compile(r"student|pupil|school response", re.IGNORECASE)
edu_mask = (df["industry"] == "Educational services") & \
           df["occupation"].str.contains(student_pattern, na=False)
df = df[~edu_mask].copy()

print(f"  {len(df):,} records after filtering")

# Compute per-settlement industry counts
counts = df.groupby(["settlement", "industry"]).size().reset_index(name="n")
totals = df.groupby("settlement").size().reset_index(name="total")
counts = counts.merge(totals, on="settlement")
counts["pct"] = (counts["n"] / counts["total"] * 100).round(1)

# Filter minimum workers and take top N per settlement
counts = counts[counts["n"] >= MIN_WORKERS]
counts = counts.sort_values(["settlement", "pct"], ascending=[True, False])
top = counts.groupby("settlement").head(TOP_N)

# Build output dict: settlement name → list of {industry, pct}
out = {}
for settlement, grp in top.groupby("settlement"):
    out[settlement] = [
        {"industry": row["industry"], "pct": row["pct"]}
        for _, row in grp.iterrows()
    ]

print(f"  {len(out)} settlements with industry data")

# ── Tier-level aggregates ─────────────────────────────────────────────────────
TIER_MAP = {
    "City":                    "City",
    "Regional Service Centre": "RSC",
    "Local Service Centre":    "LSC",
    "Small Service Centre":    "SSC",
}
TOP_N_TIER = 7

df["tier_abbr"] = df["tier"].map(TIER_MAP)
tier_counts  = df.groupby(["tier_abbr", "industry"]).size().reset_index(name="n")
tier_totals  = df.groupby("tier_abbr").size().reset_index(name="total")
tier_counts  = tier_counts.merge(tier_totals, on="tier_abbr")
tier_counts["pct"] = (tier_counts["n"] / tier_counts["total"] * 100).round(1)
tier_counts  = tier_counts.sort_values(["tier_abbr", "pct"], ascending=[True, False])
tier_top     = tier_counts.groupby("tier_abbr").head(TOP_N_TIER)

tier_industries = {}
for tier, grp in tier_top.groupby("tier_abbr"):
    tier_industries[tier] = [
        {"industry": row["industry"], "pct": row["pct"]}
        for _, row in grp.iterrows()
    ]
print(f"  Tier aggregates computed for: {list(tier_industries.keys())}")

# ── Write output ──────────────────────────────────────────────────────────────
output = {"bySettlement": out, "byTier": tier_industries}

out_path = BASE_DIR / "website" / "industry_data.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

size_kb = out_path.stat().st_size / 1024
print(f"Wrote {out_path} ({size_kb:.0f} KB)")
