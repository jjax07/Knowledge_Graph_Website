# Saskatchewan Urban Settlements, 1921

An interactive historical atlas of 429 incorporated municipalities in Saskatchewan, documenting the infrastructure of settler colonialism from the 1870s to the 1920s.

Part of the **[Mapping Settler Colonialism in Saskatchewan](https://storymaps.arcgis.com/stories/8288eb9615484e708922e81411e63936)** project — University of Saskatchewan History Department.

---

## Live Site

Deployed via GitHub Pages: [https://jjax07.github.io/Knowledge_Graph_Website/](https://jjax07.github.io/Knowledge_Graph_Website/)

---

## What It Shows

Each of the 429 settlements profiled in the 1921 federal census is represented as a clickable dot on an interactive map. Selecting a settlement opens a detail panel with:

- **Timeline** — dated events: founding, incorporation, railway arrival, first post office, first church, first school, first cemetery, first newspaper, medical facility, justice system, residential school, colonization company, land office
- **Railway connections** — which other settlements share the same railway company, with lines drawn on the map
- **Nearby settlements** — geographic proximity connections
- **Historical sources** — links to related documents from Canadiana and the Internet Archive
- **Context notes** — qualitative notes from archival research on railway lines, newspapers, residential schools, and local history sources

Dot colour indicates the primary railway company that served the settlement:

| Colour | Company |
|--------|---------|
| Red | Canadian Pacific Railway (CPR) |
| Blue | Canadian Northern Railway (CNoR / CNR) |
| Green | Grand Trunk Pacific Railway (GTPR / GTP) |
| Grey | Other (QLL&S, M&NW, minor lines) |

---

## Files

| File | Description |
|------|-------------|
| `index.html` | Landing page with project summary |
| `settlement_profiles.html` | Main interactive map — settlements coloured by railway company |
| `economic_hierarchy.html` | Economic hierarchy map — settlements coloured by commercial tier |
| `settlements.json` | Pre-processed data for all 429 settlements |
| `tier_settlements.json` | Tier + industry data for the economic hierarchy map |
| `industry_data.json` | Top industries by settlement and by tier (from Neo4j) |
| `railway_tracks.json` | Railway track geometry (from `Sask_Railway_Visualizations`) |
| `build_data.py` | Regenerates `settlements.json` |
| `build_tier_data.py` | Regenerates `tier_settlements.json` |
| `build_industry_data.py` | Regenerates `industry_data.json` via Neo4j |
| `ECONOMIC_HIERARCHY.md` | Full documentation for the economic hierarchy map |

---

## Data Sources

| Source | Contents |
|--------|---------|
| `JJack_Urban_Sask_Knowledge_Graph_Feb_2026.xlsx` | Master settlement data — 33 columns, 429 rows (Jessica Jack) |
| `settlement_coordinates.csv` | WGS84 lat/lon for each settlement |
| `settlement_timelines.csv` | 12 event types with years, 425 settlements |
| `settlement_connections.csv` | 48,870 connection edges (Railway_Company, Railway_Corridor, Proximity, Institutional_Timing) |
| `canadiana_rankings.db` | SQLite — document rankings from Canadiana.org searches |
| `internetarchive_rankings.db` | SQLite — document rankings from Internet Archive searches |

Source data lives in the parent [KnowledgeGraph](https://gitlab.com/jjack07/knowledge_graph_website) repository and is not committed here.

---

## Regenerating the Data

The `settlements.json` file is pre-built and committed to the repo. If the source XLSX or CSVs change, regenerate it by running from the `KnowledgeGraph/` parent directory:

```bash
python3 website/build_data.py
```

Requires: `pandas`, `openpyxl`

```bash
pip install pandas openpyxl
```

---

## Technology

- [Leaflet.js](https://leafletjs.com/) — interactive map
- [CartoDB Dark Matter](https://carto.com/basemaps/) — map tiles
- Vanilla HTML/CSS/JavaScript — no build step required
- Hosted on GitHub Pages (static site)

---

## Related Projects

- [Saskatchewan Railway Visualizations](https://jjax07.github.io/Sask_Railway_Visualizations/) — interactive visualizations of the railway network that connected these settlements
