"""
Pydantic Models for Smart Grid Siting Framework

Defines data structures for grid nodes, siting criteria, evaluations, and scenario comparisons.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import math


# ============================================================================
# POWER PLANT MODELS
# ============================================================================

class PowerPlant(BaseModel):
    """
    US Power Plant from eGRID database.
    
    Contains location, fuel type, capacity, and generation data.
    Used for clean generation scoring and map visualization.
    """
    oris_code: int = Field(..., description="DOE plant identification code")
    plant_name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    primary_fuel: str = Field(..., description="EIA fuel code (e.g., SUN, WND, WAT)")
    primary_fuel_category: str = Field(..., description="Fuel category (e.g., SOLAR, WIND, HYDRO)")
    nameplate_mw: float = Field(..., ge=0)
    annual_net_gen_mwh: float = Field(0.0, ge=0, description="Annual generation, 0 if not reported")
    
    def is_renewable(self) -> bool:
        """Check if plant uses renewable energy source (WIND, SOLAR, HYDRO, GEOTHERMAL only)"""
        # Only WND, SUN, WAT, GEO are considered clean energy sources
        renewable_fuels = {"WND", "SUN", "WAT", "GEO"}
        renewable_categories = {"WIND", "SOLAR", "HYDRO", "GEOTHERMAL"}
        return (self.primary_fuel in renewable_fuels or 
                self.primary_fuel_category in renewable_categories)
    
    def is_clean(self) -> bool:
        """Check if plant is clean energy (same as renewable - WND, SUN, WAT, GEO only)"""
        # Only renewable sources count as clean - no nuclear, no biomass
        return self.is_renewable()
    
    def get_fuel_color(self) -> str:
        """Get Mapbox GL color for fuel category"""
        return get_fuel_category_color(self.primary_fuel_category)
    
    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convert power plant to GeoJSON feature for Mapbox visualization"""
        return {
            "type": "Feature",
            "id": self.oris_code,
            "properties": {
                "oris_code": self.oris_code,
                "plant_name": self.plant_name,
                "primary_fuel": self.primary_fuel,
                "primary_fuel_category": self.primary_fuel_category,
                "nameplate_mw": round(self.nameplate_mw, 1),
                "annual_net_gen_mwh": round(self.annual_net_gen_mwh, 0),
                "is_renewable": self.is_renewable(),
                "is_clean": self.is_clean(),
                "fuel_color": self.get_fuel_color(),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude]
            }
        }


def get_fuel_category_color(fuel_category: str) -> str:
    """
    Get color for power plant fuel category.
    
    Clean energy sources get vibrant green/blue colors.
    Non-clean sources get distinct warm colors for visibility.
    """
    color_map = {
        # Clean energy sources (green/blue palette)
        "SOLAR": "#22c55e",      # Green-500
        "WIND": "#10b981",       # Emerald-500
        "HYDRO": "#0ea5e9",      # Sky-500
        "GEOTHERMAL": "#84cc16", # Lime-500
        
        # Non-clean sources (warm/distinct colors)
        "BIOMASS": "#f59e0b",    # Amber-500
        "NUCLEAR": "#8b5cf6",    # Violet-500
        "GAS": "#f97316",        # Orange-500
        "COAL": "#ef4444",       # Red-500
        "OIL": "#dc2626",        # Red-600
        "OFSL": "#fb923c",       # Orange-400
        "OTHF": "#a855f7",       # Purple-500
    }
    return color_map.get(fuel_category, "#6b7280")  # Default: Gray-500


def get_fuel_category_icon(fuel_category: str) -> str:
    """
    Get emoji/icon for fuel category (for UI display).
    Clean energy sources have nature icons, non-clean have industrial icons.
    """
    icon_map = {
        # Clean energy sources
        "SOLAR": "☀️",
        "WIND": "💨",
        "HYDRO": "💧",
        "GEOTHERMAL": "🌋",
        
        # Non-clean energy sources
        "BIOMASS": "🌾",
        "NUCLEAR": "⚛️",
        "GAS": "🔥",
        "COAL": "⛏️",
        "OIL": "🛢️",
        "OFSL": "⚡",
        "OTHF": "⚙️",
    }
    return icon_map.get(fuel_category, "⚡")


# ============================================================================
# GRID NODE MODELS
# ============================================================================

