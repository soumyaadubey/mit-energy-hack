# Smart Grid Siting Framework

Intelligent siting framework for optimal placement of large electro-intensive loads (data centers, electrolyzers, EV/hydrogen hubs). Evaluates 40 US grid nodes using weighted scoring across three criteria: clean generation proximity, transmission headroom, and grid reliability.

**Stack**: Python 3.12 + FastAPI + Pydantic | Vanilla JS + Mapbox GL + Chart.js | Tailwind CSS  
**Working Directory**: All development in `kazuma/` subdirectory  
**Data Source**: 10,000+ US power plants from EPA eGRID 2023 + 9 RWE renewable projects

---

## Architecture Patterns

### Backend Data Flow (5 Layers)
**`egrid2023_plants_lat_lng_fuel_power.json`** (root) → **`power_plants_data.py`** + **`energy_sources.py`** → **`scoring_utils.py`** → **`grid_data.py`** → **`siting_engine.py`** → **`main.py`**

1. **External Data** (root `egrid2023_plants_lat_lng_fuel_power.json`): 10,000+ US power plants with coordinates, fuel type, capacity. **Path is relative from `kazuma/`: `"../egrid2023_plants_lat_lng_fuel_power.json"`**
2. **Data Loaders** (`power_plants_data.py`, `energy_sources.py`): Load JSON, parse with Pydantic, geocode addresses (cached in `data/cache/`). Global caching via `_cached_plants`
3. **Scoring Layer** (`scoring_utils.py`): Distance calculations (Pythagorean), proximity decay functions, voltage-aware transmission scoring, capacity adequacy factors
4. **Grid Generation** (`grid_data.py`): Generates 40 `GridNode` objects with **real scores** calculated from power plant proximity. Startup caching: `grid_nodes = generate_grid_nodes_with_real_scores()`
5. **Engine Layer** (`siting_engine.py`): `SitingEngine` class with weighted composite scoring. Uses `math.isclose(sum, 1.0, rel_tol=1e-9)` to validate weights (never `==` for floats)
6. **API Layer** (`main.py`): FastAPI endpoints serve GeoJSON, evaluate sites, rank alternatives. In-memory scenario storage (no database)

### Pydantic Model Hierarchy
```python
PowerPlant (10,000+ from eGRID, global cache)
  └─ is_clean() -> bool  # Only WND, SUN, WAT, GEO = True

EnergySource (9 from RWE, geocoded)
  └─ coordinates (geocoded, cached in data/cache/geocode_cache.pkl)

GridNode (40 instances, real scores)
  ├─ coordinates: GridNodeCoordinates
  ├─ clean_gen: float (calculated from power_plants proximity)
  ├─ transmission_headroom: float (calculated from ALL plants, voltage-aware)
  ├─ reliability: float (still mock)
  ├─ nearby_projects: List[NearbyProject]
  └─ transmission_lines: List[TransmissionLine]

SitingRequest → converted to SitingWeights + DemandProfile
  └─ SiteEvaluation (output)
       └─ score_breakdown: ScoreBreakdown
```

**Critical Pattern**: Models have `.validate_sum()` methods (e.g., `SitingWeights`) that raise `ValueError` if weights don't sum to 1.0. Always call before calculating scores.

**Critical Data Flow**: At startup (`@app.on_event("startup")` in `main.py`):
1. Load 10,000+ power plants from `../egrid2023_plants_lat_lng_fuel_power.json` → cached in `_cached_plants`
2. Load 9 RWE energy sources from `data/rwe_projects_clean.json` → geocode (cached)
3. Generate 40 grid nodes with **real scores** from proximity calculations
4. Changes to JSON data require server restart to reload

---

## Development Workflow

### Environment Setup
```bash
cd kazuma/
python3.12 -m venv venv && source venv/bin/activate  # MUST use 3.12 (Pydantic 2.5.0 breaks on 3.13)
pip install -r requirements.txt
npm install && npm run build:css
```

**Never use Python 3.13** – Pydantic 2.5.0 has build failures. Enforced in `requirements.txt` comment.

