from fastapi import FastAPI, HTTPException
from typing import Union
import requests
import json
import uvicorn
import re

app = FastAPI(title="Azure Pricing API", version="1.0.0")

# Currency conversion rates (same as AWS API)
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

def parse_azure_vm_size(vm_size: str):
    """Parse Azure VM size to extract CPU and RAM info"""
    # Azure VM naming convention: Family + Size (e.g., Standard_D2s_v3)
    size_mappings = {
        # D-series (General purpose)
        "Standard_D1_v2": {"vcpus": 1, "ram_gb": 3.5},
        "Standard_D2_v2": {"vcpus": 2, "ram_gb": 7},
        "Standard_D3_v2": {"vcpus": 4, "ram_gb": 14},
        "Standard_D4_v2": {"vcpus": 8, "ram_gb": 28},
        "Standard_D5_v2": {"vcpus": 16, "ram_gb": 56},
        
        # D-series v3
        "Standard_D2s_v3": {"vcpus": 2, "ram_gb": 8},
        "Standard_D4s_v3": {"vcpus": 4, "ram_gb": 16},
        "Standard_D8s_v3": {"vcpus": 8, "ram_gb": 32},
        "Standard_D16s_v3": {"vcpus": 16, "ram_gb": 64},
        "Standard_D32s_v3": {"vcpus": 32, "ram_gb": 128},
        
        # B-series (Burstable)
        "Standard_B1s": {"vcpus": 1, "ram_gb": 1},
        "Standard_B1ms": {"vcpus": 1, "ram_gb": 2},
        "Standard_B2s": {"vcpus": 2, "ram_gb": 4},
        "Standard_B2ms": {"vcpus": 2, "ram_gb": 8},
        "Standard_B4ms": {"vcpus": 4, "ram_gb": 16},
        "Standard_B8ms": {"vcpus": 8, "ram_gb": 32},
        
        # F-series (Compute optimized)
        "Standard_F2s_v2": {"vcpus": 2, "ram_gb": 4},
        "Standard_F4s_v2": {"vcpus": 4, "ram_gb": 8},
        "Standard_F8s_v2": {"vcpus": 8, "ram_gb": 16},
        "Standard_F16s_v2": {"vcpus": 16, "ram_gb": 32},
        
        # E-series (Memory optimized)
        "Standard_E2s_v3": {"vcpus": 2, "ram_gb": 16},
        "Standard_E4s_v3": {"vcpus": 4, "ram_gb": 32},
        "Standard_E8s_v3": {"vcpus": 8, "ram_gb": 64},
        "Standard_E16s_v3": {"vcpus": 16, "ram_gb": 128},
    }
    
    return size_mappings.get(vm_size, {"vcpus": 0, "ram_gb": 0})

