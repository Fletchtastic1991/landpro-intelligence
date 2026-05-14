# site_assessment.py
# ─────────────────────────────────────────────────────────────────────────────
# LandPro — Site Operational Assessment Engine
# Updated to consume terrain data from terrain_engine.py
#
# KEY CHANGE FROM V1:
#   Before:  SiteConditions(slope_percent=18)   ← hardcoded
#   Now:     terrain = analyze_terrain(polygon)
#            SiteConditions(slope_percent=terrain.average_slope_pct) ← derived
#
# This is the architectural shift the feedback described.
# The environment now generates the inputs.
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Tuple, Optional

# Import the terrain engine — this is the key dependency
from engines.terrain_engine import (
    TerrainAnalysisResult,
    analyze_terrain,
    terrain_to_slope_class,
)


# ─────────────────────────────────────────────────────────────────────────────
# INPUT MODELS
# ─────────────────────────────────────────────────────────────────────────────

class SiteConditions:
    """
    Facts about the land.
    
    V2 CHANGE: slope_percent now comes from TerrainAnalysisResult,
    not from a hardcoded value. Everything else stays the same.
    The terrain engine feeds this. This feeds the assessment engine.
    Clear, traceable data flow.
    """
    def __init__(
        self,
        slope_percent: float,
        soil_type: str,
        wetness: str,
        vegetation_density: str,
        rock_presence: bool,
        rain_last_48h_inches: float,
        water_feature: str,
        debris_present: str,
        terrain_result: Optional[TerrainAnalysisResult] = None,  # full terrain data attached
    ):
        self.slope_percent         = slope_percent
        self.soil_type             = soil_type
        self.wetness               = wetness
        self.vegetation_density    = vegetation_density
        self.rock_presence         = rock_presence
        self.rain_last_48h_inches  = rain_last_48h_inches
        self.water_feature         = water_feature
        self.debris_present        = debris_present
        self.terrain_result        = terrain_result  # carried through for traceability


class MachineProfile:
    """Facts about the machine being deployed."""
    def __init__(
        self,
        machine_type: str,
        weight_lbs: float,
        ground_pressure_psi: float,
        max_slope_percent: float,
    ):
        self.machine_type         = machine_type
        self.weight_lbs           = weight_lbs
        self.ground_pressure_psi  = ground_pressure_psi
        self.max_slope_percent    = max_slope_percent


# ─────────────────────────────────────────────────────────────────────────────
# FACTORY FUNCTION — Build SiteConditions from terrain + field observations
# This is the bridge between terrain_engine and site_assessment.
# ─────────────────────────────────────────────────────────────────────────────

def build_site_conditions(
    polygon_coordinates: List[Tuple[float, float]],
    soil_type: str,
    wetness: str,
    vegetation_density: str,
    rock_presence: bool,
    rain_last_48h_inches: float,
    water_feature: str,
    debris_present: str,
    user_reported_slope: Optional[str] = None,
) -> SiteConditions:
    """
    Build SiteConditions by running the terrain engine on the polygon.
    
    This is the function that wires the two engines together.
    Instead of the caller providing slope_percent directly,
    they provide the polygon and the terrain engine derives it.
    
    The user_reported_slope is still accepted as a calibration hint
    until USGS data is integrated — it improves the placeholder estimate.
    
    Returns SiteConditions with slope derived from terrain analysis.
    """
    # Run terrain engine on the polygon
    terrain = analyze_terrain(polygon_coordinates, user_reported_slope)

    # Convert terrain result to slope percentage
    # Using average_slope_pct as the primary operational input
    slope_percent = terrain.average_slope_pct

    return SiteConditions(
        slope_percent         = slope_percent,
        soil_type             = soil_type,
        wetness               = wetness,
        vegetation_density    = vegetation_density,
        rock_presence         = rock_presence,
        rain_last_48h_inches  = rain_last_48h_inches,
        water_feature         = water_feature,
        debris_present        = debris_present,
        terrain_result        = terrain,  # attach full terrain data for traceability
    )


