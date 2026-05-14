# engines/terrain_engine.py
# ─────────────────────────────────────────────────────────────────────────────
# LandPro — Terrain Engine
#
# PURPOSE:
#   Convert spatial geometry (a polygon) into terrain facts.
#   Nothing more. Nothing less.
#
# THIS FILE RETURNS FACTS, NOT OPINIONS:
#   average_slope, max_slope, elevation_range, terrain_variability
#
# THIS FILE DOES NOT:
#   - Make operational decisions
#   - Recommend equipment
#   - Calculate costs
#   - Talk to a database
#   - Call an API (yet)
#
# CURRENT STATE — Placeholder logic:
#   The analyze_terrain() function currently returns estimated values
#   based on the polygon's shape characteristics (size, complexity).
#   This is intentional. We are proving the architecture FIRST.
#
# FUTURE STATE — Real data:
#   Replace the placeholder logic inside analyze_terrain() with a call
#   to the USGS Elevation API or a raster analysis pipeline.
#   The rest of the system (SiteAssessment, SitePro) does NOT change.
#   That's the power of this abstraction layer.
#
# UPGRADE PATH:
#   Phase 1 (now):   placeholder geometry-based estimates
#   Phase 2 (soon):  USGS 3DEP elevation API (free, accurate to 1m)
#   Phase 3 (later): rasterio + numpy raster analysis on GeoTIFF files
# ─────────────────────────────────────────────────────────────────────────────

import math
from typing import List, Tuple, Optional


# ─────────────────────────────────────────────────────────────────────────────
# DATA TYPES
# These define what terrain data looks like.
# Every engine that reads terrain data gets this exact shape.
# ─────────────────────────────────────────────────────────────────────────────