class GridNodeCoordinates(BaseModel):
    """Geographic coordinates for grid node location"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class NearbyProject(BaseModel):
    """Nearby clean energy project"""
    name: str
    distance_km: float
    capacity_mw: int
    project_type: Literal["wind", "solar", "hydro", "nuclear", "battery"]
    status: Literal["planned", "under_construction", "operational"] = "operational"


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


class TransmissionLine(BaseModel):
    """Nearby transmission infrastructure"""
    line_id: str
    distance_km: float
    voltage_kv: int  # Kilovolts (e.g., 230, 345, 500, 765)
    capacity_available_mw: Optional[float] = None
    upgrade_cost_estimate_million: Optional[float] = None


class GridNode(BaseModel):
    """
    Grid node representing a potential site for electro-intensive load.
    
    Contains three core metrics (0-100 scale):
    - clean_gen: Proximity to renewable generation resources
    - transmission_headroom: Available transmission capacity
    - reliability: Grid resilience and outage frequency score
    """
    id: int
    name: str
    coordinates: GridNodeCoordinates
    
    # Core siting metrics (0-100 scale)
    clean_gen: float = Field(..., ge=0, le=100, description="Clean generation density score")
    transmission_headroom: float = Field(..., ge=0, le=100, description="Transmission capacity headroom")
    reliability: float = Field(..., ge=0, le=100, description="Grid reliability/resilience score")
    
    # Optional enrichment data
    nearby_projects: List[NearbyProject] = []
    transmission_lines: List[TransmissionLine] = []
    
    # Metadata
    region: Optional[str] = None  # e.g., "Pacific Northwest", "ERCOT", "PJM"
    state: Optional[str] = None
    balancing_authority: Optional[str] = None
    
    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convert grid node to GeoJSON feature for Mapbox visualization"""
        return {
            "type": "Feature",
            "id": self.id,
            "properties": {
                "id": self.id,
                "name": self.name,
                "clean_gen": self.clean_gen,
                "transmission_headroom": self.transmission_headroom,
                "reliability": self.reliability,
                "region": self.region,
                "state": self.state,
                "nearby_projects_count": len(self.nearby_projects),
                "transmission_lines_count": len(self.transmission_lines),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [
                    self.coordinates.longitude,
                    self.coordinates.latitude
                ]
            }
        }


# ============================================================================
# SITING CRITERIA MODELS
# ============================================================================

class SitingWeights(BaseModel):
    """
    Weight allocation for siting criteria.
    
    Must sum to exactly 1.0 for valid composite score calculation.
    """
    weight_clean: float = Field(0.4, ge=0, le=1, description="Weight for clean generation proximity")
    weight_transmission: float = Field(0.3, ge=0, le=1, description="Weight for transmission headroom")
    weight_reliability: float = Field(0.3, ge=0, le=1, description="Weight for grid reliability")
    
    @field_validator('weight_clean', 'weight_transmission', 'weight_reliability')
    @classmethod
    def validate_weight_range(cls, v: float) -> float:
        if not (0 <= v <= 1):
            raise ValueError("Weight must be between 0 and 1")
        return v
    
    def validate_sum(self) -> None:
        """Validate that weights sum to 1.0 (with floating-point tolerance)"""
        total = self.weight_clean + self.weight_transmission + self.weight_reliability
        if not math.isclose(total, 1.0, rel_tol=1e-9):
            raise ValueError(f"Weights must sum to 1.0, got {total:.10f}")


class DemandProfile(BaseModel):
    """Profile of the electro-intensive load being sited"""
    demand_type: Literal["data_center", "electrolyzer", "ev_hub", "hydrogen_plant", "ai_compute"] = "data_center"
    size_mw: int = Field(..., ge=10, le=2000, description="Load size in megawatts")
    load_factor: float = Field(0.85, ge=0, le=1, description="Capacity factor (fraction of time at full load)")
    duration_years: int = Field(20, ge=1, le=50, description="Expected operational lifetime")


# ============================================================================
# EVALUATION MODELS
# ============================================================================

class ScoreBreakdown(BaseModel):
    """Detailed breakdown of composite score components"""
    clean_gen_score: float
    clean_gen_contribution: float  # Weighted contribution to composite
    
    transmission_score: float
    transmission_contribution: float
    
    reliability_score: float
    reliability_contribution: float
    
    composite_score: float
    
    weights_used: SitingWeights