@app.post("/azure/pricing")
def get_azure_price(vcpus: int, ram_gb: int, os: str, storage: Union[str, int] = 0, duration: str = "on_demand"):
    """Get Azure VM pricing based on specifications"""
    
    # Parse storage input
    storage_gb = parse_user_storage_input(storage)
    
    # Azure Retail Prices API
    api_url = "https://prices.azure.com/api/retail/prices"
    
    # Build filter for Virtual Machines (simplified)
    if os.lower() in ['windows', 'win']:
        filter_string = "serviceName eq 'Virtual Machines' and priceType eq 'Consumption'"
    else:
        filter_string = "serviceName eq 'Virtual Machines' and priceType eq 'Consumption'"
    
    try:
        # Make the API call with proper URL encoding
        params = {
            "$filter": filter_string,
            "$top": "100"
        }
        
        response = requests.get(api_url, params=params, timeout=30)
        
        if response.status_code != 200:
            # Try a simpler filter if the first one fails
            simple_filter = "serviceName eq 'Virtual Machines'"
            response = requests.get(
                api_url, 
                params={"$filter": simple_filter, "$top": "100"}, 
                timeout=30
            )
        
        response.raise_for_status()
        data = response.json()
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Azure pricing: {str(e)}")
    
    best_matches = []
    
    for item in data.get("Items", []):
        # Filter by OS at processing level since API filter might not work
        product_name = item.get("productName", "").lower()
        if os.lower() in ['windows', 'win']:
            if 'windows' not in product_name:
                continue
        else:
            if 'windows' in product_name:
                continue
        
        # Parse VM specifications
        vm_size = item.get("armSkuName", "")
        vm_specs = parse_azure_vm_size(vm_size)
        
        if vm_specs["vcpus"] == 0:  # Skip unknown VM sizes
            continue
            
        instance_vcpus = vm_specs["vcpus"]
        instance_ram = vm_specs["ram_gb"]
        
        # Match CPU and RAM specs (allow instances that meet or exceed requirements)
        cpu_match = instance_vcpus >= vcpus
        ram_match = instance_ram >= ram_gb
        
        # Storage matching (Azure VMs typically use managed disks)
        storage_match = True  # Azure handles storage separately via managed disks
        
        if cpu_match and ram_match and storage_match:
            # Get pricing info
            price_usd = item.get("unitPrice", 0)
            currency = item.get("currencyCode", "USD")
            region = item.get("armRegionName", "Unknown")
            
            # Convert to USD if needed
            if currency != "USD":
                price_usd = convert_to_usd(price_usd, currency)
            
            # Skip zero prices
            if price_usd == 0:
                continue
            
            # Calculate over-spec score
            cpu_ratio = instance_vcpus / vcpus
            ram_ratio = instance_ram / ram_gb
            over_spec_score = cpu_ratio + ram_ratio
            
            # Determine pricing type
            meter_name = item.get("meterName", "")
            pricing_type = "Standard"
            if "spot" in meter_name.lower():
                pricing_type = "Spot"
            elif "low priority" in meter_name.lower():
                pricing_type = "Low Priority"
            
            best_matches.append({
                "provider": "Azure",
                "region": region,
                "instance_type": vm_size,
                "price_per_hour_usd": round(price_usd, 4),
                "pricing_type": pricing_type,
                "original_currency": currency,
                "storage_type": "Managed Disk (separate)",
                "instance_storage_gb": 0,  # Azure uses managed disks
                "actual_vcpus": instance_vcpus,
                "actual_ram_gb": instance_ram,
                "over_spec_score": round(over_spec_score, 2),
                "product_name": item.get("productName", ""),
                "meter_name": meter_name
            })
    
    # Remove duplicates and keep the cheapest price for each VM type in each region
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
        "note": "Azure VMs use managed disks for storage (priced separately). Showing lowest price per VM type per region."
    }

@app.get("/")
def root():
    return {"message": "Azure Pricing API is running"}

@app.get("/azure/vm-sizes")
def get_vm_sizes():
    """Get available Azure VM sizes and their specifications"""
    vm_sizes = {
        "Standard_D1_v2": {"vcpus": 1, "ram_gb": 3.5},
        "Standard_D2_v2": {"vcpus": 2, "ram_gb": 7},
        "Standard_D3_v2": {"vcpus": 4, "ram_gb": 14},
        "Standard_D4_v2": {"vcpus": 8, "ram_gb": 28},
        "Standard_D2s_v3": {"vcpus": 2, "ram_gb": 8},
        "Standard_D4s_v3": {"vcpus": 4, "ram_gb": 16},
        "Standard_D8s_v3": {"vcpus": 8, "ram_gb": 32},
        "Standard_B1s": {"vcpus": 1, "ram_gb": 1},
        "Standard_B2s": {"vcpus": 2, "ram_gb": 4},
        "Standard_B4ms": {"vcpus": 4, "ram_gb": 16},
        "Standard_F2s_v2": {"vcpus": 2, "ram_gb": 4},
        "Standard_F4s_v2": {"vcpus": 4, "ram_gb": 8},
        "Standard_E2s_v3": {"vcpus": 2, "ram_gb": 16},
        "Standard_E4s_v3": {"vcpus": 4, "ram_gb": 32},
    }
    
    return {"vm_sizes": vm_sizes}

@app.get("/currency/rates")
def get_currency_rates():
    """Get current currency conversion rates"""
    return {
        "rates": CURRENCY_TO_USD,
        "note": "Rates show how much USD you get for 1 unit of foreign currency"
    }

@app.get("/debug/azure-data")
def debug_azure_data():
    """Debug endpoint to see raw Azure pricing data"""
    api_url = "https://prices.azure.com/api/retail/prices"
    
    try:
        response = requests.get(
            api_url,
            params={
                "$filter": "serviceName eq 'Virtual Machines'",
                "$top": "10"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "status": "success",
            "sample_items": data.get("Items", [])[:5],
            "total_items": len(data.get("Items", [])),
            "api_url": response.url
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "api_url": api_url
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Different port from AWS API