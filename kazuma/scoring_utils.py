"""
Scoring Utilities for Smart Grid Siting Framework

Provides distance calculation and proximity-based scoring functions
for evaluating clean generation access at grid nodes.

Uses Pythagorean distance approximation for speed and simplicity.
"""

import math
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Distance thresholds for proximity scoring (in km)
DISTANCE_EXCELLENT = 50   # < 50km = full credit
DISTANCE_GOOD = 100       # < 100km = 70% credit
DISTANCE_MODERATE = 200   # < 200km = 40% credit
DISTANCE_FAIR = 300       # < 300km = 20% credit
# > 300km = 0% credit

# Transmission infrastructure distance zones (in km)
# Based on typical transmission voltage capabilities and economics
TRANSMISSION_LOCAL = 50       # < 50km = local distribution/sub-transmission
TRANSMISSION_REGIONAL = 150   # < 150km = regional 230-345kV transmission
TRANSMISSION_BULK = 300       # < 300km = bulk 500-765kV transmission
TRANSMISSION_LONG = 500       # < 500km = long-distance HVDC/EHV lines
# > 500km = minimal transmission value for siting


def pythagorean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate approximate distance between two points using Pythagorean theorem.
    
    Converts lat/lon differences to kilometers using approximation:
    - 1 degree latitude ≈ 111 km
    - 1 degree longitude ≈ 111 km * cos(latitude)
    
    Faster than Haversine and sufficiently accurate for distances < 1000 km.
    
    Args:
        lat1, lon1: Latitude and longitude of first point (degrees)
        lat2, lon2: Latitude and longitude of second point (degrees)
    
    Returns:
        Distance in kilometers (approximate)
    """
    # Average latitude for longitude correction
    avg_lat = (lat1 + lat2) / 2.0
    
    # Convert lat/lon differences to km
    # 1 degree latitude ≈ 111 km everywhere
    lat_diff_km = (lat2 - lat1) * 111.0
    
    # 1 degree longitude ≈ 111 km * cos(latitude)
    lon_diff_km = (lon2 - lon1) * 111.0 * math.cos(math.radians(avg_lat))
    
    # Pythagorean theorem: distance = sqrt(x² + y²)
    distance = math.sqrt(lat_diff_km**2 + lon_diff_km**2)
    
    return distance


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points on Earth using Haversine formula.
    
    DEPRECATED: Use pythagorean_distance() for better performance.
    Kept for backward compatibility.
    
    Args:
        lat1, lon1: Latitude and longitude of first point (degrees)
        lat2, lon2: Latitude and longitude of second point (degrees)
    
    Returns:
        Distance in kilometers
    """
    # Just call pythagorean_distance for simplicity
    return pythagorean_distance(lat1, lon1, lat2, lon2)


def proximity_decay_factor(distance_km: float) -> float:
    """
    Calculate proximity decay factor for clean gen scoring.
    
    Closer energy sources contribute more to the clean generation score.
    Uses stepped decay function with smooth transitions.
    
    Args:
        distance_km: Distance from grid node to energy source
    
    Returns:
        Decay factor between 0.0 (far/no contribution) and 1.0 (very close/full contribution)
    """
    if distance_km < DISTANCE_EXCELLENT:
        # Within 50km: Full credit
        return 1.0
    elif distance_km < DISTANCE_GOOD:
        # 50-100km: Linear decay from 1.0 to 0.7
        return 1.0 - (distance_km - DISTANCE_EXCELLENT) / (DISTANCE_GOOD - DISTANCE_EXCELLENT) * 0.3
    elif distance_km < DISTANCE_MODERATE:
        # 100-200km: Linear decay from 0.7 to 0.4
        return 0.7 - (distance_km - DISTANCE_GOOD) / (DISTANCE_MODERATE - DISTANCE_GOOD) * 0.3
    elif distance_km < DISTANCE_FAIR:
        # 200-300km: Linear decay from 0.4 to 0.2
        return 0.4 - (distance_km - DISTANCE_MODERATE) / (DISTANCE_FAIR - DISTANCE_MODERATE) * 0.2
    else:
        # Beyond 300km: No contribution
        return 0.0


