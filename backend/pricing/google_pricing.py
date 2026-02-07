from fastapi import FastAPI, HTTPException
from typing import Union
import requests
import json
import uvicorn
import re

app = FastAPI(title="Google Cloud Pricing API", version="1.0.0")

# Currency conversion rates (same as other APIs)
CURRENCY_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.25,
    "CAD": 0.74,
    "AUD": 0.66,
    "JPY": 0.0067,
    "CNY": 0.14,
    "INR": 0.012,
}

def parse_user_storage_input(storage_input: Union[str, int]) -> int:
    """Parse user storage input and convert to GB"""
    if isinstance(storage_input, int):
        return storage_input
    
    if not storage_input or storage_input == "0":
        return 0
    
    storage_str = str(storage_input).lower().replace(" ", "")
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(gb|tb|g|t)?$', storage_str)
    
    if not match:
        raise HTTPException(status_code=400, detail=f"Invalid storage format: {storage_input}")
    
    number = float(match.group(1))
    unit = match.group(2) or 'gb'
    
    if unit in ['tb', 't']:
        return int(number * 1000)
    elif unit in ['gb', 'g']:
        return int(number)
    else:
        return int(number)

def convert_to_usd(price: float, currency: str) -> float:
    """Convert price from any currency to USD"""
    try:
        if currency in CURRENCY_TO_USD:
            return price * CURRENCY_TO_USD[currency]
        else:
            print(f"Warning: Unknown currency {currency}, assuming USD")
            return price
    except (ValueError, TypeError):
        return 0.0

def parse_gcp_machine_type(machine_type: str):
    """Parse GCP machine type to extract CPU and RAM info"""
    # GCP machine type naming: family-type-cpus (e.g., n1-standard-4)
    machine_specs = {
        # N1 Standard (General purpose)
        "n1-standard-1": {"vcpus": 1, "ram_gb": 3.75},
        "n1-standard-2": {"vcpus": 2, "ram_gb": 7.5},
        "n1-standard-4": {"vcpus": 4, "ram_gb": 15},
        "n1-standard-8": {"vcpus": 8, "ram_gb": 30},
        "n1-standard-16": {"vcpus": 16, "ram_gb": 60},
        "n1-standard-32": {"vcpus": 32, "ram_gb": 120},
        
        # N1 High-Memory
        "n1-highmem-2": {"vcpus": 2, "ram_gb": 13},
        "n1-highmem-4": {"vcpus": 4, "ram_gb": 26},
        "n1-highmem-8": {"vcpus": 8, "ram_gb": 52},
        "n1-highmem-16": {"vcpus": 16, "ram_gb": 104},
        
        # N1 High-CPU
        "n1-highcpu-2": {"vcpus": 2, "ram_gb": 1.8},
        "n1-highcpu-4": {"vcpus": 4, "ram_gb": 3.6},
        "n1-highcpu-8": {"vcpus": 8, "ram_gb": 7.2},
        "n1-highcpu-16": {"vcpus": 16, "ram_gb": 14.4},
        
        # N2 Standard (Newer generation)
        "n2-standard-2": {"vcpus": 2, "ram_gb": 8},
        "n2-standard-4": {"vcpus": 4, "ram_gb": 16},
        "n2-standard-8": {"vcpus": 8, "ram_gb": 32},
        "n2-standard-16": {"vcpus": 16, "ram_gb": 64},
        "n2-standard-32": {"vcpus": 32, "ram_gb": 128},
        
        # N2 High-Memory
        "n2-highmem-2": {"vcpus": 2, "ram_gb": 16},
        "n2-highmem-4": {"vcpus": 4, "ram_gb": 32},
        "n2-highmem-8": {"vcpus": 8, "ram_gb": 64},
        "n2-highmem-16": {"vcpus": 16, "ram_gb": 128},
        
        # E2 (Cost-optimized)
        "e2-micro": {"vcpus": 1, "ram_gb": 1},
        "e2-small": {"vcpus": 1, "ram_gb": 2},
        "e2-medium": {"vcpus": 1, "ram_gb": 4},
        "e2-standard-2": {"vcpus": 2, "ram_gb": 8},
        "e2-standard-4": {"vcpus": 4, "ram_gb": 16},
        "e2-standard-8": {"vcpus": 8, "ram_gb": 32},
        "e2-standard-16": {"vcpus": 16, "ram_gb": 64},
        
        # C2 (Compute-optimized)
        "c2-standard-4": {"vcpus": 4, "ram_gb": 16},
        "c2-standard-8": {"vcpus": 8, "ram_gb": 32},
        "c2-standard-16": {"vcpus": 16, "ram_gb": 64},
        "c2-standard-30": {"vcpus": 30, "ram_gb": 120},
    }
    
    return machine_specs.get(machine_type, {"vcpus": 0, "ram_gb": 0})