# ─────────────────────────────────────────────────────────────────────────────
# HARD RULES
# ─────────────────────────────────────────────────────────────────────────────

class HardRuleViolation:
    def __init__(self, code: str, message: str, severity: str = "critical"):
        self.code     = code
        self.message  = message
        self.severity = severity

    def __repr__(self):
        return f"[{self.severity.upper()}] {self.code}: {self.message}"


def check_hard_rules(site: SiteConditions, machine: MachineProfile) -> list:
    violations = []

    if site.slope_percent > machine.max_slope_percent:
        violations.append(HardRuleViolation(
            code="SLOPE_EXCEEDS_MACHINE_LIMIT",
            message=(
                f"Slope of {site.slope_percent}% exceeds this machine's "
                f"maximum rated slope of {machine.max_slope_percent}%. "
                f"Operation is unsafe. Use a machine rated for steeper terrain."
            ),
            severity="critical"
        ))

    if site.water_feature == "wetland" and site.wetness == "high":
        violations.append(HardRuleViolation(
            code="WETLAND_HIGH_SATURATION",
            message=(
                "Wetland area with high soil saturation detected. "
                "Army Corps Section 404 permit required before any ground disturbance. "
                "Verify permit status before mobilizing."
            ),
            severity="blocked"
        ))

    if site.rock_presence and machine.machine_type == "wheeled_skid_steer":
        violations.append(HardRuleViolation(
            code="EQUIPMENT_MISMATCH_ROCKY",
            message=(
                "Surface rock detected with wheeled machine selected. "
                "Use track-mounted equipment for this site."
            ),
            severity="critical"
        ))

    if (site.soil_type == "clay"
            and site.rain_last_48h_inches > 1.5
            and machine.weight_lbs > 10000):
        violations.append(HardRuleViolation(
            code="CLAY_SATURATION_HEAVY_MACHINE",
            message=(
                f"Clay soil with {site.rain_last_48h_inches}\" of rain and a "
                f"{machine.weight_lbs:,} lb machine. Delay 48–72 hours or use "
                f"lower ground pressure machine (target < 4 psi)."
            ),
            severity="critical"
        ))

    if site.slope_percent > 15 and site.wetness == "high":
        violations.append(HardRuleViolation(
            code="WET_SLOPE_ROLLOVER_RISK",
            message=(
                f"Slope of {site.slope_percent}% with high soil saturation. "
                f"Elevated rollover risk. Delay until ground dries or restrict "
                f"to slopes below 10%."
            ),
            severity="critical"
        ))

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# RISK SCORING
# ─────────────────────────────────────────────────────────────────────────────

class RiskContribution:
    def __init__(self, factor: str, points: int, reason: str):
        self.factor = factor
        self.points = points
        self.reason = reason