def transmission_decay_factor(distance_km: float, plant_capacity_mw: float) -> float:
    """
    Calculate transmission infrastructure decay factor.
    
    Transmission value depends on:
    1. Distance - closer plants = better existing infrastructure
    2. Plant size - larger plants = higher voltage transmission (longer economical distance)
    
    Large plants (>500 MW) typically connect to 345-765kV lines (economical to 300+ km)
    Medium plants (100-500 MW) connect to 230-345kV lines (economical to 150 km)
    Small plants (<100 MW) connect to 115-230kV lines (economical to 50 km)
    
    Args:
        distance_km: Distance from grid node to power plant
        plant_capacity_mw: Nameplate capacity of the plant
    
    Returns:
        Decay factor between 0.0 (no transmission value) and 1.0 (excellent transmission access)
    """
    # Determine plant size category for transmission voltage estimation
    if plant_capacity_mw >= 500:
        # Large plant: likely 500-765kV transmission (300km economic range)
        max_range = TRANSMISSION_BULK
        decay_curve = "gentle"  # High-voltage lines are economical over long distances
    elif plant_capacity_mw >= 100:
        # Medium plant: likely 230-345kV transmission (150km economic range)
        max_range = TRANSMISSION_REGIONAL
        decay_curve = "moderate"
    else:
        # Small plant: likely 115-230kV transmission (50km economic range)
        max_range = TRANSMISSION_LOCAL
        decay_curve = "steep"
    
    # Beyond max range for this voltage class: minimal value
    if distance_km > max_range:
        # Very small credit for very large plants even beyond range
        if plant_capacity_mw >= 1000 and distance_km < TRANSMISSION_LONG:
            # Super-large plants (1+ GW) might justify HVDC to 500km
            return 0.1 - (distance_km - max_range) / (TRANSMISSION_LONG - max_range) * 0.1
        else:
            return 0.0
    
    # Calculate base proximity factor
    if distance_km < TRANSMISSION_LOCAL:
        # Within 50km: Excellent access regardless of plant size
        base_factor = 1.0
    elif distance_km < TRANSMISSION_REGIONAL:
        # 50-150km: Decay based on voltage class
        if decay_curve == "steep":
            # Small plants: rapid decay
            base_factor = 1.0 - (distance_km - TRANSMISSION_LOCAL) / (TRANSMISSION_REGIONAL - TRANSMISSION_LOCAL) * 0.7
        elif decay_curve == "moderate":
            # Medium plants: moderate decay
            base_factor = 1.0 - (distance_km - TRANSMISSION_LOCAL) / (TRANSMISSION_REGIONAL - TRANSMISSION_LOCAL) * 0.4
        else:  # gentle
            # Large plants: gentle decay
            base_factor = 1.0 - (distance_km - TRANSMISSION_LOCAL) / (TRANSMISSION_REGIONAL - TRANSMISSION_LOCAL) * 0.2
    elif distance_km < TRANSMISSION_BULK:
        # 150-300km: Only medium/large plants have good access
        if decay_curve == "steep":
            # Small plants: minimal value
            base_factor = 0.3 - (distance_km - TRANSMISSION_REGIONAL) / (TRANSMISSION_BULK - TRANSMISSION_REGIONAL) * 0.3
        elif decay_curve == "moderate":
            # Medium plants: significant decay
            base_factor = 0.6 - (distance_km - TRANSMISSION_REGIONAL) / (TRANSMISSION_BULK - TRANSMISSION_REGIONAL) * 0.4
        else:  # gentle
            # Large plants: modest decay
            base_factor = 0.8 - (distance_km - TRANSMISSION_REGIONAL) / (TRANSMISSION_BULK - TRANSMISSION_REGIONAL) * 0.3
    else:
        # 300-500km: Only very large plants justify this distance
        if plant_capacity_mw >= 1000:
            base_factor = 0.5 - (distance_km - TRANSMISSION_BULK) / (TRANSMISSION_LONG - TRANSMISSION_BULK) * 0.4
        elif plant_capacity_mw >= 500:
            base_factor = 0.2 - (distance_km - TRANSMISSION_BULK) / (TRANSMISSION_LONG - TRANSMISSION_BULK) * 0.2
        else:
            base_factor = 0.0
    
    return max(0.0, base_factor)


