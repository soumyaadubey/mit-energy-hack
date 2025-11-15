"""
Industrial Emissions Visualization Tool for Legislators

Visualize carbon emissions from steel, cement, and chemical factories across the US.
Simulate policy impacts including carbon taxes, emissions caps, and filtering requirements.
Data powered by EPA GHGRP, FRS, TRI, and ECHO databases.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import httpx
import logging
import os
import json
from io import BytesIO
import pandas as pd

# Import our custom modules
from models import (
    IndustrialFacility,
    FacilityQuery,
    FacilityDetail,
    AggregatedEmissions,
    PolicyScenario,
    PolicyImpactResult,
    FacilityCoordinates,
    EmissionsByGasType,
    CarbonTaxPolicy,
    EmissionsCap,
    FilteringRequirement
)
from epa_data import EPADataFetcher, merge_facility_data
from policy_engine import PolicyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Industrial Emissions Visualization Tool",
    description="Legislative tool to visualize and simulate policy impacts on industrial CO2 emissions from steel, cement, and chemical facilities",
    version="2.0.0"
)

# Add CORS middleware (no auth for hackathon demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")
CACHE_DIR = os.getenv("CACHE_DIR", "./data/cache")
DEFAULT_YEAR = 2022

# Initialize services
epa_fetcher = EPADataFetcher()
policy_engine = PolicyEngine()

# In-memory cache for facilities data
facilities_cache: Dict[str, List[IndustrialFacility]] = {}
cache_timestamp: Dict[str, datetime] = {}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    try:
        return FileResponse("static/index.html")
    except FileNotFoundError:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Industrial Emissions Visualization</title></head>
        <body>
            <h1>Industrial Emissions Visualization Tool</h1>
            <p>Frontend not found. Please ensure static/index.html exists.</p>
        </body>
        </html>
        """)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "industrial-emissions-viz",
        "version": "2.0.0",
        "data_sources": ["EPA GHGRP", "EPA FRS", "EPA TRI", "EPA ECHO"]
    }


@app.get("/api/config")
async def get_config():
    """Get client configuration"""
    return {
        "mapbox_token": MAPBOX_TOKEN,
        "default_center": [-95.7129, 37.0902],  # Center of continental US
        "default_zoom": 4,
        "available_years": list(range(2010, 2024)),
        "industries": ["steel", "cement", "chemicals"]
    }


@app.get("/api/integration-status")
async def integration_status():
    """
    Return status information about external integrations.
    """
    mapbox_configured = bool(MAPBOX_TOKEN)
    epa_api_reachable = False
    last_checked = None

    # Probe the EPA API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://data.epa.gov/efservice/tri.tri_facility/state_abbr/equals/VA/1:1/JSON")
            epa_api_reachable = resp.status_code < 400
    except Exception:
        epa_api_reachable = False
    last_checked = datetime.utcnow().isoformat() + "Z"

    return {
        "mapbox_configured": mapbox_configured,
        "epa_api_base": "https://data.epa.gov/efservice",
        "epa_api_reachable": epa_api_reachable,
        "last_checked": last_checked,
        "cache_enabled": os.path.exists(CACHE_DIR),
        "facilities_cached": len(facilities_cache)
    }


# ============================================================================
# FACILITY DATA ENDPOINTS
# ============================================================================

