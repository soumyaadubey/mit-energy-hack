"""
Smart Grid Siting Framework API

FastAPI application for optimal siting of electro-intensive loads.
Provides endpoints for grid node data, siting evaluation, and scenario comparison.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Literal
import logging
import os

# Import grid siting modules
from models import (
    GridNode,
    SitingWeights,
    SitingRequest,
    SiteEvaluation,
    ScenarioComparison,
    GeoJSONResponse,
    DemandProfile,
    PowerPlant,
    PowerPlantFilters,
    LocationEvaluationRequest,
    GridNodeCoordinates
)
from grid_data import (
    generate_mock_grid_nodes,
    get_node_by_id,
    generate_grid_nodes_with_real_scores
)
from siting_engine import SitingEngine
from power_plants_data import (
    get_all_power_plants,
    filter_power_plants,
    power_plants_to_geojson,
    get_fuel_category_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Smart Grid Siting Framework",
    description="Intelligent siting framework for large electro-intensive loads to optimize grid integration",
    version="1.0.0"
)

# Add CORS middleware (hackathon mode)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

# Initialize services
siting_engine = SitingEngine()

# Energy sources and grid nodes (loaded at startup)
energy_sources = []  # Will be populated by load_energy_sources()
grid_nodes = []  # Will be populated with real scores if energy sources loaded
power_plants = []  # Will be populated by load_power_plants()

# Scenarios storage (in-memory for demo)
saved_scenarios: List[SiteEvaluation] = []


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the map view (home page)"""
    try:
        return FileResponse("static/map.html")
    except FileNotFoundError:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Smart Grid Siting Framework</title></head>
        <body>
            <h1>Smart Grid Siting Framework</h1>
            <p>Map view not found. Please ensure static/map.html exists.</p>
            <p><a href="/framework">Go to Siting Framework →</a></p>
        </body>
        </html>
        """)


@app.get("/framework", response_class=HTMLResponse)
async def framework_page():
    """Serve the siting framework (optimization page)"""
    try:
        return FileResponse("static/framework.html")
    except FileNotFoundError:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Siting Framework</title></head>
        <body>
            <h1>Siting Framework</h1>
            <p>Framework page not found. Please ensure static/framework.html exists.</p>
            <p><a href="/">← Back to Map View</a></p>
        </body>
        </html>
        """)