def calculate_clean_gen_score(
    node_lat: float,
    node_lon: float,
    energy_sources: List[Tuple[float, float, float, float]],
    normalization_factor: float = 100.0,
    demand_mw: Optional[float] = None
) -> float:
    """
    Calculate clean generation score for a grid node based on nearby energy sources.
    
    Score is based on:
    1. Distance to each energy source (proximity decay)
    2. Capacity of each source (larger = more contribution)
    3. Energy type multiplier (solar/wind = 1.0, nuclear = 0.9, etc.)
    4. **NEW**: Capacity adequacy relative to demand (if demand_mw provided)
    
    When demand_mw is provided, the score considers:
    - Capacity match: How well nearby clean capacity supports the load
    - Adequacy bonus: Extra credit for capacity > 2x demand (resilience)
    - Inadequacy penalty: Score reduction if capacity < demand
    
    Args:
        node_lat: Grid node latitude
        node_lon: Grid node longitude
        energy_sources: List of tuples (lat, lon, capacity_mw, clean_multiplier)
        normalization_factor: Divider to scale raw score to 0-100 range
        demand_mw: Optional demand size in MW (for capacity adequacy scoring)
    
    Returns:
        Clean generation score (0-100)
    """
    if not energy_sources:
        logger.warning("No energy sources provided for clean gen score calculation")
        return 0.0
    
    raw_score = 0.0
    nearby_capacity = 0.0  # Track total capacity within 300km for adequacy check
    
    for source_lat, source_lon, capacity_mw, clean_multiplier in energy_sources:
        # Calculate distance using Pythagorean theorem
        distance = pythagorean_distance(node_lat, node_lon, source_lat, source_lon)
        
        # Get proximity factor
        proximity = proximity_decay_factor(distance)
        
        # Calculate contribution: capacity × clean_multiplier × proximity
        contribution = capacity_mw * clean_multiplier * proximity
        raw_score += contribution
        
        # Track nearby capacity for adequacy assessment (within 300km)
        if distance < DISTANCE_FAIR:
            nearby_capacity += capacity_mw * clean_multiplier
    
    # Normalize to 0-100 scale
    base_score = min(100.0, (raw_score / normalization_factor) * 100.0)
    
    # Apply capacity adequacy adjustment if demand specified
    if demand_mw and demand_mw > 0:
        adequacy_factor = calculate_capacity_adequacy_factor(nearby_capacity, demand_mw)
        adjusted_score = base_score * adequacy_factor
        
        logger.debug(
            f"Clean gen capacity adequacy: {nearby_capacity:.0f} MW available, "
            f"{demand_mw:.0f} MW demand, factor={adequacy_factor:.2f}, "
            f"score {base_score:.1f} → {adjusted_score:.1f}"
        )
        
        return round(adjusted_score, 1)
    
    return round(base_score, 1)


def calculate_capacity_adequacy_factor(available_capacity_mw: float, demand_mw: float) -> float:
    """
    Calculate capacity adequacy multiplier for clean generation scoring.
    
    Adjusts clean gen score based on whether available capacity can support demand:
    - Capacity ratio > 3.0 (3x demand): 1.2x bonus (excellent surplus)
    - Capacity ratio > 2.0 (2x demand): 1.1x bonus (good resilience)
    - Capacity ratio > 1.5 (1.5x demand): 1.0x (adequate with buffer)
    - Capacity ratio > 1.0 (meets demand): 0.95x (adequate but tight)
    - Capacity ratio > 0.7 (70% of demand): 0.85x (moderate shortfall)
    - Capacity ratio > 0.5 (50% of demand): 0.70x (significant shortfall)
    - Capacity ratio < 0.5 (under 50%): 0.50x (severe shortfall)
    
    Args:
        available_capacity_mw: Total clean energy capacity nearby (MW)
        demand_mw: Target load size (MW)
    
    Returns:
        Adequacy factor (0.5 to 1.2) to multiply base score
    """
    if demand_mw <= 0:
        return 1.0
    
    ratio = available_capacity_mw / demand_mw
    
    if ratio >= 3.0:
        # Excellent: 3x+ capacity = 20% bonus (very resilient)
        return 1.20
    elif ratio >= 2.0:
        # Good: 2x-3x capacity = 10% bonus (resilient)
        return 1.10
    elif ratio >= 1.5:
        # Adequate: 1.5x-2x capacity = neutral (good buffer)
        return 1.00
    elif ratio >= 1.0:
        # Tight: 1x-1.5x capacity = 5% penalty (minimal buffer)
        return 0.95
    elif ratio >= 0.7:
        # Moderate shortfall: 70-100% = 15% penalty
        return 0.85
    elif ratio >= 0.5:
        # Significant shortfall: 50-70% = 30% penalty
        return 0.70
    else:
        # Severe shortfall: under 50% = 50% penalty
        return 0.50


