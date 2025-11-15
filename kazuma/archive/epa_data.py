"""
EPA Envirofacts Data Fetcher for Industrial Emissions

Fetches facility-level emissions and compliance data from EPA's Envirofacts RESTful API.
Covers GHGRP (emissions), FRS (facility registry), TRI (toxic releases), and ECHO (compliance).
"""

import httpx
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

# EPA Envirofacts API base URL
EPA_BASE = "https://data.epa.gov/efservice"

# Industry NAICS codes
NAICS_CODES = {
    "steel": ["331110", "3311"],  # Iron and Steel Mills and Ferroalloy Manufacturing
    "cement": ["327310", "3273"],  # Cement Manufacturing
    "chemicals": ["325", "3251", "3252", "3253", "3254", "3255", "3256", "3259"]  # Chemical Manufacturing
}

# All chemical NAICS codes for comprehensive filtering
ALL_CHEMICAL_NAICS = ["325", "3251", "3252", "3253", "3254", "3255", "3256", "3259",
                      "32511", "32512", "32513", "32518", "32519", "32521", "32522",
                      "32531", "32532", "32541", "32551", "32552", "32561", "32562",
                      "32591", "32592", "32599"]


class EPADataFetcher:
    """Async client for EPA Envirofacts API"""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.base_url = EPA_BASE
    
    async def _fetch_paginated(
        self,
        endpoint: str,
        page_size: int = 1000,
        max_records: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch data with pagination to handle large datasets.
        EPA limits requests to 15 minutes, so we page through results.
        """
        all_records = []
        start = 1
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                end = start + page_size - 1
                if max_records and end > max_records:
                    end = max_records
                
                # Build URL with pagination
                url = f"{self.base_url}/{endpoint}/{start}:{end}/JSON"
                
                logger.info(f"Fetching EPA data: {url}")
                
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # EPA returns list of records or empty list if no more data
                    if not data or len(data) == 0:
                        break
                    
                    all_records.extend(data)
                    
                    # Check if we got fewer records than requested (end of dataset)
                    if len(data) < page_size:
                        break
                    
                    # Check if we've reached max_records
                    if max_records and len(all_records) >= max_records:
                        all_records = all_records[:max_records]
                        break
                    
                    start = end + 1
                    
                    # Brief delay to be respectful to EPA servers
                    await asyncio.sleep(0.1)
                    
                except httpx.HTTPError as e:
                    logger.error(f"HTTP error fetching EPA data: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error fetching EPA data: {e}")
                    break
        
        logger.info(f"Fetched {len(all_records)} total records")
        return all_records
    
    async def fetch_ghgrp_facilities(
        self,
        year: int = 2022,
        industry_type: Optional[str] = None,
        state: Optional[str] = None,
        max_records: Optional[int] = 10000
    ) -> List[Dict[str, Any]]:
        """
        Fetch GHGRP (Greenhouse Gas Reporting Program) facility data.
        
        Table: ghg.ghg_emitter_facilities (or pub_dim_facility for more recent)
        
        Args:
            year: Reporting year (2010-2023)
            industry_type: 'steel', 'cement', or 'chemicals'
            state: Two-letter state code (e.g., 'TX', 'CA')
            max_records: Maximum number of records to fetch
        """
        # Build filter string
        filters = []
        
        if year:
            filters.append(f"reporting_year/equals/{year}")
        
        if state:
            filters.append(f"state/equals/{state}")
        
        # For NAICS filtering, we'll do it client-side since EPA API
        # may not have direct NAICS filtering on GHGRP table
        
        filter_str = "/and/".join(filters) if filters else ""
        
        # GHGRP facilities endpoint
        # Note: The actual table name may vary - common ones are:
        # - ghg.ghg_emitter_facilities
        # - pub_dim_facility
        endpoint = f"ghg.ghg_emitter_facilities/{filter_str}" if filter_str else "ghg.ghg_emitter_facilities"
        
        try:
            facilities = await self._fetch_paginated(endpoint, max_records=max_records)
            
            # Client-side NAICS filtering if industry_type specified
            if industry_type and industry_type in NAICS_CODES:
                target_naics = NAICS_CODES[industry_type]
                facilities = [
                    f for f in facilities
                    if any(
                        f.get("naics_code", "").startswith(code)
                        for code in target_naics
                    )
                ]
            
            return facilities
        except Exception as e:
            logger.error(f"Error fetching GHGRP facilities: {e}")
            return []
    
    async def fetch_ghgrp_emissions(
        self,
        facility_id: Optional[str] = None,
        year: int = 2022,
        max_records: Optional[int] = 10000
    ) -> List[Dict[str, Any]]:
        """
        Fetch detailed emissions data by gas type for facilities.
        
        Table: ghg.ghg_emission_data (emissions by subpart and gas type)
        
        Returns emissions broken down by:
        - CO2, CH4, N2O, HFCs, PFCs, SF6
        - Subpart (C for steel, H for cement, X/Y for chemicals, etc.)
        """
        filters = [f"reporting_year/equals/{year}"]
        
        if facility_id:
            filters.append(f"facility_id/equals/{facility_id}")
        
        filter_str = "/and/".join(filters)
        endpoint = f"ghg.ghg_emission_data/{filter_str}"
        
        try:
            emissions = await self._fetch_paginated(endpoint, max_records=max_records)
            return emissions
        except Exception as e:
            logger.error(f"Error fetching GHGRP emissions: {e}")
            return []
    
    async def fetch_frs_facilities(
        self,
        state: Optional[str] = None,
        naics_code: Optional[str] = None,
        max_records: Optional[int] = 10000
    ) -> List[Dict[str, Any]]:
        """
        Fetch FRS (Facility Registry Service) data for facility metadata and coordinates.
        
        Table: frs.frs_facilities
        
        Provides:
        - Precise lat/long coordinates
        - Facility names, addresses
        - Registry IDs that link to other EPA datasets
        """
        filters = []
        
        if state:
            filters.append(f"state_code/equals/{state}")
        
        if naics_code:
            filters.append(f"naics_code/beginsWith/{naics_code}")
        
        filter_str = "/and/".join(filters) if filters else ""
        endpoint = f"frs.frs_facilities/{filter_str}" if filter_str else "frs.frs_facilities"
        
        try:
            facilities = await self._fetch_paginated(endpoint, max_records=max_records)
            return facilities
        except Exception as e:
            logger.error(f"Error fetching FRS facilities: {e}")
            return []
    
    async def fetch_tri_facilities(
        self,
        state: Optional[str] = None,
        year: int = 2022,
        industry_type: Optional[str] = None,
        max_records: Optional[int] = 10000
    ) -> List[Dict[str, Any]]:
        """
        Fetch TRI (Toxic Release Inventory) data for environmental justice analysis.
        
        Table: tri.tri_facility
        
        Shows toxic co-pollutants alongside CO2 emissions for complete picture.
        """
        filters = [f"reporting_year/equals/{year}"]
        
        if state:
            filters.append(f"state_abbr/equals/{state}")
        
        filter_str = "/and/".join(filters)
        endpoint = f"tri.tri_facility/{filter_str}"
        
        try:
            facilities = await self._fetch_paginated(endpoint, max_records=max_records)
            
            # Filter by industry if specified
            if industry_type and industry_type in NAICS_CODES:
                target_naics = NAICS_CODES[industry_type]
                facilities = [
                    f for f in facilities
                    if any(
                        str(f.get("industry_sector_code", "")).startswith(code) or
                        str(f.get("naics_code", "")).startswith(code)
                        for code in target_naics
                    )
                ]
            
            return facilities
        except Exception as e:
            logger.error(f"Error fetching TRI facilities: {e}")
            return []
    
    async def fetch_tri_releases(
        self,
        facility_id: Optional[str] = None,
        year: int = 2022,
        max_records: Optional[int] = 5000
    ) -> List[Dict[str, Any]]:
        """
        Fetch TRI chemical releases for specific facility.
        
        Table: tri.tri_reporting_form
        
        Shows detailed toxic release data by chemical.
        """
        filters = [f"reporting_year/equals/{year}"]
        
        if facility_id:
            filters.append(f"trifid/equals/{facility_id}")
        
        filter_str = "/and/".join(filters)
        endpoint = f"tri.tri_reporting_form/{filter_str}"
        
        try:
            releases = await self._fetch_paginated(endpoint, max_records=max_records)
            return releases
        except Exception as e:
            logger.error(f"Error fetching TRI releases: {e}")
            return []
    
    async def fetch_echo_compliance(
        self,
        facility_id: Optional[str] = None,
        state: Optional[str] = None,
        max_records: Optional[int] = 5000
    ) -> List[Dict[str, Any]]:
        """
        Fetch ECHO (Enforcement and Compliance History Online) data.
        
        Table: echo.echo_exporter
        
        Shows compliance violations and enforcement actions.
        Critical for identifying which plants need stricter oversight.
        """
        filters = []
        
        if state:
            filters.append(f"fac_state/equals/{state}")
        
        if facility_id:
            filters.append(f"registry_id/equals/{facility_id}")
        
        filter_str = "/and/".join(filters) if filters else ""
        endpoint = f"echo.echo_exporter/{filter_str}" if filter_str else "echo.echo_exporter"
        
        try:
            compliance = await self._fetch_paginated(endpoint, max_records=max_records)
            return compliance
        except Exception as e:
            logger.error(f"Error fetching ECHO compliance: {e}")
            return []
    
    async def fetch_all_industrial_facilities(
        self,
        year: int = 2022,
        state: Optional[str] = None,
        industry_type: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch comprehensive facility data from multiple EPA sources.
        
        Returns dict with keys: 'ghgrp', 'frs', 'tri', 'echo'
        """
        # Fetch all datasets in parallel
        tasks = [
            self.fetch_ghgrp_facilities(year=year, industry_type=industry_type, state=state),
            self.fetch_tri_facilities(year=year, state=state, industry_type=industry_type),
            self.fetch_echo_compliance(state=state),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "ghgrp": results[0] if not isinstance(results[0], Exception) else [],
            "tri": results[1] if not isinstance(results[1], Exception) else [],
            "echo": results[2] if not isinstance(results[2], Exception) else [],
        }


# Utility functions for data transformation

def calculate_total_co2e(emissions_data: List[Dict[str, Any]]) -> float:
    """
    Calculate total CO2 equivalent from emissions data.
    
    Combines CO2, CH4, N2O, and F-gases with appropriate GWP factors.
    """
    total = 0.0
    
    # GWP (Global Warming Potential) factors
    gwp_factors = {
        "CO2": 1,
        "CH4": 25,  # Methane
        "N2O": 298,  # Nitrous Oxide
        "HFC": 1430,  # Average for HFCs
        "PFC": 7390,  # Average for PFCs
        "SF6": 22800,  # Sulfur Hexafluoride
    }
    
    for emission in emissions_data:
        gas_type = emission.get("gas_code", "CO2").upper()
        amount = float(emission.get("co2e_emission", 0) or emission.get("ghg_quantity", 0) or 0)
        
        # Use GWP factor if available
        for gas, factor in gwp_factors.items():
            if gas in gas_type:
                total += amount * factor
                break
        else:
            # If no match, assume it's already in CO2e
            total += amount
    
    return total


def merge_facility_data(
    ghgrp: List[Dict],
    frs: List[Dict],
    tri: List[Dict],
    echo: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Merge facility data from multiple EPA sources using common identifiers.
    
    Links facilities by:
    - Registry ID (FRS)
    - Facility ID
    - Name + Address matching
    """
    # This is a simplified merge - in production would use more sophisticated matching
    merged = []
    
    # Start with GHGRP as primary source (has emissions data)
    for ghgrp_facility in ghgrp:
        facility = ghgrp_facility.copy()
        facility_id = facility.get("facility_id") or facility.get("registry_id")
        
        # Try to find matching FRS data for better coordinates
        for frs_facility in frs:
            if frs_facility.get("registry_id") == facility_id:
                facility["frs_data"] = frs_facility
                # Use FRS coordinates if available (more precise)
                facility["latitude"] = frs_facility.get("latitude_measure") or facility.get("latitude")
                facility["longitude"] = frs_facility.get("longitude_measure") or facility.get("longitude")
                break
        
        # Find matching TRI data
        for tri_facility in tri:
            if tri_facility.get("trifid") == facility_id or tri_facility.get("registry_id") == facility_id:
                facility["tri_data"] = tri_facility
                break
        
        # Find matching ECHO compliance data
        for echo_facility in echo:
            if echo_facility.get("registry_id") == facility_id:
                facility["echo_data"] = echo_facility
                facility["compliance_violations"] = echo_facility.get("informal_count", 0)
                break
        
        merged.append(facility)
    
    return merged


# Example usage and testing
if __name__ == "__main__":
    async def test_fetcher():
        fetcher = EPADataFetcher()
        
        print("Testing EPA data fetcher...")
        
        # Test GHGRP facilities for steel in Texas
        print("\n1. Fetching steel facilities in Texas...")
        steel_facilities = await fetcher.fetch_ghgrp_facilities(
            year=2022,
            industry_type="steel",
            state="TX",
            max_records=100
        )
        print(f"Found {len(steel_facilities)} steel facilities")
        if steel_facilities:
            print(f"Sample: {steel_facilities[0]}")
        
        # Test TRI facilities for chemicals in Louisiana
        print("\n2. Fetching chemical facilities in Louisiana (TRI)...")
        chem_facilities = await fetcher.fetch_tri_facilities(
            year=2022,
            state="LA",
            industry_type="chemicals",
            max_records=50
        )
        print(f"Found {len(chem_facilities)} chemical facilities")
        if chem_facilities:
            print(f"Sample: {chem_facilities[0]}")
        
        # Test comprehensive fetch
        print("\n3. Fetching all industrial data for California...")
        all_data = await fetcher.fetch_all_industrial_facilities(
            year=2022,
            state="CA",
            industry_type="cement"
        )
        print(f"GHGRP: {len(all_data['ghgrp'])} facilities")
        print(f"TRI: {len(all_data['tri'])} facilities")
        print(f"ECHO: {len(all_data['echo'])} facilities")
    
    asyncio.run(test_fetcher())
