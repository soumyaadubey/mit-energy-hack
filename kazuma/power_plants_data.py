"""
Power Plants Data Loader

Loads and processes US power plant data from eGRID JSON file.
Provides filtering and GeoJSON conversion for map visualization.
"""

import json
import logging
from typing import List, Optional
from pathlib import Path
from models import PowerPlant

logger = logging.getLogger(__name__)


def load_power_plants_from_json(json_path: str = "../egrid2023_plants_lat_lng_fuel_power.json") -> List[PowerPlant]:
    """
    Load power plants from eGRID JSON file.
    
    Args:
        json_path: Path to JSON file relative to this script
    
    Returns:
        List of PowerPlant objects
    
    Raises:
        FileNotFoundError: If JSON file not found
        ValueError: If JSON is malformed
    """
    try:
        # Resolve path relative to this file
        script_dir = Path(__file__).parent
        full_path = (script_dir / json_path).resolve()
        
        logger.info(f"Loading power plants from {full_path}")
        
        with open(full_path, 'r') as f:
            raw_data = json.load(f)
        
        # Parse and validate with Pydantic
        plants = []
        for item in raw_data:
            try:
                # Handle NaN values in annual_net_gen_mwh
                annual_gen = item.get('annual_net_gen_mwh', 0.0)
                if annual_gen is None or str(annual_gen).lower() == 'nan':
                    annual_gen = 0.0
                
                plant = PowerPlant(
                    oris_code=item['oris_code'],
                    plant_name=item['plant_name'],
                    latitude=item['latitude'],
                    longitude=item['longitude'],
                    primary_fuel=item['primary_fuel'],
                    primary_fuel_category=item['primary_fuel_category'],
                    nameplate_mw=item['nameplate_mw'],
                    annual_net_gen_mwh=float(annual_gen)
                )
                plants.append(plant)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid plant entry: {e}")
                continue
        
        logger.info(f"Successfully loaded {len(plants)} power plants")
        return plants
        
    except FileNotFoundError:
        logger.error(f"Power plants JSON file not found at {json_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        raise ValueError(f"Malformed JSON file: {e}")


def filter_power_plants(
    plants: List[PowerPlant],
    fuel_category: Optional[str] = None,
    fuel_categories: Optional[List[str]] = None,
    min_capacity_mw: float = 0,
    max_capacity_mw: float = 10000,
    renewable_only: bool = False,
    clean_only: bool = False
) -> List[PowerPlant]:
    """
    Filter power plants by various criteria.
    
    Args:
        plants: List of PowerPlant objects
        fuel_category: Filter by specific fuel category (deprecated, use fuel_categories)
        fuel_categories: Filter by multiple fuel categories (e.g., ["SOLAR", "WIND"])
        min_capacity_mw: Minimum nameplate capacity
        max_capacity_mw: Maximum nameplate capacity
        renewable_only: Only include renewable sources
        clean_only: Only include clean energy (renewable + nuclear)
    
    Returns:
        Filtered list of PowerPlant objects
    """
    filtered = plants
    
    # Filter by fuel category (support both single and multiple)
    if fuel_categories:
        filtered = [p for p in filtered if p.primary_fuel_category in fuel_categories]
    elif fuel_category:
        filtered = [p for p in filtered if p.primary_fuel_category == fuel_category]
    
    # Filter by capacity range
    filtered = [
        p for p in filtered
        if min_capacity_mw <= p.nameplate_mw <= max_capacity_mw
    ]
    
    # Filter by renewable status
    if renewable_only:
        filtered = [p for p in filtered if p.is_renewable()]
    elif clean_only:
        filtered = [p for p in filtered if p.is_clean()]
    
    return filtered


def get_fuel_category_stats(plants: List[PowerPlant]) -> dict:
    """
    Calculate statistics by fuel category.
    Only includes clean energy sources (WND, SUN, WAT, GEO) in totals.
    
    Returns:
        Dictionary with counts and capacity by fuel category
    """
    stats = {}
    
    for plant in plants:
        category = plant.primary_fuel_category
        if category not in stats:
            stats[category] = {
                "count": 0,
                "total_capacity_mw": 0.0,
                "total_generation_mwh": 0.0,
                "is_clean": plant.is_clean()
            }
        
        stats[category]["count"] += 1
        stats[category]["total_capacity_mw"] += plant.nameplate_mw
        stats[category]["total_generation_mwh"] += plant.annual_net_gen_mwh
    
    # Round values for readability
    for category in stats:
        stats[category]["total_capacity_mw"] = round(stats[category]["total_capacity_mw"], 1)
        stats[category]["total_generation_mwh"] = round(stats[category]["total_generation_mwh"], 0)
    
    return stats


def power_plants_to_geojson(
    plants: List[PowerPlant],
    include_metadata: bool = True
) -> dict:
    """
    Convert power plants to GeoJSON FeatureCollection.
    Only clean energy plants (WND, SUN, WAT, GEO) are included in capacity totals.
    
    Args:
        plants: List of PowerPlant objects
        include_metadata: Include statistics in metadata field
    
    Returns:
        GeoJSON FeatureCollection dict
    """
    features = [plant.to_geojson_feature() for plant in plants]
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    if include_metadata:
        stats = get_fuel_category_stats(plants)
        
        # Only count clean energy in totals
        clean_plants = [p for p in plants if p.is_clean()]
        total_capacity = sum(p.nameplate_mw for p in clean_plants)
        total_generation = sum(p.annual_net_gen_mwh for p in clean_plants)
        
        # Count renewable vs non-clean
        renewable_count = sum(p.is_renewable() for p in plants)
        clean_count = sum(p.is_clean() for p in plants)
        
        geojson["metadata"] = {
            "total_plants": len(plants),
            "clean_energy_capacity_mw": round(total_capacity, 1),
            "clean_energy_generation_mwh": round(total_generation, 0),
            "clean_count": clean_count,
            "clean_percentage": round(clean_count / len(plants) * 100, 1) if plants else 0,
            "fuel_categories": stats,
            "note": "Only WND, SUN, WAT, GEO counted as clean energy"
        }
    
    return geojson


# Global cache for loaded plants (avoid reloading file on every request)
_cached_plants: Optional[List[PowerPlant]] = None


def get_all_power_plants(reload: bool = False) -> List[PowerPlant]:
    """
    Get all power plants (with caching).
    
    Args:
        reload: Force reload from file
    
    Returns:
        List of all PowerPlant objects
    """
    global _cached_plants
    
    if _cached_plants is None or reload:
        _cached_plants = load_power_plants_from_json()
    
    return _cached_plants


if __name__ == "__main__":
    # Test loading
    logging.basicConfig(level=logging.INFO)
    
    plants = load_power_plants_from_json()
    print(f"Loaded {len(plants)} power plants")
    
    # Show some stats
    stats = get_fuel_category_stats(plants)
    print("\nFuel Category Statistics:")
    for category, data in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"  {category}: {data['count']} plants, {data['total_capacity_mw']:,.0f} MW")
    
    # Test filtering
    renewables = filter_power_plants(plants, renewable_only=True)
    print(f"\nRenewable plants: {len(renewables)}")
    
    large_solar = filter_power_plants(plants, fuel_category="SOLAR", min_capacity_mw=50)
    print(f"Large solar farms (50+ MW): {len(large_solar)}")