def calculate_risk_score(site: SiteConditions, machine: MachineProfile) -> tuple:
    contributions = []
    score = 0

    if site.slope_percent > 20:
        contributions.append(RiskContribution("slope_severe", 35,
            f"Slope {site.slope_percent}% — track equipment mandatory, certified operators required."))
    elif site.slope_percent > 15:
        contributions.append(RiskContribution("slope_high", 25,
            f"Slope {site.slope_percent}% — significant rollover risk and reduced efficiency."))
    elif site.slope_percent > 8:
        contributions.append(RiskContribution("slope_moderate", 10,
            f"Slope {site.slope_percent}% — monitor stability and drainage."))

    if site.wetness == "high":
        contributions.append(RiskContribution("wetness_high", 30,
            "High soil saturation — major rutting risk, equipment mobility reduced."))
    elif site.wetness == "moderate":
        contributions.append(RiskContribution("wetness_moderate", 15,
            "Moderate saturation — some rutting expected, monitor low-lying areas."))

    if site.soil_type == "clay":
        contributions.append(RiskContribution("soil_clay", 20,
            "Clay soil — holds water, very high rutting potential."))
    elif site.soil_type == "rocky":
        contributions.append(RiskContribution("soil_rocky", 15,
            "Rocky soil — equipment wear, traction issues."))

    if site.rain_last_48h_inches > 2.0:
        contributions.append(RiskContribution("rain_heavy", 20,
            f"{site.rain_last_48h_inches}\" rain in 48 hours — ground likely saturated."))
    elif site.rain_last_48h_inches > 0.5:
        contributions.append(RiskContribution("rain_moderate", 10,
            f"{site.rain_last_48h_inches}\" rain in 48 hours — monitor soft spots."))

    if site.vegetation_density == "heavy":
        contributions.append(RiskContribution("vegetation_heavy", 10,
            "Heavy vegetation — reduced visibility, hidden hazards."))

    if site.water_feature == "wetland":
        contributions.append(RiskContribution("water_wetland", 15,
            "Wetland present — regulatory requirements, soft ground near water."))
    elif site.water_feature == "pond_or_creek":
        contributions.append(RiskContribution("water_creek", 8,
            "Water feature present — maintain setback, erosion control required."))

    if machine.ground_pressure_psi > 8 and site.wetness in ["moderate", "high"]:
        contributions.append(RiskContribution("ground_pressure_wet", 15,
            f"Machine at {machine.ground_pressure_psi} psi is high for wet conditions."))

    # If terrain data is available and shows high variability, add points
    if site.terrain_result and site.terrain_result.terrain_variability in ["rugged", "extreme"]:
        contributions.append(RiskContribution("terrain_variability", 10,
            f"Terrain variability is '{site.terrain_result.terrain_variability}' — "
            f"uneven ground increases machine stability risk."))

    score = min(100, sum(c.points for c in contributions))
    return score, contributions


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

class Recommendation:
    def __init__(self, action: str, reason: str, priority: str = "recommended"):
        self.action   = action
        self.reason   = reason
        self.priority = priority


