# LandPro Intelligence

Python FastAPI service — the operational intelligence layer for LandPro.

## What This Is

This service owns all calculation, spatial analysis, and operational reasoning.
The TypeScript frontend calls this API and displays the results.

**Rule:** Python calculates. TypeScript displays. Never the other way around.

## Stack

- **Python 3.11**
- **FastAPI** — web framework, auto-generates API docs
- **Pydantic** — data validation (like TypeScript interfaces but with runtime checking)
- **Shapely** — geometry operations (area, perimeter, intersections)
- **NumPy** — numerical computing
- **Pandas** — data analysis (for future batch processing)
- **Rasterio** — raster/GeoTIFF analysis (for future USGS elevation integration)

## Architecture

```
landpro-intelligence/
├── main.py                     ← FastAPI app entry point
├── requirements.txt            ← package dependencies
├── config.py                   ← shared config (multipliers, rates)
│                                 mirrors pricingConfig.ts in the frontend
│
├── engines/                    ← pure calculation logic
│   ├── terrain_engine.py       ← polygon → terrain facts (slope, elevation)
│   ├── clearing_engine.py      ← field conditions → hours, cost, risk
│   └── fence_engine.py         ← boundary + inputs → posts, materials, cost
│
├── assessments/                ← operational doctrine
│   └── site_assessment.py      ← conditions + machine → operational decision
│
└── routers/                    ← API endpoints
    ├── clearing.py             ← POST /clearing/estimate
    ├── fence.py                ← POST /fence/estimate
    └── terrain.py              ← POST /terrain/analyze (coming soon)
```

## Data Flow

```
Frontend sends polygon + field observations
              ↓
         FastAPI router receives request
              ↓
         Engine runs calculation
         (terrain_engine → clearing_engine → site_assessment)
              ↓
         JSON result returned to frontend
              ↓
         TypeScript formats and displays it
```

## Getting Started

```bash
# Create virtual environment with Python 3.11
py -3.11 -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python -m uvicorn main:app --reload
```

Server starts at `http://localhost:8000`

## API Documentation

FastAPI auto-generates interactive docs at:
- `http://localhost:8000/docs` — Swagger UI (try requests interactively)
- `http://localhost:8000/redoc` — ReDoc

## Upgrade Path

| Phase | What changes |
|---|---|
| Now | Placeholder terrain estimates from polygon geometry |
| Phase 2 | USGS 3DEP elevation API replaces placeholder slope values |
| Phase 3 | Rasterio raster analysis on GeoTIFF elevation data |
| Phase 4 | Soil survey API, weather API integration |

## Related Repos

- **[landpro-web](https://github.com/Fletchtastic1991/landpro-web)** — TypeScript/React frontend