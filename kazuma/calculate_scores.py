#!/usr/bin/env python3
"""
Calculate real clean_gen scores for grid nodes using RWE energy sources.
Run this to get updated hardcoded values for grid_data.py
"""

import json
import math
from pathlib import Path

# Energy sources from RWE with geocoded coordinates
# Geocoded using Nominatim (OpenStreetMap)
ENERGY_SOURCES = [
    {"name": "360 Solar", "address": "21501 Hull Street Road, Mosley, VA", "lat": 37.4019, "lon": -77.5311, "capacity": 52, "type": "solar"},
    {"name": "Wythe County", "address": "Foster Falls Road, Suffolk, VA", "lat": 36.9204, "lon": -76.5833, "capacity": 52, "type": "solar"},
    {"name": "Waterloo Solar", "address": "Bastrop County, Texas", "lat": 30.0000, "lon": -97.1167, "capacity": 52, "type": "solar"},
    {"name": "Switchgrass", "address": "Hoosier Road, Suffolk, VA", "lat": 36.7286, "lon": -76.5833, "capacity": 52, "type": "solar"},
    {"name": "Lafitte Solar Park", "address": "343 McHenry Gin Rd., Monroe, LA 71202", "lat": 32.5093, "lon": -92.1221, "capacity": 52, "type": "solar"},
    {"name": "Harrisonburg", "address": "3793 Kratzer Road, Harrisonburg, VA", "lat": 38.4496, "lon": -78.8689, "capacity": 52, "type": "solar"},
    {"name": "Groves", "address": "Westmoreland County, VA", "lat": 38.0293, "lon": -76.8803, "capacity": 52, "type": "solar"},
    {"name": "Bluestem", "address": "LaPorte County, Indiana", "lat": 41.6094, "lon": -86.7326, "capacity": 52, "type": "battery storage + solar"},
    {"name": "Big Pine", "address": "Sussex County, Virginia", "lat": 36.8468, "lon": -77.2803, "capacity": 52, "type": "solar"},
]

# Grid nodes (first 40)
GRID_NODES = [
    (1, "Pacific Northwest Node A", 45.523, -122.676),
    (2, "Washington State Node B", 47.606, -122.332),
    (3, "Northern California Node C", 40.55, -122.39),
    (4, "Central California Node D", 36.778, -119.417),
    (5, "Texas Panhandle Node E", 35.22, -101.83),
    (6, "West Texas Node F", 31.997, -102.078),
    (7, "Central Texas Node G", 30.267, -97.743),
    (8, "Iowa Wind Corridor Node H", 41.6, -93.62),
    (9, "Illinois Hub Node I", 40.633, -89.398),
    (10, "Minnesota Node J", 46.729, -94.686),
    (11, "Georgia Corridor Node K", 33.95, -83.38),
    (12, "North Carolina Node L", 35.779, -78.638),
    (13, "Colorado Renewables Node M", 39.739, -104.99),
    (14, "New Mexico Node N", 35.085, -106.605),
    (15, "New York Upstate Node O", 43.048, -76.147),
    (16, "Arizona Solar Belt Node P", 33.448, -112.074),
    (17, "Nevada Renewables Node Q", 36.171, -115.137),
    (18, "Utah Grid Node R", 40.761, -111.891),
    (19, "Southern Arizona Node S", 32.222, -110.926),
    (20, "Northern Nevada Node T", 39.529, -119.814),
    (21, "Oklahoma Wind Node U", 35.467, -97.516),
    (22, "Kansas Energy Hub Node V", 38.956, -95.255),
    (23, "Nebraska Grid Node W", 41.256, -96.011),
    (24, "South Dakota Wind Node X", 43.545, -96.731),
    (25, "North Dakota Energy Node Y", 46.827, -100.779),
    (26, "Pennsylvania Grid Node Z", 40.441, -79.996),
    (27, "Virginia Corridor Node AA", 37.431, -78.656),
    (28, "Maryland Hub Node AB", 39.290, -76.612),
    (29, "Louisiana Industrial Node AC", 30.224, -92.020),
    (30, "Mississippi Grid Node AD", 32.298, -90.184),
    (31, "Alabama Energy Node AE", 33.520, -86.802),
    (32, "Florida Panhandle Node AF", 30.438, -84.281),
    (33, "Montana Wind Node AG", 46.872, -113.994),
    (34, "Wyoming Energy Hub Node AH", 41.139, -104.820),
    (35, "Idaho Hydro Node AI", 43.615, -116.202),
    (36, "Eastern Oregon Node AJ", 45.711, -118.789),
    (37, "Massachusetts Hub Node AK", 42.361, -71.057),
    (38, "Connecticut Grid Node AL", 41.763, -72.685),
    (39, "Maine Renewables Node AM", 44.311, -69.778),
    (40, "Vermont Green Node AN", 44.260, -72.576),
]

