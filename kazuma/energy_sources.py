"""
Energy Source Data Loader for Smart Grid Siting Framework

Loads RWE clean energy projects from JSON, geocodes addresses, and provides
proximity-based clean generation scoring capabilities.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
import json
import logging
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import pickle

logger = logging.getLogger(__name__)

# Geocoding cache file location
CACHE_DIR = Path(__file__).parent / "data" / "cache"
GEOCODE_CACHE_FILE = CACHE_DIR / "geocode_cache.pkl"

# Energy source type multipliers for clean gen scoring
ENERGY_TYPE_MULTIPLIERS = {
    "solar": 1.0,
    "wind": 1.0,
    "battery storage + solar": 0.95,  # Slightly lower due to storage losses
    "hydro": 0.95,
    "nuclear": 0.9,
    "natural gas": 0.0,
    "coal": 0.0,
}


class EnergySourceCoordinates(BaseModel):
    """Geographic coordinates for energy source location"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    geocoded: bool = Field(True, description="Whether coordinates were geocoded from address")
    geocode_confidence: Optional[str] = None  # "exact", "approximate", "low"


class EnergySource(BaseModel):
    """
    Clean energy project/source from RWE dataset.
    
    Represents a renewable energy generation facility with capacity and location.
    Used to calculate proximity-based clean generation scores for grid nodes.
    """
    name: str
    energy_source: str  # "Solar", "Wind", "Battery Storage + Solar", etc.
    ppa_capacity_mw: float = Field(..., gt=0, description="PPA capacity in megawatts")
    address: str
    
    # Geocoded coordinates (populated after loading)
    coordinates: Optional[EnergySourceCoordinates] = None
    
    @field_validator('energy_source')
    @classmethod
    def normalize_energy_source(cls, v: str) -> str:
        """Normalize energy source to lowercase for consistent matching"""
        return v.lower()
    
    def get_clean_multiplier(self) -> float:
        """
        Get clean energy multiplier for this source type.
        
        Returns:
            Float multiplier (0.0-1.0) where 1.0 = 100% clean/renewable
        """
        return ENERGY_TYPE_MULTIPLIERS.get(self.energy_source, 0.5)
    
    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convert energy source to GeoJSON feature for map visualization"""
        if not self.coordinates:
            raise ValueError(f"Energy source {self.name} has not been geocoded yet")
        
        return {
            "type": "Feature",
            "properties": {
                "name": self.name,
                "energy_source": self.energy_source,
                "capacity_mw": self.ppa_capacity_mw,
                "address": self.address,
                "clean_multiplier": self.get_clean_multiplier(),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [
                    self.coordinates.longitude,
                    self.coordinates.latitude
                ]
            }
        }


class GeocodingCache:
    """Simple pickle-based cache for geocoding results"""
    
    def __init__(self, cache_file: Path = GEOCODE_CACHE_FILE):
        self.cache_file = cache_file
        self.cache: Dict[str, Dict[str, float]] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk if it exists"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    self.cache = pickle.load(f)
                logger.info(f"Loaded {len(self.cache)} geocoded addresses from cache")
            except Exception as e:
                logger.warning(f"Failed to load geocode cache: {e}")
                self.cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to disk"""
        try:
            # Ensure cache directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.info(f"Saved {len(self.cache)} geocoded addresses to cache")
        except Exception as e:
            logger.error(f"Failed to save geocode cache: {e}")
    
    def get(self, address: str) -> Optional[Dict[str, float]]:
        """Get cached coordinates for address"""
        return self.cache.get(address)
    
    def set(self, address: str, lat: float, lon: float) -> None:
        """Cache coordinates for address"""
        self.cache[address] = {"latitude": lat, "longitude": lon}
        self._save_cache()


