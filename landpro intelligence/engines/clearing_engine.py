# engines/clearing_engine.py
# ─────────────────────────────────────────────────────────────────────────────
# This is the Python port of src/engines/ClearingPro.ts
#
# Same logic. Same math. Different language.
# TypeScript uses camelCase  → Python uses snake_case
# TypeScript uses interfaces → Python uses Pydantic models (dataclasses with validation)
# TypeScript uses const/let  → Python just writes the variable name
# ─────────────────────────────────────────────────────────────────────────────

# Pydantic is like TypeScript interfaces — it defines what shape data must be
# and automatically validates it. If you send wrong data, it returns a clear error.
from pydantic import BaseModel, Field

# Optional means a field doesn't have to be provided
# List is like TypeScript's array type
from typing import Optional, List

# Import our config — single source of truth for all numbers
from core.config import (
    TERRAIN_MULTIPLIERS,
    ACCESS_MULTIPLIERS,
    WATER_MULTIPLIERS,
    PRODUCTION_HOURS,
    MACHINE_RATE_PER_HR,
    LABOR_RATE_PER_HR,
    CREW_BY_VEGETATION,
    BASELINE_PER_ACRE_MIN,
    BASELINE_PER_ACRE_MAX,
    BASELINE_LABEL,
)


# ─── Input Model ──────────────────────────────────────────────────────────────
# This is like ClearingProInput in TypeScript.
# Pydantic automatically validates that the data matches these types.
# If someone sends "vegetation": "none", it will return an error immediately.

class ClearingInput(BaseModel):
    # Field() lets us add descriptions — shown in the auto-generated API docs
    acreage:         float  = Field(..., gt=0, description="Property size in acres")
    vegetation:      str    = Field(..., pattern="^(light|medium|heavy)$")
    terrain:         str    = Field(..., pattern="^(flat|slight_slope|steep)$")
    accessibility:   str    = Field(..., pattern="^(easy|moderate|difficult)$")
    water:           str    = Field(..., pattern="^(none|pond_or_creek|wetland)$")
    debris:          str    = Field(..., pattern="^(none|light|heavy)$")
    structures:      str    = Field(..., pattern="^(none|fencing|buildings_utilities)$")
    production_rate: str    = Field(..., pattern="^(conservative|standard|aggressive)$")
    # ... means "required" — no default value


# ─── Output Models ────────────────────────────────────────────────────────────
# These define what we RETURN. TypeScript reads these as JSON.
# Each class = one section of the result.

class HoursResult(BaseModel):
    base_min:     float
    base_max:     float
    adjusted_min: float
    adjusted_max: float
    terrain_factor: float
    access_factor:  float
    water_factor:   float


class CrewResult(BaseModel):
    size:          int
    difficulty:    str
    assumption:    str
    justification: str


class CostAddon(BaseModel):
    label: str
    low:   int
    high:  int


class CostResult(BaseModel):
    machine_min:  int
    machine_max:  int
    labor_min:    int
    labor_max:    int
    addons:       List[CostAddon]
    total_min:    int
    total_max:    int
    per_acre_min: int
    per_acre_max: int
    per_acre_note: str


class CostDriver(BaseModel):
    label:  str
    impact: str


class RealityAnchor(BaseModel):
    baseline_range:   str
    baseline_label:   str
    exceeds_by:       Optional[str]     # Optional = can be None/null
    exceeds_reasons:  List[str]


class RiskFactor(BaseModel):
    label:       str
    consequence: str
    severity:    str    # "high", "medium", or "low"


class ConfidenceDimension(BaseModel):
    level: str  # "High", "Medium", or "Low"
    note:  str


class ConfidenceBreakdown(BaseModel):
    geometry:        ConfidenceDimension
    site_conditions: ConfidenceDimension
    cost_model:      ConfidenceDimension


class ConfidenceResult(BaseModel):
    level:      str   # "Medium" or "Low" — High is intentionally excluded
    breakdown:  ConfidenceBreakdown
    disclaimer: str


class ClearingResult(BaseModel):
    """The complete result returned to TypeScript."""
    status:          str   # "available" or "blocked"
    reason_if_blocked: Optional[str]

    hours:          Optional[HoursResult]
    crew:           Optional[CrewResult]
    cost:           Optional[CostResult]
    cost_drivers:   List[CostDriver]
    reality_anchor: Optional[RealityAnchor]
    equipment:      List[str]
    risk_factors:   List[RiskFactor]
    non_linear_flags: List[str]
    confidence:     Optional[ConfidenceResult]


