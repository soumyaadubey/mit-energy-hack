"""
Policy Simulation Engine for Industrial Emissions

Calculates impacts of carbon taxes, emissions caps, and filtering requirements
on steel, cement, and chemical facilities.
"""

from typing import List, Dict, Any
import logging
from models import (
    IndustrialFacility,
    PolicyScenario,
    PolicyImpactResult,
    CarbonTaxPolicy,
    EmissionsCap,
    FilteringRequirement
)

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Engine for simulating policy impacts on industrial emissions"""
    
    def __init__(self):
        # Technology costs (realistic estimates for industrial facilities)
        self.technology_costs = {
            "carbon_capture": {
                "capital_per_facility_million": 150,  # $150M typical for industrial CCS
                "annual_operating_pct": 0.08,  # 8% of capital cost annually
                "capture_efficiency": 0.90  # 90% CO2 capture
            },
            "scrubber": {
                "capital_per_facility_million": 50,
                "annual_operating_pct": 0.05,
                "capture_efficiency": 0.70
            },
            "process_improvement": {
                "capital_per_facility_million": 30,
                "annual_operating_pct": 0.03,
                "capture_efficiency": 0.20  # 20% efficiency improvement
            }
        }
        
        # Industry-specific parameters
        self.industry_baselines = {
            "steel": {
                "avg_emissions_mt_co2e": 1_500_000,  # 1.5M metric tons/year typical
                "production_unit": "metric_tons_steel",
                "carbon_intensity": 1.9,  # tCO2 per ton of steel (global avg)
                "hardest_to_decarbonize": True
            },
            "cement": {
                "avg_emissions_mt_co2e": 1_200_000,
                "production_unit": "metric_tons_cement",
                "carbon_intensity": 0.9,  # tCO2 per ton of cement
                "hardest_to_decarbonize": True  # Process emissions from limestone
            },
            "chemicals": {
                "avg_emissions_mt_co2e": 800_000,
                "production_unit": "metric_tons_product",
                "carbon_intensity": 1.5,  # Varies widely by chemical
                "hardest_to_decarbonize": False
            }
        }
    
    def calculate_carbon_tax_impact(
        self,
        facilities: List[IndustrialFacility],
        carbon_tax: CarbonTaxPolicy
    ) -> Dict[str, Any]:
        """
        Calculate revenue and cost impacts of carbon tax.
        
        Returns:
            - total_tax_revenue: Annual tax revenue
            - cost_by_industry: Tax cost breakdown by industry
            - cost_by_state: Tax cost breakdown by state
            - facilities_affected: Number of facilities subject to tax
        """
        total_revenue = 0.0
        cost_by_industry = {}
        cost_by_state = {}
        facilities_affected = 0
        
        for facility in facilities:
            # Check if facility is exempt
            if facility.naics_code in carbon_tax.exemptions:
                continue
            
            # Calculate tax for this facility
            emissions = facility.emissions_by_gas.total_co2e
            
            if carbon_tax.tax_type == "flat":
                tax_amount = emissions * carbon_tax.tax_rate_per_ton_co2e
            elif carbon_tax.tax_type == "progressive":
                # Progressive tax: higher rate for larger emitters
                if emissions < 100_000:
                    tax_amount = emissions * carbon_tax.tax_rate_per_ton_co2e * 0.5
                elif emissions < 500_000:
                    tax_amount = emissions * carbon_tax.tax_rate_per_ton_co2e
                else:
                    tax_amount = emissions * carbon_tax.tax_rate_per_ton_co2e * 1.5
            else:  # cap_and_trade
                # Simplified cap-and-trade (would need market price modeling)
                tax_amount = emissions * carbon_tax.tax_rate_per_ton_co2e * 0.7
            
            # Phase-in adjustment
            if carbon_tax.phase_in_years > 1:
                tax_amount = tax_amount / carbon_tax.phase_in_years
            
            total_revenue += tax_amount
            facilities_affected += 1
            
            # Aggregate by industry
            industry = facility.industry_type
            if industry not in cost_by_industry:
                cost_by_industry[industry] = {"facilities": 0, "total_cost": 0, "total_emissions": 0}
            cost_by_industry[industry]["facilities"] += 1
            cost_by_industry[industry]["total_cost"] += tax_amount
            cost_by_industry[industry]["total_emissions"] += emissions
            
            # Aggregate by state
            state = facility.state
            if state not in cost_by_state:
                cost_by_state[state] = {"facilities": 0, "total_cost": 0, "total_emissions": 0}
            cost_by_state[state]["facilities"] += 1
            cost_by_state[state]["total_cost"] += tax_amount
            cost_by_state[state]["total_emissions"] += emissions
        
        return {
            "total_tax_revenue": total_revenue,
            "cost_by_industry": cost_by_industry,
            "cost_by_state": cost_by_state,
            "facilities_affected": facilities_affected
        }
    
    def calculate_emissions_cap_impact(
        self,
        facilities: List[IndustrialFacility],
        emissions_cap: EmissionsCap
    ) -> Dict[str, Any]:
        """
        Calculate impact of emissions reduction targets.
        
        Returns:
            - target_reduction: Total emissions reduction needed (metric tons CO2e)
            - facilities_above_cap: Number of facilities exceeding their cap
            - estimated_compliance_cost: Cost to achieve reduction
        """
        baseline_year = emissions_cap.baseline_year
        target_reduction_pct = emissions_cap.reduction_percentage / 100.0
        
        total_baseline_emissions = sum(f.emissions_by_gas.total_co2e for f in facilities)
        target_emissions = total_baseline_emissions * (1 - target_reduction_pct)
        required_reduction = total_baseline_emissions - target_emissions
        
        # Estimate compliance cost (varies by industry difficulty)
        compliance_cost = 0.0
        facilities_above_cap = 0
        
        for facility in facilities:
            facility_reduction_needed = facility.emissions_by_gas.total_co2e * target_reduction_pct
            
            if facility_reduction_needed > 0:
                facilities_above_cap += 1
                
                # Cost depends on industry and reduction difficulty
                industry_params = self.industry_baselines.get(facility.industry_type, {})
                
                if industry_params.get("hardest_to_decarbonize"):
                    # Steel/cement: expensive to decarbonize (need CCS or process changes)
                    cost_per_ton = 200  # $200/ton CO2e reduced
                else:
                    # Chemicals: somewhat easier (fuel switching, efficiency)
                    cost_per_ton = 100  # $100/ton CO2e reduced
                
                compliance_cost += facility_reduction_needed * cost_per_ton
        
        return {
            "baseline_emissions": total_baseline_emissions,
            "target_emissions": target_emissions,
            "required_reduction_mt_co2e": required_reduction,
            "reduction_percentage": emissions_cap.reduction_percentage,
            "facilities_above_cap": facilities_above_cap,
            "estimated_compliance_cost": compliance_cost,
            "avg_cost_per_ton_reduced": compliance_cost / required_reduction if required_reduction > 0 else 0
        }
    
    def calculate_filtering_requirement_impact(
        self,
        facilities: List[IndustrialFacility],
        filtering_req: FilteringRequirement
    ) -> Dict[str, Any]:
        """
        Calculate cost and emissions impact of required filtering technology.
        
        Returns:
            - total_capital_cost: One-time installation cost
            - total_annual_operating_cost: Ongoing operating cost
            - emissions_captured_mt_co2e: Annual emissions reduction
            - facilities_affected: Number of facilities requiring technology
        """
        total_capital = 0.0
        total_annual_operating = 0.0
        emissions_captured = 0.0
        facilities_affected = 0
        
        for facility in facilities:
            # Check if this facility's industry must comply
            if filtering_req.applicable_industries:
                if facility.industry_type not in filtering_req.applicable_industries:
                    continue
            
            facilities_affected += 1
            
            # Costs
            total_capital += filtering_req.capital_cost_per_facility
            total_annual_operating += filtering_req.annual_operating_cost
            
            # Emissions reduction
            current_emissions = facility.emissions_by_gas.total_co2e
            captured = current_emissions * (filtering_req.capture_efficiency / 100.0)
            emissions_captured += captured
        
        return {
            "total_capital_cost": total_capital,
            "total_annual_operating_cost": total_annual_operating,
            "emissions_captured_mt_co2e": emissions_captured,
            "facilities_affected": facilities_affected,
            "cost_per_ton_co2e_captured": (
                (total_capital + total_annual_operating * 10) / emissions_captured
                if emissions_captured > 0 else 0
            )
        }
    
    def simulate_policy(
        self,
        facilities: List[IndustrialFacility],
        scenario: PolicyScenario
    ) -> PolicyImpactResult:
        """
        Run complete policy simulation.
        
        Combines carbon tax, emissions cap, and filtering requirements
        to project overall impact.
        """
        # Filter facilities based on scenario targets
        filtered_facilities = self._filter_facilities_for_scenario(facilities, scenario)
        
        baseline_emissions = sum(f.emissions_by_gas.total_co2e for f in filtered_facilities)
        
        # Calculate impacts from each policy component
        tax_impact = {}
        if scenario.carbon_tax:
            tax_impact = self.calculate_carbon_tax_impact(
                filtered_facilities,
                scenario.carbon_tax
            )
        
        cap_impact = {}
        if scenario.emissions_cap:
            cap_impact = self.calculate_emissions_cap_impact(
                filtered_facilities,
                scenario.emissions_cap
            )
        
        filtering_impacts = []
        for filtering_req in scenario.filtering_requirements:
            impact = self.calculate_filtering_requirement_impact(
                filtered_facilities,
                filtering_req
            )
            filtering_impacts.append(impact)
        
        # Aggregate emissions reduction
        emissions_reduction = 0.0
        if cap_impact:
            emissions_reduction += cap_impact.get("required_reduction_mt_co2e", 0)
        for f_impact in filtering_impacts:
            emissions_reduction += f_impact.get("emissions_captured_mt_co2e", 0)
        
        projected_emissions = baseline_emissions - emissions_reduction
        
        # Aggregate costs
        total_compliance_cost = cap_impact.get("estimated_compliance_cost", 0)
        for f_impact in filtering_impacts:
            total_compliance_cost += f_impact.get("total_capital_cost", 0)
            total_compliance_cost += f_impact.get("total_annual_operating_cost", 0) * 10  # 10-year estimate
        
        # Build result
        result = PolicyImpactResult(
            scenario=scenario,
            baseline_emissions_mt_co2e=baseline_emissions,
            projected_emissions_mt_co2e=projected_emissions,
            emissions_reduction_mt_co2e=emissions_reduction,
            emissions_reduction_percentage=(emissions_reduction / baseline_emissions * 100) if baseline_emissions > 0 else 0,
            total_carbon_tax_revenue=tax_impact.get("total_tax_revenue", 0),
            total_compliance_cost=total_compliance_cost,
            facilities_affected=len(filtered_facilities),
            impact_by_industry=self._aggregate_by_industry(filtered_facilities, tax_impact, cap_impact),
            impact_by_state=self._aggregate_by_state(filtered_facilities, tax_impact, cap_impact),
            emissions_trajectory=self._project_emissions_trajectory(
                baseline_emissions,
                emissions_reduction,
                scenario.phase_in_period_years
            )
        )
        
        return result
    
    def _filter_facilities_for_scenario(
        self,
        facilities: List[IndustrialFacility],
        scenario: PolicyScenario
    ) -> List[IndustrialFacility]:
        """Filter facilities based on scenario target criteria"""
        filtered = facilities
        
        if scenario.target_states:
            filtered = [f for f in filtered if f.state in scenario.target_states]
        
        if scenario.target_industries:
            filtered = [f for f in filtered if f.industry_type in scenario.target_industries]
        
        if scenario.target_naics_codes:
            filtered = [
                f for f in filtered
                if any(f.naics_code.startswith(code) for code in scenario.target_naics_codes)
            ]
        
        return filtered
    
    def _aggregate_by_industry(
        self,
        facilities: List[IndustrialFacility],
        tax_impact: Dict,
        cap_impact: Dict
    ) -> Dict[str, Dict[str, float]]:
        """Aggregate impacts by industry type"""
        by_industry = {}
        
        for industry in ["steel", "cement", "chemicals"]:
            industry_facilities = [f for f in facilities if f.industry_type == industry]
            
            if not industry_facilities:
                continue
            
            total_emissions = sum(f.emissions_by_gas.total_co2e for f in industry_facilities)
            
            industry_tax_data = tax_impact.get("cost_by_industry", {}).get(industry, {})
            
            by_industry[industry] = {
                "facilities_count": len(industry_facilities),
                "total_emissions": total_emissions,
                "tax_cost": industry_tax_data.get("total_cost", 0),
                "avg_emissions_per_facility": total_emissions / len(industry_facilities) if industry_facilities else 0
            }
        
        return by_industry
    
    def _aggregate_by_state(
        self,
        facilities: List[IndustrialFacility],
        tax_impact: Dict,
        cap_impact: Dict
    ) -> Dict[str, Dict[str, float]]:
        """Aggregate impacts by state"""
        by_state = {}
        
        for facility in facilities:
            state = facility.state
            if state not in by_state:
                by_state[state] = {
                    "facilities_count": 0,
                    "total_emissions": 0,
                    "tax_cost": 0
                }
            
            by_state[state]["facilities_count"] += 1
            by_state[state]["total_emissions"] += facility.emissions_by_gas.total_co2e
        
        # Add tax costs from tax_impact
        state_tax_data = tax_impact.get("cost_by_state", {})
        for state, data in state_tax_data.items():
            if state in by_state:
                by_state[state]["tax_cost"] = data.get("total_cost", 0)
        
        return by_state
    
    def _project_emissions_trajectory(
        self,
        baseline: float,
        total_reduction: float,
        phase_in_years: int
    ) -> List[Dict[str, Any]]:
        """
        Project year-by-year emissions trajectory during phase-in.
        
        Creates the "bending the curve" visualization data.
        """
        trajectory = []
        current_year = 2025  # Starting year
        
        for year in range(phase_in_years + 1):
            # Linear phase-in of reduction
            reduction_pct = year / phase_in_years if phase_in_years > 0 else 1.0
            current_reduction = total_reduction * reduction_pct
            projected_emissions = baseline - current_reduction
            
            trajectory.append({
                "year": current_year + year,
                "emissions_mt_co2e": projected_emissions,
                "cumulative_reduction": current_reduction,
                "reduction_percentage": (current_reduction / baseline * 100) if baseline > 0 else 0
            })
        
        return trajectory
