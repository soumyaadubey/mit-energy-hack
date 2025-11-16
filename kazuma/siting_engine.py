"""
Siting Engine for Smart Grid Optimization

Calculates composite siting scores using weighted criteria and ranks alternative locations.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import math
from models import (
    GridNode,
    SitingWeights,
    ScoreBreakdown,
    SiteEvaluation,
    DemandProfile,
    ScenarioComparison
)

logger = logging.getLogger(__name__)


class SitingEngine:
    """Engine for calculating optimal siting scores and comparing locations"""
    
    def __init__(self):
        # Default weights for quick evaluations
        self.default_weights = SitingWeights(
            weight_clean=0.4,
            weight_transmission=0.3,
            weight_reliability=0.3
        )
    
    def calculate_composite_score(
        self,
        node: GridNode,
        weights: SitingWeights
    ) -> ScoreBreakdown:
        """
        Calculate composite siting score using weighted criteria.
        
        Formula:
            score = (clean_gen × weight_clean) 
                  + (transmission_headroom × weight_transmission)
                  + (reliability × weight_reliability)
        
        Args:
            node: Grid node with 0-100 scores for each criterion
            weights: Weight allocation (must sum to 1.0)
        
        Returns:
            ScoreBreakdown with composite score and individual contributions
        
        Raises:
            ValueError: If weights don't sum to 1.0
        """
        # Validate weights sum to 1.0
        weights.validate_sum()
        
        # Calculate weighted contributions
        clean_contribution = node.clean_gen * weights.weight_clean
        transmission_contribution = node.transmission_headroom * weights.weight_transmission
        reliability_contribution = node.reliability * weights.weight_reliability
        
        # Composite score
        composite = clean_contribution + transmission_contribution + reliability_contribution
        
        # Round to 1 decimal for display, but keep full precision internally
        composite_rounded = round(composite, 1)
        
        logger.info(
            f"Calculated score for {node.name}: {composite_rounded:.1f} "
            f"(clean={clean_contribution:.1f}, trans={transmission_contribution:.1f}, "
            f"rel={reliability_contribution:.1f})"
        )
        
        return ScoreBreakdown(
            clean_gen_score=node.clean_gen,
            clean_gen_contribution=round(clean_contribution, 1),
            transmission_score=node.transmission_headroom,
            transmission_contribution=round(transmission_contribution, 1),
            reliability_score=node.reliability,
            reliability_contribution=round(reliability_contribution, 1),
            composite_score=composite_rounded,
            weights_used=weights
        )
    
    def calculate_scores_from_coordinates(
        self,
        latitude: float,
        longitude: float,
        energy_sources: List,
        power_plants: List,
        weights: SitingWeights,
        demand_profile: Optional[DemandProfile] = None
    ) -> ScoreBreakdown:
        """
        Calculate siting scores for arbitrary coordinates without a predefined GridNode.
        
        Dynamically calculates:
        - clean_gen: Based on proximity to clean energy power plants (from eGrid data)
                    PLUS capacity adequacy relative to demand size
        - transmission_headroom: Based on proximity to high-capacity power plants
        - reliability: Based on density of diverse power sources nearby
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            energy_sources: DEPRECATED - not used, clean plants filtered from power_plants
            power_plants: List of power plant objects for all calculations
            weights: Weight allocation (must sum to 1.0)
            demand_profile: Optional demand profile for capacity adequacy scoring
        
        Returns:
            ScoreBreakdown with calculated scores and composite
        """
        from scoring_utils import calculate_clean_gen_score, find_nearby_sources, estimate_normalization_factor
        from grid_data import generate_mock_grid_nodes
        
        # Validate weights
        weights.validate_sum()
        
        # Extract demand size if provided
        demand_mw = demand_profile.size_mw if demand_profile else None
        
        # Calculate clean_gen score from clean energy power plants
        clean_gen_score = 0.0
        if power_plants:
            # Filter for clean energy plants only (renewable + nuclear)
            clean_plants = [p for p in power_plants if p.is_clean()]
            
            # Prepare clean plant data (lat, lon, capacity, clean multiplier)
            # All clean plants get multiplier of 1.0 (equal weighting)
            source_data = [
                (
                    p.latitude,
                    p.longitude,
                    p.nameplate_mw,
                    1.0  # All clean energy equally valued
                )
                for p in clean_plants
            ]
            
            if source_data:
                # Estimate normalization factor (use existing nodes as reference)
                grid_nodes = generate_mock_grid_nodes()
                node_coords = [(n.coordinates.latitude, n.coordinates.longitude) for n in grid_nodes]
                normalization_factor = estimate_normalization_factor(node_coords, source_data)
                
                # Calculate clean gen score
                clean_gen_score = calculate_clean_gen_score(
                    latitude,
                    longitude,
                    source_data,
                    normalization_factor,
                    demand_mw=demand_mw  # Pass demand for capacity adequacy
                )
        
        # Calculate transmission_headroom score based on ALL nearby power plants
        transmission_score = 0.0
        if power_plants:
            from scoring_utils import calculate_transmission_score, estimate_transmission_normalization_factor
            
            # Estimate normalization factor (use existing nodes as reference)
            grid_nodes = generate_mock_grid_nodes()
            node_coords = [(n.coordinates.latitude, n.coordinates.longitude) for n in grid_nodes]
            trans_normalization = estimate_transmission_normalization_factor(node_coords, power_plants)
            
            # Calculate transmission score using ALL power plants
            transmission_score = calculate_transmission_score(
                latitude,
                longitude,
                power_plants,
                trans_normalization
            )
        
        # Calculate reliability score based on power source diversity
        reliability_score = self._calculate_reliability_score(
            latitude, longitude, power_plants
        )
        
        # Calculate weighted contributions
        clean_contribution = clean_gen_score * weights.weight_clean
        transmission_contribution = transmission_score * weights.weight_transmission
        reliability_contribution = reliability_score * weights.weight_reliability
        
        # Composite score
        composite = clean_contribution + transmission_contribution + reliability_contribution
        composite_rounded = round(composite, 1)
        
        logger.info(
            f"Calculated score for coordinates ({latitude:.3f}, {longitude:.3f}): {composite_rounded:.1f} "
            f"(clean={clean_contribution:.1f}, trans={transmission_contribution:.1f}, "
            f"rel={reliability_contribution:.1f})"
        )
        
        return ScoreBreakdown(
            clean_gen_score=round(clean_gen_score, 1),
            clean_gen_contribution=round(clean_contribution, 1),
            transmission_score=round(transmission_score, 1),
            transmission_contribution=round(transmission_contribution, 1),
            reliability_score=round(reliability_score, 1),
            reliability_contribution=round(reliability_contribution, 1),
            composite_score=composite_rounded,
            weights_used=weights
        )
    
    def _calculate_transmission_score(
        self,
        latitude: float,
        longitude: float,
        power_plants: List
    ) -> float:
        """
        Calculate transmission headroom score based on ALL nearby power infrastructure.
        
        ENHANCED VERSION: Now uses sophisticated transmission decay modeling that considers:
        - Plant capacity (larger plants = higher voltage transmission = better infrastructure)
        - Distance-based voltage zones (small plants useful to 50km, large to 300km+)
        - All fuel types (transmission infrastructure serves all generation)
        
        This replaces the old simple method with capacity-weighted, voltage-aware scoring.
        
        Args:
            latitude: Node latitude
            longitude: Node longitude  
            power_plants: List of PowerPlant objects (all fuel types)
        
        Returns:
            Transmission score 0-100
        """
        from scoring_utils import calculate_transmission_score, estimate_transmission_normalization_factor
        from grid_data import generate_mock_grid_nodes
        
        if not power_plants:
            return 50.0  # Neutral default for no data
        
        # Estimate normalization factor using all grid nodes as reference
        grid_nodes = generate_mock_grid_nodes()
        node_coords = [(n.coordinates.latitude, n.coordinates.longitude) for n in grid_nodes]
        normalization_factor = estimate_transmission_normalization_factor(node_coords, power_plants)
        
        # Calculate transmission score using comprehensive algorithm
        score = calculate_transmission_score(
            latitude,
            longitude,
            power_plants,
            normalization_factor
        )
        
        return score
    
    def _calculate_reliability_score(
        self,
        latitude: float,
        longitude: float,
        power_plants: List
    ) -> float:
        """
        Calculate grid reliability score based on power source diversity and density.
        
        Considers:
        - Number of nearby plants (redundancy)
        - Diversity of fuel types (resilience)
        - Total capacity (grid strength)
        
        Returns score 0-100
        """
        from scoring_utils import pythagorean_distance
        
        if not power_plants:
            return 50.0  # Default moderate score
        
        # Find plants within 200km (reliability zone)
        nearby_plants = []
        for plant in power_plants:
            distance = pythagorean_distance(
                latitude, longitude,
                plant.latitude, plant.longitude
            )
            if distance <= 200:
                nearby_plants.append(plant)
        
        if not nearby_plants:
            return 30.0  # Low score if isolated
        
        # Factor 1: Plant count (redundancy)
        # 20+ plants = full credit, linear below
        count_score = min(100.0, (len(nearby_plants) / 20.0) * 100.0)
        
        # Factor 2: Fuel diversity (resilience)
        fuel_types = set(p.primary_fuel_category for p in nearby_plants)
        # 5+ fuel types = full credit
        diversity_score = min(100.0, (len(fuel_types) / 5.0) * 100.0)
        
        # Factor 3: Total capacity (grid strength)
        total_capacity = sum(p.nameplate_mw for p in nearby_plants)
        # 10,000 MW = full credit
        capacity_score = min(100.0, (total_capacity / 10000.0) * 100.0)
        
        # Weighted average: count=40%, diversity=30%, capacity=30%
        reliability = (
            count_score * 0.4 +
            diversity_score * 0.3 +
            capacity_score * 0.3
        )
        
        return reliability
    
    def evaluate_site(
        self,
        node: GridNode,
        weights: Optional[SitingWeights] = None,
        demand_profile: Optional[DemandProfile] = None,
        all_nodes: Optional[List[GridNode]] = None,
        power_plants: Optional[List] = None
    ) -> SiteEvaluation:
        """
        Complete site evaluation with ranking context.
        
        Args:
            node: Grid node to evaluate
            weights: Siting criteria weights (uses defaults if None)
            demand_profile: Optional load profile for context
            all_nodes: All available nodes for percentile calculation
            power_plants: Optional list of power plants for nearby analysis
        
        Returns:
            SiteEvaluation with score, breakdown, ranking context, and nearby plants
        """
        if weights is None:
            weights = self.default_weights
        
        # Calculate score breakdown
        score_breakdown = self.calculate_composite_score(node, weights)
        
        # Calculate percentile rank if all nodes provided
        percentile_rank = None
        if all_nodes:
            percentile_rank = self._calculate_percentile(
                node,
                all_nodes,
                weights
            )
        
        # Find alternative sites
        alternative_sites = []
        if all_nodes:
            alternative_sites = self._find_alternatives(
                node,
                all_nodes,
                weights,
                limit=5
            )
        
        # Find nearby power plants
        nearby_power_plants = []
        if power_plants:
            nearby_power_plants = self._find_nearby_power_plants(
                node.coordinates.latitude,
                node.coordinates.longitude,
                power_plants
            )
        
        # Generate evaluation notes
        notes = self._generate_evaluation_notes(node, score_breakdown)
        
        evaluation = SiteEvaluation(
            site=node,
            weights=weights,
            demand_profile=demand_profile,
            score_breakdown=score_breakdown,
            percentile_rank=percentile_rank,
            alternative_sites=alternative_sites,
            nearby_power_plants=nearby_power_plants,
            evaluation_notes=notes
        )
        
        return evaluation
    
    def rank_sites(
        self,
        nodes: List[GridNode],
        weights: SitingWeights
    ) -> List[Tuple[GridNode, float]]:
        """
        Rank all sites by composite score.
        
        Args:
            nodes: List of grid nodes to rank
            weights: Siting criteria weights
        
        Returns:
            List of (node, score) tuples sorted by score descending
        """
        scored_nodes = []
        
        for node in nodes:
            breakdown = self.calculate_composite_score(node, weights)
            scored_nodes.append((node, breakdown.composite_score))
        
        # Sort by score descending
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        
        return scored_nodes
    
    def compare_scenarios(
        self,
        evaluations: List[SiteEvaluation],
        scenario_name: str = "Comparison"
    ) -> ScenarioComparison:
        """
        Compare multiple site evaluations.
        
        Args:
            evaluations: List of site evaluations to compare
            scenario_name: Name for this comparison
        
        Returns:
            ScenarioComparison with best site and delta analysis
        """
        if not evaluations:
            raise ValueError("Must provide at least one evaluation")
        
        # Find best scoring site
        best_eval = max(evaluations, key=lambda e: e.score_breakdown.composite_score)
        best_score = best_eval.score_breakdown.composite_score
        best_site_id = best_eval.site.id
        
        # Calculate score range
        scores = [e.score_breakdown.composite_score for e in evaluations]
        score_range = (min(scores), max(scores))
        
        # Calculate deltas from best
        score_deltas = {
            e.site.id: round(e.score_breakdown.composite_score - best_score, 1)
            for e in evaluations
        }
        
        return ScenarioComparison(
            scenario_name=scenario_name,
            scenarios=evaluations,
            best_site_id=best_site_id,
            score_range=score_range,
            score_deltas=score_deltas
        )
    
    def _calculate_percentile(
        self,
        node: GridNode,
        all_nodes: List[GridNode],
        weights: SitingWeights
    ) -> float:
        """Calculate what percentile this node ranks in (0-100)"""
        ranked = self.rank_sites(all_nodes, weights)
        scores = [score for _, score in ranked]
        
        node_breakdown = self.calculate_composite_score(node, weights)
        node_score = node_breakdown.composite_score
        
        # Count how many sites this node beats
        better_than = sum(1 for score in scores if node_score > score)
        
        # Percentile = (number of sites beaten / total sites) * 100
        percentile = (better_than / len(scores)) * 100
        
        return round(percentile, 1)
    
    def _find_alternatives(
        self,
        reference_node: GridNode,
        all_nodes: List[GridNode],
        weights: SitingWeights,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find top alternative sites similar to reference.
        
        Excludes the reference node itself and returns top N by score.
        """
        # Rank all nodes
        ranked = self.rank_sites(all_nodes, weights)
        
        # Filter out reference node
        alternatives = [
            (node, score) for node, score in ranked
            if node.id != reference_node.id
        ]
        
        # Take top N
        top_alternatives = alternatives[:limit]
        
        # Format as dicts for JSON serialization
        return [
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
            for node, score in top_alternatives
        ]
    
    def _generate_evaluation_notes(
        self,
        node: GridNode,
        breakdown: ScoreBreakdown
    ) -> List[str]:
        """Generate human-readable notes about the evaluation"""
        notes = []
        
        # Overall score assessment
        score = breakdown.composite_score
        if score >= 80:
            notes.append("Excellent overall siting location")
        elif score >= 70:
            notes.append("Very good siting location with minor trade-offs")
        elif score >= 60:
            notes.append("Good siting location suitable for most applications")
        elif score >= 50:
            notes.append("Moderate siting location with some constraints")
        else:
            notes.append("Challenging siting location requiring mitigation")
        
        # Individual criterion assessments
        if node.clean_gen >= 80:
            notes.append("Outstanding clean energy resources nearby")
        elif node.clean_gen < 50:
            notes.append("Limited clean energy access may require additional renewables")
        
        if node.transmission_headroom >= 80:
            notes.append("Excellent transmission capacity available")
        elif node.transmission_headroom < 40:
            notes.append("Transmission upgrades likely required")
        
        if node.reliability >= 80:
            notes.append("Highly reliable grid infrastructure")
        elif node.reliability < 60:
            notes.append("Grid reliability concerns should be assessed")
        
        # Nearby projects
        if len(node.nearby_projects) >= 2:
            notes.append(f"{len(node.nearby_projects)} nearby clean energy projects identified")
        
        # Transmission lines
        if len(node.transmission_lines) >= 1:
            closest_line = min(node.transmission_lines, key=lambda l: l.distance_km)
            notes.append(
                f"High-voltage transmission line ({closest_line.voltage_kv}kV) "
                f"within {closest_line.distance_km:.0f}km"
            )
        
        return notes
    
    def _find_nearby_power_plants(
        self,
        latitude: float,
        longitude: float,
        power_plants: List,
        max_distance_km: float = 200.0,
        limit: int = 20
    ) -> List:
        """
        Find nearby power plants for site evaluation context.
        
        Returns the closest plants that influence scoring, prioritizing:
        1. Clean energy plants (for clean_gen score transparency)
        2. Large plants (for transmission_headroom score transparency)
        
        Args:
            latitude: Site latitude
            longitude: Site longitude
            power_plants: List of PowerPlant objects
            max_distance_km: Maximum distance to consider
            limit: Maximum number of plants to return
        
        Returns:
            List of NearbyPowerPlant objects
        """
        from scoring_utils import find_nearby_power_plants
        from models import NearbyPowerPlant
        
        logger.info(f"_find_nearby_power_plants called: lat={latitude:.3f}, lon={longitude:.3f}, plants={len(power_plants) if power_plants else 0}, max_dist={max_distance_km}")
        
        # Get nearby plants using scoring utility
        nearby_plants_data = find_nearby_power_plants(
            latitude,
            longitude,
            power_plants,
            max_distance_km=max_distance_km,
            limit=limit,
            clean_only=False  # Include all plants for full context
        )
        
        logger.info(f"Found {len(nearby_plants_data)} nearby plants within {max_distance_km}km")
        
        # Convert to NearbyPowerPlant models
        nearby_plants = [
            NearbyPowerPlant(**plant_data)
            for plant_data in nearby_plants_data
        ]
        
        logger.info(f"Converted to {len(nearby_plants)} NearbyPowerPlant objects")
        
        return nearby_plants