def find_nearby_sources(
    node_lat: float,
    node_lon: float,
    energy_sources: List[Tuple[str, float, float, float, str]],
    max_distance_km: float = 300.0,
    limit: int = 10
) -> List[dict]:
    """
    Find energy sources near a grid node, sorted by distance.
    
    Args:
        node_lat: Grid node latitude
        node_lon: Grid node longitude
        energy_sources: List of tuples (name, lat, lon, capacity_mw, energy_type)
        max_distance_km: Maximum distance to consider
        limit: Maximum number of sources to return
    
    Returns:
        List of dicts with source info and distance, sorted by distance
    """
    nearby = []
    
    for name, source_lat, source_lon, capacity_mw, energy_type in energy_sources:
        distance = pythagorean_distance(node_lat, node_lon, source_lat, source_lon)
        
        if distance <= max_distance_km:
            nearby.append({
                "name": name,
                "distance_km": round(distance, 1),
                "capacity_mw": capacity_mw,
                "energy_type": energy_type,
                "latitude": source_lat,
                "longitude": source_lon
            })
    
    # Sort by distance (closest first)
    nearby.sort(key=lambda x: x["distance_km"])
    
    # Return top N
    return nearby[:limit]


def find_nearby_power_plants(
    node_lat: float,
    node_lon: float,
    power_plants: List,  # List of PowerPlant objects
    max_distance_km: float = 200.0,
    limit: int = 20,
    clean_only: bool = False
) -> List[dict]:
    """
    Find power plants near a location, sorted by distance.
    
    Returns plants with their distance, capacity, fuel type, and whether they're clean.
    Useful for understanding what drives clean_gen and transmission scores.
    
    Args:
        node_lat: Location latitude
        node_lon: Location longitude
        power_plants: List of PowerPlant objects
        max_distance_km: Maximum distance to consider
        limit: Maximum number of plants to return
        clean_only: If True, only return clean energy plants
    
    Returns:
        List of dicts with plant info and distance, sorted by distance
    """
    logger.debug(f"find_nearby_power_plants: lat={node_lat:.3f}, lon={node_lon:.3f}, {len(power_plants)} total plants, max_dist={max_distance_km}km, clean_only={clean_only}")
    
    nearby = []
    
    for plant in power_plants:
        # Skip non-clean plants if clean_only=True
        if clean_only and not plant.is_clean():
            continue
        
        distance = pythagorean_distance(
            node_lat, node_lon,
            plant.latitude, plant.longitude
        )
        
        if distance <= max_distance_km:
            nearby.append({
                "oris_code": plant.oris_code,
                "plant_name": plant.plant_name,
                "distance_km": round(distance, 1),
                "primary_fuel": plant.primary_fuel,
                "primary_fuel_category": plant.primary_fuel_category,
                "nameplate_mw": round(plant.nameplate_mw, 1),
                "is_clean": plant.is_clean(),
                "latitude": plant.latitude,
                "longitude": plant.longitude
            })
    
    logger.debug(f"Found {len(nearby)} plants within {max_distance_km}km before sorting/limiting")
    
    # Sort by distance (closest first)
    nearby.sort(key=lambda x: x["distance_km"])
    
    # Return top N
    result = nearby[:limit]
    logger.debug(f"Returning {len(result)} plants after limit={limit}")
    
    return result


