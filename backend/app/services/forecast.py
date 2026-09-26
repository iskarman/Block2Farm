"""Local IMD snapshot plus a transparent prototype downscaling pipeline."""
from datetime import date, datetime, time, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Advisory, Forecast, Panchayat

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "imd_sujanpur_forecast.json"
IST = ZoneInfo("Asia/Kolkata")


def load_imd_snapshot() -> dict:
    with SNAPSHOT_PATH.open("r", encoding="utf-8") as source:
        return json.load(source)


def downscale(panchayat: Panchayat, coarse: dict[str, float], input_trace: dict) -> tuple[dict, dict]:
    # Environmental lapse-rate approximation relative to the published block baseline.
    physics_temp = coarse["temperature_c"] - (panchayat.elevation_m - 200.0) * 0.0065
    rain_factor = 1.18 if panchayat.aspect == "windward" else 0.92 if panchayat.aspect == "leeward" else 1.0
    physics_rain = coarse["rainfall_mm"] * rain_factor
    land_adjustment = {"barren": 0.4, "forest": -0.3, "cropland": 0.0, "water": -0.2}.get(panchayat.land_cover, 0.0)
    # Bounded example correction; it is not a trained ML model.
    residual = max(-1.0, min(1.0, land_adjustment + (0.35 - panchayat.soil_moisture) * 0.6))
    final = {
        "temperature_c": round(physics_temp + residual, 1),
        "rainfall_mm": round(max(0.0, physics_rain), 1),
        "humidity_pct": round(max(15.0, min(100.0, coarse["humidity_pct"] - residual * 2)), 1),
        "wind_kph": round(max(0.0, coarse["wind_kph"] * (1.0 + min(panchayat.slope_deg, 30) / 300)), 1),
        "physics_temperature_c": round(physics_temp, 1),
        "ml_residual_c": round(residual, 2),
    }
    steps = {
        "1_ingestion": {"source": "Bundled IMD block-forecast snapshot", **input_trace, "block_values": coarse},
        "2_physics_baseline": {"method": "6.5 C/km lapse rate and demo windward/leeward rain factor", "temperature_c": round(physics_temp, 1), "rainfall_mm": round(physics_rain, 1)},
        "3_residual_correction": {"method": "bounded example land-cover and soil-moisture residual", "temperature_residual_c": round(residual, 2)},
        "4_clamping": {"rules": ["rainfall >= 0", "humidity in [15, 100]", "wind >= 0", "residual in [-1, 1]"]},
        "5_spatial_advisory": {"crop": panchayat.crop, "stage": panchayat.crop_stage},
    }
    return final, steps


def build_advisory(panchayat: Panchayat, forecast: dict) -> dict[str, str]:
    rain = forecast["rainfall_mm"]
    temp = forecast["temperature_c"]
    if rain >= 20 and panchayat.crop_stage.lower() in {"harvest", "harvesting"}:
        return {"severity": "critical", "title": "Heavy rain during harvest", "message": f"About {rain:.0f} mm is forecast during the {panchayat.crop_stage.lower()} stage for {panchayat.crop}.", "action": "Delay cutting if possible, move harvested grain under cover and clear field drainage."}
    if rain >= 20:
        return {"severity": "warning", "title": "Heavy rainfall expected", "message": f"About {rain:.0f} mm of rain is forecast for this Panchayat.", "action": "Avoid irrigation on the forecast date and check field drainage."}
    if temp <= 5:
        return {"severity": "warning", "title": "Cold stress risk", "message": f"The adjusted forecast temperature is near {temp:.1f} C.", "action": "Check local conditions and follow district agriculture advisories for frost protection."}
    if rain < 2:
        return {"severity": "info", "title": "Mostly dry conditions", "message": f"About {rain:.1f} mm of rain is forecast.", "action": "Check soil moisture before irrigation and follow your crop's local water schedule."}
    return {"severity": "good", "title": "No major weather alert", "message": f"Snapshot conditions are moderate for {panchayat.crop} at the {panchayat.crop_stage} stage.", "action": "Continue routine crop monitoring and check an updated IMD forecast when needed."}


def refresh_all(db: Session) -> int:
    snapshot = load_imd_snapshot()
    # Rebuild from the bundled snapshot so refresh never implies a live IMD request.
    db.query(Advisory).delete(synchronize_session=False)
    db.query(Forecast).delete(synchronize_session=False)
    panchayats = db.scalars(select(Panchayat)).all()
    for panchayat in panchayats:
        for day in snapshot["forecasts"]:
            coarse = {
                "temperature_c": (float(day["temperature_max_c"]) + float(day["temperature_min_c"])) / 2,
                "rainfall_mm": float(day["rainfall_mm"]),
                "humidity_pct": (float(day["humidity_morning_pct"]) + float(day["humidity_evening_pct"])) / 2,
                "wind_kph": float(day["wind_kph"]),
            }
            valid_date = date.fromisoformat(day["date"])
            valid_at = datetime.combine(valid_date, time.min, tzinfo=IST).astimezone(timezone.utc)
            input_trace = {
                "location": snapshot["location"],
                "forecast_date": day["date"],
                "snapshot_date": snapshot["snapshot_date"],
                "source_url": snapshot["source_url"],
                "forecast_max_c": day["temperature_max_c"],
                "forecast_min_c": day["temperature_min_c"],
                "humidity_morning_pct": day["humidity_morning_pct"],
                "humidity_evening_pct": day["humidity_evening_pct"],
                "wind_direction_deg": day["wind_direction_deg"],
                "cloud_cover_octa": day["cloud_cover_octa"],
            }
            adjusted, steps = downscale(panchayat, coarse, input_trace)
            row = Forecast(
                panchayat_id=panchayat.id, valid_at=valid_at,
                source=f"IMD snapshot · {snapshot['location']}",
                temperature_c=adjusted["temperature_c"], rainfall_mm=adjusted["rainfall_mm"],
                humidity_pct=adjusted["humidity_pct"], wind_kph=adjusted["wind_kph"],
                physics_temperature_c=adjusted["physics_temperature_c"], ml_residual_c=adjusted["ml_residual_c"], pipeline=steps,
            )
            db.add(row)
            db.flush()
            db.add(Advisory(panchayat_id=panchayat.id, forecast_id=row.id, **build_advisory(panchayat, adjusted)))
    db.commit()
    return len(panchayats)


def latest_for(db: Session, panchayat_id: int):
    return db.scalar(select(Forecast).where(Forecast.panchayat_id == panchayat_id).order_by(Forecast.valid_at.asc()).limit(1))


def latest_advisory(db: Session, panchayat_id: int):
    return db.scalar(select(Advisory).join(Forecast, Advisory.forecast_id == Forecast.id).where(Advisory.panchayat_id == panchayat_id).order_by(Forecast.valid_at.asc()).limit(1))
