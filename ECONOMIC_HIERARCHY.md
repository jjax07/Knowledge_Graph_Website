# Economic Hierarchy Map — Documentation

Interactive map visualizing the commercial service tier of all 429 incorporated Saskatchewan municipalities in 1921, overlaid with the provincial railway network.

---

## What It Shows

Each settlement is represented as a dot coloured by its **commercial tier** — a classification derived from population, banking, and professional-service criteria. The tier hierarchy reflects the functional division of labour identified in Finding 21 of the thesis.

Dot size is proportional to population (1921 census).

### Tier Colours (heat-map gradient: hot = highest tier)

| Colour | Tier | Count | Criteria |
|--------|------|-------|----------|
| Red `#ef5350` | City | 7 | Pop. ≥400 + bank + legal services |
| Orange `#ffa726` | Regional Service Centre (RSC) | 39 | Pop. ≥400 + bank + medical or legal services |
| Yellow `#ffee58` | Local Service Centre (LSC) | 27 | Pop. ≥400 + bank |
| Green `#81c784` | Small Service Centre (SSC) | 356 | All remaining settlements |

### Railway Lines

Track geometry drawn from `railway_tracks.json` (sourced from `HR_rails_NEW.shp` + the National Railway Network). Only lines built by 1921 are shown (`built_year ≤ 1921`). Lines from builders not attributable to CPR, CNR, or GTP are omitted. Tracks with no coordinates inside a generous Saskatchewan bounding box are skipped.

| Colour | Company |
|--------|---------|
| Red | Canadian Pacific Railway (CPR) |
| Blue | Canadian Northern Railway (CNoR / CNR) |
| Green | Grand Trunk Pacific Railway (GTPR / GTP) |

---

## Clicking a Settlement

Selecting a settlement opens a detail panel showing:

- **Tier badge** and full commercial type label
- **Population** (1921)
- **Railway** company pills
- **Top 5 industries** — the five industries accounting for the largest share of that settlement's classified workforce (1921 census, same filters as Phase 2 occupation analysis)
- **About this tier** — a brief description of what the tier means economically
- **Link** to the settlement's full profile in `settlement_profiles.html`

### Industry Display Names

Several census industry labels are translated for a modern audience in the JavaScript `INDUSTRY_DISPLAY` map (no data is altered):

| Census label | Display label |
|---|---|
| Private households | Domestic service (private households) |
| Not specified retail trade | Retail trade (unspecified) |
| Not specified manufacturing industries | Manufacturing (unspecified) |
| Electrical goods, hardware, and plumbing equipment | Hardware & electrical goods |
| Railroads and railway express service | Railroads & railway express |
| Local public administration | Local government |
| Misc. personal services | Personal services |
| … | … |

---

## Overview Panel (no settlement selected)

Before any settlement is clicked, the sidebar shows:

- **Provincial overview** — settlement counts per tier (7 / 39 / 27 / 356)
- **Tier definitions** — description of each tier's economic character, followed by its top 7 industries by share of the tier's total classified workforce (computed from the 1921 census via Neo4j)

---

## Files

| File | Description |
|------|-------------|
| `economic_hierarchy.html` | The visualization page |
| `tier_settlements.json` | Pre-built data for all 429 settlements (tier, coordinates, population, railways, top industries) |
| `industry_data.json` | Industry breakdowns: `bySettlement` (top 5 per settlement) and `byTier` (top 7 per tier) |
| `railway_tracks.json` | Track geometry copied from `Sask_Railway_Visualizations/data/` |
| `settlement_connections.json` | Settlement-to-settlement railway connections (copied from `Sask_Railway_Visualizations/data/`, not currently used for rendering) |
| `build_tier_data.py` | Regenerates `tier_settlements.json` from source data |
| `build_industry_data.py` | Regenerates `industry_data.json` via Neo4j query |

---

## Regenerating the Data

Run both scripts from the `KnowledgeGraph/` parent directory. `build_industry_data.py` requires a running Neo4j instance.

```bash
# Step 1 — rebuild industry data (requires Neo4j)
python3 website/build_industry_data.py

# Step 2 — rebuild tier_settlements.json
python3 website/build_tier_data.py
```

### Sources consumed by `build_tier_data.py`

| Source | Field(s) used |
|--------|--------------|
| `analysis/tier_structural_correlates.xlsx` — Sheet: Settlement Roster | Commercial Type, Tier |
| `website/settlements.json` | lat, lon, population, railways, primaryRailway |
| `website/industry_data.json` | bySettlement (top 5 industries per settlement) |

### Sources consumed by `build_industry_data.py`

| Source | Field(s) used |
|--------|--------------|
| Neo4j — Person nodes | `industry`, `occupation` |
| Neo4j — Settlement nodes | `census_name` |
| Neo4j — SettlementType nodes | `name` (commercial tier) |

**Filters applied** (same as Phase 2 occupation analysis):
- Exclude `industry` starting with `Ambiguous` or `Non-`, or equal to `Unclassifiable industry`
- Exclude `occupation` starting with `Ambiguous` or `Non-`
- Exclude artifact industries (OFFICE, CLERK, RETIRED, etc. — full list in script)
- Exclude students/pupils from Educational services
- Minimum 2 workers per industry per settlement (suppresses noise in tiny settlements)

---

## Design Decisions

**Why a heat-map colour gradient?**
Red → orange → yellow → green maps directly onto the hierarchy from most to least economically complex, making the spatial distribution of tier levels immediately legible at province scale.

**Why top 5 industries rather than a fixed threshold?**
A fixed 10% threshold (used in the Phase 2 Local Concentration sheet) leaves Cities nearly empty — Saskatoon's diversified workforce spreads across dozens of industries, none of which dominates. Top-N ensures every settlement shows a meaningful snapshot regardless of size.

**Why straight-line track geometry rather than routed paths?**
The `railway_tracks.json` geometry is drawn from historical shapefiles and extends beyond the provincial boundary in places. Straight lines between settlements were considered as a fallback but rejected because they misrepresent the actual network. The current implementation uses the shapefile geometry with a loose bounding-box filter to exclude tracks with no Saskatchewan coordinates.

---

## Thesis Findings Reflected

| Finding | What the map shows |
|---------|-------------------|
| F21 | Industry specialization by tier: Cities diversified across coordination functions; SSCs dominated by Own Farm |
| F22 | Tier is primarily a temporal ordering — Cities founded ~1888, SSCs ~1906 |
| F26 | Organizational hierarchy: Cities = wage employment; SSCs = own-account operators |
| F1/F2 | Railway degree does not predict tier — RSCs are not network hubs |