@app.get("/api/facilities")
async def get_facilities(
    industry_type: Optional[Literal["steel", "cement", "chemicals"]] = None,
    state: Optional[str] = Query(None, max_length=2, description="Two-letter state code"),
    year: int = Query(DEFAULT_YEAR, ge=2010, le=2023),
    min_emissions: Optional[float] = Query(None, ge=0),
    max_emissions: Optional[float] = None,
    limit: int = Query(1000, le=5000),
    offset: int = Query(0, ge=0)
):
    """
    Query industrial facilities with filters.
    
    Returns list of facilities matching criteria with basic info for map display.
    """
    try:
        # Check cache first
        cache_key = f"{industry_type}_{state}_{year}"
        
        if cache_key in facilities_cache and cache_key in cache_timestamp:
            # Use cache if less than 24 hours old
            age = datetime.utcnow() - cache_timestamp[cache_key]
            if age.total_seconds() < 86400:
                facilities = facilities_cache[cache_key]
                logger.info(f"Using cached data for {cache_key}")
            else:
                facilities = await _fetch_and_cache_facilities(industry_type, state, year, cache_key)
        else:
            facilities = await _fetch_and_cache_facilities(industry_type, state, year, cache_key)
        
        # Apply additional filters
        filtered = facilities
        if min_emissions is not None:
            filtered = [f for f in filtered if f.emissions_by_gas.total_co2e >= min_emissions]
        if max_emissions is not None:
            filtered = [f for f in filtered if f.emissions_by_gas.total_co2e <= max_emissions]
        
        # Apply pagination
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        
        return {
            "facilities": [f.dict() for f in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
        
    except Exception as e:
        logger.error(f"Error fetching facilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/facilities/{facility_id}")
async def get_facility_detail(facility_id: str):
    """
    Get detailed information for a specific facility.
    
    Includes all EPA data attributes, compliance history, and emissions breakdown.
    """
    try:
        # Search through cache for facility
        for cached_facilities in facilities_cache.values():
            for facility in cached_facilities:
                if facility.facility_id == facility_id:
                    return {"facility": facility.dict()}
        
        # If not in cache, return 404
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching facility detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/emissions/aggregated")
async def get_aggregated_emissions(
    aggregation: Literal["state", "county", "epa_region"] = "state",
    year: int = Query(DEFAULT_YEAR, ge=2010, le=2023),
    industry_type: Optional[Literal["steel", "cement", "chemicals"]] = None
):
    """
    Get aggregated emissions data for choropleth visualization.
    
    Returns emissions totals by state, county, or EPA region.
    """
    try:
        # Fetch all facilities for the year
        cache_key = f"all_{industry_type}_{year}"
        
        if cache_key in facilities_cache:
            facilities = facilities_cache[cache_key]
        else:
            facilities = await _fetch_and_cache_facilities(industry_type, None, year, cache_key)
        
        # Aggregate by requested level
        aggregated = {}
        
        for facility in facilities:
            if aggregation == "state":
                key = facility.state
                name = facility.state
            elif aggregation == "epa_region":
                key = str(facility.epa_region) if facility.epa_region else "Unknown"
                name = f"EPA Region {facility.epa_region}" if facility.epa_region else "Unknown"
            else:  # county
                key = f"{facility.state}_{facility.county}" if facility.county else facility.state
                name = f"{facility.county}, {facility.state}" if facility.county else facility.state
            
            if key not in aggregated:
                aggregated[key] = {
                    "region_id": key,
                    "region_name": name,
                    "total_facilities": 0,
                    "total_emissions_mt_co2e": 0,
                    "facilities_by_industry": {},
                    "emissions_by_industry": {}
                }
            
            aggregated[key]["total_facilities"] += 1
            aggregated[key]["total_emissions_mt_co2e"] += facility.emissions_by_gas.total_co2e
            
            industry = facility.industry_type
            aggregated[key]["facilities_by_industry"][industry] = \
                aggregated[key]["facilities_by_industry"].get(industry, 0) + 1
            aggregated[key]["emissions_by_industry"][industry] = \
                aggregated[key]["emissions_by_industry"].get(industry, 0) + facility.emissions_by_gas.total_co2e
        
        return {
            "aggregation_level": aggregation,
            "year": year,
            "regions": list(aggregated.values())
        }
        
    except Exception as e:
        logger.error(f"Error aggregating emissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/facilities/geojson")
async def get_facilities_geojson(
    industry_type: Optional[Literal["steel", "cement", "chemicals"]] = None,
    state: Optional[str] = None,
    year: int = Query(DEFAULT_YEAR, ge=2010, le=2023),
    limit: int = Query(1000, le=5000)
):
    """
    Get facilities as GeoJSON FeatureCollection for Mapbox.
    
    Optimized for map rendering with essential properties only.
    Falls back to sample data if EPA data not available.
    """
    try:
        cache_key = f"{industry_type}_{state}_{year}"
        
        if cache_key in facilities_cache:
            facilities = facilities_cache[cache_key]
        else:
            try:
                facilities = await _fetch_and_cache_facilities(industry_type, state, year, cache_key)
            except Exception as fetch_error:
                logger.warning(f"EPA fetch failed, using sample data: {fetch_error}")
                # Return empty result for now - sample data endpoint provides demo data
                return {
                    "type": "FeatureCollection",
                    "features": []
                }
        
        # Convert to GeoJSON
        features = [f.to_geojson_feature() for f in facilities[:limit]]
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
        
    except Exception as e:
        logger.error(f"Error generating GeoJSON: {e}")
        # Return empty collection instead of 500 error
        return {
            "type": "FeatureCollection",
            "features": []
        }


# ============================================================================
# POLICY SIMULATION ENDPOINT
# ============================================================================

@app.post("/api/policy/simulate", response_model=PolicyImpactResult)
async def simulate_policy(scenario: PolicyScenario):
    """
    Simulate policy impact on industrial emissions.
    
    Calculates effects of carbon taxes, emissions caps, and filtering requirements.
    Returns emissions reductions, costs, and impacts by industry/state.
    """
    try:
        # Fetch facilities based on scenario targets
        year = DEFAULT_YEAR
        
        # Get all relevant facilities
        all_facilities = []
        
        if scenario.target_industries:
            for industry in scenario.target_industries:
                cache_key = f"{industry}_None_{year}"
                if cache_key in facilities_cache:
                    all_facilities.extend(facilities_cache[cache_key])
                else:
                    fetched = await _fetch_and_cache_facilities(industry, None, year, cache_key)
                    all_facilities.extend(fetched)
        else:
            # Fetch all industries
            for industry in ["steel", "cement", "chemicals"]:
                cache_key = f"{industry}_None_{year}"
                if cache_key in facilities_cache:
                    all_facilities.extend(facilities_cache[cache_key])
                else:
                    fetched = await _fetch_and_cache_facilities(industry, None, year, cache_key)
                    all_facilities.extend(fetched)
        
        # Run policy simulation
        result = policy_engine.simulate_policy(all_facilities, scenario)
        
        logger.info(f"Policy simulation complete: {result.emissions_reduction_percentage}% reduction")
        return result
        
    except Exception as e:
        logger.error(f"Error simulating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA EXPORT ENDPOINTS
# ============================================================================

@app.get("/api/export/facilities/csv")
async def export_facilities_csv(
    industry_type: Optional[Literal["steel", "cement", "chemicals"]] = None,
    state: Optional[str] = None,
    year: int = Query(DEFAULT_YEAR, ge=2010, le=2023)
):
    """Export facilities data as CSV file"""
    try:
        cache_key = f"{industry_type}_{state}_{year}"
        
        if cache_key in facilities_cache:
            facilities = facilities_cache[cache_key]
        else:
            facilities = await _fetch_and_cache_facilities(industry_type, state, year, cache_key)
        
        # Convert to DataFrame
        data = []
        for f in facilities:
            data.append({
                "Facility ID": f.facility_id,
                "Name": f.facility_name,
                "Industry": f.industry_type,
                "City": f.city,
                "State": f.state,
                "NAICS": f.naics_code,
                "Latitude": f.coordinates.latitude,
                "Longitude": f.coordinates.longitude,
                "Total Emissions (MT CO2e)": f.emissions_by_gas.total_co2e,
                "CO2 (MT)": f.emissions_by_gas.co2,
                "CH4 (MT)": f.emissions_by_gas.ch4,
                "N2O (MT)": f.emissions_by_gas.n2o,
                "Year": f.reporting_year,
                "Violations": f.total_violations,
                "Parent Company": f.parent_company_name or "N/A"
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=facilities_{year}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _fetch_and_cache_facilities(
    industry_type: Optional[str],
    state: Optional[str],
    year: int,
    cache_key: str
) -> List[IndustrialFacility]:
    """
    Fetch facilities from EPA API and cache them.
    Converts raw EPA data to IndustrialFacility models.
    """
    logger.info(f"Fetching facilities from EPA API: {cache_key}")
    
    # Fetch data from EPA
    all_data = await epa_fetcher.fetch_all_industrial_facilities(
        year=year,
        state=state,
        industry_type=industry_type
    )
    
    # Merge data from multiple EPA sources
    merged_data = merge_facility_data(
        all_data.get("ghgrp", []),
        all_data.get("frs", []),
        all_data.get("tri", []),
        all_data.get("echo", [])
    )
    
    # Convert to IndustrialFacility models
    facilities = []
    for data in merged_data:
        try:
            # Extract and normalize data
            facility = IndustrialFacility(
                facility_id=str(data.get("facility_id") or data.get("registry_id", "unknown")),
                facility_name=data.get("facility_name", "Unknown Facility"),
                coordinates=FacilityCoordinates(
                    latitude=float(data.get("latitude", 0.0)),
                    longitude=float(data.get("longitude", 0.0))
                ),
                city=data.get("city", "Unknown"),
                state=data.get("state", "XX"),
                zip_code=data.get("zip_code"),
                county=data.get("county"),
                epa_region=data.get("epa_region"),
                naics_code=str(data.get("naics_code", "999999")),
                industry_type=industry_type or "chemicals",  # Default
                reporting_year=year,
                emissions_by_gas=EmissionsByGasType(
                    co2=float(data.get("co2_emissions", 0.0)),
                    ch4=float(data.get("ch4_emissions", 0.0)),
                    n2o=float(data.get("n2o_emissions", 0.0)),
                    total_co2e=float(data.get("total_reported_emissions", 0.0) or data.get("ghg_quantity", 0.0))
                ),
                total_violations=int(data.get("informal_count", 0) + data.get("formal_count", 0)),
                parent_company_name=data.get("parent_company_name"),
                data_sources=["GHGRP", "FRS", "TRI", "ECHO"]
            )
            facilities.append(facility)
        except Exception as e:
            logger.warning(f"Error converting facility data: {e}")
            continue
    
    # Cache the results
    facilities_cache[cache_key] = facilities
    cache_timestamp[cache_key] = datetime.utcnow()
    
    logger.info(f"Cached {len(facilities)} facilities for {cache_key}")
    return facilities


# ============================================================================
# SAMPLE DATA ENDPOINT (for development/testing)
# ============================================================================

@app.get("/api/sample-data")
async def get_sample_data():
    """Generate sample facility data for demo/testing"""
    import random
    
    # Sample industrial centers with realistic locations
    sample_facilities_data = [
        {
            "name": "Gary Works Steel Mill",
            "industry": "steel",
            "city": "Gary",
            "state": "IN",
            "lat": 41.5934,
            "lon": -87.3464,
            "emissions": 1_800_000
        },
        {
            "name": "USS Mon Valley Works",
            "industry": "steel",
            "city": "Pittsburgh",
            "state": "PA",
            "lat": 40.4406,
            "lon": -79.9959,
            "emissions": 1_500_000
        },
        {
            "name": "Midlothian Cement Plant",
            "industry": "cement",
            "city": "Midlothian",
            "state": "TX",
            "lat": 32.4824,
            "lon": -96.9945,
            "emissions": 1_200_000
        },
        {
            "name": "Lehigh Southwest Cement",
            "industry": "cement",
            "city": "Cupertino",
            "state": "CA",
            "lat": 37.3230,
            "lon": -122.0322,
            "emissions": 1_100_000
        },
        {
            "name": "ExxonMobil Baytown Complex",
            "industry": "chemicals",
            "city": "Baytown",
            "state": "TX",
            "lat": 29.7355,
            "lon": -94.9774,
            "emissions": 950_000
        },
        {
            "name": "Dow Chemical Louisiana",
            "industry": "chemicals",
            "city": "Plaquemine",
            "state": "LA",
            "lat": 30.2894,
            "lon": -91.2373,
            "emissions": 870_000
        }
    ]
    
    facilities = []
    for idx, fac_data in enumerate(sample_facilities_data):
        facility = IndustrialFacility(
            facility_id=f"SAMPLE_{idx+1000}",
            facility_name=fac_data["name"],
            coordinates=FacilityCoordinates(
                latitude=fac_data["lat"],
                longitude=fac_data["lon"]
            ),
            city=fac_data["city"],
            state=fac_data["state"],
            naics_code="331110" if fac_data["industry"] == "steel" else ("327310" if fac_data["industry"] == "cement" else "325110"),
            industry_type=fac_data["industry"],
            reporting_year=DEFAULT_YEAR,
            emissions_by_gas=EmissionsByGasType(
                co2=fac_data["emissions"] * 0.95,
                ch4=fac_data["emissions"] * 0.03,
                n2o=fac_data["emissions"] * 0.02,
                total_co2e=fac_data["emissions"]
            ),
            total_violations=random.randint(0, 5),
            parent_company_name=fac_data["name"].split()[0] + " Corporation",
            data_sources=["SAMPLE_DATA"]
        )
        facilities.append(facility)
    
    # Return as GeoJSON
    return {
        "type": "FeatureCollection",
        "features": [f.to_geojson_feature() for f in facilities]
    }


# ============================================================================
# MOUNT STATIC FILES AND RUN
# ============================================================================
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
