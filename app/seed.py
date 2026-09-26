from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Panchayat

# Fictional Panchayat micro-sites used to demo downscaling within the configured IMD block.
# Replace these rows and geometries with LGD/Bhuvan features for the chosen pilot.
DEMO_PANCHAYATS = [
    ("Demo North", "DEMO-001", 32.31, 75.59, 280, 2, "plain", "cropland", .36, "wheat", "vegetative"),
    ("Demo East", "DEMO-002", 32.32, 75.62, 315, 7, "windward", "forest", .48, "maize", "vegetative"),
    ("Demo Valley", "DEMO-003", 32.30, 75.60, 245, 4, "leeward", "cropland", .52, "rice", "harvest"),
    ("Demo Ridge", "DEMO-004", 32.34, 75.64, 520, 18, "windward", "barren", .22, "wheat", "flowering"),
    ("Demo South", "DEMO-005", 32.28, 75.57, 265, 1, "plain", "cropland", .31, "mustard", "vegetative"),
    ("Demo West", "DEMO-006", 32.33, 75.55, 390, 12, "leeward", "forest", .44, "maize", "harvest"),
]


def seed_panchayats(db: Session) -> None:
    if db.scalar(select(Panchayat.id).limit(1)) is not None:
        return
    for name, code, lat, lon, elevation, slope, aspect, cover, moisture, crop, stage in DEMO_PANCHAYATS:
        db.add(Panchayat(
            name=name, lgd_code=code, block_name="Sujanpur (demo)", district_name="Pathankot (demo)",
            state_name="Punjab (demo)", latitude=lat, longitude=lon, elevation_m=elevation,
            slope_deg=slope, aspect=aspect, land_cover=cover, soil_moisture=moisture,
            crop=crop, crop_stage=stage,
        ))
    db.commit()
