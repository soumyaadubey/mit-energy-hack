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
from models_grid import (
    GridNode,
    SitingWeights,
    SitingRequest,
    SiteEvaluation,
    ScenarioComparison,
    GeoJSONResponse,
    DemandProfile
)
from grid_data import generate_mock_grid_nodes, get_node_by_id
from siting_engine import SitingEngine

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
grid_nodes = generate_mock_grid_nodes()  # Cache in memory

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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "smart-grid-siting",
        "version": "1.0.0",
        "nodes_loaded": len(grid_nodes)
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
            all_nodes=grid_nodes
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
# MOUNT STATIC FILES AND RUN
# ============================================================================

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
