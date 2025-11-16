# Quick Start: Real Clean Gen Scores

## Installation

```bash
cd kazuma/
source venv/bin/activate  # Python 3.12 only!
pip install geopy==2.4.1
```

## Start Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Watch startup logs** for:
```
Loading energy sources from JSON...
Successfully loaded 9 energy sources
Generating grid nodes with real clean gen scores...
  Pacific Northwest Node A: 82.0 → 45.3 (delta: -36.7)
  ...
Generated 40 grid nodes with real scores
```

## Test Endpoints

```bash
# Check status
curl http://localhost:8000/health

# View energy sources
curl http://localhost:8000/api/energy-sources/stats

# Get all grid nodes (now with real clean_gen scores)
curl http://localhost:8000/api/grid/nodes | jq

# Find sources near a specific node
curl "http://localhost:8000/api/grid/nodes/27/nearby-sources?limit=3" | jq

# Reload data without restarting
curl -X POST http://localhost:8000/api/energy-sources/reload
```

## Key Files

| File | Purpose |
|------|---------|
| `data/rwe_projects_clean.json` | Input: 9 renewable energy projects |
| `data/cache/geocode_cache.pkl` | Auto-generated: Geocoding cache |
| `energy_sources.py` | Loads & geocodes energy sources |
| `scoring_utils.py` | Distance & scoring algorithms |
| `grid_data.py` | Calculates real clean_gen scores |
| `main.py` | API with energy source endpoints |

## Scoring Logic

```
For each grid node:
  1. Find all energy sources within 300km
  2. For each source:
     - Calculate distance (Pythagorean: sqrt((Δlat×111)² + (Δlon×111×cos(lat))²))
     - Apply proximity decay (closer = more credit)
     - Weight by capacity (MW)
     - Multiply by clean factor (solar/wind=1.0)
  3. Sum all contributions
  4. Normalize to 0-100 scale
```

**Proximity Decay**:
- < 50km: 100% credit
- 50-100km: 70% credit
- 100-200km: 40% credit
- 200-300km: 20% credit
- \> 300km: 0% credit

## Expected Results

**Nodes with HIGH scores** (near RWE projects):
- Virginia nodes (VA solar projects)
- Texas nodes (Waterloo Solar)
- Louisiana nodes (Lafitte Solar)

**Nodes with LOW scores** (no nearby projects):
- Pacific Northwest (no RWE projects there)
- California (no RWE projects there)
- Most other states

This reflects **reality**: clean_gen score = proximity to actual renewables!

## Troubleshooting

**Problem**: No energy sources loaded  
**Solution**: Check `ls kazuma/data/rwe_projects_clean.json`

**Problem**: Geocoding timeout  
**Solution**: Wait (Nominatim rate limit) or delete cache: `rm data/cache/geocode_cache.pkl`

**Problem**: Import errors  
**Solution**: `pip install -r requirements.txt` (ensure Python 3.12)

## Add More Energy Sources

1. Add projects to `data/rwe_projects_clean.json`:
```json
{
  "name": "New Solar Farm",
  "energy_source": "Solar",
  "ppa_capacity_mw": 100,
  "address": "123 Main St, City, State"
}
```

2. Reload: `curl -X POST http://localhost:8000/api/energy-sources/reload`

3. Check updated scores: `curl http://localhost:8000/api/grid/nodes`

## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check status + energy source count |
| `/api/energy-sources` | GET | List all sources (filter by type/capacity) |
| `/api/energy-sources/geojson` | GET | GeoJSON for map viz |
| `/api/energy-sources/stats` | GET | Summary statistics |
| `/api/energy-sources/reload` | POST | Reload & recalculate |
| `/api/grid/nodes` | GET | Grid nodes with real scores |
| `/api/grid/nodes/{id}/nearby-sources` | GET | Find sources near node |

Done! 🚀