@app.post("/gcp/pricing")
def get_gcp_price(vcpus: int, ram_gb: int, os: str, storage: Union[str, int] = 0, duration: str = "on_demand"):
    """Get Google Cloud VM pricing based on specifications"""
    
    # Parse storage input
    storage_gb = parse_user_storage_input(storage)
    
    # Google Cloud Billing API (public pricing)
    # Note: This is a simplified approach using known pricing data
    # For production, you'd want to use the official Cloud Billing API
    
    # Simulate GCP pricing data (in a real implementation, this would come from GCP API)
    gcp_pricing_data = [
        # N1 Standard instances
        {"machine_type": "n1-standard-1", "region": "us-central1", "price_usd": 0.0475, "os_type": "linux"},
        {"machine_type": "n1-standard-2", "region": "us-central1", "price_usd": 0.0950, "os_type": "linux"},
        {"machine_type": "n1-standard-4", "region": "us-central1", "price_usd": 0.1900, "os_type": "linux"},
        {"machine_type": "n1-standard-8", "region": "us-central1", "price_usd": 0.3800, "os_type": "linux"},
        {"machine_type": "n1-standard-16", "region": "us-central1", "price_usd": 0.7600, "os_type": "linux"},
        
        # N2 Standard instances
        {"machine_type": "n2-standard-2", "region": "us-central1", "price_usd": 0.0971, "os_type": "linux"},
        {"machine_type": "n2-standard-4", "region": "us-central1", "price_usd": 0.1942, "os_type": "linux"},
        {"machine_type": "n2-standard-8", "region": "us-central1", "price_usd": 0.3884, "os_type": "linux"},
        {"machine_type": "n2-standard-16", "region": "us-central1", "price_usd": 0.7768, "os_type": "linux"},
        
        # E2 Cost-optimized instances
        {"machine_type": "e2-micro", "region": "us-central1", "price_usd": 0.0063, "os_type": "linux"},
        {"machine_type": "e2-small", "region": "us-central1", "price_usd": 0.0126, "os_type": "linux"},
        {"machine_type": "e2-medium", "region": "us-central1", "price_usd": 0.0252, "os_type": "linux"},
        {"machine_type": "e2-standard-2", "region": "us-central1", "price_usd": 0.0504, "os_type": "linux"},
        {"machine_type": "e2-standard-4", "region": "us-central1", "price_usd": 0.1008, "os_type": "linux"},
        {"machine_type": "e2-standard-8", "region": "us-central1", "price_usd": 0.2016, "os_type": "linux"},
        
        # C2 Compute-optimized instances
        {"machine_type": "c2-standard-4", "region": "us-central1", "price_usd": 0.2056, "os_type": "linux"},
        {"machine_type": "c2-standard-8", "region": "us-central1", "price_usd": 0.4112, "os_type": "linux"},
        {"machine_type": "c2-standard-16", "region": "us-central1", "price_usd": 0.8224, "os_type": "linux"},
        
        # High-memory instances
        {"machine_type": "n1-highmem-2", "region": "us-central1", "price_usd": 0.1184, "os_type": "linux"},
        {"machine_type": "n1-highmem-4", "region": "us-central1", "price_usd": 0.2368, "os_type": "linux"},
        {"machine_type": "n1-highmem-8", "region": "us-central1", "price_usd": 0.4736, "os_type": "linux"},
        {"machine_type": "n2-highmem-2", "region": "us-central1", "price_usd": 0.1281, "os_type": "linux"},
        {"machine_type": "n2-highmem-4", "region": "us-central1", "price_usd": 0.2562, "os_type": "linux"},
        {"machine_type": "n2-highmem-8", "region": "us-central1", "price_usd": 0.5124, "os_type": "linux"},
        
        # Windows pricing (approximately 2x Linux pricing)
        {"machine_type": "n1-standard-2", "region": "us-central1", "price_usd": 0.1900, "os_type": "windows"},
        {"machine_type": "n1-standard-4", "region": "us-central1", "price_usd": 0.3800, "os_type": "windows"},
        {"machine_type": "n2-standard-2", "region": "us-central1", "price_usd": 0.1942, "os_type": "windows"},
        {"machine_type": "n2-standard-4", "region": "us-central1", "price_usd": 0.3884, "os_type": "windows"},
        {"machine_type": "e2-standard-2", "region": "us-central1", "price_usd": 0.1008, "os_type": "windows"},
        {"machine_type": "e2-standard-4", "region": "us-central1", "price_usd": 0.2016, "os_type": "windows"},
        
        # Additional regions (with slight price variations)
        {"machine_type": "n1-standard-4", "region": "us-east1", "price_usd": 0.1900, "os_type": "linux"},
        {"machine_type": "n1-standard-4", "region": "europe-west1", "price_usd": 0.2090, "os_type": "linux"},
        {"machine_type": "n1-standard-4", "region": "asia-east1", "price_usd": 0.2090, "os_type": "linux"},
        {"machine_type": "n2-standard-4", "region": "us-east1", "price_usd": 0.1942, "os_type": "linux"},
        {"machine_type": "n2-standard-4", "region": "europe-west1", "price_usd": 0.2136, "os_type": "linux"},
        {"machine_type": "e2-standard-4", "region": "us-east1", "price_usd": 0.1008, "os_type": "linux"},
        {"machine_type": "e2-standard-4", "region": "europe-west1", "price_usd": 0.1109, "os_type": "linux"},
    ]
    
    best_matches = []
    
    for item in gcp_pricing_data:
        # Filter by OS
        item_os = item["os_type"]
        if os.lower() in ['windows', 'win']:
            if item_os != "windows":
                continue
        else:
            if item_os != "linux":
                continue
        
        # Parse machine specifications
        machine_type = item["machine_type"]
        machine_specs = parse_gcp_machine_type(machine_type)
        
        if machine_specs["vcpus"] == 0:  # Skip unknown machine types
            continue
            
        instance_vcpus = machine_specs["vcpus"]
        instance_ram = machine_specs["ram_gb"]
        
        # Match CPU and RAM specs (allow instances that meet or exceed requirements)
        cpu_match = instance_vcpus >= vcpus
        ram_match = instance_ram >= ram_gb
        
        # Storage matching (GCP uses persistent disks)
        storage_match = True  # GCP handles storage separately via persistent disks
        
        if cpu_match and ram_match and storage_match:
            price_usd = item["price_usd"]
            region = item["region"]
            
            # Skip zero prices
            if price_usd == 0:
                continue
            
            # Calculate over-spec score
            cpu_ratio = instance_vcpus / vcpus
            ram_ratio = instance_ram / ram_gb
            over_spec_score = cpu_ratio + ram_ratio
            
            # Determine machine family
            family = "Unknown"
            if machine_type.startswith("n1-"):
                family = "N1 (1st gen)"
            elif machine_type.startswith("n2-"):
                family = "N2 (2nd gen)"
            elif machine_type.startswith("e2-"):
                family = "E2 (Cost-optimized)"
            elif machine_type.startswith("c2-"):
                family = "C2 (Compute-optimized)"
            
            best_matches.append({
                "provider": "Google Cloud",
                "region": region,
                "instance_type": machine_type,
                "machine_family": family,
                "price_per_hour_usd": round(price_usd, 6),
                "original_currency": "USD",
                "storage_type": "Persistent Disk (separate)",
                "instance_storage_gb": 0,  # GCP uses persistent disks
                "actual_vcpus": instance_vcpus,
                "actual_ram_gb": instance_ram,
                "over_spec_score": round(over_spec_score, 2),
                "os_type": item_os
            })
    
    # Remove duplicates and keep the cheapest price for each machine type in each region
    unique_matches = {}
    for match in best_matches:
        key = (match["instance_type"], match["region"])
        if key not in unique_matches or match["price_per_hour_usd"] < unique_matches[key]["price_per_hour_usd"]:
            unique_matches[key] = match
    
    # Convert back to list and sort
    deduplicated_matches = list(unique_matches.values())
    deduplicated_matches.sort(key=lambda x: (x["over_spec_score"], x["price_per_hour_usd"]))

    # Ensure all price_per_hour_usd are rounded to 4 decimals in the output
    for match in deduplicated_matches:
        match["price_per_hour_usd"] = round(match.get("price_per_hour_usd", 0), 4)

    return {
        "requested_specs": {
            "vcpus": vcpus,
            "ram_gb": ram_gb,
            "os": os,
            "storage": storage,
            "storage_gb": storage_gb,
            "duration": duration
        },
        "best_matches": deduplicated_matches[:10],
        "total_matches": len(deduplicated_matches),
        "total_raw_matches": len(best_matches),
        "note": "GCP VMs use persistent disks for storage (priced separately). Pricing data is representative."
    }