# ─── Main Engine Function ─────────────────────────────────────────────────────
# This is the Python version of runClearingPro() in ClearingPro.ts
# Same logic, same math, just Python syntax.

def run_clearing_engine(input: ClearingInput) -> ClearingResult:
    """
    Run the clearing cost engine.
    Takes field observations → returns hours, cost, risk factors, confidence.
    """

    # ── Get multipliers from config ──────────────────────────────────────────
    # In TypeScript: const tFac = TERRAIN_HRS[input.terrain]
    # In Python:     t_fac = TERRAIN_MULTIPLIERS[input.terrain]

    t_fac = TERRAIN_MULTIPLIERS[input.terrain]
    a_fac = ACCESS_MULTIPLIERS[input.accessibility]
    w_fac = WATER_MULTIPLIERS[input.water]

    # Count how many multipliers are stacked (used to degrade confidence)
    stacked_multipliers = sum([
        1 if t_fac > 1 else 0,
        1 if a_fac > 1 else 0,
        1 if w_fac > 1 else 0,
    ])

    # ── Hours calculation ────────────────────────────────────────────────────
    # In TypeScript: const [baseMin, baseMax] = PROD_HOURS[rate][vegetation]
    # In Python:     base_min, base_max = PRODUCTION_HOURS[rate][vegetation]

    base_min, base_max = PRODUCTION_HOURS[input.production_rate][input.vegetation]

    # Multiply base hours by acreage, then apply condition multipliers
    # This is identical math to ClearingPro.ts — just Python syntax
    adj_min = round(base_min * input.acreage * t_fac * a_fac * w_fac, 1)
    adj_max = round(base_max * input.acreage * t_fac * a_fac * w_fac, 1)

    hours = HoursResult(
        base_min=round(base_min * input.acreage, 1),
        base_max=round(base_max * input.acreage, 1),
        adjusted_min=adj_min,
        adjusted_max=adj_max,
        terrain_factor=t_fac,
        access_factor=a_fac,
        water_factor=w_fac,
    )

    # ── Crew ─────────────────────────────────────────────────────────────────

    crew_def  = CREW_BY_VEGETATION[input.vegetation]
    crew_size = crew_def["size"]

    # Determine difficulty label
    if input.vegetation == "heavy" or input.terrain == "steep" or input.accessibility == "difficult":
        difficulty = "Challenging"
    elif input.vegetation == "medium" or input.terrain == "slight_slope":
        difficulty = "Moderate"
    else:
        difficulty = "Standard"

    crew = CrewResult(
        size=crew_size,
        difficulty=difficulty,
        assumption=crew_def["assumption"],
        justification=crew_def["justification"],
    )

    # ── Cost calculation ─────────────────────────────────────────────────────
    # machine cost = hours × $150/hr
    # labor cost   = hours × crew_size × $50/hr
    # Same formula as ClearingPro.ts

    machine_min = round(adj_min * MACHINE_RATE_PER_HR)
    machine_max = round(adj_max * MACHINE_RATE_PER_HR)
    labor_min   = round(adj_min * crew_size * LABOR_RATE_PER_HR)
    labor_max   = round(adj_max * crew_size * LABOR_RATE_PER_HR)

    addons    = _build_addons(input)
    addon_min = sum(a.low  for a in addons)
    addon_max = sum(a.high for a in addons)

    # Round to nearest $100 — avoids false precision
    total_min = round((machine_min + labor_min + addon_min) / 100) * 100
    total_max = round((machine_max + labor_max + addon_max) / 100) * 100

    per_acre_min = round(total_min / input.acreage / 100) * 100
    per_acre_max = round(total_max / input.acreage / 100) * 100

    cost = CostResult(
        machine_min=machine_min,
        machine_max=machine_max,
        labor_min=labor_min,
        labor_max=labor_max,
        addons=addons,
        total_min=total_min,
        total_max=total_max,
        per_acre_min=per_acre_min,
        per_acre_max=per_acre_max,
        per_acre_note=_build_per_acre_note(input),
    )

    # ── Everything else ──────────────────────────────────────────────────────

    cost_drivers     = _build_cost_drivers(input, stacked_multipliers)
    reality_anchor   = _build_reality_anchor(input, per_acre_min, per_acre_max)
    non_linear_flags = _build_non_linear_flags(input)
    risk_factors     = _build_risk_factors(input)
    confidence       = _build_confidence(input, risk_factors, stacked_multipliers)
    equipment        = _build_equipment(input)

    return ClearingResult(
        status="available",
        reason_if_blocked=None,
        hours=hours,
        crew=crew,
        cost=cost,
        cost_drivers=cost_drivers,
        reality_anchor=reality_anchor,
        equipment=equipment,
        risk_factors=risk_factors,
        non_linear_flags=non_linear_flags,
        confidence=confidence,
    )


