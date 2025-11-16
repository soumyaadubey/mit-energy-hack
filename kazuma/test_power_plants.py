#!/usr/bin/env python3
"""
Quick test script to verify power plants integration
"""

import sys
sys.path.insert(0, '/Users/kazumachoji/Desktop/mit-energy-hack/kazuma')

from power_plants_data import (
    load_power_plants_from_json,
    filter_power_plants,
    get_fuel_category_stats,
    power_plants_to_geojson
)

def main():
    print("=" * 60)
    print("POWER PLANTS DATA INTEGRATION TEST")
    print("=" * 60)
    
    # Load data
    print("\n1. Loading power plants from JSON...")
    try:
        plants = load_power_plants_from_json()
        print(f"   ✓ Loaded {len(plants):,} power plants")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # Test filtering
    print("\n2. Testing filters...")
    renewables = filter_power_plants(plants, renewable_only=True)
    print(f"   ✓ Renewable plants: {len(renewables):,} ({len(renewables)/len(plants)*100:.1f}%)")
    
    solar = filter_power_plants(plants, fuel_category="SOLAR")
    print(f"   ✓ Solar plants: {len(solar):,}")
    
    large_wind = filter_power_plants(plants, fuel_category="WIND", min_capacity_mw=50)
    print(f"   ✓ Large wind farms (50+ MW): {len(large_wind):,}")
    
    # Stats
    print("\n3. Fuel category statistics:")
    stats = get_fuel_category_stats(plants)
    for category, data in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)[:10]:
        print(f"   {category:12s} {data['count']:>5,} plants  {data['total_capacity_mw']:>10,.0f} MW")
    
    # GeoJSON conversion
    print("\n4. Testing GeoJSON conversion...")
    geojson = power_plants_to_geojson(renewables[:100], include_metadata=True)
    print(f"   ✓ GeoJSON features: {len(geojson['features'])}")
    print(f"   ✓ Metadata included: {'metadata' in geojson}")
    
    if 'metadata' in geojson:
        meta = geojson['metadata']
        print(f"   ✓ Total capacity: {meta['total_capacity_mw']:,.0f} MW")
        print(f"   ✓ Renewable count: {meta['renewable_count']:,}")
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    
    # Sample plant
    print("\n5. Sample power plant:")
    sample = plants[0]
    print(f"   Name: {sample.plant_name}")
    print(f"   Fuel: {sample.primary_fuel_category}")
    print(f"   Capacity: {sample.nameplate_mw} MW")
    print(f"   Location: ({sample.latitude}, {sample.longitude})")
    print(f"   Renewable: {sample.is_renewable()}")
    print(f"   Color: {sample.get_fuel_color()}")

if __name__ == "__main__":
    main()