@app.get("/")
def root():
    return {"message": "Google Cloud Pricing API is running"}

@app.get("/gcp/machine-types")
def get_machine_types():
    """Get available GCP machine types and their specifications"""
    machine_types = {
        # N1 Standard
        "n1-standard-1": {"vcpus": 1, "ram_gb": 3.75, "family": "N1 (1st gen)"},
        "n1-standard-2": {"vcpus": 2, "ram_gb": 7.5, "family": "N1 (1st gen)"},
        "n1-standard-4": {"vcpus": 4, "ram_gb": 15, "family": "N1 (1st gen)"},
        "n1-standard-8": {"vcpus": 8, "ram_gb": 30, "family": "N1 (1st gen)"},
        
        # N2 Standard
        "n2-standard-2": {"vcpus": 2, "ram_gb": 8, "family": "N2 (2nd gen)"},
        "n2-standard-4": {"vcpus": 4, "ram_gb": 16, "family": "N2 (2nd gen)"},
        "n2-standard-8": {"vcpus": 8, "ram_gb": 32, "family": "N2 (2nd gen)"},
        
        # E2 Cost-optimized
        "e2-micro": {"vcpus": 1, "ram_gb": 1, "family": "E2 (Cost-optimized)"},
        "e2-small": {"vcpus": 1, "ram_gb": 2, "family": "E2 (Cost-optimized)"},
        "e2-standard-2": {"vcpus": 2, "ram_gb": 8, "family": "E2 (Cost-optimized)"},
        "e2-standard-4": {"vcpus": 4, "ram_gb": 16, "family": "E2 (Cost-optimized)"},
        
        # C2 Compute-optimized
        "c2-standard-4": {"vcpus": 4, "ram_gb": 16, "family": "C2 (Compute-optimized)"},
        "c2-standard-8": {"vcpus": 8, "ram_gb": 32, "family": "C2 (Compute-optimized)"},
        
        # High-memory
        "n1-highmem-2": {"vcpus": 2, "ram_gb": 13, "family": "N1 High-Memory"},
        "n1-highmem-4": {"vcpus": 4, "ram_gb": 26, "family": "N1 High-Memory"},
        "n2-highmem-2": {"vcpus": 2, "ram_gb": 16, "family": "N2 High-Memory"},
        "n2-highmem-4": {"vcpus": 4, "ram_gb": 32, "family": "N2 High-Memory"},
    }
    
    return {"machine_types": machine_types}

@app.get("/currency/rates")
def get_currency_rates():
    """Get current currency conversion rates"""
    return {
        "rates": CURRENCY_TO_USD,
        "note": "Rates show how much USD you get for 1 unit of foreign currency"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)  # Different port from AWS and Azure APIs