# ─── Helper functions ─────────────────────────────────────────────────────────
# In Python, functions starting with _ are "private" by convention
# They're only meant to be used inside this file, not imported elsewhere.

def _build_addons(input: ClearingInput) -> List[CostAddon]:
    """Build fixed cost addons based on conditions."""
    addons = []

    # Each condition adds a specific fixed cost range — not a percentage
    if input.debris == "light":
        addons.append(CostAddon(label="Light debris haul-off", low=500, high=1500))
    if input.debris == "heavy":
        addons.append(CostAddon(label="Heavy debris haul-off", low=2000, high=6000))
    if input.water == "pond_or_creek":
        addons.append(CostAddon(label="Erosion control / silt fencing", low=300, high=800))
    if input.water == "wetland":
        addons.append(CostAddon(label="Wetland erosion control + consultant", low=1500, high=5000))
    if input.accessibility == "difficult":
        addons.append(CostAddon(label="Equipment mobilization", low=1000, high=3000))
    if input.structures == "fencing":
        addons.append(CostAddon(label="Remove existing fencing", low=300, high=1000))
    if input.structures == "buildings_utilities":
        addons.append(CostAddon(label="Utility locate + demo", low=500, high=2500))

    return addons


def _build_cost_drivers(input: ClearingInput, stacked_multipliers: int) -> List[CostDriver]:
    """Explain WHY the estimate is what it is — shown above total cost."""
    drivers = []

    if input.vegetation == "heavy":
        drivers.append(CostDriver(
            label="Heavy vegetation",
            impact="Requires D6/D7 dozer + forestry mulcher — heaviest equipment class, highest hourly rate"
        ))
    elif input.vegetation == "medium":
        drivers.append(CostDriver(
            label="Medium vegetation",
            impact="Mixed stand requires forestry mulcher and material management simultaneously"
        ))

    if input.acreage < 2:
        drivers.append(CostDriver(
            label=f"Small parcel ({input.acreage} ac)",
            impact="Mobilization, setup, and teardown costs don't scale down — fixed costs dominate small jobs"
        ))

    if input.terrain == "steep":
        drivers.append(CostDriver(
            label="Steep terrain",
            impact="Track equipment required, slower production rate, specialized operators"
        ))
    elif input.terrain == "slight_slope":
        drivers.append(CostDriver(
            label="Sloped terrain",
            impact="Reduced equipment efficiency — terrain factor applied to all hours"
        ))

    if input.water == "wetland":
        drivers.append(CostDriver(
            label="Wetland area",
            impact="Wetland-rated equipment required, consultant likely needed, regulatory compliance adds scope"
        ))
    elif input.water == "pond_or_creek":
        drivers.append(CostDriver(
            label="Water present",
            impact="Soft ground near water, erosion controls required, may restrict equipment access zones"
        ))

    if input.accessibility == "difficult":
        drivers.append(CostDriver(
            label="Difficult access",
            impact="Mobilization add-on applied — remote haul road or specialized transport likely needed"
        ))

    if input.debris == "heavy":
        drivers.append(CostDriver(
            label="Heavy debris",
            impact="Haul-off add-on applied — licensed disposal required for heavy material"
        ))

    if stacked_multipliers >= 2:
        drivers.append(CostDriver(
            label="Multiple compounding conditions",
            impact=f"{stacked_multipliers} condition multipliers stacked — effects interact non-linearly in the field"
        ))

    return drivers


def _build_reality_anchor(input: ClearingInput, per_acre_min: int, per_acre_max: int):
    """Compare this estimate to baseline clearing cost — grounds high numbers."""
    exceeds_reasons = []
    is_above_baseline = per_acre_min > BASELINE_PER_ACRE_MAX

    if is_above_baseline:
        if input.vegetation == "heavy":
            exceeds_reasons.append("heavy vegetation (vs. open land)")
        if input.terrain != "flat":
            exceeds_reasons.append("sloped terrain")
        if input.water != "none":
            exceeds_reasons.append("water presence")
        if input.accessibility != "easy":
            exceeds_reasons.append("access difficulty")
        if input.acreage < 2:
            exceeds_reasons.append("small parcel size")
        if input.debris != "none":
            exceeds_reasons.append("debris disposal")

    return RealityAnchor(
        baseline_range=f"${BASELINE_PER_ACRE_MIN:,}–${BASELINE_PER_ACRE_MAX:,}/acre",
        baseline_label=BASELINE_LABEL,
        exceeds_by=f"This site runs ${per_acre_min:,}–${per_acre_max:,}/acre" if is_above_baseline else None,
        exceeds_reasons=exceeds_reasons,
    )


