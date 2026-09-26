# Block2Farm — Panchayat Weather Downscaling

A local Smart India Hackathon prototype using **Python/FastAPI**, **React/Leaflet**, and **PostgreSQL/PostGIS**. It uses a bundled, dated snapshot of a published India Meteorological Department (IMD) block forecast.

## Data and limitations

For initial prototype The bundled forecast is for **Sujanpur, Pathankot, Punjab**, published **26 September 2026**, and covers 26–30 September 2026. The app stores this snapshot in PostgreSQL and applies a transparent example downscaling adjustment for its sample locations. Reloading the snapshot reuses the same local file; currently it does not update weather data in our prototype but in our full version it will.


Source: [IMD Chandigarh block forecast PDF](https://mausam.imd.gov.in/chandigarh/mcdata/block_pun.pdf). See `app/data/imd_sujanpur_forecast.json` for the included values and source metadata.

The sample Panchayat names, coordinates, terrain, land cover, and crop stages are synthetic examples. The adjustment and advisories are a prototype, not operational forecasts. Update the JSON snapshot manually with a newly published IMD block forecast when needed, after checking its source and units.

## Requirements

- Python 3.12+
- Node.js 20 or later with npm
- PostgreSQL with the PostGIS extension installed and enabled

currently The database runs locally on your computer.

## 1. Set up PostgreSQL

Install PostgreSQL and PostGIS for your operating system. In `psql` or pgAdmin, create a local user and database; for example, in `psql` as a PostgreSQL administrator:

```sql
CREATE USER weather WITH PASSWORD 'choose_a_local_password';
CREATE DATABASE panchayat_weather OWNER weather;
\c panchayat_weather
CREATE EXTENSION postgis;
```

Keep the password local. The application creates its tables when it starts.

## 2. Start the FastAPI backend (PowerShell)

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set `DATABASE_URL` in `.env` to the PostgreSQL username and password you created, for example:

```text
DATABASE_URL=postgresql+psycopg://weather:choose_a_local_password@localhost:5432/panchayat_weather
```

Save `.env`, then start the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

The first run seeds the sample locations and loads forecasts from the bundled JSON snapshot. API docs are at http://localhost:8000/docs.

## 3. Start the React frontend

Open another PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL Vite prints (usually http://localhost:5173). Stop either server with `Ctrl+C`.

## API routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API and database status |
| GET | `/api/meta` | Snapshot date, location, and data notice |
| GET | `/api/panchayats` | Sample location list with forecast and advisory |
| GET | `/api/panchayats/{id}` | One location and its summary |
| GET | `/api/panchayats/{id}/forecast` | Earliest forecast date from the bundled snapshot |
| GET | `/api/panchayats/{id}/advisory` | Advisory for that forecast date |
| POST | `/api/forecasts/refresh` | Rebuild stored results from the same local snapshot |

## Project layout

```text

  app/main.py                         FastAPI routes and database startup
  app/models.py                       SQLAlchemy tables and PostGIS geometry
  app/seed.py                         Synthetic sample Panchayat locations
  app/data/imd_sujanpur_forecast.json Published IMD forecast snapshot
  app/services/forecast.py            Local downscaling and advisory logic
frontend/
  src/App.jsx                         React map and dashboard
  src/styles.css                      Responsive dashboard styling
```