@app.on_event("startup")
async def startup_event():
    """Load energy sources, power plants, and initialize grid nodes on startup"""
    global energy_sources, grid_nodes, power_plants
    
    logger.info("=== Smart Grid Siting Framework Startup ===")
    
    # Load energy sources for clean gen scoring
    try:
        from energy_sources import load_energy_sources
        
        logger.info("Loading energy sources from JSON...")
        energy_sources = load_energy_sources()
        logger.info(f"Successfully loaded {len(energy_sources)} energy sources")
        
    except FileNotFoundError as e:
        logger.warning(f"Energy sources file not found: {e}")
        logger.info("Will use mock clean gen scores")
        energy_sources = []
    except ImportError as e:
        logger.warning(f"Failed to import energy_sources module: {e}")
        logger.info("Will use mock clean gen scores")
        energy_sources = []
    except Exception as e:
        logger.error(f"Error loading energy sources: {e}")
        logger.info("Will use mock clean gen scores")
        energy_sources = []
    
    # Load US power plants for transmission scoring
    try:
        logger.info("Loading US power plants from eGRID data...")
        power_plants = get_all_power_plants()
        logger.info(f"Successfully loaded {len(power_plants)} power plants")
        
        # Show quick stats
        stats = get_fuel_category_stats(power_plants)
        renewable_count = sum(p.is_renewable() for p in power_plants)
        clean_count = sum(p.is_clean() for p in power_plants)
        logger.info(f"  Clean energy: {clean_count} plants ({clean_count/len(power_plants)*100:.1f}%)")
        logger.info(f"  All plants: {len(power_plants)} (will be used for transmission scoring)")
        
    except FileNotFoundError as e:
        logger.warning(f"Power plants file not found: {e}")
        logger.info("Will use mock transmission scores")
        power_plants = []
    except Exception as e:
        logger.error(f"Error loading power plants: {e}")
        logger.info("Will use mock transmission scores")
        power_plants = []
    
    # Generate grid nodes with real scores (clean_gen + transmission_headroom)
    try:
        logger.info("Generating grid nodes with real scores...")
        grid_nodes = generate_grid_nodes_with_real_scores(
            energy_sources=energy_sources if energy_sources else None,
            power_plants=power_plants if power_plants else None
        )
        logger.info(f"Generated {len(grid_nodes)} grid nodes")
        
        if energy_sources:
            logger.info("  ✓ Using real clean_gen scores from energy sources")
        else:
            logger.info("  ✗ Using mock clean_gen scores")
            
        if power_plants:
            logger.info("  ✓ Using real transmission_headroom scores from power plants")
        else:
            logger.info("  ✗ Using mock transmission_headroom scores")
            
    except Exception as e:
        logger.error(f"Error generating grid nodes: {e}")
        logger.info("Falling back to mock grid nodes")
        grid_nodes = generate_mock_grid_nodes()
    
    logger.info(f"Startup complete: {len(grid_nodes)} nodes, {len(energy_sources)} energy sources, {len(power_plants)} power plants")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "smart-grid-siting",
        "version": "1.0.0",
        "nodes_loaded": len(grid_nodes),
        "energy_sources_loaded": len(energy_sources),
        "power_plants_loaded": len(power_plants),
        "using_real_clean_gen": len(energy_sources) > 0,
        "using_real_transmission": len(power_plants) > 0
    }


@app.get("/api/config")
async def get_config():
    """Get client configuration"""
    return {
        "mapbox_token": MAPBOX_TOKEN,
        "default_center": [-98.5795, 39.8283],  # Geographic center of continental US
        "default_zoom": 4,
        "default_weights": {
            "clean": 0.4,
            "transmission": 0.3,
            "reliability": 0.3
        },
        "demand_types": ["data_center", "electrolyzer", "ev_hub", "hydrogen_plant", "ai_compute"]
    }


# ============================================================================
# GRID DATA ENDPOINTS
# ============================================================================

@app.get("/api/grid/nodes")
async def get_grid_nodes(
    region: Optional[str] = None,
    state: Optional[str] = None,
    min_clean_gen: Optional[float] = Query(None, ge=0, le=100),
    min_transmission: Optional[float] = Query(None, ge=0, le=100),
    min_reliability: Optional[float] = Query(None, ge=0, le=100)
):
    """
    Get grid nodes with optional filters.
    
    Returns list of grid nodes with metadata.
    """
    nodes = grid_nodes
    
    # Apply filters
    if region:
        nodes = [n for n in nodes if n.region == region]
    
    if state:
        nodes = [n for n in nodes if n.state == state]
    
    if min_clean_gen is not None:
        nodes = [n for n in nodes if n.clean_gen >= min_clean_gen]
    
    if min_transmission is not None:
        nodes = [n for n in nodes if n.transmission_headroom >= min_transmission]
    
    if min_reliability is not None:
        nodes = [n for n in nodes if n.reliability >= min_reliability]
    
    return {
        "nodes": [n.dict() for n in nodes],
        "total": len(nodes),
        "filters_applied": {
            "region": region,
            "state": state,
            "min_clean_gen": min_clean_gen,
            "min_transmission": min_transmission,
            "min_reliability": min_reliability
        }
    }