def _build_non_linear_flags(input: ClearingInput) -> List[str]:
    """
    Diagnosis-level flags — explains WHY the math breaks down.
    These are not warnings. They are explanations of non-linear reality.
    """
    flags = []

    if input.vegetation == "heavy" and input.water != "none":
        flags.append(
            "DIAGNOSIS — Heavy vegetation + water: Linear math underestimates this job. "
            "Wet ground under dense canopy causes machines to bog down. The clearing method "
            "may need to change from mulch-in-place to cut-and-pile — a fundamentally different "
            "operation. Expect actual hours to exceed the model by 20–50%."
        )

    if input.terrain == "steep" and input.vegetation == "heavy":
        flags.append(
            "DIAGNOSIS — Steep terrain + heavy vegetation: This combination can require "
            "hand-felling before machine clearing begins. That's a separate labor crew, "
            "separate scheduling, and separate cost not captured in any per-acre model. "
            "If slope exceeds 30%, treat this estimate as a floor, not a range."
        )

    if input.accessibility == "difficult" and input.vegetation == "heavy":
        flags.append(
            "DIAGNOSIS — Remote site + heavy clearing: Haul road construction may need "
            "to happen before clearing starts — potentially as a separate mobilization event. "
            "This can cost as much as the clearing itself. Estimates begin at the property "
            "line, not the nearest road."
        )

    if input.water == "wetland":
        flags.append(
            "DIAGNOSIS — Wetland on parcel: Permitting, mitigation banking, and compliance "
            "costs exist independently of clearing cost and can exceed it. The clearing "
            "estimate is only one part of the total project cost on a wetland site."
        )

    return flags


def _build_risk_factors(input: ClearingInput) -> List[RiskFactor]:
    """
    Risk factors sorted high → medium → low.
    Each one states a CONSEQUENCE, not just an observation.
    """
    risks = []

    # Always present
    risks.append(RiskFactor(
        label="Hours are pre-site-visit",
        consequence="Actual stump density and ground conditions aren't visible from the map. A denser stand can double machine hours without warning.",
        severity="medium"
    ))
    risks.append(RiskFactor(
        label="Permitting not included",
        consequence="County clearing and disposal permits vary. Some require pre-clearing inspection. Not reflected in cost or timeline.",
        severity="medium"
    ))

    if input.vegetation == "heavy":
        risks.append(RiskFactor(
            label="Dense canopy hides ground hazards",
            consequence="Stumps, debris piles, sinkholes won't be visible until clearing begins. Budget 10–20% additional machine time for discovery.",
            severity="high"
        ))
        risks.append(RiskFactor(
            label="Timber may have resale value",
            consequence="A timber cruise before clearing could recover $500–$5,000+. Skip it and you leave money on the ground.",
            severity="medium"
        ))

    if input.terrain == "steep":
        risks.append(RiskFactor(
            label="Slope increases rollover risk",
            consequence="OSHA requires certified operators on slopes above 15%. Specialist crews cost 20–40% more per hour.",
            severity="high"
        ))
        risks.append(RiskFactor(
            label="Erosion control plan required",
            consequence="Most counties require an approved E&S plan before ground disturbance on slopes. Without it, work can be stopped mid-project.",
            severity="high"
        ))

    if input.water == "wetland":
        risks.append(RiskFactor(
            label="Federal permit likely required",
            consequence="Army Corps Section 404 permit required for wetland disturbance. Timeline 60–120 days minimum. Work without it risks $25k+ fines.",
            severity="high"
        ))

    if input.water == "pond_or_creek":
        risks.append(RiskFactor(
            label="Waterway setback may restrict clearing area",
            consequence="Most counties require 25–100 ft vegetated buffers from waterways. You may not be able to clear the full acreage shown.",
            severity="high"
        ))

    if input.accessibility == "difficult":
        risks.append(RiskFactor(
            label="Haul road may be needed first",
            consequence="Without equipment access, clearing can't begin. Road construction ($3k–$15k) must happen first — separate from clearing cost.",
            severity="high"
        ))

    if input.structures == "buildings_utilities":
        risks.append(RiskFactor(
            label="Underground utilities — call 811",
            consequence="Hitting a buried line stops the job instantly. Unexpected utility work can add $2k–$10k+ to the project.",
            severity="high"
        ))

    if input.debris == "heavy":
        risks.append(RiskFactor(
            label="Hazardous material possible",
            consequence="Tires, chemicals, or construction waste require licensed disposal. Discovery on-site adds $1k–$5k+ and causes delays.",
            severity="high"
        ))

    risks.append(RiskFactor(
        label="Hours exclude haul-off time",
        consequence="Add 20–40% to total hours if debris is hauled off-site rather than chipped in place.",
        severity="medium"
    ))

    # Sort: high first, then medium, then low
    severity_rank = {"high": 3, "medium": 2, "low": 1}
    risks.sort(key=lambda r: severity_rank.get(r.severity, 0), reverse=True)

    return risks