class EnergySourceLoader:
    """Loads and geocodes energy sources from JSON file"""
    
    def __init__(self, json_path: Path):
        self.json_path = json_path
        self.geocoder = Nominatim(user_agent="smart-grid-siting-framework-v1.0")
        self.cache = GeocodingCache()
        self.sources: List[EnergySource] = []
    
    def load(self) -> List[EnergySource]:
        """
        Load energy sources from JSON and geocode all addresses.
        
        Returns:
            List of EnergySource objects with geocoded coordinates
        """
        logger.info(f"Loading energy sources from {self.json_path}")
        
        # Load JSON
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        projects = data.get("projects", [])
        logger.info(f"Found {len(projects)} energy projects in JSON")
        
        # Parse into EnergySource objects
        sources = []
        for project in projects:
            try:
                source = EnergySource(**project)
                sources.append(source)
            except Exception as e:
                logger.error(f"Failed to parse project {project.get('name', 'unknown')}: {e}")
        
        logger.info(f"Successfully parsed {len(sources)} energy sources")
        
        # Geocode all addresses
        sources = self._geocode_all(sources)
        
        self.sources = sources
        return sources
    
    def _geocode_all(self, sources: List[EnergySource]) -> List[EnergySource]:
        """
        Geocode all energy source addresses.
        
        Uses caching to avoid repeated API calls. Adds delay between
        requests to respect Nominatim usage policy.
        """
        logger.info("Starting geocoding process...")
        
        geocoded_count = 0
        cached_count = 0
        failed_count = 0
        
        for i, source in enumerate(sources):
            # Check cache first
            cached_coords = self.cache.get(source.address)
            
            if cached_coords:
                source.coordinates = EnergySourceCoordinates(
                    latitude=cached_coords["latitude"],
                    longitude=cached_coords["longitude"],
                    geocoded=True,
                    geocode_confidence="cached"
                )
                cached_count += 1
                logger.debug(f"[{i+1}/{len(sources)}] Cached: {source.name}")
            else:
                # Geocode from API
                coords = self._geocode_address(source.address)
                
                if coords:
                    source.coordinates = coords
                    self.cache.set(source.address, coords.latitude, coords.longitude)
                    geocoded_count += 1
                    logger.info(f"[{i+1}/{len(sources)}] Geocoded: {source.name} -> ({coords.latitude:.4f}, {coords.longitude:.4f})")
                    
                    # Rate limiting - Nominatim requires 1 request per second
                    time.sleep(1.1)
                else:
                    failed_count += 1
                    logger.warning(f"[{i+1}/{len(sources)}] Failed to geocode: {source.name} at {source.address}")
        
        logger.info(f"Geocoding complete: {geocoded_count} geocoded, {cached_count} from cache, {failed_count} failed")
        
        # Filter out sources that failed geocoding
        valid_sources = [s for s in sources if s.coordinates is not None]
        logger.info(f"Returning {len(valid_sources)} energy sources with valid coordinates")
        
        return valid_sources
    
    def _geocode_address(self, address: str, max_retries: int = 3) -> Optional[EnergySourceCoordinates]:
        """
        Geocode a single address using Nominatim.
        
        Args:
            address: Full address string
            max_retries: Number of retry attempts on timeout
        
        Returns:
            EnergySourceCoordinates if successful, None if failed
        """
        for attempt in range(max_retries):
            try:
                # Add country constraint to improve success rate and specify US addresses
                location = self.geocoder.geocode(
                    address, 
                    country_codes='us',  # Assume US addresses
                    addressdetails=True,  # Get detailed address components
                    timeout=10
                )
                
                if location:
                    # Determine confidence based on address components
                    confidence = "approximate"
                    if hasattr(location, 'raw'):
                        address_type = location.raw.get('type', '')
                        if address_type in ['house', 'building']:
                            confidence = "exact"
                        elif address_type in ['administrative', 'county']:
                            confidence = "low"
                    
                    return EnergySourceCoordinates(
                        latitude=location.latitude,
                        longitude=location.longitude,
                        geocoded=True,
                        geocode_confidence=confidence
                    )
                else:
                    logger.debug(f"No geocoding result for: {address}")
                    return None
                    
            except GeocoderTimedOut:
                if attempt < max_retries - 1:
                    logger.warning(f"Geocoding timeout for {address}, retrying ({attempt+1}/{max_retries})")
                    time.sleep(2)
                else:
                    logger.error(f"Geocoding failed after {max_retries} attempts: {address}")
                    return None
                    
            except GeocoderServiceError as e:
                logger.error(f"Geocoding service error for {address}: {e}")
                return None
                
            except Exception as e:
                logger.error(f"Unexpected geocoding error for {address}: {e}")
                return None
        
        return None


def load_energy_sources(json_path: Optional[Path] = None) -> List[EnergySource]:
    """
    Convenience function to load energy sources.
    
    Args:
        json_path: Path to RWE projects JSON. Defaults to data/rwe_projects_clean.json
    
    Returns:
        List of geocoded EnergySource objects
    """
    if json_path is None:
        json_path = Path(__file__).parent / "data" / "rwe_projects_clean.json"
    
    loader = EnergySourceLoader(json_path)
    return loader.load()


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Energy Source Loader Test ===\n")
    
    # Load sources
    sources = load_energy_sources()
    
    print(f"\nLoaded {len(sources)} energy sources:")
    for source in sources:
        if source.coordinates:
            print(f"  - {source.name} ({source.energy_source})")
            print(f"    {source.ppa_capacity_mw} MW at ({source.coordinates.latitude:.4f}, {source.coordinates.longitude:.4f})")
            print(f"    Clean multiplier: {source.get_clean_multiplier()}")
    
    # Summary stats
    total_capacity = sum(s.ppa_capacity_mw for s in sources)
    print(f"\nTotal capacity: {total_capacity:.0f} MW")
    
    energy_types = {}
    for source in sources:
        energy_types[source.energy_source] = energy_types.get(source.energy_source, 0) + 1
    
    print("\nEnergy source breakdown:")
    for energy_type, count in sorted(energy_types.items()):
        print(f"  {energy_type}: {count} projects")