### Running the App
```bash
# Primary method (hot reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# CSS development (parallel terminal)
npm run watch:css
```

**No test suite exists**. When adding: use `pytest` with `httpx.AsyncClient` per `AGENTS.md` guidance.

**Critical Dependencies**:
- `geopy==2.4.1` for geocoding (Nominatim, rate-limited to 1 req/sec)
- Geocoding cache: `data/cache/geocode_cache.pkl` (pickle format, persists across restarts)
- Delete cache to retry failed geocodes: `rm kazuma/data/cache/geocode_cache.pkl`

### Tailwind Workflow
1. Edit `static/input.css` (only `@tailwind` directives)
2. Run `npm run build:css` → generates `static/output.css` (gitignored)
3. HTML uses utility classes: `class="bg-blue-500 hover:bg-blue-600"`

**Never commit `static/output.css`** – regenerated on each build.

---

## Core Business Logic

### Real Scoring Architecture (Replaces Mock Data)

**Clean Gen Score** (0-100): Calculated from proximity to **clean power plants only** (WND, SUN, WAT, GEO from eGRID)
- Distance decay: <50km=100%, 50-100km=70%, 100-200km=40%, 200-300km=20%, >300km=0%
- Capacity weighting: Larger plants contribute more
- **Demand adequacy**: If `demand_mw` provided, adjusts score based on capacity ratio:
  - ≥3x demand: 1.20x bonus (excellent surplus)
  - 2-3x: 1.10x bonus (good resilience)
  - 1.5-2x: 1.0x (adequate)
  - 1-1.5x: 0.95x (tight)
  - 0.7-1x: 0.85x (moderate shortfall)
  - <0.5x: 0.50x (severe shortfall)
- Normalization: 90th percentile of all node scores → 100

**Transmission Score** (0-100): Calculated from **ALL power plants** (not just clean)
- Why: Large fossil plants often have best transmission (500-765kV lines)
- **Voltage-aware decay** based on plant size:
  - Large (≥500 MW): gentle decay to 300km (500-765kV lines)
  - Medium (100-500 MW): moderate decay to 150km (230-345kV lines)
  - Small (<100 MW): steep decay to 50km (115-230kV lines)
- Function: `transmission_decay_factor(distance_km, plant_capacity_mw)`
- Normalization: 90th percentile → 100

**Reliability Score** (0-100): Still mock (future: grid stability data)

### Scoring Formula (Critical Implementation)
```python
def calculate_composite_score(node: GridNode, weights: SitingWeights) -> ScoreBreakdown:
    weights.validate_sum()  # Raises ValueError if sum ≠ 1.0
    
    composite = (node.clean_gen * weights.weight_clean +
                 node.transmission_headroom * weights.weight_transmission +
                 node.reliability * weights.weight_reliability)
    
    return ScoreBreakdown(composite_score=round(composite, 1), ...)
```

**Default weights**: `0.4 / 0.3 / 0.3` (clean/transmission/reliability)

**Key Functions in `scoring_utils.py`**:
```python
pythagorean_distance(lat1, lon1, lat2, lon2) -> float
  # Fast approximation: 1° lat ≈ 111km, 1° lon ≈ 111km × cos(lat)
  # Accurate for <1000km distances

proximity_decay_factor(distance_km) -> float
  # Returns 0.0-1.0 based on stepped decay (50/100/200/300km thresholds)

transmission_decay_factor(distance_km, plant_capacity_mw) -> float
  # Voltage-aware: Large plants useful to 300km, small to 50km

calculate_capacity_adequacy_factor(available_mw, demand_mw) -> float
  # Returns 0.5-1.2x multiplier based on capacity/demand ratio

calculate_clean_gen_score(..., demand_mw: Optional[float] = None) -> float
  # Main scoring function with demand-aware adjustment

calculate_transmission_score(lat, lon, power_plants, norm_factor) -> float
  # Uses ALL plants (not just clean) for transmission infrastructure
```