# Energy type multipliers
ENERGY_MULTIPLIERS = {
    "solar": 1.0,
    "wind": 1.0,
    "battery storage + solar": 0.95,
    "hydro": 0.95,
    "nuclear": 0.9,
}

def pythagorean_distance(lat1, lon1, lat2, lon2):
    """Calculate distance using Pythagorean theorem"""
    avg_lat = (lat1 + lat2) / 2.0
    lat_diff_km = (lat2 - lat1) * 111.0
    lon_diff_km = (lon2 - lon1) * 111.0 * math.cos(math.radians(avg_lat))
    return math.sqrt(lat_diff_km**2 + lon_diff_km**2)

def proximity_decay_factor(distance_km):
    """Calculate proximity decay factor"""
    if distance_km < 50:
        return 1.0
    elif distance_km < 100:
        return 1.0 - (distance_km - 50) / 50 * 0.3
    elif distance_km < 200:
        return 0.7 - (distance_km - 100) / 100 * 0.3
    elif distance_km < 300:
        return 0.4 - (distance_km - 200) / 100 * 0.2
    else:
        return 0.0

def calculate_clean_gen_score(node_lat, node_lon, normalization_factor):
    """Calculate clean gen score for a node"""
    raw_score = 0.0
    
    for source in ENERGY_SOURCES:
        distance = pythagorean_distance(node_lat, node_lon, source["lat"], source["lon"])
        proximity = proximity_decay_factor(distance)
        multiplier = ENERGY_MULTIPLIERS.get(source["type"], 0.5)
        contribution = source["capacity"] * multiplier * proximity
        raw_score += contribution
    
    score = min(100.0, (raw_score / normalization_factor) * 100.0)
    return round(score, 1)

def estimate_normalization_factor():
    """Estimate normalization factor from all nodes"""
    raw_scores = []
    
    for node_id, name, lat, lon in GRID_NODES:
        raw_score = 0.0
        for source in ENERGY_SOURCES:
            distance = pythagorean_distance(lat, lon, source["lat"], source["lon"])
            proximity = proximity_decay_factor(distance)
            multiplier = ENERGY_MULTIPLIERS.get(source["type"], 0.5)
            contribution = source["capacity"] * multiplier * proximity
            raw_score += contribution
        raw_scores.append(raw_score)
    
    raw_scores.sort()
    percentile_90_idx = int(len(raw_scores) * 0.9)
    return raw_scores[percentile_90_idx] if raw_scores else 100.0

if __name__ == "__main__":
    print("Calculating real clean_gen scores...\n")
    
    # Calculate normalization factor
    norm_factor = estimate_normalization_factor()
    print(f"Normalization factor: {norm_factor:.1f}\n")
    
    # Calculate scores for all nodes
    print("=" * 80)
    print("UPDATED CLEAN_GEN SCORES")
    print("=" * 80)
    
    for node_id, name, lat, lon in GRID_NODES:
        score = calculate_clean_gen_score(lat, lon, norm_factor)
        print(f"Node {node_id:2d} - {name:45s}: clean_gen={score:5.1f}")
    
    print("\n" + "=" * 80)
    print("Copy these scores to grid_data.py")
    print("=" * 80)
