# Smart Grid Siting Framework - AI Agent Instructions

## Project Overview
Intelligent siting framework that identifies **optimal locations for large electro-intensive loads** (data centers, electrolyzers, EV/hydrogen hubs) to reduce transmission congestion, improve system reliability, lower emissions, and accelerate clean-energy integration. Evaluates sites using clean generation proximity, transmission headroom, and grid resilience metrics.

**Stack**: Python 3.12 + FastAPI + Pydantic, Vanilla JS frontend with Mapbox GL, Tailwind CSS

## Product Architecture (2 Pages)

### Page 1: Map View (Interactive Geospatial Explorer)
- **Purpose**: Home page showing spatial layers for clean generation, transmission headroom, and reliability
- **Left Panel**: Layer toggles, legend, mini site-summary on hover
- **Right Panel**: Fullscreen Mapbox with 12-20 mock grid nodes across US
- **Interaction**: Click marker → preview box → "Send to Siting Framework" button
- **Mock Data Layers**:
  - Clean Generation Density (0-100): proximity to renewable resources
  - Transmission Headroom (0-100): available capacity on high-voltage lines
  - Reliability Score (0-100): outage frequency + grid topology robustness

### Page 2: Siting Framework (Optimization Sandbox)
- **Purpose**: Structured interface to evaluate/compare candidate sites
- **Left Panel Inputs**:
  - Selected location (from map or manual lat/lon)
  - Criteria weight sliders (must sum to 1.0): clean_gen, transmission_headroom, reliability
  - Demand size selector: 10MW/50MW/200MW/500MW
- **Right Panel Results**:
  - Composite siting score with category breakdown
  - Spider/radar chart visualization
  - "Similar alternative sites" ranked list
  - Save/Compare scenario buttons (modal, not separate page)

## Core Data Flow

### Service Boundaries (New Architecture)
- **`main.py`**: FastAPI endpoints for grid nodes, siting score calculation, scenario comparison
- **`models.py`**: Pydantic schemas for `GridNode`, `SitingCriteria`, `SiteEvaluation`, `ScenarioComparison`
- **`siting_engine.py`**: Composite score calculator using weighted criteria (replaces `policy_engine.py`)
- **`grid_data.py`**: Mock data generator for 12-20 US grid nodes with clean-gen/transmission/reliability scores (replaces `epa_data.py`)
- **`static/map.html`**: Map View page with layer toggles
- **`static/framework.html`**: Siting Framework page with weight sliders and evaluation UI

### Scoring Formula (Core Algorithm)
```python
composite_score = (clean_gen * weight_clean) 
                + (transmission_headroom * weight_transmission)
                + (reliability * weight_reliability)

# Constraint: weight_clean + weight_transmission + weight_reliability == 1.0
# Default weights: 0.4 / 0.3 / 0.3
```

**Example Calculation**:
- Pacific Northwest Node A: clean_gen=82, transmission=74, reliability=68
- Weights: 0.4 / 0.35 / 0.25
- Score = 82×0.4 + 74×0.35 + 68×0.25 = **75.7**

### Mock Data Structure
Each grid node has:
```python
{
  "id": 1,
  "name": "Pacific Northwest Node A",
  "lat": 45.523,
  "lon": -122.676,
  "clean_gen": 82,           # 0-100 scale
  "transmission_headroom": 74,
  "reliability": 68,
  "nearby_projects": [...],   # Optional: nearby clean energy additions
  "nearest_line_km": 12       # Optional: transmission distance
}
```

## Development Workflow

### Environment Setup
```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm install && npm run build:css
export MAPBOX_TOKEN="pk.ey..." # Optional but recommended for frontend map
```

**Python 3.12 Required**: Pydantic 2.5.0 has build issues on 3.13—always use 3.12.

### Running & Testing
```bash
# Backend with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend CSS development (parallel terminal)
npm run watch:css

# Manual API testing
curl http://localhost:8000/api/facilities?industry_type=steel&state=TX&year=2022
```

**No pytest suite exists yet**—test endpoints manually via browser/curl. When adding tests, follow pattern in `AGENTS.md`: use `pytest` with `httpx.AsyncClient` for endpoints and pandas fixtures for data validation.

## Code Conventions & Patterns

### Type Hints & Validation
**All public functions** require explicit type hints. Pydantic models handle runtime validation:
```python
async def evaluate_site(
    site_id: int,
    weight_clean: float = Query(0.4, ge=0, le=1),
    weight_transmission: float = Query(0.3, ge=0, le=1),
    weight_reliability: float = Query(0.3, ge=0, le=1),
    demand_size_mw: Optional[int] = Query(None, ge=10, le=500)
) -> SiteEvaluation:
    # Validate weights sum to 1.0
    if not math.isclose(weight_clean + weight_transmission + weight_reliability, 1.0):
        raise HTTPException(400, "Weights must sum to 1.0")
```

### Layer Value Ranges (Critical for UI)
All three metrics use **0-100 scales** with specific thresholds:

**Clean Generation Density**:
- 0-20: Weak clean energy access
- 20-50: Moderate wind/solar potential  
- 50-80: Strong clean resource areas
- 80-100: Highest resource zones + proximity to planned renewables

**Transmission Headroom**:
- 0-30: Congested
- 30-60: Moderate headroom
- 60-90: Strong headroom
- 90-100: Ideal placement area

**Reliability/Resilience Score**:
- 0-25: Low reliability (high outage frequency, wildfire/storm exposure)
- 25-60: Medium reliability
- 60-85: High reliability
- 85-100: Very high reliability

