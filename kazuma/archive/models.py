"""
Pydantic Models for Industrial Emissions Data

Defines data structures for EPA facility data, emissions, compliance, and policy scenarios.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ============================================================================
# FACILITY MODELS
# ============================================================================

class FacilityCoordinates(BaseModel):
    """Geographic coordinates for facility location"""
    latitude: float
    longitude: float
    accuracy: Optional[str] = None  # e.g., "ADDRESS", "ROOFTOP", "APPROXIMATE"


class EmissionsByGasType(BaseModel):
    """Emissions broken down by greenhouse gas type"""
    co2: float = 0.0  # Carbon dioxide (metric tons)
    ch4: float = 0.0  # Methane (metric tons)
    n2o: float = 0.0  # Nitrous oxide (metric tons)
    hfc: float = 0.0  # Hydrofluorocarbons (metric tons CO2e)
    pfc: float = 0.0  # Perfluorocarbons (metric tons CO2e)
    sf6: float = 0.0  # Sulfur hexafluoride (metric tons CO2e)
    total_co2e: float = 0.0  # Total CO2 equivalent (metric tons)


class EmissionsBySource(BaseModel):
    """Emissions broken down by source category within facility"""
    source_category: str  # e.g., "Blast Furnace", "Cement Kiln", "Ethylene Cracker"
    subpart_code: Optional[str] = None  # GHGRP subpart (C, H, X, Y, etc.)
    emissions_mt_co2e: float = 0.0
    description: Optional[str] = None


class ProductionData(BaseModel):
    """Production volume data for carbon intensity calculations"""
    product_type: str  # e.g., "Steel", "Cement", "Ethylene"
    annual_production: float  # Annual production volume
    production_unit: str  # e.g., "metric tons", "short tons"
    carbon_intensity: Optional[float] = None  # tCO2e per unit product


class ComplianceRecord(BaseModel):
    """Environmental compliance and violation history"""
    facility_id: str
    program: str  # e.g., "CAA" (Clean Air Act), "CWA" (Clean Water Act)
    informal_enforcement_count: int = 0
    formal_enforcement_count: int = 0
    violations_count: int = 0
    last_inspection_date: Optional[datetime] = None
    compliance_status: Optional[str] = None  # "In Compliance", "Violation", "Unknown"


class ToxicRelease(BaseModel):
    """TRI toxic release data for environmental justice analysis"""
    chemical_name: str
    cas_number: Optional[str] = None
    total_releases_lbs: float = 0.0  # Total releases in pounds
    air_releases_lbs: float = 0.0
    water_releases_lbs: float = 0.0
    land_releases_lbs: float = 0.0
    carcinogen: bool = False


class WaterUsage(BaseModel):
    """Water usage and discharge data"""
    annual_withdrawal_gallons: Optional[float] = None
    annual_discharge_gallons: Optional[float] = None
    water_source: Optional[str] = None  # e.g., "Municipal", "Surface Water", "Groundwater"
    discharge_permit_number: Optional[str] = None


class IndustrialFacility(BaseModel):
    """
    Complete industrial facility data combining all EPA sources.
    
    Represents the 18 key EPA data attributes for legislative visualization.
    """
    # 1. Facility Identification
    facility_id: str = Field(..., description="Primary facility identifier (Registry ID or GHGRP ID)")
    facility_name: str
    
    # 2. Location & Coordinates (FRS data)
    coordinates: FacilityCoordinates
    street_address: Optional[str] = None
    city: str
    state: str  # Two-letter code
    zip_code: Optional[str] = None
    county: Optional[str] = None
    epa_region: Optional[int] = None  # EPA Region 1-10
    
    # 3. Industry Classification (NAICS)
    naics_code: str
    industry_type: Literal["steel", "cement", "chemicals"]
    industry_sector_description: Optional[str] = None
    
    # 4. Emissions Data (GHGRP)
    reporting_year: int
    emissions_by_gas: EmissionsByGasType
    
    # 5. Emissions by Source Category
    emissions_by_source: List[EmissionsBySource] = []
    
    # 6. Multi-Year Trends
    historical_emissions: List[Dict[int, float]] = []  # {year: total_co2e}
    
    # 7. Toxic Releases (TRI)
    toxic_releases: List[ToxicRelease] = []
    total_toxic_releases_lbs: float = 0.0
    
    # 8. Air Quality Impact (placeholder for AQS integration)
    nearest_aqs_station_id: Optional[str] = None
    distance_to_aqs_miles: Optional[float] = None
    
    # 9. Compliance & Enforcement (ECHO)
    compliance_records: List[ComplianceRecord] = []
    total_violations: int = 0
    enforcement_actions: int = 0
    
    # 10. Operational Status
    operational_status: str = "Active"  # "Active", "Closed", "Under Construction", "Seasonal"
    permit_status: Optional[str] = None
    
    # 11. Waste Data (RCRA - placeholder)
    hazardous_waste_generated_tons: Optional[float] = None
    
    # 12. Water Usage (ICIS/PCS)
    water_usage: Optional[WaterUsage] = None
    
    # 13. Geospatial Boundaries (optional polygon)
    facility_boundary_geojson: Optional[Dict[str, Any]] = None
    
    # 14. Energy Use
    annual_energy_use_mmbtu: Optional[float] = None  # Million BTU
    electricity_use_mwh: Optional[float] = None
    
    # 15. Subpart-Specific Data
    ghgrp_subparts: List[str] = []  # e.g., ["C", "D"] for steel facilities
    
    # 16. Parent Company
    parent_company_name: Optional[str] = None
    parent_company_id: Optional[str] = None
    
    # 17. Production Volume & Carbon Intensity
    production_data: List[ProductionData] = []
    
    # 18. Additional Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_sources: List[str] = []  # e.g., ["GHGRP", "FRS", "TRI", "ECHO"]
    data_quality_flags: List[str] = []  # Any data quality issues
    
    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convert facility to GeoJSON feature for Mapbox visualization"""
        return {
            "type": "Feature",
            "id": self.facility_id,
            "properties": {
                "facility_id": self.facility_id,
                "name": self.facility_name,
                "industry": self.industry_type,
                "city": self.city,
                "state": self.state,
                "naics": self.naics_code,
                "total_emissions": self.emissions_by_gas.total_co2e,
                "co2": self.emissions_by_gas.co2,
                "ch4": self.emissions_by_gas.ch4,
                "n2o": self.emissions_by_gas.n2o,
                "year": self.reporting_year,
                "violations": self.total_violations,
                "toxic_releases": self.total_toxic_releases_lbs,
                "parent_company": self.parent_company_name,
                "operational_status": self.operational_status,
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
# POLICY SIMULATION MODELS
# ============================================================================

class CarbonTaxPolicy(BaseModel):
    """Carbon tax policy parameters"""
    tax_rate_per_ton_co2e: float = 0.0  # $/metric ton CO2e
    tax_type: Literal["flat", "progressive", "cap_and_trade"] = "flat"
    exemptions: List[str] = []  # NAICS codes exempt from tax
    phase_in_years: int = 1  # Years to phase in full tax


class EmissionsCap(BaseModel):
    """Emissions cap or reduction target"""
    target_year: int
    reduction_percentage: float  # Percent reduction from baseline
    baseline_year: int = 2022
    enforcement_mechanism: Literal["penalty", "shutdown", "offset"] = "penalty"


class FilteringRequirement(BaseModel):
    """Required emissions filtering/capture technology"""
    technology_type: str  # e.g., "Carbon Capture", "Scrubber", "Catalytic Converter"
    capture_efficiency: float  # Percent of emissions captured
    capital_cost_per_facility: float  # One-time installation cost
    annual_operating_cost: float  # Annual operating cost
    applicable_industries: List[str] = []  # Which industries must comply


class PolicyScenario(BaseModel):
    """Complete policy scenario for simulation"""
    scenario_name: str
    description: Optional[str] = None
    
    # Policy components
    carbon_tax: Optional[CarbonTaxPolicy] = None
    emissions_cap: Optional[EmissionsCap] = None
    filtering_requirements: List[FilteringRequirement] = []
    
    # Additional parameters
    enforcement_level: Literal["low", "medium", "high"] = "medium"
    phase_in_period_years: int = 5
    
    # Target facilities
    target_states: List[str] = []  # Empty = all states
    target_industries: List[str] = []  # Empty = all industries
    target_naics_codes: List[str] = []


class PolicyImpactResult(BaseModel):
    """Results from policy simulation"""
    scenario: PolicyScenario
    
    # Emissions impact
    baseline_emissions_mt_co2e: float
    projected_emissions_mt_co2e: float
    emissions_reduction_mt_co2e: float
    emissions_reduction_percentage: float
    
    # Economic impact
    total_carbon_tax_revenue: float  # Annual revenue from carbon tax
    total_compliance_cost: float  # Cost to industry for compliance
    facilities_affected: int
    
    # By industry breakdown
    impact_by_industry: Dict[str, Dict[str, float]] = {}  # {industry: {emissions_reduction, cost, etc}}
    
    # By state breakdown
    impact_by_state: Dict[str, Dict[str, float]] = {}
    
    # Timeline projection
    emissions_trajectory: List[Dict[str, Any]] = []  # Year-by-year projections
    
    # Facility-level impacts
    facility_impacts: List[Dict[str, Any]] = []  # Per-facility cost and emission changes


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class FacilityQuery(BaseModel):
    """Query parameters for facility search"""
    industry_type: Optional[Literal["steel", "cement", "chemicals"]] = None
    state: Optional[str] = None
    epa_region: Optional[int] = None
    min_emissions: Optional[float] = None  # Minimum total CO2e
    max_emissions: Optional[float] = None
    year: int = 2022
    parent_company: Optional[str] = None
    compliance_status: Optional[str] = None
    limit: int = 1000
    offset: int = 0


class AggregatedEmissions(BaseModel):
    """Aggregated emissions data for choropleth visualization"""
    aggregation_level: Literal["state", "county", "epa_region"]
    region_id: str  # State code, county FIPS, or EPA region number
    region_name: str
    total_facilities: int
    total_emissions_mt_co2e: float
    facilities_by_industry: Dict[str, int]  # {industry: count}
    emissions_by_industry: Dict[str, float]  # {industry: emissions}


class FacilityDetail(BaseModel):
    """Detailed facility information for popup/detail view"""
    facility: IndustrialFacility
    nearby_facilities: List[IndustrialFacility] = []  # Within 50 miles
    emissions_trend_chart_data: Dict[str, List] = {}  # For charting
    compliance_timeline: List[Dict[str, Any]] = []
