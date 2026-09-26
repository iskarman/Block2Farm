from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Panchayat(Base):
    __tablename__ = "panchayats"

    id: Mapped[int] = mapped_column(primary_key=True)
    lgd_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    block_name: Mapped[str] = mapped_column(String(120))
    district_name: Mapped[str] = mapped_column(String(120))
    state_name: Mapped[str] = mapped_column(String(120))
    elevation_m: Mapped[float] = mapped_column(Float)
    slope_deg: Mapped[float] = mapped_column(Float, default=0)
    aspect: Mapped[str] = mapped_column(String(20), default="plain")
    land_cover: Mapped[str] = mapped_column(String(40), default="cropland")
    soil_moisture: Mapped[float] = mapped_column(Float, default=0.35)
    crop: Mapped[str] = mapped_column(String(60), default="wheat")
    crop_stage: Mapped[str] = mapped_column(String(60), default="vegetative")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    forecasts: Mapped[list["Forecast"]] = relationship(back_populates="panchayat", cascade="all, delete-orphan")


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    panchayat_id: Mapped[int] = mapped_column(ForeignKey("panchayats.id", ondelete="CASCADE"), index=True)
    valid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    temperature_c: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    wind_kph: Mapped[float] = mapped_column(Float)
    physics_temperature_c: Mapped[float] = mapped_column(Float)
    ml_residual_c: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(80), default="Synthetic demo input")
    pipeline: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    panchayat: Mapped[Panchayat] = relationship(back_populates="forecasts")


class Advisory(Base):
    __tablename__ = "advisories"

    id: Mapped[int] = mapped_column(primary_key=True)
    panchayat_id: Mapped[int] = mapped_column(ForeignKey("panchayats.id", ondelete="CASCADE"), index=True)
    forecast_id: Mapped[int] = mapped_column(ForeignKey("forecasts.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