### Siting Score Calculation
`SitingEngine.calculate_composite_score()` is the core algorithm:
1. **Validate weights** sum to exactly 1.0 (use `math.isclose()` for floating-point tolerance)
2. **Apply weighted sum** to three normalized (0-100) metrics
3. **Round to 1 decimal** place for display (e.g., 75.7 not 75.6834)
4. **Return breakdown** showing contribution of each factor

Always return both the composite score AND per-factor contributions for transparency.

## Frontend Integration

### Map View Page (`static/map.html`)
- **Layer Toggles**: 3 checkboxes control which Mapbox layers are visible
- **Click Interaction**: 
  ```javascript
  map.on('click', 'grid-nodes-layer', (e) => {
    const node = e.features[0].properties;
    showPreviewBox(node);  // Display mini-summary
  });
  ```
- **Preview Box**: Shows name, 3 scores, auto-calculated composite (default weights)
- **Send to Framework Button**: Navigates to `framework.html?site_id=${node.id}`

### Siting Framework Page (`static/framework.html`)
- **Weight Sliders**: 3 range inputs with live validation that weights sum to 1.0
- **Auto-recalculation**: On slider change, immediately call `/api/siting/evaluate` 
- **Visualization**: Use Chart.js radar chart for 3-axis comparison
- **Comparison Modal**: Popup (not separate page) showing table of saved scenarios

### Mapbox Workflow
- `static/map.html` fetches `/api/grid/nodes/geojson` for mock data points
- GeoJSON layers use `circle-radius` expression based on composite score
- Color coding by layer value ranges (see Layer Value Ranges section)
- Falls back to hardcoded 5 sample nodes if backend unavailable

### Tailwind Build Process
- Edit `static/input.css` (utility imports only)
- Run `npm run build:css` → generates `static/output.css` (gitignored)
- Use utility classes directly in HTML—no custom CSS files

## Common Gotchas

1. **Weight Validation**: Always use `math.isclose(sum, 1.0, rel_tol=1e-9)` not `sum == 1.0` because floating-point arithmetic causes errors like 0.4 + 0.3 + 0.3 = 0.9999999999.

2. **Score Rounding**: Display composite scores rounded to 1 decimal (75.7) but store full precision internally for accurate comparisons.

3. **Mock Data Consistency**: Grid node IDs must match between GeoJSON endpoint and evaluation endpoint. Use same source of truth.

4. **Layer Toggle State**: Map layers persist across page reloads using localStorage—clear it when testing layer changes.

5. **Demand Size Parameter**: Currently optional/cosmetic (doesn't affect score). If implementing load-dependent logic later, add to scoring formula.

6. **CORS Middleware**: Set to `allow_origins=["*"]` for hackathon—**remove for production**.

7. **Environment Variables**: `MAPBOX_TOKEN` loaded via `os.getenv()`. No `.env` file parsing—set manually or use deployment secrets.

## Adding New Features

### New Siting Criterion
1. Add field to `GridNode` model in `models.py` (e.g., `water_availability: float`)
2. Update mock data in `grid_data.py` with 0-100 value for new criterion
3. Add weight parameter to `SitingEngine.calculate_composite_score()`
4. Add slider to `framework.html` UI with constraint validation
5. Update radar chart in frontend to show 4th axis

### New Demand Type
1. Add to `DemandType` Literal in `models.py`: `"ai_compute_hub"` | `"hydrogen_plant"`
2. Update `demand_size_mw` ranges in Query validation
3. (Optional) Implement load-dependent scoring if criteria have threshold effects

### New Comparison Feature
1. Add `/api/siting/scenarios` endpoint to save evaluations
2. Return list of `SavedScenario` models with site_id, weights, score
3. Frontend: Build comparison table in modal showing delta columns
4. Highlight winner with green background (highest composite score)

### New API Endpoint Pattern
Follow FastAPI patterns in `main.py`:
- Use Pydantic models for request/response types
- Group endpoints with comment blocks: `# === GRID DATA ENDPOINTS ===`
- Include weight validation with descriptive error messages
- Log with `logger.info(f"Evaluated site {site_id} with score {score:.1f}")`

## Key Files Reference
- **Mock Grid Nodes**: Minimum 5 nodes required (Pacific NW, N. California, Texas, Midwest, Southeast), expand to 12-20 for full coverage
- **Scoring Defaults**: weight_clean=0.4, weight_transmission=0.3, weight_reliability=0.3 (matches energy policy best practices)
- **Sample API Response**: `/api/grid/nodes/geojson` returns FeatureCollection with 3 metric properties per node
- **Existing Agent Guide**: `kazuma/AGENTS.md` contains detailed build/test/commit workflows

## API Endpoints (New)

### GET `/api/grid/nodes/geojson`
Returns GeoJSON FeatureCollection of all grid nodes for map display.

### GET `/api/grid/nodes/{site_id}`
Returns detailed GridNode model for specific site.

### POST `/api/siting/evaluate`
Evaluates site with custom weights. Request body:
```json
{
  "site_id": 1,
  "weight_clean": 0.4,
  "weight_transmission": 0.35,
  "weight_reliability": 0.25,
  "demand_size_mw": 200
}
```

### GET `/api/siting/alternatives?site_id={id}&limit={n}`
Returns top N alternative sites ranked by composite score using same weights.

## External Dependencies
- **Mapbox GL JS**: v2.15.0 for map rendering (requires token for production use)
- **Chart.js**: For radar/spider charts showing 3-axis siting criteria
- **No external APIs**: All data is mock/generated—no EPA or grid operator integrations yet
- **No database**: All data in-memory (expand to PostgreSQL + PostGIS for real deployment)
