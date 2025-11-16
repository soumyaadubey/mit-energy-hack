"""
Mock Grid Data Generator for Smart Siting Framework

Generates 12-20 representative grid nodes across the US with realistic
clean generation, transmission headroom, and reliability scores.

When energy sources are provided, calculates real clean_gen scores based on
proximity to actual renewable energy projects. Otherwise uses mock data.
"""

from typing import List, Optional
from models import GridNode, GridNodeCoordinates, NearbyProject, TransmissionLine
import logging

logger = logging.getLogger(__name__)


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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
            clean_gen=100.0,
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
            clean_gen=0.0,
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
            clean_gen=32.2,
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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
            clean_gen=100.0,
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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
            clean_gen=0.0,
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
        
        # Southwest (16-20)
        GridNode(
            id=16,
            name="Arizona Solar Belt Node P",
            coordinates=GridNodeCoordinates(latitude=33.448, longitude=-112.074),
            clean_gen=0.0,
            transmission_headroom=84,
            reliability=73,
            region="Southwest",
            state="AZ",
            balancing_authority="WECC",
            nearby_projects=[
                NearbyProject(
                    name="Phoenix Solar Complex",
                    distance_km=25,
                    capacity_mw=750,
                    project_type="solar",
                    status="operational"
                ),
                NearbyProject(
                    name="Palo Verde Nuclear Station",
                    distance_km=65,
                    capacity_mw=3900,
                    project_type="nuclear",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="WECC-500-34",
                    distance_km=18,
                    voltage_kv=500,
                    capacity_available_mw=580
                )
            ]
        ),
        GridNode(
            id=17,
            name="Nevada Renewables Node Q",
            coordinates=GridNodeCoordinates(latitude=36.171, longitude=-115.137),
            clean_gen=0.0,
            transmission_headroom=78,
            reliability=69,
            region="Southwest",
            state="NV",
            balancing_authority="WECC",
            nearby_projects=[
                NearbyProject(
                    name="Mojave Desert Solar Array",
                    distance_km=45,
                    capacity_mw=1100,
                    project_type="solar",
                    status="operational"
                ),
                NearbyProject(
                    name="Hoover Dam Hydro",
                    distance_km=48,
                    capacity_mw=2080,
                    project_type="hydro",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="WECC-500-56",
                    distance_km=12,
                    voltage_kv=500,
                    capacity_available_mw=620
                )
            ]
        ),
        GridNode(
            id=18,
            name="Utah Grid Node R",
            coordinates=GridNodeCoordinates(latitude=40.761, longitude=-111.891),
            clean_gen=0.0,
            transmission_headroom=76,
            reliability=75,
            region="Southwest",
            state="UT",
            balancing_authority="WECC",
            nearby_projects=[
                NearbyProject(
                    name="Wasatch Wind Farm",
                    distance_km=38,
                    capacity_mw=450,
                    project_type="wind",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=19,
            name="Southern Arizona Node S",
            coordinates=GridNodeCoordinates(latitude=32.222, longitude=-110.926),
            clean_gen=0.0,
            transmission_headroom=81,
            reliability=71,
            region="Southwest",
            state="AZ",
            balancing_authority="WECC",
            nearby_projects=[
                NearbyProject(
                    name="Tucson Solar Park",
                    distance_km=28,
                    capacity_mw=600,
                    project_type="solar",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="WECC-345-78",
                    distance_km=15,
                    voltage_kv=345,
                    capacity_available_mw=440
                )
            ]
        ),
        GridNode(
            id=20,
            name="Northern Nevada Node T",
            coordinates=GridNodeCoordinates(latitude=39.529, longitude=-119.814),
            clean_gen=0.0,
            transmission_headroom=72,
            reliability=68,
            region="Southwest",
            state="NV",
            balancing_authority="WECC"
        ),
        
        # Plains States (21-25)
        GridNode(
            id=21,
            name="Oklahoma Wind Node U",
            coordinates=GridNodeCoordinates(latitude=35.467, longitude=-97.516),
            clean_gen=0.0,
            transmission_headroom=83,
            reliability=76,
            region="Plains",
            state="OK",
            balancing_authority="SPP",
            nearby_projects=[
                NearbyProject(
                    name="Oklahoma Wind Corridor",
                    distance_km=35,
                    capacity_mw=850,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Central Plains Wind",
                    distance_km=52,
                    capacity_mw=650,
                    project_type="wind",
                    status="under_construction"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="SPP-345-23",
                    distance_km=20,
                    voltage_kv=345,
                    capacity_available_mw=490
                )
            ]
        ),
        GridNode(
            id=22,
            name="Kansas Energy Hub Node V",
            coordinates=GridNodeCoordinates(latitude=38.956, longitude=-95.255),
            clean_gen=0.0,
            transmission_headroom=85,
            reliability=78,
            region="Plains",
            state="KS",
            balancing_authority="SPP",
            nearby_projects=[
                NearbyProject(
                    name="Kansas Wind Belt",
                    distance_km=42,
                    capacity_mw=750,
                    project_type="wind",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="SPP-345-45",
                    distance_km=18,
                    voltage_kv=345,
                    capacity_available_mw=510
                )
            ]
        ),
        GridNode(
            id=23,
            name="Nebraska Grid Node W",
            coordinates=GridNodeCoordinates(latitude=41.256, longitude=-96.011),
            clean_gen=0.0,
            transmission_headroom=80,
            reliability=80,
            region="Plains",
            state="NE",
            balancing_authority="SPP"
        ),
        GridNode(
            id=24,
            name="South Dakota Wind Node X",
            coordinates=GridNodeCoordinates(latitude=43.545, longitude=-96.731),
            clean_gen=0.0,
            transmission_headroom=77,
            reliability=77,
            region="Plains",
            state="SD",
            balancing_authority="MISO",
            nearby_projects=[
                NearbyProject(
                    name="Dakota Wind Project",
                    distance_km=30,
                    capacity_mw=550,
                    project_type="wind",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=25,
            name="North Dakota Energy Node Y",
            coordinates=GridNodeCoordinates(latitude=46.827, longitude=-100.779),
            clean_gen=0.0,
            transmission_headroom=74,
            reliability=75,
            region="Plains",
            state="ND",
            balancing_authority="MISO",
            nearby_projects=[
                NearbyProject(
                    name="Great Plains Wind Farm",
                    distance_km=45,
                    capacity_mw=600,
                    project_type="wind",
                    status="operational"
                )
            ]
        ),
        
        # Mid-Atlantic (26-28)
        GridNode(
            id=26,
            name="Pennsylvania Grid Node Z",
            coordinates=GridNodeCoordinates(latitude=40.441, longitude=-79.996),
            clean_gen=35.4,
            transmission_headroom=67,
            reliability=84,
            region="Mid-Atlantic",
            state="PA",
            balancing_authority="PJM",
            nearby_projects=[
                NearbyProject(
                    name="Allegheny Solar Initiative",
                    distance_km=38,
                    capacity_mw=400,
                    project_type="solar",
                    status="operational"
                ),
                NearbyProject(
                    name="Susquehanna Nuclear Station",
                    distance_km=145,
                    capacity_mw=2500,
                    project_type="nuclear",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="PJM-500-12",
                    distance_km=14,
                    voltage_kv=500,
                    capacity_available_mw=380
                )
            ]
        ),
        GridNode(
            id=27,
            name="Virginia Corridor Node AA",
            coordinates=GridNodeCoordinates(latitude=37.431, longitude=-78.656),
            clean_gen=100.0,
            transmission_headroom=71,
            reliability=79,
            region="Mid-Atlantic",
            state="VA",
            balancing_authority="PJM",
            nearby_projects=[
                NearbyProject(
                    name="Virginia Offshore Wind",
                    distance_km=185,
                    capacity_mw=2600,
                    project_type="wind",
                    status="under_construction"
                ),
                NearbyProject(
                    name="Shenandoah Solar Park",
                    distance_km=42,
                    capacity_mw=350,
                    project_type="solar",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=28,
            name="Maryland Hub Node AB",
            coordinates=GridNodeCoordinates(latitude=39.290, longitude=-76.612),
            clean_gen=100.0,
            transmission_headroom=65,
            reliability=81,
            region="Mid-Atlantic",
            state="MD",
            balancing_authority="PJM",
            nearby_projects=[
                NearbyProject(
                    name="Chesapeake Offshore Wind",
                    distance_km=95,
                    capacity_mw=1500,
                    project_type="wind",
                    status="planned"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="PJM-345-67",
                    distance_km=22,
                    voltage_kv=345,
                    capacity_available_mw=320
                )
            ]
        ),
        
        # Gulf Coast (29-32)
        GridNode(
            id=29,
            name="Louisiana Industrial Node AC",
            coordinates=GridNodeCoordinates(latitude=30.224, longitude=-92.020),
            clean_gen=32.6,
            transmission_headroom=79,
            reliability=72,
            region="Gulf Coast",
            state="LA",
            balancing_authority="MISO",
            nearby_projects=[
                NearbyProject(
                    name="Louisiana Solar Farm",
                    distance_km=48,
                    capacity_mw=450,
                    project_type="solar",
                    status="operational"
                ),
                NearbyProject(
                    name="Gulf Coast Offshore Wind",
                    distance_km=125,
                    capacity_mw=1800,
                    project_type="wind",
                    status="planned"
                )
            ]
        ),
        GridNode(
            id=30,
            name="Mississippi Grid Node AD",
            coordinates=GridNodeCoordinates(latitude=32.298, longitude=-90.184),
            clean_gen=50.2,
            transmission_headroom=73,
            reliability=74,
            region="Gulf Coast",
            state="MS",
            balancing_authority="MISO",
            nearby_projects=[
                NearbyProject(
                    name="Mississippi Solar Initiative",
                    distance_km=35,
                    capacity_mw=300,
                    project_type="solar",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=31,
            name="Alabama Energy Node AE",
            coordinates=GridNodeCoordinates(latitude=33.520, longitude=-86.802),
            clean_gen=0.0,
            transmission_headroom=69,
            reliability=77,
            region="Gulf Coast",
            state="AL",
            balancing_authority="Southern Company",
            nearby_projects=[
                NearbyProject(
                    name="Alabama Nuclear Plant",
                    distance_km=88,
                    capacity_mw=3600,
                    project_type="nuclear",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="SO-500-23",
                    distance_km=19,
                    voltage_kv=500,
                    capacity_available_mw=410
                )
            ]
        ),
        GridNode(
            id=32,
            name="Florida Panhandle Node AF",
            coordinates=GridNodeCoordinates(latitude=30.438, longitude=-84.281),
            clean_gen=0.0,
            transmission_headroom=66,
            reliability=75,
            region="Gulf Coast",
            state="FL",
            balancing_authority="Southern Company",
            nearby_projects=[
                NearbyProject(
                    name="Florida Solar Belt",
                    distance_km=52,
                    capacity_mw=700,
                    project_type="solar",
                    status="operational"
                )
            ]
        ),
        
        # Mountain West Expansion (33-36)
        GridNode(
            id=33,
            name="Montana Wind Node AG",
            coordinates=GridNodeCoordinates(latitude=46.872, longitude=-113.994),
            clean_gen=0.0,
            transmission_headroom=70,
            reliability=66,
            region="Mountain West",
            state="MT",
            balancing_authority="WAPA",
            nearby_projects=[
                NearbyProject(
                    name="Montana Wind Corridor",
                    distance_km=62,
                    capacity_mw=800,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Glacier Hydro Project",
                    distance_km=95,
                    capacity_mw=500,
                    project_type="hydro",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=34,
            name="Wyoming Energy Hub Node AH",
            coordinates=GridNodeCoordinates(latitude=41.139, longitude=-104.820),
            clean_gen=0.0,
            transmission_headroom=82,
            reliability=73,
            region="Mountain West",
            state="WY",
            balancing_authority="WAPA",
            nearby_projects=[
                NearbyProject(
                    name="Wyoming Wind Farm",
                    distance_km=40,
                    capacity_mw=650,
                    project_type="wind",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="WAPA-345-56",
                    distance_km=25,
                    voltage_kv=345,
                    capacity_available_mw=460
                )
            ]
        ),
        GridNode(
            id=35,
            name="Idaho Hydro Node AI",
            coordinates=GridNodeCoordinates(latitude=43.615, longitude=-116.202),
            clean_gen=0.0,
            transmission_headroom=75,
            reliability=70,
            region="Mountain West",
            state="ID",
            balancing_authority="WECC",
            nearby_projects=[
                NearbyProject(
                    name="Snake River Hydro Complex",
                    distance_km=55,
                    capacity_mw=900,
                    project_type="hydro",
                    status="operational"
                ),
                NearbyProject(
                    name="Idaho Wind Project",
                    distance_km=72,
                    capacity_mw=400,
                    project_type="wind",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=36,
            name="Eastern Oregon Node AJ",
            coordinates=GridNodeCoordinates(latitude=45.711, longitude=-118.789),
            clean_gen=0.0,
            transmission_headroom=76,
            reliability=69,
            region="Mountain West",
            state="OR",
            balancing_authority="BPA"
        ),
        
        # New England (37-40)
        GridNode(
            id=37,
            name="Massachusetts Hub Node AK",
            coordinates=GridNodeCoordinates(latitude=42.361, longitude=-71.057),
            clean_gen=0.0,
            transmission_headroom=58,
            reliability=85,
            region="New England",
            state="MA",
            balancing_authority="ISO-NE",
            nearby_projects=[
                NearbyProject(
                    name="Cape Cod Offshore Wind",
                    distance_km=85,
                    capacity_mw=2400,
                    project_type="wind",
                    status="under_construction"
                ),
                NearbyProject(
                    name="Massachusetts Solar Initiative",
                    distance_km=35,
                    capacity_mw=350,
                    project_type="solar",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="ISONE-345-12",
                    distance_km=12,
                    voltage_kv=345,
                    capacity_available_mw=310
                )
            ]
        ),
        GridNode(
            id=38,
            name="Connecticut Grid Node AL",
            coordinates=GridNodeCoordinates(latitude=41.763, longitude=-72.685),
            clean_gen=0.0,
            transmission_headroom=62,
            reliability=83,
            region="New England",
            state="CT",
            balancing_authority="ISO-NE",
            nearby_projects=[
                NearbyProject(
                    name="Long Island Sound Offshore Wind",
                    distance_km=68,
                    capacity_mw=1800,
                    project_type="wind",
                    status="planned"
                )
            ]
        ),
        GridNode(
            id=39,
            name="Maine Renewables Node AM",
            coordinates=GridNodeCoordinates(latitude=44.311, longitude=-69.778),
            clean_gen=0.0,
            transmission_headroom=64,
            reliability=78,
            region="New England",
            state="ME",
            balancing_authority="ISO-NE",
            nearby_projects=[
                NearbyProject(
                    name="Maine Offshore Wind",
                    distance_km=95,
                    capacity_mw=2000,
                    project_type="wind",
                    status="planned"
                ),
                NearbyProject(
                    name="Kennebec Hydro",
                    distance_km=42,
                    capacity_mw=550,
                    project_type="hydro",
                    status="operational"
                )
            ]
        ),
        GridNode(
            id=40,
            name="Vermont Green Node AN",
            coordinates=GridNodeCoordinates(latitude=44.260, longitude=-72.576),
            clean_gen=0.0,
            transmission_headroom=61,
            reliability=80,
            region="New England",
            state="VT",
            balancing_authority="ISO-NE",
            nearby_projects=[
                NearbyProject(
                    name="Vermont Wind Farm",
                    distance_km=38,
                    capacity_mw=300,
                    project_type="wind",
                    status="operational"
                ),
                NearbyProject(
                    name="Green Mountain Hydro",
                    distance_km=55,
                    capacity_mw=450,
                    project_type="hydro",
                    status="operational"
                )
            ],
            transmission_lines=[
                TransmissionLine(
                    line_id="ISONE-345-34",
                    distance_km=28,
                    voltage_kv=345,
                    capacity_available_mw=280
                )
            ]
        ),
    ]
    
    return nodes


def get_node_by_id(node_id: int, nodes: Optional[List[GridNode]] = None) -> GridNode:
    """Get a specific grid node by ID"""
    if nodes is None:
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


def calculate_real_clean_gen_scores(
    nodes: List[GridNode],
    energy_sources: List,
    demand_mw: Optional[float] = None
) -> List[GridNode]:
    """
    Calculate real clean_gen scores for grid nodes based on energy sources.
    
    Replaces mock clean_gen values with scores calculated from proximity
    to actual renewable energy projects. Optionally considers capacity
    adequacy relative to a target demand size.
    
    Args:
        nodes: List of GridNode objects with mock clean_gen scores
        energy_sources: List of EnergySource objects from energy_sources.py
        demand_mw: Optional demand size for capacity adequacy scoring
    
    Returns:
        Updated list of GridNode objects with real clean_gen scores
    """
    try:
        from scoring_utils import calculate_clean_gen_score, estimate_normalization_factor
        
        logger.info(f"Calculating real clean gen scores for {len(nodes)} nodes using {len(energy_sources)} energy sources")
        if demand_mw:
            logger.info(f"  Using demand-aware scoring: {demand_mw} MW target load")
        
        # Filter energy sources to only those with valid coordinates
        valid_sources = [s for s in energy_sources if s.coordinates is not None]
        
        if not valid_sources:
            logger.warning("No energy sources with valid coordinates found, keeping mock scores")
            return nodes
        
        logger.info(f"Using {len(valid_sources)} energy sources with valid coordinates")
        
        # Prepare energy source data for scoring
        source_data = [
            (
                s.coordinates.latitude,
                s.coordinates.longitude,
                s.ppa_capacity_mw,
                s.get_clean_multiplier()
            )
            for s in valid_sources
        ]
        
        # Estimate normalization factor based on all nodes (without demand adjustment)
        node_coords = [(n.coordinates.latitude, n.coordinates.longitude) for n in nodes]
        normalization_factor = estimate_normalization_factor(node_coords, source_data)
        
        logger.info(f"Using normalization factor: {normalization_factor:.1f}")
        
        # Calculate clean gen score for each node
        updated_nodes = []
        for node in nodes:
            old_score = node.clean_gen
            
            # Calculate new score with optional demand adequacy
            new_score = calculate_clean_gen_score(
                node.coordinates.latitude,
                node.coordinates.longitude,
                source_data,
                normalization_factor,
                demand_mw=demand_mw
            )
            
            # Update node (create new instance to maintain immutability)
            updated_node = node.model_copy(update={"clean_gen": new_score})
            updated_nodes.append(updated_node)
            
            logger.info(f"  {node.name}: {old_score:.1f} → {new_score:.1f} (delta: {new_score - old_score:+.1f})")
        
        return updated_nodes
        
    except ImportError as e:
        logger.error(f"Failed to import scoring utilities: {e}")
        logger.warning("Keeping mock clean_gen scores")
        return nodes
    except Exception as e:
        logger.error(f"Error calculating real clean gen scores: {e}")
        logger.warning("Keeping mock clean_gen scores")
        return nodes


def calculate_real_transmission_scores(
    nodes: List[GridNode],
    power_plants: List
) -> List[GridNode]:
    """
    Calculate real transmission_headroom scores for grid nodes based on ALL power plants.
    
    Replaces mock transmission_headroom values with scores calculated from proximity
    to actual power infrastructure (all fuel types, weighted by capacity).
    
    Args:
        nodes: List of GridNode objects with mock transmission_headroom scores
        power_plants: List of PowerPlant objects from power_plants_data.py (ALL TYPES)
    
    Returns:
        Updated list of GridNode objects with real transmission_headroom scores
    """
    try:
        from scoring_utils import calculate_transmission_score, estimate_transmission_normalization_factor
        
        logger.info(f"Calculating real transmission scores for {len(nodes)} nodes using {len(power_plants)} power plants")
        
        if not power_plants:
            logger.warning("No power plants found, keeping mock transmission scores")
            return nodes
        
        # Estimate normalization factor based on all nodes
        node_coords = [(n.coordinates.latitude, n.coordinates.longitude) for n in nodes]
        normalization_factor = estimate_transmission_normalization_factor(node_coords, power_plants)
        
        logger.info(f"Using transmission normalization factor: {normalization_factor:.1f}")
        
        # Calculate transmission score for each node
        updated_nodes = []
        for node in nodes:
            old_score = node.transmission_headroom
            
            # Calculate new score using ALL power plants
            new_score = calculate_transmission_score(
                node.coordinates.latitude,
                node.coordinates.longitude,
                power_plants,
                normalization_factor
            )
            
            # Update node (create new instance to maintain immutability)
            updated_node = node.model_copy(update={"transmission_headroom": new_score})
            updated_nodes.append(updated_node)
            
            logger.info(f"  {node.name}: transmission {old_score:.1f} → {new_score:.1f} (delta: {new_score - old_score:+.1f})")
        
        return updated_nodes
        
    except ImportError as e:
        logger.error(f"Failed to import scoring utilities: {e}")
        logger.warning("Keeping mock transmission scores")
        return nodes
    except Exception as e:
        logger.error(f"Error calculating real transmission scores: {e}")
        logger.warning("Keeping mock transmission scores")
        return nodes


def generate_grid_nodes_with_real_scores(
    energy_sources: Optional[List] = None,
    power_plants: Optional[List] = None
) -> List[GridNode]:
    """
    Generate grid nodes with real scores if data is provided.
    
    This is the main function to use when loading grid data with real scores.
    
    Args:
        energy_sources: Optional list of EnergySource objects. If provided,
                       clean_gen scores will be calculated from real clean energy data.
        power_plants: Optional list of PowerPlant objects. If provided,
                     transmission_headroom scores will be calculated from real 
                     power infrastructure data (all fuel types).
    
    Returns:
        List of GridNode objects with either real or mock scores
    """
    # Generate base nodes with mock data
    nodes = generate_mock_grid_nodes()
    
    # If energy sources provided, calculate real clean_gen scores
    if energy_sources:
        logger.info("Energy sources provided, calculating real clean_gen scores")
        nodes = calculate_real_clean_gen_scores(nodes, energy_sources)
    else:
        logger.info("No energy sources provided, using mock clean_gen scores")
    
    # If power plants provided, calculate real transmission_headroom scores
    if power_plants:
        logger.info("Power plants provided, calculating real transmission_headroom scores")
        nodes = calculate_real_transmission_scores(nodes, power_plants)
    else:
        logger.info("No power plants provided, using mock transmission_headroom scores")
    
    return nodes


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
