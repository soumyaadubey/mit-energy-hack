# Nearby Power Plants Feature

## Overview

Added functionality to display nearby power plants when evaluating a location in the siting framework. This provides transparency into which power plants are influencing the clean generation and transmission headroom scores.

## Implementation Details

### Backend Changes

#### 1. New Model: `NearbyPowerPlant` (models.py)
```python
class NearbyPowerPlant(BaseModel):
    """Nearby power plant from eGRID data"""
    oris_code: int
    plant_name: str
    distance_km: float
    primary_fuel: str
    primary_fuel_category: str
    nameplate_mw: float
    is_clean: bool
    latitude: float
    longitude: float
```

#### 2. Updated Model: `SiteEvaluation` (models.py)
Added new field to include nearby power plants in evaluation results:
```python
class SiteEvaluation(BaseModel):
    # ... existing fields ...
    nearby_power_plants: List[NearbyPowerPlant] = []
```

#### 3. New Function: `find_nearby_power_plants()` (scoring_utils.py)
```python
def find_nearby_power_plants(
    node_lat: float,
    node_lon: float,
    power_plants: List,
    max_distance_km: float = 200.0,
    limit: int = 20,
    clean_only: bool = False
) -> List[dict]
```

**Features:**
- Finds power plants within specified distance (default: 200km)
- Sorts by distance (closest first)
- Optional filter for clean energy plants only
- Returns plant details including distance, capacity, fuel type, and clean status

#### 4. Updated Engine: `SitingEngine` (siting_engine.py)

**New Method:** `_find_nearby_power_plants()`
- Called during site evaluation
- Converts plant data to `NearbyPowerPlant` models
- Returns up to 20 nearest plants

**Updated Method:** `evaluate_site()`
- Now accepts optional `power_plants` parameter
- Populates `nearby_power_plants` field in evaluation results

#### 5. Updated API Endpoints (main.py)

**Updated Endpoints:**
- `POST /api/siting/evaluate` - Now passes `power_plants` to engine
- `POST /api/siting/evaluate-location` - Now includes nearby plants in response

### Frontend Changes

#### 1. New UI Section (framework.html)

Added "Nearby Power Plants" section after "Alternative Sites":
```html
<div class="bg-white rounded-lg shadow p-6 mb-6">
    <h2 class="text-lg font-semibold text-gray-900 mb-4">Nearby Power Plants</h2>
    <p class="text-xs text-gray-600 mb-3">Plants within 200km that influence clean gen and transmission scores</p>
    <div id="nearby-plants-list" class="space-y-2">
        <!-- Populated by JS -->
    </div>
</div>
```

#### 2. Updated Display Logic (framework.html)

**JavaScript Features:**
- Groups plants into "Clean Energy Plants" 🌱 and "Transmission Infrastructure" ⚡
- Color-coded display:
  - Clean plants: Green background/border
  - Other plants: Gray background/border
- Shows key details: Name, fuel type, capacity, distance
- Limits display to first 10 non-clean plants (with count of remaining)
- Handles empty state gracefully

**Display Format:**
```
🌱 Clean Energy Plants
  Wind Farm A
  WIND • 500 MW • 45.2 km away

⚡ Transmission Infrastructure
  Coal Plant B
  COAL • 1200 MW • 87.5 km away
  + 5 more plants
```

## How Nearby Plants Influence Scores

### Clean Generation Score
- **Only clean energy plants** (WND, SUN, WAT, GEO) contribute
- Closer plants have higher contribution (proximity decay)
- Larger plants contribute more
- Distance thresholds:
  - <50km: 100% contribution
  - 50-100km: 70% contribution
  - 100-200km: 40% contribution
  - 200-300km: 20% contribution
  - >300km: 0% contribution

### Transmission Headroom Score
- **ALL power plants** contribute (fossil + clean)
- Why: Fossil plants often have best transmission infrastructure (high voltage lines)
- Voltage-aware decay based on plant size:
  - Large plants (≥500 MW): Useful to 300km (500-765kV lines)
  - Medium plants (100-500 MW): Useful to 150km (230-345kV lines)
  - Small plants (<100 MW): Useful to 50km (115-230kV lines)

## Usage Examples

### 1. Evaluate a Grid Node
```bash
curl -X POST http://localhost:8000/api/siting/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 1,
    "weight_clean": 0.4,
    "weight_transmission": 0.3,
    "weight_reliability": 0.3
  }'
```

**Response includes:**
```json
{
  "site": {...},
  "score_breakdown": {...},
  "nearby_power_plants": [
    {
      "oris_code": 123,
      "plant_name": "Columbia Gorge Wind Farm",
      "distance_km": 45.2,
      "primary_fuel": "WND",
      "primary_fuel_category": "WIND",
      "nameplate_mw": 500.0,
      "is_clean": true,
      "latitude": 45.7,
      "longitude": -121.5
    }
  ]
}
```