def calculate_transmission_score(
    node_lat: float,
    node_lon: float,
    power_plants: List,  # List of PowerPlant objects
    normalization_factor: float = 100.0
) -> float:
    """
    Calculate transmission headroom score based on ALL nearby power infrastructure.
    
    Unlike clean_gen scoring (which only uses clean energy), transmission scoring uses
    ALL power plants because:
    1. Transmission infrastructure serves all generation types
    2. Large fossil plants often have the best transmission access (high voltage lines)
    3. Proximity to any large plant indicates strong grid infrastructure
    
    Score is based on:
    1. Total capacity of nearby plants (weighted by distance)
    2. Plant size (larger plants = higher voltage transmission = longer useful distance)
    3. Distance decay (transmission economics vary by voltage class)
    
    Args:
        node_lat: Grid node latitude
        node_lon: Grid node longitude
        power_plants: List of PowerPlant objects (all fuel types)
        normalization_factor: Divider to scale raw score to 0-100 range
    
    Returns:
        Transmission headroom score (0-100)
    """
    if not power_plants:
        logger.warning("No power plants provided for transmission score calculation")
        return 50.0  # Neutral default
    
    raw_score = 0.0
    plants_considered = 0
    total_capacity_nearby = 0.0
    
    for plant in power_plants:
        # Calculate distance
        distance = pythagorean_distance(
            node_lat, node_lon,
            plant.latitude, plant.longitude
        )
        
        # Get transmission decay factor (considers plant size and distance)
        decay = transmission_decay_factor(distance, plant.nameplate_mw)
        
        if decay > 0.0:
            # Calculate contribution: capacity × decay
            # Larger plants contribute more (indicates better transmission infrastructure)
            contribution = plant.nameplate_mw * decay
            raw_score += contribution
            plants_considered += 1
            
            if distance < TRANSMISSION_REGIONAL:
                total_capacity_nearby += plant.nameplate_mw
    
    # Log summary for debugging
    if plants_considered > 0:
        logger.debug(
            f"Transmission score calculation: {plants_considered} plants considered, "
            f"{total_capacity_nearby:.0f} MW within 150km, raw_score={raw_score:.1f}"
        )
    
    # Normalize to 0-100 scale
    score = min(100.0, (raw_score / normalization_factor) * 100.0)
    
    return round(score, 1)


def estimate_normalization_factor(
    all_nodes: List[Tuple[float, float]],
    energy_sources: List[Tuple[float, float, float, float]],
    demand_mw: Optional[float] = None
) -> float:
    """
    Estimate appropriate normalization factor for clean gen scoring.
    
    Calculates raw scores for all nodes and returns the 90th percentile
    value as the normalization factor. This ensures:
    - Top 10% of nodes score ~90-100
    - Median nodes score ~50
    - Bottom nodes score proportionally lower
    
    Note: Does NOT apply capacity adequacy adjustments during normalization
    to avoid biasing the scale based on a single demand size.
    
    Args:
        all_nodes: List of (lat, lon) tuples for all grid nodes
        energy_sources: List of (lat, lon, capacity_mw, clean_multiplier) tuples
        demand_mw: Ignored in normalization (kept for API compatibility)
    
    Returns:
        Normalization factor to use in calculate_clean_gen_score()
    """
    if not all_nodes or not energy_sources:
        logger.warning("Cannot estimate normalization factor with empty data")
        return 100.0  # Default fallback
    
    raw_scores = []
    
    for node_lat, node_lon in all_nodes:
        raw_score = 0.0
        
        for source_lat, source_lon, capacity_mw, clean_multiplier in energy_sources:
            distance = pythagorean_distance(node_lat, node_lon, source_lat, source_lon)
            proximity = proximity_decay_factor(distance)
            contribution = capacity_mw * clean_multiplier * proximity
            raw_score += contribution
        
        raw_scores.append(raw_score)
    
    # Sort and find 90th percentile
    raw_scores.sort()
    percentile_90_idx = int(len(raw_scores) * 0.9)
    normalization_factor = raw_scores[percentile_90_idx]
    
    # Ensure it's not zero
    if normalization_factor < 1.0:
        normalization_factor = max(raw_scores) or 100.0
    
    logger.info(f"Estimated normalization factor: {normalization_factor:.1f} (90th percentile of raw scores)")
    
    return normalization_factor


