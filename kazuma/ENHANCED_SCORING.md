# Enhanced Transmission & Clean Energy Scoring

## Overview

The siting framework now uses **sophisticated, capacity-weighted scoring** for both transmission infrastructure and clean energy generation. Scores are calculated from real EPA eGrid power plant data and consider the target load size.

---

## 🔌 Transmission Headroom Scoring

### Key Enhancements

**Uses ALL power plants** (not just clean energy) because transmission infrastructure serves all generation types. Large fossil plants often have the best transmission access with high-voltage lines.

### Scoring Logic

```python
transmission_score = Σ (plant_capacity_mw × transmission_decay_factor)
                     normalized to 0-100 scale (90th percentile = 100)
```

### Voltage-Aware Distance Decay

The decay factor considers **plant size as a proxy for transmission voltage**:

| Plant Size | Voltage Class | Economic Range | Decay Curve |
|------------|---------------|----------------|-------------|
| **Large (≥500 MW)** | 500-765kV | 300 km | Gentle (0.8 at 300km) |
| **Medium (100-500 MW)** | 230-345kV | 150 km | Moderate (0.6 at 150km) |
| **Small (<100 MW)** | 115-230kV | 50 km | Steep (0.3 at 150km) |

**Example**: A 1000 MW coal plant 200km away contributes more to transmission score than a 50 MW solar farm 100km away, because the coal plant requires 500kV transmission that can economically serve large loads.

### Distance Zones

- **0-50 km (Local)**: 100% credit for all plants
- **50-150 km (Regional)**: 60-100% credit (depends on plant size)
- **150-300 km (Bulk)**: 20-80% credit (large plants only)
- **300-500 km (Long-distance)**: 10-50% credit (1+ GW plants only)
- **>500 km**: Minimal/no credit

---

## ⚡ Clean Generation Scoring (NEW: Demand-Aware)

### Key Enhancements

**Now considers target load size** to score capacity adequacy. A location with 200 MW of nearby clean energy scores differently for a 50 MW data center vs. a 500 MW AI compute hub.

### Scoring Logic

```python
base_score = Σ (clean_capacity_mw × proximity_decay × clean_multiplier)
             normalized to 0-100 scale

final_score = base_score × capacity_adequacy_factor
```

### Capacity Adequacy Multipliers

Based on ratio of available clean capacity to demand size:

| Capacity Ratio | Factor | Meaning |
|----------------|--------|---------|
| **≥3.0x demand** | **1.20x** | 🟢 Excellent surplus (20% bonus) |
| **2.0-3.0x** | **1.10x** | 🟢 Good resilience (10% bonus) |
| **1.5-2.0x** | **1.00x** | 🟡 Adequate buffer (neutral) |
| **1.0-1.5x** | **0.95x** | 🟡 Meets demand, tight (5% penalty) |
| **0.7-1.0x** | **0.85x** | 🟠 Moderate shortfall (15% penalty) |
| **0.5-0.7x** | **0.70x** | 🔴 Significant shortfall (30% penalty) |
| **<0.5x** | **0.50x** | 🔴 Severe shortfall (50% penalty) |

### Example Scenarios

**Location A: 300 MW clean capacity nearby**
- 50 MW demand (6x capacity): Base score 85 → **102** (capped at 100) ✅
- 100 MW demand (3x capacity): Base score 85 → **102** (capped at 100) ✅
- 200 MW demand (1.5x capacity): Base score 85 → **85** (neutral) ✅
- 400 MW demand (0.75x capacity): Base score 85 → **72** (shortfall penalty) ⚠️

**Location B: 100 MW clean capacity nearby**
- 50 MW demand (2x capacity): Base score 60 → **66** (resilience bonus) ✅
- 200 MW demand (0.5x capacity): Base score 60 → **42** (severe shortfall) ❌

---

## 🎯 Integration with Demand Profile

### User Input (Framework Page)

```html
<select id="demand-size">
  <option value="50">50 MW (Small Data Center)</option>
  <option value="200">200 MW (Large Data Center)</option>
  <option value="500">500 MW (AI Compute Hub)</option>
</select>
```

### API Request

```json
{
  "site_id": 1,
  "weight_clean": 0.4,
  "weight_transmission": 0.3,
  "weight_reliability": 0.3,
  "demand_size_mw": 200,
  "demand_type": "data_center"
}
```

### Backend Flow

```python
# Extract demand profile
demand_profile = DemandProfile(
    demand_type="data_center",
    size_mw=200
)

# Calculate scores with demand awareness
score_breakdown = siting_engine.calculate_scores_from_coordinates(
    latitude=40.0,
    longitude=-100.0,
    power_plants=all_plants,
    weights=weights,
    demand_profile=demand_profile  # ← Enables capacity adequacy scoring
)
```