class SiteEvaluation(BaseModel):
    """
    Complete evaluation result for a grid node site.
    
    Includes composite score, breakdown, and contextual information.
    """
    site: GridNode
    weights: SitingWeights
    demand_profile: Optional[DemandProfile] = None
    
    score_breakdown: ScoreBreakdown
    
    # Ranking context
    percentile_rank: Optional[float] = None  # Where this site ranks (0-100)
    alternative_sites: List[Dict[str, Any]] = []  # Top N alternatives
    
    # Nearby power plants (for transparency on score drivers)
    nearby_power_plants: List[NearbyPowerPlant] = []
    
    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    evaluation_notes: List[str] = []


class ScenarioComparison(BaseModel):
    """
    Comparison of multiple site evaluations.
    
    Used in the comparison modal on Siting Framework page.
    """
    scenario_name: str
    scenarios: List[SiteEvaluation]
    
    # Comparison insights
    best_site_id: int
    score_range: tuple[float, float]  # (min, max)
    
    # Delta analysis
    score_deltas: Dict[int, float]  # {site_id: delta_from_best}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class SitingRequest(BaseModel):
    """Request to evaluate a site with specific criteria"""
    site_id: int
    weight_clean: float = Field(0.4, ge=0, le=1)
    weight_transmission: float = Field(0.3, ge=0, le=1)
    weight_reliability: float = Field(0.3, ge=0, le=1)
    demand_size_mw: Optional[int] = Field(None, ge=10, le=2000)
    demand_type: Optional[Literal["data_center", "electrolyzer", "ev_hub", "hydrogen_plant", "ai_compute"]] = None
    
    def to_weights(self) -> SitingWeights:
        """Convert to SitingWeights model with validation"""
        weights = SitingWeights(
            weight_clean=self.weight_clean,
            weight_transmission=self.weight_transmission,
            weight_reliability=self.weight_reliability
        )
        weights.validate_sum()
        return weights
    
    def to_demand_profile(self) -> Optional[DemandProfile]:
        """Convert to DemandProfile if demand info provided"""
        if self.demand_size_mw and self.demand_type:
            return DemandProfile(
                demand_type=self.demand_type,
                size_mw=self.demand_size_mw
            )
        return None


class AlternativeSitesRequest(BaseModel):
    """Request for alternative sites ranked by score"""
    site_id: int  # Reference site
    weights: SitingWeights
    limit: int = Field(5, ge=1, le=20, description="Number of alternatives to return")
    exclude_self: bool = Field(True, description="Exclude the reference site from results")


class LocationEvaluationRequest(BaseModel):
    """Request to evaluate an arbitrary location by lat/lon coordinates"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of location to evaluate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of location to evaluate")
    weight_clean: float = Field(0.4, ge=0, le=1)
    weight_transmission: float = Field(0.3, ge=0, le=1)
    weight_reliability: float = Field(0.3, ge=0, le=1)
    demand_size_mw: Optional[int] = Field(None, ge=10, le=2000)
    demand_type: Optional[Literal["data_center", "electrolyzer", "ev_hub", "hydrogen_plant", "ai_compute"]] = None
    location_name: Optional[str] = Field(None, description="Optional name for the clicked location")
    
    def to_weights(self) -> SitingWeights:
        """Convert to SitingWeights model with validation"""
        weights = SitingWeights(
            weight_clean=self.weight_clean,
            weight_transmission=self.weight_transmission,
            weight_reliability=self.weight_reliability
        )
        weights.validate_sum()
        return weights
    
    def to_demand_profile(self) -> Optional[DemandProfile]:
        """Convert to DemandProfile if demand info provided"""
        if self.demand_size_mw and self.demand_type:
            return DemandProfile(
                demand_type=self.demand_type,
                size_mw=self.demand_size_mw
            )
        return None


class GeoJSONResponse(BaseModel):
    """GeoJSON FeatureCollection response"""
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class PowerPlantFilters(BaseModel):
    """Filters for power plant queries"""
    fuel_category: Optional[str] = None
    min_capacity_mw: float = Field(0, ge=0)
    max_capacity_mw: float = Field(10000, ge=0)
    renewable_only: bool = False
    clean_only: bool = False
