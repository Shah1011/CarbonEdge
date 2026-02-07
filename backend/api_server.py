from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

@app.post("/api/pricing")
def get_pricing(data: PricingRequest):
    result = get_cloud_pricing_json(
        vcpus=data.vcpus,
        ram_gb=data.ram,
        storage=data.storage,
        utilization=data.utilization
    )
    return result
