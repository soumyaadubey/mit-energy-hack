"""
Siting Engine for Smart Grid Optimization

Calculates composite siting scores using weighted criteria and ranks alternative locations.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import math
from models_grid import (
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
    
    def evaluate_site(
        self,
        node: GridNode,
        weights: Optional[SitingWeights] = None,
        demand_profile: Optional[DemandProfile] = None,
        all_nodes: Optional[List[GridNode]] = None
    ) -> SiteEvaluation:
        """
        Complete site evaluation with ranking context.
        
        Args:
            node: Grid node to evaluate
            weights: Siting criteria weights (uses defaults if None)
            demand_profile: Optional load profile for context
            all_nodes: All available nodes for percentile calculation
        
        Returns:
            SiteEvaluation with score, breakdown, and ranking context
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
        
        # Generate evaluation notes
        notes = self._generate_evaluation_notes(node, score_breakdown)
        
        evaluation = SiteEvaluation(
            site=node,
            weights=weights,
            demand_profile=demand_profile,
            score_breakdown=score_breakdown,
            percentile_rank=percentile_rank,
            alternative_sites=alternative_sites,
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