def derive_recommendations(site: SiteConditions, machine: MachineProfile, risk_score: int) -> list:
    recs = []

    if site.rain_last_48h_inches > 1.5 and site.soil_type in ["clay", "loam"]:
        recs.append(Recommendation(
            action="Delay operation 48–72 hours to allow ground to dry",
            reason=f"Clay/loam soil with {site.rain_last_48h_inches}\" of rain creates extreme rutting risk.",
            priority="required"
        ))

    if site.slope_percent > 20:
        recs.append(Recommendation(
            action="Use track-mounted equipment only — no wheeled machines on this site",
            reason=f"Slope of {site.slope_percent}% requires maximum traction.",
            priority="required"
        ))

    if site.wetness == "high" and machine.ground_pressure_psi > 6:
        recs.append(Recommendation(
            action="Switch to lower ground pressure equipment (target < 4 psi) or use timber mats in wet areas",
            reason=f"Machine at {machine.ground_pressure_psi} psi will cause rutting in wet areas.",
            priority="required"
        ))

    if site.slope_percent > 15:
        recs.append(Recommendation(
            action="Assign only OSHA-certified operators to slope operations",
            reason="OSHA requires certified operators on slopes above 15%. This is a legal requirement.",
            priority="required"
        ))

    if site.slope_percent > 8:
        recs.append(Recommendation(
            action="Install erosion control (silt fencing) at base of slope before clearing begins",
            reason="Clearing removes vegetation that holds soil. Erosion control required before ground disturbance.",
            priority="required"
        ))

    if site.water_feature == "wetland":
        recs.append(Recommendation(
            action="Verify Army Corps Section 404 permit before any ground disturbance",
            reason="Permit timeline is 60–120 days. Work without permit risks $25,000+ fines.",
            priority="required"
        ))

    if site.water_feature in ["pond_or_creek", "wetland"]:
        recs.append(Recommendation(
            action="Mark and maintain 50 ft equipment exclusion zone from water edge",
            reason="Most counties require 25–100 ft buffer from waterways. Verify local setback requirements.",
            priority="required"
        ))

    if site.vegetation_density == "heavy":
        recs.append(Recommendation(
            action="Walk the site on foot before machine entry to identify hidden hazards",
            reason="Dense canopy conceals stumps, debris, sinkholes, and old structures.",
            priority="recommended"
        ))
        recs.append(Recommendation(
            action="Request timber cruise if merchantable trees are suspected",
            reason="Identifies trees with resale value before clearing — recovers cost.",
            priority="optional"
        ))

    if risk_score >= 60:
        recs.append(Recommendation(
            action="Conduct on-site supervisor review before operation begins",
            reason=f"Risk score of {risk_score}/100 indicates significant operational complexity.",
            priority="required"
        ))

    if site.debris_present == "heavy":
        recs.append(Recommendation(
            action="Conduct hazardous material inspection before clearing",
            reason="Heavy debris may contain materials requiring licensed disposal.",
            priority="required"
        ))

    # Terrain-specific recommendation if we have real terrain data
    if site.terrain_result:
        if site.terrain_result.terrain_variability == "extreme":
            recs.append(Recommendation(
                action="Commission topographic survey before finalizing equipment selection",
                reason=(
                    f"Terrain variability is '{site.terrain_result.terrain_variability}' "
                    f"with estimated elevation range of {site.terrain_result.elevation_range_ft} ft. "
                    f"Equipment selection depends heavily on actual grade distribution."
                ),
                priority="recommended"
            ))

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT + MAIN ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class AssessmentResult:
    def __init__(self, operation_status, risk_score, risk_level,
                 hard_violations, risk_contributions, recommendations, summary,
                 terrain_result=None):
        self.operation_status    = operation_status
        self.risk_score          = risk_score
        self.risk_level          = risk_level
        self.hard_violations     = hard_violations
        self.risk_contributions  = risk_contributions
        self.recommendations     = recommendations
        self.summary             = summary
        self.terrain_result      = terrain_result  # terrain data attached for traceability

    def display(self):
        print("\n" + "="*65)
        print("  LANDPRO SITE OPERATIONAL ASSESSMENT")
        print("="*65)
        print(f"\n  STATUS:     {self.operation_status}")
        print(f"  RISK SCORE: {self.risk_score}/100")
        print(f"  RISK LEVEL: {self.risk_level}")
        print(f"\n  SUMMARY: {self.summary}")

        # Show terrain data source so user knows if it's estimated
        if self.terrain_result:
            print(f"\n  ── TERRAIN DATA ({self.terrain_result.data_source}, confidence: {self.terrain_result.confidence}) ──")
            print(f"  Average slope:      {self.terrain_result.average_slope_pct}%")
            print(f"  Max slope:          {self.terrain_result.max_slope_pct}%")
            print(f"  Elevation range:    {self.terrain_result.elevation_range_ft} ft")
            print(f"  Terrain class:      {self.terrain_result.slope_class}")
            print(f"  Variability:        {self.terrain_result.terrain_variability}")

        if self.hard_violations:
            print("\n  ── HARD VIOLATIONS (non-negotiable) ──")
            for v in self.hard_violations:
                print(f"\n  ❌ [{v.severity.upper()}] {v.code}")
                print(f"     {v.message}")

        if self.risk_contributions:
            print("\n  ── RISK SCORE BREAKDOWN ──")
            for c in self.risk_contributions:
                print(f"  +{c.points:2d} pts  {c.reason}")

        if self.recommendations:
            print("\n  ── RECOMMENDATIONS ──")
            for priority in ["required", "recommended", "optional"]:
                group = [r for r in self.recommendations if r.priority == priority]
                if group:
                    print(f"\n  {priority.upper()}:")
                    for r in group:
                        print(f"  → {r.action}")
                        print(f"    Why: {r.reason}")

        print("\n" + "="*65 + "\n")