### 2. Evaluate Custom Location
```bash
curl -X POST http://localhost:8000/api/siting/evaluate-location \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 45.5,
    "longitude": -122.7,
    "weight_clean": 0.5,
    "weight_transmission": 0.3,
    "weight_reliability": 0.2
  }'
```

### 3. Frontend Usage
User clicks "Evaluate Site" → API returns evaluation with nearby plants → Frontend displays:
1. Score breakdown
2. Evaluation notes
3. Alternative sites
4. **Nearby power plants** (new!)

## Benefits

### Transparency
- Users can see exactly which plants influence scores
- Understand why a location scores high or low
- Validate scoring logic with real data

### Decision Support
- Identify specific clean energy resources nearby
- Assess transmission infrastructure quality
- Plan for interconnection with specific plants

### Educational Value
- Learn about power plant distribution
- Understand grid infrastructure patterns
- See relationship between plant type and distance impact

## Testing

Run validation tests:
```bash
cd kazuma/
source venv/bin/activate

# Test models
python -c "from models import NearbyPowerPlant, SiteEvaluation; print('✓ Models OK')"

# Test scoring utils
python -c "from scoring_utils import find_nearby_power_plants; print('✓ Scoring utils OK')"

# Test full integration
uvicorn main:app --reload
# Then visit http://localhost:8000/framework
```

## Future Enhancements

1. **Interactive Plant Markers**
   - Click plant to see details
   - Highlight on map
   - Show contribution to score

2. **Filtering Options**
   - Filter by fuel type
   - Filter by capacity range
   - Adjust distance threshold

3. **Visual Indicators**
   - Distance rings on map (50km, 100km, 200km)
   - Color-coded by contribution to score
   - Size proportional to capacity

4. **Export Functionality**
   - Download plant list as CSV
   - Include in scenario comparison reports
   - Generate interconnection study inputs

## Troubleshooting

### "No power plants nearby" despite clicking near a plant

**Symptoms**:
- Click very close to a power plant on the map
- Evaluation shows "No power plants found within 200km"

**Root Cause**:
Power plants are loaded at server startup. If the server hasn't fully initialized or there was an error loading the data, the `power_plants` global variable may be empty.

**Solutions**:

1. **Check server logs** for errors during startup:
   ```bash
   # Look for these lines in the logs:
   INFO:main:Loading US power plants from eGRID data...
   INFO:main:Successfully loaded 12337 power plants
   ```

2. **Restart the server** to reload power plants:
   ```bash
   # Stop the server (Ctrl+C)
   # Start again
   cd kazuma/
   source venv/bin/activate
   uvicorn main:app --reload
   ```

3. **Check the eGRID data file exists**:
   ```bash
   ls -lh ../egrid2023_plants_lat_lng_fuel_power.json
   # Should show a ~10MB file
   ```

4. **Verify power plants are loaded** via API:
   ```bash
   curl http://localhost:8000/api/power-plants?limit=5 | jq
   # Should return 5 plants
   ```

5. **Check for Pydantic validation errors**:
   - Some plants have negative `annual_net_gen_mwh` which triggers warnings
   - These are logged but skipped (plants still load, just fewer than 13k)
   - Look for: `WARNING:power_plants_data:Skipping invalid plant entry`

### Debug Mode

The code now includes extensive logging. Set log level to DEBUG to see detailed trace:

```python
# In main.py, change:
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- `find_nearby_power_plants: lat=X, lon=Y, N total plants`
- `Found N plants within 200km before sorting/limiting`
- `Returning N plants after limit=20`

## Files Modified

### Backend
- `kazuma/models.py` - Added `NearbyPowerPlant` model, updated `SiteEvaluation`
- `kazuma/scoring_utils.py` - Added `find_nearby_power_plants()` function
- `kazuma/siting_engine.py` - Added `_find_nearby_power_plants()`, updated `evaluate_site()`
- `kazuma/main.py` - Updated both evaluation endpoints to include power plants

### Frontend
- `kazuma/static/framework.html` - Added UI section and display logic

## Performance Notes

- Nearby plant search: O(n) where n = number of power plants (~10,000)
- Distance calculations: Fast Pythagorean approximation (not Haversine)
- Typical response time: <100ms for 20 nearest plants
- Results cached at grid node level (no per-request recalculation)

## Data Source

All power plant data from:
- **EPA eGRID 2023**: 10,000+ US power plants
- Fields used: ORIS code, name, lat/lon, fuel type, capacity
- Clean energy definition: WND, SUN, WAT, GEO only