def _build_equipment(input: ClearingInput) -> List[str]:
    """Return list of recommended equipment based on conditions."""
    eq = []

    if input.vegetation == "light":
        eq += ["Skid steer with brush cutter", "Disc mower or rotary cutter"]
    elif input.vegetation == "medium":
        eq += ["Forestry mulcher", "Skid steer with grapple", "Mid-size bulldozer (D4–D5)"]
    else:
        eq += ["Heavy-duty bulldozer (D6/D7)", "Excavator with thumb (20–30 ton)", "Forestry mulcher or tub grinder", "Haul trucks for debris removal"]

    if input.terrain == "steep":
        eq += ["Track-mounted equipment only", "Erosion control materials"]
    if input.accessibility == "difficult":
        eq.append("Low-ground-pressure equipment")
    if input.water == "pond_or_creek":
        eq.append("Silt fencing / sediment barriers")
    if input.water == "wetland":
        eq += ["Wetland-rated equipment", "Environmental consultant required"]
    if input.structures == "buildings_utilities":
        eq.append("Utility locate service (call 811 first)")
    if input.debris == "heavy":
        eq.append("Dumpsters / additional haul trucks")

    return eq


def _build_per_acre_note(input: ClearingInput) -> str:
    if input.acreage < 2:
        return f"Small parcel ({input.acreage} ac) — mobilization costs don't scale down, raising per-acre rate."
    if input.acreage < 5:
        return "Fixed costs spread across fewer acres on smaller jobs."
    return "Per-acre rate shown for comparison with contractor quotes."


def _build_confidence(input: ClearingInput, risk_factors: List[RiskFactor], stacked_multipliers: int) -> ConfidenceResult:
    """
    Confidence breakdown across 3 dimensions.
    Medium is the MAXIMUM — High is intentionally excluded.
    A field estimate from toggles cannot be High confidence.
    """
    high_risk_count = sum(1 for r in risk_factors if r.severity == "high")

    # Geometry: acreage from drawn boundary is reliable
    geometry = ConfidenceDimension(
        level="High",
        note="Acreage from drawn boundary — geometry is the most reliable input. Note: drawn boundary may differ from actual clearing area due to setbacks."
    )

    # Site conditions: user-reported, not verified
    has_complex = (
        input.vegetation == "heavy" or
        input.terrain == "steep" or
        input.water != "none" or
        input.accessibility == "difficult"
    )
    site_conditions = ConfidenceDimension(
        level="Low" if has_complex else "Medium",
        note="User-reported conditions with high variability — on-site verification required" if has_complex
             else "User-reported conditions — moderate variability expected"
    )

    # Cost model: degrades when multipliers stack
    cost_model_low = high_risk_count >= 2 or stacked_multipliers >= 2
    cost_model = ConfidenceDimension(
        level="Low" if cost_model_low else "Medium",
        note=f"{stacked_multipliers} condition multipliers stacked — compounding effects exceed what linear math captures" if stacked_multipliers >= 2
             else "Multiple high-risk conditions — cost model may underestimate significantly" if high_risk_count >= 2
             else "Hours × rates model — reasonable for budgeting, not for final bid"
    )

    # Overall: take the worst dimension
    levels = [geometry.level, site_conditions.level, cost_model.level]
    overall = "Low" if "Low" in levels else "Medium"

    disclaimer = (
        "Multiple high-severity conditions present. Wide uncertainty. On-site assessment strongly recommended before quoting."
        if overall == "Low" else
        "Preliminary field estimate. Use for budgeting only — not for final bid. Conditions must be verified on-site."
    )

    return ConfidenceResult(
        level=overall,
        breakdown=ConfidenceBreakdown(
            geometry=geometry,
            site_conditions=site_conditions,
            cost_model=cost_model,
        ),
        disclaimer=disclaimer,
    )