@app.get("/api/grid/nodes/geojson")
async def get_grid_nodes_geojson(
    region: Optional[str] = None,
    state: Optional[str] = None
):
    """
    Get grid nodes as GeoJSON FeatureCollection for Mapbox.
    
    Optimized for map rendering with essential properties only.
    """
    nodes = grid_nodes
    
    # Apply filters
    if region:
        nodes = [n for n in nodes if n.region == region]
    
    if state:
        nodes = [n for n in nodes if n.state == state]
    
    # Convert to GeoJSON
    features = [n.to_geojson_feature() for n in nodes]
    
    return GeoJSONResponse(
        features=features,
        metadata={
            "total_nodes": len(features),
            "region_filter": region,
            "state_filter": state
        }
    )


@app.get("/api/grid/nodes/{node_id}")
async def get_grid_node(node_id: int):
    """
    Get detailed information for a specific grid node.
    """
    try:
        node = get_node_by_id(node_id)
        return {"node": node.dict()}
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Grid node {node_id} not found")


@app.get("/api/grid/regions")
async def get_regions():
    """Get list of available regions"""
    regions = list(set(n.region for n in grid_nodes if n.region))
    return {
        "regions": sorted(regions),
        "total": len(regions)
    }


@app.get("/api/grid/states")
async def get_states():
    """Get list of available states"""
    states = list(set(n.state for n in grid_nodes if n.state))
    return {
        "states": sorted(states),
        "total": len(states)
    }


# ============================================================================
# POWER PLANTS ENDPOINTS
# ============================================================================