# Example usage and testing
if __name__ == "__main__":
    from grid_data import generate_mock_grid_nodes
    
    # Initialize engine
    engine = SitingEngine()
    
    # Get mock data
    nodes = generate_mock_grid_nodes()
    
    print("=== Siting Engine Test ===\n")
    
    # Test 1: Evaluate Pacific Northwest Node A with default weights
    print("Test 1: Pacific Northwest Node A (default weights)")
    pnw_node = nodes[0]
    eval_result = engine.evaluate_site(pnw_node, all_nodes=nodes)
    print(f"  Composite Score: {eval_result.score_breakdown.composite_score:.1f}")
    print(f"  Percentile Rank: {eval_result.percentile_rank:.0f}th")
    print(f"  Notes: {eval_result.evaluation_notes[0]}")
    
    # Test 2: Custom weights favoring clean energy
    print("\nTest 2: Same node with clean-energy focused weights")
    clean_weights = SitingWeights(
        weight_clean=0.6,
        weight_transmission=0.2,
        weight_reliability=0.2
    )
    eval_clean = engine.evaluate_site(pnw_node, weights=clean_weights, all_nodes=nodes)
    print(f"  Composite Score: {eval_clean.score_breakdown.composite_score:.1f}")
    print(f"  Clean Gen Contribution: {eval_clean.score_breakdown.clean_gen_contribution:.1f}")
    
    # Test 3: Rank all sites
    print("\nTest 3: Top 5 sites (default weights)")
    ranked = engine.rank_sites(nodes, engine.default_weights)
    for i, (node, score) in enumerate(ranked[:5], 1):
        print(f"  {i}. {node.name}: {score:.1f}")
    
    # Test 4: Compare scenarios
    print("\nTest 4: Compare two different sites")
    eval1 = engine.evaluate_site(nodes[0], all_nodes=nodes)
    eval2 = engine.evaluate_site(nodes[2], all_nodes=nodes)
    comparison = engine.compare_scenarios([eval1, eval2], "PNW vs California")
    print(f"  Best site: {comparison.best_site_id}")
    print(f"  Score range: {comparison.score_range[0]:.1f} - {comparison.score_range[1]:.1f}")
    print(f"  Deltas: {comparison.score_deltas}")