def estimate_transmission_normalization_factor(
    all_nodes: List[Tuple[float, float]],
    power_plants: List  # List of PowerPlant objects
) -> float:
    """
    Estimate appropriate normalization factor for transmission headroom scoring.
    
    Calculates raw transmission scores for all nodes and returns the 90th percentile
    value. This ensures good scaling across diverse grid regions.
    
    Args:
        all_nodes: List of (lat, lon) tuples for all grid nodes
        power_plants: List of PowerPlant objects (all fuel types)
    
    Returns:
        Normalization factor to use in calculate_transmission_score()
    """
    if not all_nodes or not power_plants:
        logger.warning("Cannot estimate transmission normalization factor with empty data")
        return 5000.0  # Default: 5000 MW weighted capacity = 100 score
    
    raw_scores = []
    
    for node_lat, node_lon in all_nodes:
        raw_score = 0.0
        
        for plant in power_plants:
            distance = pythagorean_distance(
                node_lat, node_lon,
                plant.latitude, plant.longitude
            )
            decay = transmission_decay_factor(distance, plant.nameplate_mw)
            contribution = plant.nameplate_mw * decay
            raw_score += contribution
        
        raw_scores.append(raw_score)
    
    # Sort and find 90th percentile
    raw_scores.sort()
    percentile_90_idx = int(len(raw_scores) * 0.9)
    normalization_factor = raw_scores[percentile_90_idx]
    
    # Ensure it's reasonable (not zero or too small)
    if normalization_factor < 1000.0:
        # Fallback to max or default
        normalization_factor = max(raw_scores) if raw_scores else 5000.0
        if normalization_factor < 1000.0:
            normalization_factor = 5000.0
    
    logger.info(
        f"Estimated transmission normalization factor: {normalization_factor:.1f} "
        f"(90th percentile of raw scores)"
    )
    
    return normalization_factor


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Scoring Utilities Test ===\n")
    
    # Test 1: Distance calculation
    print("Test 1: Pythagorean distance")
    # Portland, OR to Seattle, WA
    portland = (45.523, -122.676)
    seattle = (47.606, -122.332)
    distance = pythagorean_distance(*portland, *seattle)
    print(f"  Portland to Seattle: {distance:.1f} km (Pythagorean approximation)")
    
    # Test 2: Proximity decay
    print("\nTest 2: Proximity decay factors")
    test_distances = [25, 75, 150, 250, 350]
    for dist in test_distances:
        factor = proximity_decay_factor(dist)
        print(f"  {dist} km: {factor:.2f}")
    
    # Test 3: Clean gen score calculation
    print("\nTest 3: Clean gen score calculation")
    
    # Mock grid node at Portland, OR
    node_lat, node_lon = portland
    
    # Mock energy sources: (lat, lon, capacity_mw, clean_multiplier)
    sources = [
        (45.7, -122.5, 300, 1.0),   # Close solar farm
        (45.9, -122.8, 500, 1.0),   # Nearby wind farm
        (46.5, -123.0, 200, 0.95),  # Moderate distance hydro
        (48.0, -123.5, 800, 1.0),   # Far wind farm
    ]
    
    score = calculate_clean_gen_score(node_lat, node_lon, sources, normalization_factor=100.0)
    print(f"  Clean gen score: {score:.1f}/100")
    
    # Test 4: Find nearby sources
    print("\nTest 4: Find nearby sources")
    
    sources_with_names = [
        ("Columbia Gorge Wind", 45.7, -122.5, 300, "wind"),
        ("Cascade Solar", 45.9, -122.8, 500, "solar"),
        ("River Hydro", 46.5, -123.0, 200, "hydro"),
        ("North Wind Farm", 48.0, -123.5, 800, "wind"),
    ]
    
    nearby = find_nearby_sources(node_lat, node_lon, sources_with_names, max_distance_km=200, limit=3)
    
    for i, source in enumerate(nearby, 1):
        print(f"  {i}. {source['name']} ({source['energy_type']})")
        print(f"     {source['distance_km']} km, {source['capacity_mw']} MW")
    
    # Test 5: Normalization factor estimation
    print("\nTest 5: Estimate normalization factor")
    
    # Mock 10 grid nodes across US
    mock_nodes = [
        (45.5, -122.7),  # Portland, OR
        (47.6, -122.3),  # Seattle, WA
        (37.8, -122.4),  # San Francisco, CA
        (34.0, -118.2),  # Los Angeles, CA
        (32.7, -117.2),  # San Diego, CA
        (39.7, -105.0),  # Denver, CO
        (41.9, -87.6),   # Chicago, IL
        (40.7, -74.0),   # New York, NY
        (29.8, -95.4),   # Houston, TX
        (33.4, -112.1),  # Phoenix, AZ
    ]
    
    norm_factor = estimate_normalization_factor(mock_nodes, sources)
    print(f"  Estimated normalization factor: {norm_factor:.1f}")