@app.get("/api/power-plants")
async def get_power_plants(
    fuel_category: Optional[str] = Query(None, description="Filter by fuel category (e.g., SOLAR, WIND)"),
    min_capacity_mw: float = Query(0, ge=0, description="Minimum nameplate capacity"),
    max_capacity_mw: float = Query(10000, ge=0, description="Maximum nameplate capacity"),
    renewable_only: bool = Query(False, description="Only renewable sources"),
    clean_only: bool = Query(False, description="Only clean energy (renewable + nuclear)"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Limit number of results")
):
    """
    Get power plants with optional filters.
    
    Returns list of power plants with metadata.
    Performance tip: Use renewable_only or clean_only filters to reduce dataset size.
    """
    if not power_plants:
        raise HTTPException(status_code=503, detail="Power plant data not available")
    
    # Apply filters
    filtered = filter_power_plants(
        power_plants,
        fuel_category=fuel_category,
        min_capacity_mw=min_capacity_mw,
        max_capacity_mw=max_capacity_mw,
        renewable_only=renewable_only,
        clean_only=clean_only
    )
    
    # Apply limit
    if limit:
        filtered = filtered[:limit]
    
    return {
        "plants": [p.dict() for p in filtered],
        "total": len(filtered),
        "total_capacity_mw": round(sum(p.nameplate_mw for p in filtered), 1),
        "filters_applied": {
            "fuel_category": fuel_category,
            "min_capacity_mw": min_capacity_mw,
            "max_capacity_mw": max_capacity_mw,
            "renewable_only": renewable_only,
            "clean_only": clean_only,
            "limit": limit
        }
    }


@app.get("/api/power-plants/geojson")
async def get_power_plants_geojson(
    fuel_category: Optional[List[str]] = Query(None, description="Filter by fuel categories (can specify multiple)"),
    min_capacity_mw: float = Query(0, ge=0),
    max_capacity_mw: float = Query(10000, ge=0),
    renewable_only: bool = Query(False),
    clean_only: bool = Query(False)
):
    """
    Get power plants as GeoJSON FeatureCollection for Mapbox.
    
    Optimized for map rendering with clustering support.
    Use filters to reduce dataset size for better performance.
    """
    if not power_plants:
        raise HTTPException(status_code=503, detail="Power plant data not available")
    
    # Apply filters
    filtered = filter_power_plants(
        power_plants,
        fuel_categories=fuel_category,
        min_capacity_mw=min_capacity_mw,
        max_capacity_mw=max_capacity_mw,
        renewable_only=renewable_only,
        clean_only=clean_only
    )
    
    # Convert to GeoJSON with metadata
    geojson = power_plants_to_geojson(filtered, include_metadata=True)
    
    return geojson


@app.get("/api/power-plants/stats")
async def get_power_plants_stats():
    """
    Get statistics about power plants by fuel category.
    
    Returns counts, total capacity, and total generation by fuel type.
    """
    if not power_plants:
        raise HTTPException(status_code=503, detail="Power plant data not available")
    
    stats = get_fuel_category_stats(power_plants)
    
    # Calculate totals
    total_plants = len(power_plants)
    renewable_count = sum(p.is_renewable() for p in power_plants)
    clean_count = sum(p.is_clean() for p in power_plants)
    
    return {
        "total_plants": total_plants,
        "renewable_count": renewable_count,
        "renewable_percentage": round(renewable_count / total_plants * 100, 1),
        "clean_count": clean_count,
        "clean_percentage": round(clean_count / total_plants * 100, 1),
        "by_fuel_category": stats
    }


@app.get("/api/power-plants/fuel-categories")
async def get_fuel_categories():
    """
    Get list of available fuel categories with colors.
    
    Useful for building filter UI and legend.
    """
    if not power_plants:
        raise HTTPException(status_code=503, detail="Power plant data not available")
    
    from models import get_fuel_category_color, get_fuel_category_icon
    
    # Get unique categories
    categories = list(set(p.primary_fuel_category for p in power_plants))
    
    # Build response with colors and counts
    result = []
    for category in sorted(categories):
        count = sum(1 for p in power_plants if p.primary_fuel_category == category)
        total_capacity = sum(p.nameplate_mw for p in power_plants if p.primary_fuel_category == category)
        
        result.append({
            "category": category,
            "color": get_fuel_category_color(category),
            "icon": get_fuel_category_icon(category),
            "count": count,
            "total_capacity_mw": round(total_capacity, 1)
        })
    
    return {
        "fuel_categories": result,
        "total": len(result)
    }


# ============================================================================
# SITING EVALUATION ENDPOINTS
# ============================================================================

@app.post("/api/siting/evaluate")
async def evaluate_site(request: SitingRequest) -> SiteEvaluation:
    """
    Evaluate a site with custom criteria weights.
    
    Calculates composite siting score and provides ranking context.
    """
    try:
        # Get the node
        node = get_node_by_id(request.site_id)
        
        # Convert request to weights and demand profile
        weights = request.to_weights()
        demand_profile = request.to_demand_profile()
        
        # Evaluate the site
        evaluation = siting_engine.evaluate_site(
            node=node,
            weights=weights,
            demand_profile=demand_profile,
            all_nodes=grid_nodes,
            power_plants=power_plants
        )
        
        logger.info(
            f"Evaluated site {request.site_id} ({node.name}): "
            f"score={evaluation.score_breakdown.composite_score:.1f}"
        )
        
        return evaluation
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error evaluating site: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/siting/evaluate-location")
async def evaluate_location(request: LocationEvaluationRequest):
    """
    Evaluate an arbitrary location by lat/lon coordinates.
    
    Dynamically calculates siting scores based on proximity to:
    - Clean energy sources (clean_gen score)
    - Power infrastructure (transmission_headroom score)
    - Grid reliability indicators (reliability score)
    
    This endpoint enables click-anywhere map evaluation without predefined grid nodes.
    """
    try:
        # Convert request to weights and demand profile
        weights = request.to_weights()
        demand_profile = request.to_demand_profile()
        
        # Calculate scores dynamically from coordinates
        score_breakdown = siting_engine.calculate_scores_from_coordinates(
            latitude=request.latitude,
            longitude=request.longitude,
            energy_sources=energy_sources,
            power_plants=power_plants,
            weights=weights,
            demand_profile=demand_profile  # Pass demand for capacity adequacy
        )
        
        # Create a temporary GridNode for the clicked location
        location_name = request.location_name or f"Location ({request.latitude:.3f}, {request.longitude:.3f})"
        temp_node = GridNode(
            id=-1,  # Special ID for dynamic locations
            name=location_name,
            coordinates=GridNodeCoordinates(
                latitude=request.latitude,
                longitude=request.longitude
            ),
            clean_gen=score_breakdown.clean_gen_score,
            transmission_headroom=score_breakdown.transmission_score,
            reliability=score_breakdown.reliability_score,
            region="Custom Location",
            state=None,
            balancing_authority=None,
            nearby_projects=[],
            transmission_lines=[]
        )
        
        # Find nearby power plants for context
        nearby_power_plants = []
        logger.info(f"Power plants available: {len(power_plants) if power_plants else 0}")
        
        if not power_plants:
            logger.error("No power plants loaded! This should not happen after startup.")
            # Still return evaluation, but with empty nearby plants
        elif len(power_plants) > 0:
            logger.info(f"Finding nearby power plants for location ({request.latitude:.3f}, {request.longitude:.3f}). Total plants available: {len(power_plants)}")
            try:
                nearby_power_plants = siting_engine._find_nearby_power_plants(
                    request.latitude,
                    request.longitude,
                    power_plants
                )
                logger.info(f"Successfully found {len(nearby_power_plants)} nearby power plants")
            except Exception as e:
                logger.error(f"Error finding nearby power plants: {e}", exc_info=True)
                # Continue with empty list
                nearby_power_plants = []
        else:
            logger.warning("Power plants list is empty!")
        
        # Generate evaluation notes
        notes = siting_engine._generate_evaluation_notes(temp_node, score_breakdown)
        
        # Create evaluation response
        evaluation = SiteEvaluation(
            site=temp_node,
            weights=weights,
            demand_profile=demand_profile,
            score_breakdown=score_breakdown,
            percentile_rank=None,  # Can't rank against grid nodes for custom location
            alternative_sites=[],
            nearby_power_plants=nearby_power_plants,
            evaluation_notes=notes
        )
        
        logger.info(
            f"Evaluated custom location ({request.latitude:.3f}, {request.longitude:.3f}): "
            f"score={score_breakdown.composite_score:.1f}"
        )
        
        return evaluation
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error evaluating location: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/siting/alternatives")
async def get_alternative_sites(
    site_id: int,
    weight_clean: float = Query(0.4, ge=0, le=1),
    weight_transmission: float = Query(0.3, ge=0, le=1),
    weight_reliability: float = Query(0.3, ge=0, le=1),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Get top N alternative sites ranked by composite score.
    
    Uses same weights as reference site for fair comparison.
    """
    try:
        # Validate weights
        weights = SitingWeights(
            weight_clean=weight_clean,
            weight_transmission=weight_transmission,
            weight_reliability=weight_reliability
        )
        weights.validate_sum()
        
        # Get reference node
        reference_node = get_node_by_id(site_id)
        
        # Rank all sites
        ranked = siting_engine.rank_sites(grid_nodes, weights)
        
        # Filter out reference site and take top N
        alternatives = [
            {
                "id": node.id,
                "name": node.name,
                "composite_score": score,
                "clean_gen": node.clean_gen,
                "transmission_headroom": node.transmission_headroom,
                "reliability": node.reliability,
                "region": node.region,
                "state": node.state
            }
            for node, score in ranked
            if node.id != site_id
        ][:limit]
        
        return {
            "reference_site_id": site_id,
            "reference_site_name": reference_node.name,
            "alternatives": alternatives,
            "weights_used": weights.dict()
        }
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting alternatives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/siting/rankings")
async def get_site_rankings(
    weight_clean: float = Query(0.4, ge=0, le=1),
    weight_transmission: float = Query(0.3, ge=0, le=1),
    weight_reliability: float = Query(0.3, ge=0, le=1),
    limit: Optional[int] = Query(None, ge=1, le=50)
):
    """
    Get all sites ranked by composite score.
    
    Useful for showing best overall sites across the country.
    """
    try:
        # Validate weights
        weights = SitingWeights(
            weight_clean=weight_clean,
            weight_transmission=weight_transmission,
            weight_reliability=weight_reliability
        )
        weights.validate_sum()
        
        # Rank all sites
        ranked = siting_engine.rank_sites(grid_nodes, weights)
        
        # Format results
        rankings = [
            {
                "rank": i + 1,
                "id": node.id,
                "name": node.name,
                "composite_score": score,
                "clean_gen": node.clean_gen,
                "transmission_headroom": node.transmission_headroom,
                "reliability": node.reliability,
                "region": node.region,
                "state": node.state
            }
            for i, (node, score) in enumerate(ranked[:limit] if limit else ranked)
        ]
        
        return {
            "rankings": rankings,
            "total_sites": len(grid_nodes),
            "weights_used": weights.dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error ranking sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SCENARIO MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/siting/scenarios/save")
async def save_scenario(evaluation: SiteEvaluation):
    """
    Save a site evaluation for later comparison.
    
    Stores evaluation in memory (for demo; use DB in production).
    """
    saved_scenarios.append(evaluation)
    
    logger.info(
        f"Saved scenario for site {evaluation.site.id} "
        f"(score={evaluation.score_breakdown.composite_score:.1f})"
    )
    
    return {
        "status": "saved",
        "scenario_id": len(saved_scenarios) - 1,
        "total_saved": len(saved_scenarios)
    }


@app.get("/api/siting/scenarios")
async def get_saved_scenarios():
    """Get all saved scenarios"""
    return {
        "scenarios": [s.dict() for s in saved_scenarios],
        "total": len(saved_scenarios)
    }


@app.post("/api/siting/scenarios/compare")
async def compare_scenarios(
    scenario_ids: List[int],
    scenario_name: str = "Comparison"
):
    """
    Compare multiple saved scenarios.
    
    Returns comparison with best site and delta analysis.
    """
    if not scenario_ids:
        raise HTTPException(status_code=400, detail="Must provide at least one scenario ID")
    
    # Validate IDs
    if any(sid >= len(saved_scenarios) or sid < 0 for sid in scenario_ids):
        raise HTTPException(status_code=404, detail="Invalid scenario ID")
    
    # Get evaluations
    evaluations = [saved_scenarios[sid] for sid in scenario_ids]
    
    # Compare
    comparison = siting_engine.compare_scenarios(evaluations, scenario_name)
    
    return comparison.dict()


@app.delete("/api/siting/scenarios/clear")
async def clear_saved_scenarios():
    """Clear all saved scenarios"""
    global saved_scenarios
    count = len(saved_scenarios)
    saved_scenarios = []
    
    return {
        "status": "cleared",
        "scenarios_deleted": count
    }


# ============================================================================
# ENERGY SOURCE ENDPOINTS
# ============================================================================

@app.get("/api/energy-sources")
async def get_energy_sources(
    energy_type: Optional[str] = Query(None, description="Filter by energy type (solar, wind, etc.)"),
    min_capacity: Optional[float] = Query(None, ge=0, description="Minimum capacity in MW"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit number of results")
):
    """
    Get all loaded energy sources.
    
    Returns energy project data with coordinates and capacity.
    """
    filtered_sources = energy_sources.copy()
    
    # Filter by energy type
    if energy_type:
        filtered_sources = [
            s for s in filtered_sources
            if s.energy_source.lower() == energy_type.lower()
        ]
    
    # Filter by minimum capacity
    if min_capacity is not None:
        filtered_sources = [
            s for s in filtered_sources
            if s.ppa_capacity_mw >= min_capacity
        ]
    
    # Limit results
    if limit:
        filtered_sources = filtered_sources[:limit]
    
    return {
        "sources": [
            {
                "name": s.name,
                "energy_source": s.energy_source,
                "capacity_mw": s.ppa_capacity_mw,
                "address": s.address,
                "coordinates": {
                    "latitude": s.coordinates.latitude,
                    "longitude": s.coordinates.longitude
                } if s.coordinates else None,
                "clean_multiplier": s.get_clean_multiplier()
            }
            for s in filtered_sources
        ],
        "total": len(filtered_sources),
        "total_capacity_mw": sum(s.ppa_capacity_mw for s in filtered_sources),
        "filters_applied": {
            "energy_type": energy_type,
            "min_capacity": min_capacity,
            "limit": limit
        }
    }


@app.get("/api/energy-sources/geojson")
async def get_energy_sources_geojson():
    """
    Get energy sources as GeoJSON FeatureCollection for map visualization.
    """
    features = []
    
    # Hardcoded energy source coordinates (pre-geocoded)
    hardcoded_sources = [
        {"name": "360 Solar", "address": "21501 Hull Street Road, Mosley, VA", "lat": 37.4019, "lon": -77.5311, "capacity": 52, "type": "Solar"},
        {"name": "Wythe County", "address": "Foster Falls Road, Suffolk, VA", "lat": 36.9204, "lon": -76.5833, "capacity": 52, "type": "Solar"},
        {"name": "Waterloo Solar", "address": "Bastrop County, Texas", "lat": 30.0000, "lon": -97.1167, "capacity": 52, "type": "Solar"},
        {"name": "Switchgrass", "address": "Hoosier Road, Suffolk, VA", "lat": 36.7286, "lon": -76.5833, "capacity": 52, "type": "Solar"},
        {"name": "Lafitte Solar Park", "address": "343 McHenry Gin Rd., Monroe, LA 71202", "lat": 32.5093, "lon": -92.1221, "capacity": 52, "type": "Solar"},
        {"name": "Harrisonburg", "address": "3793 Kratzer Road, Harrisonburg, VA", "lat": 38.4496, "lon": -78.8689, "capacity": 52, "type": "Solar"},
        {"name": "Groves", "address": "Westmoreland County, VA", "lat": 38.0293, "lon": -76.8803, "capacity": 52, "type": "Solar"},
        {"name": "Bluestem", "address": "LaPorte County, Indiana", "lat": 41.6094, "lon": -86.7326, "capacity": 52, "type": "Battery Storage + Solar"},
        {"name": "Big Pine", "address": "Sussex County, Virginia", "lat": 36.8468, "lon": -77.2803, "capacity": 52, "type": "Solar"},
    ]
    
    # If energy sources loaded from file
    if energy_sources:
        for source in energy_sources:
            if source.coordinates:  # Only include geocoded sources
                try:
                    features.append(source.to_geojson_feature())
                except Exception as e:
                    logger.warning(f"Failed to convert {source.name} to GeoJSON: {e}")
    
    # Fallback: Use hardcoded coordinates if no sources loaded
    if not features:
        logger.info("Using hardcoded energy source coordinates")
        
        for source in hardcoded_sources:
            features.append({
                "type": "Feature",
                "properties": {
                    "name": source["name"],
                    "energy_source": source["type"],
                    "capacity_mw": source["capacity"],
                    "address": source["address"],
                    "clean_multiplier": 1.0 if "solar" in source["type"].lower() else 0.95,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [source["lon"], source["lat"]]  # [longitude, latitude]
                }
            })
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_sources": len(hardcoded_sources),
            "geocoded_sources": len(features),
            "total_capacity_mw": sum(f["properties"]["capacity_mw"] for f in features) if features else 468
        }
    }


@app.get("/api/energy-sources/stats")
async def get_energy_source_stats():
    """Get statistics about loaded energy sources"""
    if not energy_sources:
        return {
            "total_sources": 0,
            "total_capacity_mw": 0,
            "by_type": {},
            "geocoded_count": 0,
            "using_real_scores": False
        }
    
    # Count by energy type
    by_type = {}
    for source in energy_sources:
        energy_type = source.energy_source
        if energy_type not in by_type:
            by_type[energy_type] = {"count": 0, "capacity_mw": 0}
        by_type[energy_type]["count"] += 1
        by_type[energy_type]["capacity_mw"] += source.ppa_capacity_mw
    
    geocoded_count = sum(1 for s in energy_sources if s.coordinates is not None)
    
    return {
        "total_sources": len(energy_sources),
        "total_capacity_mw": sum(s.ppa_capacity_mw for s in energy_sources),
        "by_type": by_type,
        "geocoded_count": geocoded_count,
        "geocoding_rate": f"{(geocoded_count / len(energy_sources) * 100):.1f}%" if energy_sources else "0%",
        "using_real_scores": len(energy_sources) > 0
    }


@app.post("/api/energy-sources/reload")
async def reload_energy_sources():
    """
    Reload energy sources from JSON and recalculate grid node scores.
    
    Useful for updating data without restarting the server.
    """
    global energy_sources, grid_nodes
    
    try:
        from energy_sources import load_energy_sources
        
        logger.info("Reloading energy sources and power plants...")
        energy_sources = load_energy_sources()
        logger.info(f"Reloaded {len(energy_sources)} energy sources")
        
        # Reload power plants
        power_plants = get_all_power_plants(reload=True)
        logger.info(f"Reloaded {len(power_plants)} power plants")
        
        # Recalculate grid node scores (both clean_gen and transmission)
        logger.info("Recalculating grid node scores (clean_gen + transmission)...")
        grid_nodes = generate_grid_nodes_with_real_scores(
            energy_sources=energy_sources,
            power_plants=power_plants
        )
        logger.info(f"Updated {len(grid_nodes)} grid nodes")
        
        return {
            "status": "success",
            "energy_sources_loaded": len(energy_sources),
            "power_plants_loaded": len(power_plants),
            "grid_nodes_updated": len(grid_nodes),
            "message": "Data reloaded and grid scores recalculated (clean_gen + transmission)"
        }
        
    except Exception as e:
        logger.error(f"Failed to reload data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload data: {str(e)}"
        )


@app.get("/api/grid/nodes/{node_id}/nearby-sources")
async def get_nearby_sources_for_node(
    node_id: int,
    max_distance_km: float = Query(300.0, ge=0, le=1000, description="Maximum distance in km"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of sources to return")
):
    """
    Get energy sources near a specific grid node.
    
    Returns sources sorted by distance.
    """
    # Get the node
    try:
        node = get_node_by_id(node_id, grid_nodes)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Grid node {node_id} not found")
    
    if not energy_sources:
        return {
            "node_id": node_id,
            "node_name": node.name,
            "nearby_sources": [],
            "total": 0,
            "message": "No energy sources loaded"
        }
    
    try:
        from scoring_utils import find_nearby_sources
        
        # Prepare source data
        source_data = [
            (
                s.name,
                s.coordinates.latitude,
                s.coordinates.longitude,
                s.ppa_capacity_mw,
                s.energy_source
            )
            for s in energy_sources
            if s.coordinates is not None
        ]
        
        # Find nearby sources
        nearby = find_nearby_sources(
            node.coordinates.latitude,
            node.coordinates.longitude,
            source_data,
            max_distance_km=max_distance_km,
            limit=limit
        )
        
        return {
            "node_id": node_id,
            "node_name": node.name,
            "node_coordinates": {
                "latitude": node.coordinates.latitude,
                "longitude": node.coordinates.longitude
            },
            "nearby_sources": nearby,
            "total": len(nearby),
            "search_params": {
                "max_distance_km": max_distance_km,
                "limit": limit
            }
        }
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Scoring utilities not available"
        )


# ============================================================================
# MOUNT STATIC FILES AND RUN
# ============================================================================

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