---

## 📊 Real-World Impact

### Before Enhancement
- Clean gen score: **Fixed** based only on proximity to renewable projects
- Transmission score: **Simple** linear decay, no voltage awareness
- **Problem**: 50 MW data center scored same as 500 MW AI hub

### After Enhancement
- Clean gen score: **Adaptive** based on load size vs. available capacity
- Transmission score: **Sophisticated** voltage-aware decay by plant size
- **Benefit**: Accurate scoring for different demand profiles

### Example Comparison

**Node: Texas Panhandle (850 MW clean capacity nearby)**

| Demand Size | Old Clean Score | New Clean Score | Change |
|-------------|----------------|-----------------|--------|
| 50 MW | 78 | **94** | +16 (excellent surplus) |
| 200 MW | 78 | **86** | +8 (good match) |
| 500 MW | 78 | **74** | -4 (moderate shortfall) |
| 1000 MW | 78 | **39** | -39 (severe shortfall) |

---

## 🛠️ Technical Implementation

### New Functions (scoring_utils.py)

```python
# Transmission scoring with voltage-aware decay
def transmission_decay_factor(distance_km, plant_capacity_mw) -> float
def calculate_transmission_score(lat, lon, all_plants, norm_factor) -> float
def estimate_transmission_normalization_factor(nodes, plants) -> float

# Clean gen scoring with demand adequacy
def calculate_capacity_adequacy_factor(available_mw, demand_mw) -> float
def calculate_clean_gen_score(..., demand_mw=None) -> float  # Updated
```

### Updated Functions (siting_engine.py)

```python
def calculate_scores_from_coordinates(
    ...,
    demand_profile: Optional[DemandProfile] = None  # ← NEW
) -> ScoreBreakdown
```

### Updated Functions (grid_data.py)

```python
def calculate_real_transmission_scores(nodes, power_plants) -> List[GridNode]
def calculate_real_clean_gen_scores(nodes, sources, demand_mw=None) -> List[GridNode]
def generate_grid_nodes_with_real_scores(
    energy_sources=None,
    power_plants=None  # ← NEW: Uses all plants for transmission
) -> List[GridNode]
```

---

## ✅ Testing

Run comprehensive tests:

```bash
cd kazuma
source venv/bin/activate

# Test transmission decay factors
python3 -c "
from scoring_utils import transmission_decay_factor
print('Large plant (1000 MW) at 250 km:', transmission_decay_factor(250, 1000))
print('Small plant (50 MW) at 75 km:', transmission_decay_factor(75, 50))
"

# Test capacity adequacy
python3 -c "
from scoring_utils import calculate_capacity_adequacy_factor
print('3x capacity available:', calculate_capacity_adequacy_factor(300, 100))
print('0.5x capacity available:', calculate_capacity_adequacy_factor(50, 100))
"

# Test demand-aware scoring
python3 -c "
from scoring_utils import calculate_clean_gen_score
sources = [(40.0, -100.0, 150, 1.0)]  # 150 MW nearby
print('No demand:', calculate_clean_gen_score(40.0, -100.0, sources, 100))
print('50 MW demand:', calculate_clean_gen_score(40.0, -100.0, sources, 100, 50))
print('300 MW demand:', calculate_clean_gen_score(40.0, -100.0, sources, 100, 300))
"
```

---

## 🎓 Key Design Decisions

### Why Transmission Uses All Plants (Not Just Clean)
Transmission infrastructure serves all generation. Large fossil plants often have the best transmission access (500-765kV lines) which benefits new clean loads.

### Why Plant Size Proxies for Voltage
Real transmission voltage data is unavailable in eGrid. Plant capacity correlates strongly with transmission voltage:
- Small plants (<100 MW) → 115-230kV
- Medium plants (100-500 MW) → 230-345kV  
- Large plants (>500 MW) → 345-765kV

### Why Capacity Adequacy Matters
A data center needs reliable clean energy supply. 200 MW of solar 50km away is excellent for a 50 MW load, but inadequate for a 500 MW load. The scoring now reflects this.

### Why 90th Percentile Normalization
Ensures fair comparison across diverse US regions. Top 10% of locations score ~90-100 regardless of absolute capacity values.

---

## 📝 Summary

The enhanced scoring system provides **realistic, demand-aware evaluation** of grid locations by:

1. ✅ Modeling transmission economics with voltage-aware decay
2. ✅ Scoring all power infrastructure (not just clean energy)
3. ✅ Considering capacity adequacy for target load size
4. ✅ Providing actionable insights (surplus vs. shortfall)

This enables better siting decisions for large electro-intensive loads across different demand profiles.
