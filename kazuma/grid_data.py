"""
Mock Grid Data Generator for Smart Siting Framework

Generates 12-20 representative grid nodes across the US with realistic
clean generation, transmission headroom, and reliability scores.
"""

from typing import List
from models_grid import GridNode, GridNodeCoordinates, NearbyProject, TransmissionLine


def generate_mock_grid_nodes() -> List[GridNode]:
    """
    Generate 15 mock grid nodes across major US regions.
    
    Scores reflect realistic characteristics:
    - Pacific NW: High clean gen (hydro/wind), good transmission
    - California: High clean gen but transmission constrained
    - Texas: High wind/solar, excellent transmission (ERCOT)
    - Midwest: Good wind, strong transmission backbone
    - Southeast: Lower clean gen, moderate reliability
    """
    
    nodes = [
        # Pacific Northwest (1-2)
        GridNode(
            id=1,
            name="Pacific Northwest Node A",
            coordinates=GridNodeCoordinates(latitude=45.523, longitude=-122.676),
            clean_gen=82,
            transmission_headroom=74,
            reliability=68,
            region="Pacific Northwest",
            state="OR",
            balancing_authority="BPA",
            nearby_projects=[
                NearbyProject(
                    name="Columbia Gorge Wind Farm",
                    distance_km=48,
                    capacity_mw=300,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Cascade Hydro Expansion",
                    distance_km=85,
                    capacity_mw=450,
                    project_type="hydro",
                    status="under_construction"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="BPA-500-01",
                    distance_km=12,
                    voltage_kv=500,
                    capacity_available_mw=350,
                    upgrade_cost_estimate_million=2.1
                )
            ]
        ),
        GridNode(
            id=2,
            name="Washington State Node B",
            coordinates=GridNodeCoordinates(latitude=47.606, longitude=-122.332),
            clean_gen=78,
            transmission_headroom=82,
            reliability=71,
            region="Pacific Northwest",
            state="WA",
            balancing_authority="BPA",
            nearby_projects=[
                NearbyProject(
                    name="Puget Sound Offshore Wind",
                    distance_km=65,
                    capacity_mw=800,
                    project_type="wind",
                    status="planned"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="BPA-500-02",
                    distance_km=8,
                    voltage_kv=500,
                    capacity_available_mw=420
                )
            ]
        ),
        
        # California (3-4)
        GridNode(
            id=3,
            name="Northern California Node C",
            coordinates=GridNodeCoordinates(latitude=40.55, longitude=-122.39),
            clean_gen=91,
            transmission_headroom=55,
            reliability=58,
            region="California",
            state="CA",
            balancing_authority="CAISO",
            nearby_projects=[
                NearbyProject(
                    name="Sierra Solar Array",
                    distance_km=32,
                    capacity_mw=500,
                    project_type="solar",
                    status="operational"
                ),
                NearbyProject(
                    name="Shasta Pumped Storage",
                    distance_km=55,
                    capacity_mw=1200,
                    project_type="hydro",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="CAISO-500-12",
                    distance_km=18,
                    voltage_kv=500,
                    capacity_available_mw=180,
                    upgrade_cost_estimate_million=4.5
                )
            ]
        ),
        GridNode(
            id=4,
            name="Central California Node D",
            coordinates=GridNodeCoordinates(latitude=36.778, longitude=-119.417),
            clean_gen=88,
            transmission_headroom=48,
            reliability=62,
            region="California",
            state="CA",
            balancing_authority="CAISO",
            nearby_projects=[
                NearbyProject(
                    name="Central Valley Solar Farm",
                    distance_km=22,
                    capacity_mw=650,
                    project_type="solar",
                    status="operational"
                ),
                NearbyProject(
                    name="Diablo Canyon Extension",
                    distance_km=95,
                    capacity_mw=2200,
                    project_type="nuclear",
                    status="operational"
                )
            ]
        ),
        
        # Texas (5-7)
        GridNode(
            id=5,
            name="Texas Panhandle Node E",
            coordinates=GridNodeCoordinates(latitude=35.22, longitude=-101.83),
            clean_gen=75,
            transmission_headroom=88,
            reliability=72,
            region="Texas",
            state="TX",
            balancing_authority="ERCOT",
            nearby_projects=[
                NearbyProject(
                    name="Panhandle Wind Complex",
                    distance_km=18,
                    capacity_mw=1100,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Amarillo Solar Park",
                    distance_km=42,
                    capacity_mw=300,
                    project_type="solar",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="ERCOT-345-23",
                    distance_km=15,
                    voltage_kv=345,
                    capacity_available_mw=520
                )
            ]
        ),
        GridNode(
            id=6,
            name="West Texas Node F",
            coordinates=GridNodeCoordinates(latitude=31.997, longitude=-102.078),
            clean_gen=84,
            transmission_headroom=92,
            reliability=75,
            region="Texas",
            state="TX",
            balancing_authority="ERCOT",
            nearby_projects=[
                NearbyProject(
                    name="Permian Basin Solar",
                    distance_km=28,
                    capacity_mw=850,
                    project_type="solar",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="ERCOT-500-45",
                    distance_km=10,
                    voltage_kv=500,
                    capacity_available_mw=680
                )
            ]
        ),
        GridNode(
            id=7,
            name="Central Texas Node G",
            coordinates=GridNodeCoordinates(latitude=30.267, longitude=-97.743),
            clean_gen=68,
            transmission_headroom=71,
            reliability=78,
            region="Texas",
            state="TX",
            balancing_authority="ERCOT"
        ),
        
        # Midwest (8-10)
        GridNode(
            id=8,
            name="Iowa Wind Corridor Node H",
            coordinates=GridNodeCoordinates(latitude=41.6, longitude=-93.62),
            clean_gen=72,
            transmission_headroom=79,
            reliability=81,
            region="Midwest",
            state="IA",
            balancing_authority="MISO",
            nearby_projects=[
                NearbyProject(
                    name="Iowa Wind Belt",
                    distance_km=25,
                    capacity_mw=950,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Des Moines Solar Hub",
                    distance_km=35,
                    capacity_mw=200,
                    project_type="solar",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="MISO-345-67",
                    distance_km=14,
                    voltage_kv=345,
                    capacity_available_mw=410
                )
            ]
        ),
        GridNode(
            id=9,
            name="Illinois Hub Node I",
            coordinates=GridNodeCoordinates(latitude=40.633, longitude=-89.398),
            clean_gen=58,
            transmission_headroom=85,
            reliability=83,
            region="Midwest",
            state="IL",
            balancing_authority="MISO",
            nearby_projects=[
                NearbyProject(
                    name="Illinois Wind Farm",
                    distance_km=45,
                    capacity_mw=400,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Byron Nuclear Station",
                    distance_km=120,
                    capacity_mw=2300,
                    project_type="nuclear",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=10,
            name="Minnesota Node J",
            coordinates=GridNodeCoordinates(latitude=46.729, longitude=-94.686),
            clean_gen=65,
            transmission_headroom=73,
            reliability=79,
            region="Midwest",
            state="MN",
            balancing_authority="MISO"
        ),
        
        # Southeast (11-12)
        GridNode(
            id=11,
            name="Georgia Corridor Node K",
            coordinates=GridNodeCoordinates(latitude=33.95, longitude=-83.38),
            clean_gen=48,
            transmission_headroom=62,
            reliability=76,
            region="Southeast",
            state="GA",
            balancing_authority="Southern Company",
            nearby_projects=[
                NearbyProject(
                    name="Georgia Solar Initiative",
                    distance_km=38,
                    capacity_mw=350,
                    project_type="solar",
                    status="operational"
                ),
                NearbyProject(
                    name="Vogtle Nuclear Expansion",
                    distance_km=155,
                    capacity_mw=2200,
                    project_type="nuclear",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=12,
            name="North Carolina Node L",
            coordinates=GridNodeCoordinates(latitude=35.779, longitude=-78.638),
            clean_gen=52,
            transmission_headroom=68,
            reliability=74,
            region="Southeast",
            state="NC",
            balancing_authority="Duke Energy"
        ),
        
        # Mountain West (13-14)
        GridNode(
            id=13,
            name="Colorado Renewables Node M",
            coordinates=GridNodeCoordinates(latitude=39.739, longitude=-104.99),
            clean_gen=79,
            transmission_headroom=77,
            reliability=70,
            region="Mountain West",
            state="CO",
            balancing_authority="WAPA",
            nearby_projects=[
                NearbyProject(
                    name="Front Range Wind",
                    distance_km=55,
                    capacity_mw=600,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Rocky Mountain Solar",
                    distance_km=42,
                    capacity_mw=400,
                    project_type="solar",
                    status="under_construction"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="WAPA-345-89",
                    distance_km=22,
                    voltage_kv=345,
                    capacity_available_mw=380
                )
            ]
        ),
        GridNode(
            id=14,
            name="New Mexico Node N",
            coordinates=GridNodeCoordinates(latitude=35.085, longitude=-106.605),
            clean_gen=86,
            transmission_headroom=81,
            reliability=67,
            region="Mountain West",
            state="NM",
            balancing_authority="WAPA"
        ),
        
        # Northeast (15)
        GridNode(
            id=15,
            name="New York Upstate Node O",
            coordinates=GridNodeCoordinates(latitude=43.048, longitude=-76.147),
            clean_gen=61,
            transmission_headroom=59,
            reliability=82,
            region="Northeast",
            state="NY",
            balancing_authority="NYISO",
            nearby_projects=[
                NearbyProject(
                    name="Lake Ontario Offshore Wind",
                    distance_km=72,
                    capacity_mw=1200,
                    project_type="wind",
                    status="planned"
                ),
                NearbyProject(
                    name="Niagara Hydro Upgrade",
                    distance_km=95,
                    capacity_mw=800,
                    project_type="hydro",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="NYISO-345-12",
                    distance_km=16,
                    voltage_kv=345,
                    capacity_available_mw=290
                )
            ]
        ),
    ]
    
    return nodes


def get_node_by_id(node_id: int) -> GridNode:
    """Get a specific grid node by ID"""
    nodes = generate_mock_grid_nodes()
    for node in nodes:
        if node.id == node_id:
            return node
    raise ValueError(f"Grid node with ID {node_id} not found")


def get_nodes_by_region(region: str) -> List[GridNode]:
    """Filter nodes by region"""
    nodes = generate_mock_grid_nodes()
    return [node for node in nodes if node.region == region]


def get_nodes_by_state(state: str) -> List[GridNode]:
    """Filter nodes by state code"""
    nodes = generate_mock_grid_nodes()
    return [node for node in nodes if node.state == state]


# Quick stats for documentation
if __name__ == "__main__":
    nodes = generate_mock_grid_nodes()
    print(f"Generated {len(nodes)} grid nodes")
    print(f"\nScore ranges:")
    print(f"  Clean Gen: {min(n.clean_gen for n in nodes):.0f} - {max(n.clean_gen for n in nodes):.0f}")
    print(f"  Transmission: {min(n.transmission_headroom for n in nodes):.0f} - {max(n.transmission_headroom for n in nodes):.0f}")
    print(f"  Reliability: {min(n.reliability for n in nodes):.0f} - {max(n.reliability for n in nodes):.0f}")
    print(f"\nRegions covered:")
    regions = set(n.region for n in nodes if n.region)
    for region in sorted(regions):
        count = len([n for n in nodes if n.region == region])
        print(f"  {region}: {count} nodes")
