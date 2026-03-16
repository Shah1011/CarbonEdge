from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from engine import get_cloud_pricing_json

app = FastAPI()

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PricingRequest(BaseModel):
    vcpus: int
    ram: int
    storage: str
    utilization: float

class ForecastRequest(BaseModel):
    provider: str
    region: str

class ForecastAllRequest(BaseModel):
    providers: Optional[List[str]] = None

@app.post("/api/pricing")
def get_pricing(data: PricingRequest):
    result = get_cloud_pricing_json(
        vcpus=data.vcpus,
        ram_gb=data.ram,
        storage=data.storage,
        utilization=data.utilization
    )
    return result

@app.post("/api/forecast")
def get_forecast(data: ForecastRequest):
    """Return TFT-based 7-day carbon intensity forecast for a region."""
    try:
        from ml.predict import get_carbon_forecast
        result = get_carbon_forecast(data.provider, data.region)
        if result is None:
            return {
                "error": "No forecast available for this region",
                "provider": data.provider,
                "region": data.region,
            }
        return result
    except FileNotFoundError as e:
        return {
            "error": "Model not trained yet. Run `python -m ml.train` first.",
            "detail": str(e),
        }
    except Exception as e:
        return {
            "error": str(e),
            "provider": data.provider,
            "region": data.region,
        }

@app.post("/api/forecasts/all")
def get_all_forecasts(data: ForecastAllRequest = ForecastAllRequest()):
    """Return all cached forecasts, optionally filtered by provider list."""
    try:
        from ml.predict import get_forecaster
        forecaster = get_forecaster()
        all_fc = forecaster.get_all_forecasts()
        if not all_fc:
            return {"regions": [], "error": "No forecasts available. Train the model first."}

        regions = []
        for gid, fc in all_fc.items():
            if "error" in fc:
                continue
            provider = fc.get("provider", "").lower()
            # Filter by provider if specified
            if data.providers and provider not in [p.lower() for p in data.providers]:
                continue
            regions.append({
                "group_id": gid,
                "provider": fc.get("provider", ""),
                "region": fc.get("region", ""),
                "summary": fc.get("summary", {}),
            })

        # Sort by forecast average carbon intensity (lowest first = eco-optimized)
        regions.sort(key=lambda r: r["summary"].get("forecast_avg_gCO2", 9999))
        return {"regions": regions}

    except FileNotFoundError:
        return {"regions": [], "error": "Model not trained yet."}
    except Exception as e:
        return {"regions": [], "error": str(e)}
