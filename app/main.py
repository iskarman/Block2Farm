from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, get_db
from .models import Advisory, Forecast, Panchayat
from .schemas import AdvisoryOut, ForecastOut, PanchayatOut, RefreshOut
from .seed import seed_panchayats
from .services.forecast import latest_advisory, latest_for, refresh_all


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Ensure PostGIS is available in the user's local PostgreSQL database.
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        seed_panchayats(session)
        # Remove records created by earlier prototypes; retain only the bundled IMD snapshot.
        legacy_forecasts = session.query(Forecast.id).filter(~Forecast.source.like("IMD snapshot%"))
        session.query(Advisory).filter(Advisory.forecast_id.in_(legacy_forecasts)).delete(synchronize_session=False)
        session.query(Forecast).filter(~Forecast.source.like("IMD snapshot%")).delete(synchronize_session=False)
        session.commit()
    yield


app = FastAPI(title="Panchayat Weather Downscaling", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected", "demo_mode": settings.demo_mode}


@app.get("/api/panchayats", response_model=list[PanchayatOut])
def list_panchayats(db: Session = Depends(get_db)):
    rows = db.query(Panchayat).order_by(Panchayat.name).all()
    return [PanchayatOut(
        id=p.id, lgd_code=p.lgd_code, name=p.name, block_name=p.block_name,
        district_name=p.district_name, state_name=p.state_name, elevation_m=p.elevation_m,
        latitude=p.latitude, longitude=p.longitude,
        slope_deg=p.slope_deg, aspect=p.aspect, land_cover=p.land_cover, crop=p.crop,
        crop_stage=p.crop_stage, latest_forecast=latest_for(db, p.id), advisory=latest_advisory(db, p.id),
    ) for p in rows]


@app.get("/api/panchayats/{panchayat_id}", response_model=PanchayatOut)
def get_panchayat(panchayat_id: int, db: Session = Depends(get_db)):
    p = db.get(Panchayat, panchayat_id)
    if not p:
        raise HTTPException(status_code=404, detail="Panchayat not found")
    return PanchayatOut(
        id=p.id, lgd_code=p.lgd_code, name=p.name, block_name=p.block_name,
        district_name=p.district_name, state_name=p.state_name, elevation_m=p.elevation_m,
        latitude=p.latitude, longitude=p.longitude,
        slope_deg=p.slope_deg, aspect=p.aspect, land_cover=p.land_cover, crop=p.crop,
        crop_stage=p.crop_stage, latest_forecast=latest_for(db, p.id), advisory=latest_advisory(db, p.id),
    )


@app.get("/api/panchayats/{panchayat_id}/forecast", response_model=ForecastOut)
def get_forecast(panchayat_id: int, db: Session = Depends(get_db)):
    if not db.get(Panchayat, panchayat_id):
        raise HTTPException(status_code=404, detail="Panchayat not found")
    row = latest_for(db, panchayat_id)
    if not row:
        raise HTTPException(status_code=404, detail="Forecast not available")
    return row


@app.get("/api/panchayats/{panchayat_id}/advisory", response_model=AdvisoryOut)
def get_advisory(panchayat_id: int, db: Session = Depends(get_db)):
    if not db.get(Panchayat, panchayat_id):
        raise HTTPException(status_code=404, detail="Panchayat not found")
    row = latest_advisory(db, panchayat_id)
    if not row:
        raise HTTPException(status_code=404, detail="Advisory not available")
    return row


@app.post("/api/forecasts/refresh", response_model=RefreshOut)
def refresh_forecasts(db: Session = Depends(get_db)):
    updated = refresh_all(db)
    return RefreshOut(updated=updated, source="India Meteorological Department", message="Forecast values were loaded from the bundled static IMD block-forecast snapshot. No current observations were requested.")


@app.get("/api/meta")
def metadata():
    return {
        "demo_mode": settings.demo_mode,
        "data_notice": "Weather values are a static snapshot of an IMD Sujanpur block forecast published on 2026-09-26. No current-weather endpoint or live IMD request is used. Panchayat names, coordinates and terrain features are synthetic examples.",
        "imd_snapshot_location": "Sujanpur, Pathankot, Punjab",
        "imd_snapshot_date": "2026-09-26",
        "pipeline": ["Bundled IMD block forecast", "Elevation and terrain adjustment", "Bounded land-cover residual", "Physical clamping", "Crop-stage advisory"],
        "planned_sources": ["LGD and Bhuvan boundaries", "SRTM or CartoDEM", "ERA5-Land", "MODIS NDVI / ESA WorldCover", "SoilGrids"],
    }
