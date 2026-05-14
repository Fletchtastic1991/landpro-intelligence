# engines/config.py
# ─────────────────────────────────────────────────────────────────────────────
# This is the Python mirror of your TypeScript pricingConfig.ts
# Single source of truth for all multipliers and rates.
#
# Rule: if you change a number here, it changes everywhere in Python.
# Just like pricingConfig.ts does in TypeScript.
# ─────────────────────────────────────────────────────────────────────────────


# ─── Pricing multipliers ──────────────────────────────────────────────────────
# These match DEFAULT_PRICING_CONFIG in src/lib/pricingConfig.ts exactly.
# If you change pricingConfig.ts, update these numbers too.

TERRAIN_MULTIPLIERS = {
    "flat":         1.0,
    "slight_slope": 1.25,   # matches pricingConfig.ts terrain.slight_slope
    "steep":        1.75,   # matches pricingConfig.ts terrain.steep
}

ACCESS_MULTIPLIERS = {
    "easy":      1.0,
    "moderate":  1.25,  # matches pricingConfig.ts accessibility.moderate
    "difficult": 1.5,   # matches pricingConfig.ts accessibility.difficult
}

WATER_MULTIPLIERS = {
    "none":          1.0,
    "pond_or_creek": 1.15,
    "wetland":       1.30,
}


# ─── Production hours per acre ────────────────────────────────────────────────
# How many machine hours does 1 acre take?
# These are ranges [min, max] — reality is never a single number.
# Matches PROD_HOURS in ClearingPro.ts exactly.

PRODUCTION_HOURS = {
    "conservative": {
        "light":  [12, 20],
        "medium": [28, 50],
        "heavy":  [60, 100],
    },
    "standard": {
        "light":  [8,  16],
        "medium": [18, 36],
        "heavy":  [40, 80],
    },
    "aggressive": {
        "light":  [5,  10],
        "medium": [12, 24],
        "heavy":  [28, 55],
    },
}


# ─── Labor rates ─────────────────────────────────────────────────────────────
# $/hr for machine and crew
# These match MACHINE_RATE and LABOR_RATE in ClearingPro.ts

MACHINE_RATE_PER_HR = 150   # $/hr for excavator/bulldozer/mulcher
LABOR_RATE_PER_HR   = 50    # $/hr per crew operator


# ─── Crew size by vegetation ──────────────────────────────────────────────────
# Matches CREW_BY_VEGETATION in ClearingPro.ts
# The justification explains WHY to contractors who question crew size.

CREW_BY_VEGETATION = {
    "light": {
        "size":          2,
        "assumption":    "2 operators — light brush, skid steer + mower",
        "justification": "Light vegetation can be handled by 2 operators efficiently. Additional crew adds cost without proportional time savings at this density.",
    },
    "medium": {
        "size":          3,
        "assumption":    "3 operators — mixed stand, mulcher + dozer + support",
        "justification": "Mixed stands require simultaneous mulching and material management. A 3-operator spread keeps machines moving without bottlenecks.",
    },
    "heavy": {
        "size":          5,
        "assumption":    "5 operators — heavy clearing, full equipment spread",
        "justification": "Heavy clearing requires concurrent felling, mulching, debris management, and equipment support. Fewer operators cause machine idle time and significantly extend project duration.",
    },
}


# ─── Baseline for reality anchor ─────────────────────────────────────────────
# What does "normal" land clearing cost per acre?
# This is shown in reports to ground the estimate.

BASELINE_PER_ACRE_MIN = 2000    # $/acre for open, flat, easy land
BASELINE_PER_ACRE_MAX = 6000    # $/acre for open, flat, easy land
BASELINE_LABEL = "Typical open, dry land clearing (light vegetation, flat, easy access)"


# ─── Fence structure rules ────────────────────────────────────────────────────
# Matches STRUCTURE_RULES in FencePro.ts

FENCE_TYPE_RULES = {
    "wood": {
        "default_spacing_ft": 6,
        "rails_per_span":     3,
        "concrete_per_post":  2,
        "posts_per_day":      80,
        "wire_strands":       0,
        "description":        "Wood fence. 6 ft spacing, 3 rails per span.",
    },
    "chain_link": {
        "default_spacing_ft": 10,
        "rails_per_span":     0,
        "concrete_per_post":  1.5,
        "posts_per_day":      100,
        "wire_strands":       0,
        "description":        "Chain-link fence. 10 ft spacing, no rails.",
    },
    "farm": {
        "default_spacing_ft": 12,
        "rails_per_span":     0,
        "concrete_per_post":  1,
        "posts_per_day":      120,
        "wire_strands":       4,
        "description":        "Farm/agricultural fence. 12 ft spacing, 4 wire strands.",
    },
}

FENCE_DEFAULT_RATES = {
    "crew_size":            3,
    "daily_rate_usd":       1200,
    "post_cost_usd":        8,
    "concrete_bag_cost_usd": 7,
    "markup_pct":           20,
}