class TerrainAnalysisResult:
    """
    Facts about terrain derived from a polygon.
    
    These are FACTS, not scores or opinions.
    Every field is a measurable physical property.
    
    Source tells downstream systems where this data came from —
    so confidence can be adjusted accordingly.
    """
    def __init__(
        self,
        average_slope_pct: float,       # mean slope across the parcel in percent (0=flat, 45=very steep)
        max_slope_pct: float,            # steepest point on the parcel
        elevation_range_ft: float,       # difference between highest and lowest point in feet
        terrain_variability: str,        # "flat", "gentle", "moderate", "rugged", "extreme"
        slope_class: str,                # USDA slope classification label
        data_source: str,               # "placeholder", "usgs_api", "raster_analysis"
        confidence: str,                # "estimated", "low", "medium", "high"
        notes: List[str] = None,        # any warnings or caveats about the data
    ):
        self.average_slope_pct   = average_slope_pct
        self.max_slope_pct       = max_slope_pct
        self.elevation_range_ft  = elevation_range_ft
        self.terrain_variability = terrain_variability
        self.slope_class         = slope_class
        self.data_source         = data_source
        self.confidence          = confidence
        self.notes               = notes or []

    def __repr__(self):
        return (
            f"TerrainAnalysisResult("
            f"avg_slope={self.average_slope_pct}%, "
            f"max_slope={self.max_slope_pct}%, "
            f"elevation_range={self.elevation_range_ft}ft, "
            f"variability={self.terrain_variability}, "
            f"source={self.data_source})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GEOMETRY HELPERS
# These work on raw polygon coordinates.
# Coordinates are [longitude, latitude] pairs (GeoJSON standard).
# ─────────────────────────────────────────────────────────────────────────────

def haversine_distance_ft(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate distance between two [lon, lat] points in feet.
    Uses the Haversine formula — accounts for Earth's curvature.
    
    This is the same math as in FencePro.ts, just in Python.
    """
    lon1, lat1 = point1
    lon2, lat2 = point2

    R = 20925524.9  # Earth radius in feet (6,371,000 metres × 3.28084)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_polygon_area_acres(coordinates: List[Tuple[float, float]]) -> float:
    """
    Calculate the area of a polygon in acres using the Shoelace formula.
    Input: list of [lon, lat] pairs (closing coord should be same as first).
    
    This gives us approximate area in geographic degrees, which we convert
    to square feet using a scale factor based on the polygon's latitude.
    """
    if len(coordinates) < 3:
        return 0.0

    # Remove closing coordinate if present
    pts = coordinates[:-1] if coordinates[0] == coordinates[-1] else coordinates

    # Shoelace formula for area in degree² units
    n = len(pts)
    area_deg = 0.0
    for i in range(n):
        j = (i + 1) % n
        area_deg += pts[i][0] * pts[j][1]
        area_deg -= pts[j][0] * pts[i][1]
    area_deg = abs(area_deg) / 2.0

    # Convert degree² to square feet
    # At the equator, 1 degree ≈ 364,000 ft. We use the centroid latitude to adjust.
    avg_lat = sum(p[1] for p in pts) / len(pts)
    lat_scale = 364000.0         # feet per degree of latitude (approx)
    lon_scale = 364000.0 * math.cos(math.radians(avg_lat))  # shrinks toward poles

    area_sq_ft = area_deg * lat_scale * lon_scale
    return area_sq_ft / 43560.0  # convert to acres


def calculate_perimeter_ft(coordinates: List[Tuple[float, float]]) -> float:
    """Calculate total perimeter of polygon in feet."""
    total = 0.0
    pts = coordinates[:-1] if coordinates[0] == coordinates[-1] else coordinates
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        total += haversine_distance_ft(pts[i], pts[j])
    return total


def calculate_shape_complexity(coordinates: List[Tuple[float, float]]) -> float:
    """
    Calculate how irregular/complex the polygon shape is.
    
    Uses the Polsby-Popper compactness score:
        score = (4π × area) / perimeter²
    
    Score of 1.0 = perfect circle (most compact)
    Score near 0 = very irregular shape (lots of notches, peninsulas)
    
    Why this matters for terrain:
    Irregular parcels often indicate varied topography — the boundary
    follows ridgelines, creek beds, or slope breaks.
    Simple rectangles are usually flat agricultural land.
    
    This is our proxy for terrain complexity until we have real elevation data.
    """
    area_acres    = calculate_polygon_area_acres(coordinates)
    perimeter_ft  = calculate_perimeter_ft(coordinates)
    area_sq_ft    = area_acres * 43560.0

    if perimeter_ft == 0:
        return 1.0

    score = (4 * math.pi * area_sq_ft) / (perimeter_ft ** 2)
    return min(1.0, max(0.0, score))  # clamp to 0–1


# ─────────────────────────────────────────────────────────────────────────────
# SLOPE CLASSIFICATION
# USDA standard slope classes — used by soil scientists and land managers.
# These are the labels contractors and engineers recognize.
# ─────────────────────────────────────────────────────────────────────────────

def classify_slope(slope_pct: float) -> str:
    """
    Return USDA slope class label for a given slope percentage.
    
    USDA slope classes:
    0–2%    = Nearly level
    2–6%    = Gently sloping
    6–10%   = Moderately sloping
    10–15%  = Strongly sloping
    15–30%  = Steeply sloping
    30–45%  = Very steeply sloping
    45%+    = Extremely steep
    """
    if slope_pct < 2:
        return "Nearly level (0–2%)"
    elif slope_pct < 6:
        return "Gently sloping (2–6%)"
    elif slope_pct < 10:
        return "Moderately sloping (6–10%)"
    elif slope_pct < 15:
        return "Strongly sloping (10–15%)"
    elif slope_pct < 30:
        return "Steeply sloping (15–30%)"
    elif slope_pct < 45:
        return "Very steeply sloping (30–45%)"
    else:
        return "Extremely steep (45%+)"


def classify_variability(elevation_range_ft: float, area_acres: float) -> str:
    """
    Classify terrain variability based on elevation change relative to parcel size.
    A 50 ft elevation change on 1 acre is very rugged.
    A 50 ft elevation change on 100 acres is gentle.
    """
    if area_acres <= 0:
        return "unknown"

    # Elevation change per acre — normalizes for parcel size
    change_per_acre = elevation_range_ft / area_acres

    if change_per_acre < 5:
        return "flat"
    elif change_per_acre < 15:
        return "gentle"
    elif change_per_acre < 35:
        return "moderate"
    elif change_per_acre < 70:
        return "rugged"
    else:
        return "extreme"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENGINE FUNCTION
# This is the function everything else calls.
# Input: polygon coordinates (GeoJSON format)
# Output: TerrainAnalysisResult
# ─────────────────────────────────────────────────────────────────────────────

def analyze_terrain(
    coordinates: List[Tuple[float, float]],
    user_reported_slope: Optional[str] = None,
) -> TerrainAnalysisResult:
    """
    Analyze terrain from polygon coordinates.
    
    CURRENT IMPLEMENTATION: Placeholder estimates.
    Uses polygon geometry (size, shape complexity) to estimate terrain.
    
    Why this is valid for now:
    - Irregular shapes on large parcels tend to have varied terrain
    - Small compact polygons are often flat (lawns, fields)
    - Shape complexity correlates with topographic complexity
    
    This is architecture validation, not terrain science.
    Replace the internals when USGS API is integrated.
    
    Parameters:
        coordinates:           List of [lon, lat] pairs forming the polygon boundary
        user_reported_slope:   Optional override from field toggles ("flat", "slight_slope", "steep")
                               Used to calibrate estimates until real data is available
    
    Returns:
        TerrainAnalysisResult with terrain facts
    """
    notes = []

    # ── Calculate geometry facts ──────────────────────────────────────────────
    area_acres       = calculate_polygon_area_acres(coordinates)
    perimeter_ft     = calculate_perimeter_ft(coordinates)
    shape_complexity = calculate_shape_complexity(coordinates)

    # ── User-reported slope as calibration seed ───────────────────────────────
    # Until we have real elevation data, the user's field observation
    # helps us produce a more realistic estimate.
    # This is explicit — we label it "estimated" so downstream systems know.

    if user_reported_slope == "steep":
        base_slope = 22.0
        slope_variance = 8.0
    elif user_reported_slope == "slight_slope":
        base_slope = 9.0
        slope_variance = 5.0
    else:
        # "flat" or not provided
        base_slope = 3.0
        slope_variance = 2.0

    # ── Shape complexity modifier ─────────────────────────────────────────────
    # Less compact (more irregular) = likely more varied terrain
    # compactness of 1.0 = circle (flat field), 0.1 = very irregular (follows terrain)
    complexity_factor = 1.0 + (1.0 - shape_complexity) * 0.5

    # ── Estimate slope values ─────────────────────────────────────────────────
    average_slope = round(base_slope * complexity_factor, 1)
    max_slope     = round(average_slope + slope_variance * complexity_factor, 1)

    # ── Estimate elevation range ──────────────────────────────────────────────
    # Larger parcels have more elevation change
    # Steeper slopes have more elevation change over the same area
    elevation_range = round(average_slope * math.sqrt(area_acres) * 2.1, 1)

    # ── Classify ─────────────────────────────────────────────────────────────
    terrain_variability = classify_variability(elevation_range, area_acres)
    slope_class         = classify_slope(average_slope)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes.append(
        "Terrain values are estimated from polygon geometry and user-reported slope. "
        "Accuracy will improve significantly when USGS elevation data is integrated."
    )
    if user_reported_slope:
        notes.append(f"Calibrated using user-reported slope: '{user_reported_slope}'.")
    if shape_complexity < 0.4:
        notes.append(
            f"Polygon shape is irregular (compactness score: {shape_complexity:.2f}). "
            f"This may indicate the boundary follows natural features like ridgelines or creeks, "
            f"suggesting more varied terrain than a standard rectangular parcel."
        )

    return TerrainAnalysisResult(
        average_slope_pct   = average_slope,
        max_slope_pct       = max_slope,
        elevation_range_ft  = elevation_range,
        terrain_variability = terrain_variability,
        slope_class         = slope_class,
        data_source         = "placeholder_geometry",
        confidence          = "estimated",
        notes               = notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — Convert terrain result to SiteConditions slope input
# This is the bridge function between engines.
# terrain_engine produces facts → site_assessment consumes them.
# ─────────────────────────────────────────────────────────────────────────────

def terrain_to_slope_class(terrain: TerrainAnalysisResult) -> str:
    """
    Convert TerrainAnalysisResult into the slope class string
    that SiteConditions expects.
    
    This is an explicit translation layer — it maps terrain facts
    into the vocabulary of the operational assessment engine.
    
    When USGS data replaces placeholder data, this function
    automatically improves without any other changes.
    """
    avg = terrain.average_slope_pct

    if avg < 6:
        return "flat"
    elif avg < 15:
        return "slight_slope"
    else:
        return "steep"


# ─────────────────────────────────────────────────────────────────────────────
# TEST — Run this file directly: python engines/terrain_engine.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\n" + "="*60)
    print("  TERRAIN ENGINE — TEST CASES")
    print("="*60)

    # Test 1: Small rectangular parcel (likely flat)
    print("\nTest 1: Small rectangular parcel (~0.5 acres, flat)")
    rect_coords = [
        (-97.1234, 32.7891),
        (-97.1220, 32.7891),
        (-97.1220, 32.7880),
        (-97.1234, 32.7880),
        (-97.1234, 32.7891),  # closing coord
    ]
    result1 = analyze_terrain(rect_coords, user_reported_slope="flat")
    print(f"  Area:               ~{calculate_polygon_area_acres(rect_coords):.2f} acres")
    print(f"  Shape complexity:   {calculate_shape_complexity(rect_coords):.2f} (1.0 = perfect circle)")
    print(f"  Average slope:      {result1.average_slope_pct}%")
    print(f"  Max slope:          {result1.max_slope_pct}%")
    print(f"  Elevation range:    {result1.elevation_range_ft} ft")
    print(f"  Terrain variability:{result1.terrain_variability}")
    print(f"  Slope class:        {result1.slope_class}")
    print(f"  Data source:        {result1.data_source}")
    print(f"  Confidence:         {result1.confidence}")
    print(f"  → SiteConditions slope input: '{terrain_to_slope_class(result1)}'")

    # Test 2: Irregular parcel on sloped terrain
    print("\nTest 2: Irregular parcel (~2 acres, slight slope)")
    irregular_coords = [
        (-97.1250, 32.7900),
        (-97.1230, 32.7910),
        (-97.1210, 32.7905),
        (-97.1200, 32.7890),
        (-97.1215, 32.7875),
        (-97.1240, 32.7870),
        (-97.1255, 32.7880),
        (-97.1250, 32.7900),
    ]
    result2 = analyze_terrain(irregular_coords, user_reported_slope="slight_slope")
    print(f"  Area:               ~{calculate_polygon_area_acres(irregular_coords):.2f} acres")
    print(f"  Shape complexity:   {calculate_shape_complexity(irregular_coords):.2f}")
    print(f"  Average slope:      {result2.average_slope_pct}%")
    print(f"  Max slope:          {result2.max_slope_pct}%")
    print(f"  Elevation range:    {result2.elevation_range_ft} ft")
    print(f"  Terrain variability:{result2.terrain_variability}")
    print(f"  Slope class:        {result2.slope_class}")
    print(f"  → SiteConditions slope input: '{terrain_to_slope_class(result2)}'")

    # Test 3: Large steep parcel
    print("\nTest 3: Large parcel with steep terrain (~15 acres, steep)")
    large_coords = [
        (-97.1300, 32.7950),
        (-97.1250, 32.7970),
        (-97.1200, 32.7960),
        (-97.1180, 32.7930),
        (-97.1200, 32.7900),
        (-97.1260, 32.7890),
        (-97.1310, 32.7910),
        (-97.1300, 32.7950),
    ]
    result3 = analyze_terrain(large_coords, user_reported_slope="steep")
    print(f"  Area:               ~{calculate_polygon_area_acres(large_coords):.2f} acres")
    print(f"  Shape complexity:   {calculate_shape_complexity(large_coords):.2f}")
    print(f"  Average slope:      {result3.average_slope_pct}%")
    print(f"  Max slope:          {result3.max_slope_pct}%")
    print(f"  Elevation range:    {result3.elevation_range_ft} ft")
    print(f"  Terrain variability:{result3.terrain_variability}")
    print(f"  Slope class:        {result3.slope_class}")
    print(f"  → SiteConditions slope input: '{terrain_to_slope_class(result3)}'")
    for note in result3.notes:
        print(f"\n  Note: {note}")

    print("\n" + "="*60)