def assess_site(site: SiteConditions, machine: MachineProfile) -> AssessmentResult:
    """Run the complete operational assessment. Same interface as V1."""
    violations    = check_hard_rules(site, machine)
    risk_score, contributions = calculate_risk_score(site, machine)
    recommendations = derive_recommendations(site, machine, risk_score)

    if violations:
        has_critical = any(v.severity == "critical" for v in violations)
        operation_status = "UNSAFE" if has_critical else "BLOCKED"
        risk_level = "Severe"
        summary = f"Operation cannot proceed — {len(violations)} non-negotiable violation(s) detected."
    elif risk_score >= 80:
        operation_status = "HIGH_RISK"
        risk_level = "Severe"
        summary = f"Risk score {risk_score}/100. Operation should be reconsidered or significantly modified."
    elif risk_score >= 60:
        operation_status = "HIGH_RISK"
        risk_level = "High"
        summary = f"Risk score {risk_score}/100. Significant precautions and supervisor review required."
    elif risk_score >= 30:
        operation_status = "CAUTION"
        risk_level = "Moderate"
        summary = f"Risk score {risk_score}/100. Standard precautions apply."
    else:
        operation_status = "SAFE"
        risk_level = "Low"
        summary = f"Risk score {risk_score}/100. Conditions are favorable."

    return AssessmentResult(
        operation_status   = operation_status,
        risk_score         = risk_score,
        risk_level         = risk_level,
        hard_violations    = violations,
        risk_contributions = contributions,
        recommendations    = recommendations,
        summary            = summary,
        terrain_result     = site.terrain_result,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEST — Shows the full flow: polygon → terrain engine → site assessment
# Run: python site_assessment.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\nDemonstrating full flow: polygon → terrain engine → site assessment")
    print("─" * 65)
    print("This is the architectural shift: terrain engine feeds site assessment.")
    print("Slope is no longer hardcoded — it's derived from the polygon.\n")

    # ── Test 1: Full flow — polygon drives everything ─────────────────────────
    print("Test 1: Heavy clearing, irregular polygon, user reports slight slope")

    polygon = [
        (-97.1250, 32.7900),
        (-97.1230, 32.7915),
        (-97.1205, 32.7908),
        (-97.1195, 32.7885),
        (-97.1212, 32.7868),
        (-97.1243, 32.7862),
        (-97.1258, 32.7875),
        (-97.1250, 32.7900),
    ]

    # This is the new way — terrain engine derives slope from polygon
    site = build_site_conditions(
        polygon_coordinates  = polygon,
        soil_type            = "clay",
        wetness              = "high",
        vegetation_density   = "heavy",
        rock_presence        = False,
        rain_last_48h_inches = 2.1,
        water_feature        = "pond_or_creek",
        debris_present       = "light",
        user_reported_slope  = "slight_slope",  # calibration hint
    )

    machine = MachineProfile(
        machine_type        = "tracked_dozer",
        weight_lbs          = 35000,
        ground_pressure_psi = 4.2,
        max_slope_percent   = 25,
    )

    result = assess_site(site, machine)
    result.display()

    # ── Test 2: Flat clean site ───────────────────────────────────────────────
    print("Test 2: Light clearing, rectangular polygon, flat")

    flat_polygon = [
        (-97.1234, 32.7891),
        (-97.1220, 32.7891),
        (-97.1220, 32.7880),
        (-97.1234, 32.7880),
        (-97.1234, 32.7891),
    ]

    site2 = build_site_conditions(
        polygon_coordinates  = flat_polygon,
        soil_type            = "sandy",
        wetness              = "dry",
        vegetation_density   = "light",
        rock_presence        = False,
        rain_last_48h_inches = 0.0,
        water_feature        = "none",
        debris_present       = "none",
        user_reported_slope  = "flat",
    )

    machine2 = MachineProfile(
        machine_type        = "tracked_skid_steer",
        weight_lbs          = 8500,
        ground_pressure_psi = 3.8,
        max_slope_percent   = 20,
    )

    result2 = assess_site(site2, machine2)
    result2.display()