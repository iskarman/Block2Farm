from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    valid_at: datetime
    temperature_c: float
    rainfall_mm: float
    humidity_pct: float
    wind_kph: float
    physics_temperature_c: float
    ml_residual_c: float
    source: str
    pipeline: dict


class AdvisoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    severity: str
    title: str
    message: str
    action: str


class PanchayatOut(BaseModel):
    id: int
    lgd_code: str
    name: str
    block_name: str
    district_name: str
    state_name: str
    elevation_m: float
    latitude: float
    longitude: float
    slope_deg: float
    aspect: str
    land_cover: str
    crop: str
    crop_stage: str
    latest_forecast: ForecastOut | None = None
    advisory: AdvisoryOut | None = None


class RefreshOut(BaseModel):
    updated: int
    source: str
    message: str