### Float Comparison Pattern
```python
# WRONG - float rounding errors
if weight_sum == 1.0:

# CORRECT - always use math.isclose()
import math
if math.isclose(weight_sum, 1.0, rel_tol=1e-9):
```

**Why**: `0.4 + 0.3 + 0.3 == 0.9999999999...` in IEEE 754 arithmetic.

### Real Data Pattern (Replaces Mock)
`grid_data.py` calculates scores from EPA data:
```python
def generate_grid_nodes_with_real_scores(
    energy_sources: Optional[List] = None,
    power_plants: Optional[List] = None
) -> List[GridNode]:
    # Generate 40 nodes with coordinates
    nodes = generate_base_nodes()
    
    # Calculate real clean_gen scores (only clean plants: WND, SUN, WAT, GEO)
    nodes = calculate_real_clean_gen_scores(nodes, power_plants)
    
    # Calculate real transmission scores (ALL plants, voltage-aware)
    nodes = calculate_real_transmission_scores(nodes, power_plants)
    
    return nodes
```

Cached at startup in `main.py`: `grid_nodes = generate_grid_nodes_with_real_scores(energy_sources, power_plants)`. Changes to JSON data require server restart.

**Critical Paths**:
- Power plants JSON: `kazuma/../egrid2023_plants_lat_lng_fuel_power.json` (10,000+ plants)
- Energy sources JSON: `kazuma/data/rwe_projects_clean.json` (9 projects)
- Geocoding cache: `kazuma/data/cache/geocode_cache.pkl` (auto-generated)

---

## API Patterns

### Standard Response Structure
```python
# List endpoints - include metadata
return {"nodes": [...], "total": len(nodes), "filters_applied": {...}}

# Evaluation endpoints - return Pydantic models
return SiteEvaluation(...)  # FastAPI auto-serializes
```

### Error Handling
```python
try:
    node = get_node_by_id(site_id)
except ValueError:
    raise HTTPException(status_code=404, detail=f"Node {site_id} not found")
```

Use `HTTPException` (FastAPI), not plain `raise`. Log with `logger.info()` before returning.

---

## Code Conventions

### Type Hints (Strictly Enforced)
```python
async def evaluate_site(request: SitingRequest) -> SiteEvaluation:
    # Pydantic handles runtime validation
```

**Never omit** return types or parameter types in API/engine code.

### Pydantic Validators
```python
class SitingWeights(BaseModel):
    weight_clean: float = Field(0.4, ge=0, le=1)
    
    @field_validator('weight_clean')
    @classmethod
    def validate_weight_range(cls, v: float) -> float:
        if not (0 <= v <= 1):
            raise ValueError("Weight must be 0-1")
        return v
```

Use `@field_validator` for per-field checks, instance methods for cross-field validation.

### GeoJSON Conversion
```python
def to_geojson_feature(self) -> Dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [self.coordinates.longitude, self.coordinates.latitude]
        }
    }
```

**Coordinate order**: `[lon, lat]` (GeoJSON spec), not `[lat, lon]`.

---

## Frontend Integration

### Mapbox Pattern
```javascript
// Fetch config first
const config = await fetch('/api/config').then(r => r.json());
mapboxgl.accessToken = config.mapbox_token;

// Load GeoJSON
const data = await fetch('/api/grid/nodes/geojson').then(r => r.json());
map.addSource('grid-nodes', { type: 'geojson', data });
```

### Weight Slider Validation
```javascript
const sum = clean + trans + rel;
if (Math.abs(sum - 1.0) > 0.001) {
    showError('Weights must sum to 1.0');
}
```

Mirror backend validation in frontend for immediate feedback.

### Chart.js Radar
```javascript
new Chart(ctx, {
    type: 'radar',
    data: {
        labels: ['Clean Gen', 'Transmission', 'Reliability'],
        datasets: [{ data: [clean_gen, transmission, reliability] }]
    }
});
```

---

## Common Issues

**"Weights must sum to 1.0" with 0.4 + 0.3 + 0.3**  
→ Use `math.isclose(sum, 1.0, rel_tol=1e-9)` not `==`

**Grid nodes not showing on map**  
→ Check: GeoJSON valid, coordinates `[lon, lat]`, Mapbox token set

**Server crash with Python 3.13**  
→ Delete `venv/`, recreate with `python3.12 -m venv venv`

**CSS changes not appearing**  
→ Run `npm run build:css`, clear browser cache

**Mock data inconsistencies**  
→ Cache at startup: `grid_nodes = generate_mock_grid_nodes()`

---

## Adding Features

### New Siting Criterion (4th metric)
1. Add to `GridNode`: `water_availability: float`
2. Update `generate_mock_grid_nodes()` with values for all 15 nodes
3. Add to `SitingWeights`: `weight_water: float = 0.25`
4. Update `calculate_composite_score()` formula
5. Frontend: Add slider, update Chart.js to 4-axis radar

### New API Endpoint
```python
@app.get("/api/grid/statistics")
async def get_grid_statistics():
    return {
        "total_nodes": len(grid_nodes),
        "avg_clean_gen": sum(n.clean_gen for n in grid_nodes) / len(grid_nodes)
    }
```

Group with comment: `# === STATISTICS ENDPOINTS ===`

---

## Key Files

**Backend** (`kazuma/`):
- `main.py`: API with startup event loading power plants + energy sources
- `models.py`: Pydantic models (`PowerPlant`, `GridNode`, `EnergySource`, etc.)
- `siting_engine.py`: `SitingEngine` class with `calculate_scores_from_coordinates()`
- `grid_data.py`: Real score generator using proximity algorithms
- `scoring_utils.py`: Distance calculations, decay functions, normalization
- `power_plants_data.py`: eGRID data loader with global cache
- `energy_sources.py`: RWE data loader with geocoding + caching
- `calculate_scores.py`: Standalone script for score calculation testing

**Frontend** (`kazuma/static/`):
- `map.html`: Mapbox with power plant layers (color-coded by fuel)
- `framework.html`: Sliders + Chart.js + demand size selector
- `input.css` / `output.css`: Tailwind (output gitignored)

**Data** (`kazuma/data/`):
- `rwe_projects_clean.json`: 9 renewable projects (input)
- `cache/geocode_cache.pkl`: Geocoding cache (auto-generated)

**Root** (`../` from `kazuma/`):
- `egrid2023_plants_lat_lng_fuel_power.json`: 10,000+ power plants (critical)

**Config**:
- `requirements.txt`: Python deps + 3.12 warning + geopy
- `package.json`: Tailwind build scripts

---

## Testing & Debugging

### Manual API Testing
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/grid/nodes/geojson | jq
curl -X POST http://localhost:8000/api/siting/evaluate \
  -H "Content-Type: application/json" \
  -d '{"site_id": 1, "weight_clean": 0.5, "weight_transmission": 0.3, "weight_reliability": 0.2}'
```

### Logging
```python
logger.info(f"Evaluated site {site_id} with score {score:.1f}")
```

### Future pytest Pattern
```python
async with AsyncClient(app=app, base_url="http://test") as ac:
    response = await ac.post("/api/siting/evaluate", json={...})
assert response.status_code == 200
```

---

## Quick Reference

**Default Weights**: `0.4 / 0.3 / 0.3`  
**Score Range**: 0-100 for all metrics  
**Total Nodes**: 40 across US regions  
**Power Plants**: 10,000+ from EPA eGRID 2023  
**Energy Sources**: 9 RWE renewable projects (geocoded)  
**Port**: 8000  
**Python**: 3.12 only (3.13 breaks Pydantic 2.5.0)  
**CORS**: Wide open (hackathon mode)

**Clean Energy Definition**: Only `WND, SUN, WAT, GEO` fuel codes count as clean
- `is_clean()` method in `PowerPlant` model
- Nuclear/biomass excluded from clean scoring
- Transmission scoring uses ALL plants (fossil plants have best lines)

See `kazuma/AGENTS.md` for commit/test/build workflows.
