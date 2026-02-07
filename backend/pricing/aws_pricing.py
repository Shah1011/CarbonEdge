from fastapi import FastAPI, HTTPException
from typing import Union
import boto3
import json
import uvicorn
import re
import requests

app = FastAPI(title="AWS Pricing API", version="1.0.0")

# Initialize AWS Pricing client (only available in us-east-1)
try:
    client = boto3.client("pricing", region_name="us-east-1")
except Exception as e:
    print(f"Warning: Could not initialize AWS client: {e}")
    client = None

# Currency conversion rates (approximate, for common currencies)
CURRENCY_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,  # 1 EUR ≈ 1.08 USD
    "GBP": 1.25,  # 1 GBP ≈ 1.25 USD
    "CAD": 0.74,  # 1 CAD ≈ 0.74 USD
    "AUD": 0.66,  # 1 AUD ≈ 0.66 USD
    "JPY": 0.0067, # 1 JPY ≈ 0.0067 USD
    "CNY": 0.14,  # 1 CNY ≈ 0.14 USD
    "INR": 0.012, # 1 INR ≈ 0.012 USD
}

def convert_to_usd(price_str: str, currency: str) -> float:
    """Convert price from any currency to USD"""
    try:
        price = float(price_str)
        if currency in CURRENCY_TO_USD:
            return price * CURRENCY_TO_USD[currency]
        else:
            # If currency not in our list, assume it's already USD
            print(f"Warning: Unknown currency {currency}, assuming USD")
            return price
    except (ValueError, TypeError):
        return 0.0

def get_live_exchange_rates():
    """Get live exchange rates (optional enhancement)"""
    try:
        # Using a free API for live rates (you can replace with your preferred service)
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if response.status_code == 200:
            data = response.json()
            rates = data.get("rates", {})
            # Convert to our format (how much USD you get for 1 unit of foreign currency)
            live_rates = {}
            for currency, rate in rates.items():
                live_rates[currency] = 1.0 / rate if rate != 0 else 1.0
            live_rates["USD"] = 1.0
            return live_rates
    except:
        pass
    return CURRENCY_TO_USD

def parse_user_storage_input(storage_input: Union[str, int]) -> int:
    """Parse user storage input and convert to GB"""
    if isinstance(storage_input, int):
        return storage_input
    
    if not storage_input or storage_input == "0":
        return 0
    
    # Convert to lowercase and remove spaces
    storage_str = str(storage_input).lower().replace(" ", "")
    
    # Extract number and unit using regex
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(gb|tb|g|t)?$', storage_str)
    
    if not match:
        raise HTTPException(status_code=400, detail=f"Invalid storage format: {storage_input}. Use formats like '250gb', '1tb', '500', etc.")
    
    number = float(match.group(1))
    unit = match.group(2) or 'gb'  # Default to GB if no unit specified
    
    # Convert to GB
    if unit in ['tb', 't']:
        return int(number * 1000)  # TB to GB
    elif unit in ['gb', 'g']:
        return int(number)
    else:
        return int(number)  # Assume GB if unclear

def parse_storage_info(storage_attr):
    """Parse AWS storage attribute and return storage in GB"""
    if not storage_attr or storage_attr.lower() in ['ebs only', 'ebs-only']:
        return 0  # EBS-only instances have no instance storage
    
    try:
        # Handle formats like "1 x 150 NVMe SSD" or "2 x 300 SSD"
        if 'x' in storage_attr.lower():
            parts = storage_attr.lower().split('x')
            if len(parts) >= 2:
                count = int(parts[0].strip())
                size_part = parts[1].strip().split()[0]
                size = float(size_part.replace(',', ''))
                return count * size
        
        # Handle simple formats like "150 GB SSD"
        numbers = [float(s) for s in storage_attr.replace(',', '').split() if s.replace('.', '').isdigit()]
        if numbers:
            return numbers[0]
    except:
        pass
    
    return 0

@app.post("/aws/pricing")
def get_aws_price(vcpus: int, ram_gb: int, storage: Union[str, int] = 0, duration: str = "on_demand"):
    if not client:
        raise HTTPException(status_code=500, detail="AWS client not initialized")
    
    # Parse storage input to GB
    storage_gb = parse_user_storage_input(storage)
    
    # Add storage filter if specified
    filters = [
        {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
        {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
    ]
    
    response = client.get_products(
        ServiceCode="AmazonEC2",
        Filters=filters,
        MaxResults=100  # AWS limit is 100
    )

    best_matches = []
    debug_info = []  # For debugging
    
    for price_item in response["PriceList"]:
        data = json.loads(price_item)
        attributes = data["product"]["attributes"]

        if "vcpu" in attributes and "memory" in attributes:
            instance_vcpus = int(attributes["vcpu"])
            instance_ram = float(attributes["memory"].split()[0])
            
            # Parse storage information
            instance_storage = 0
            storage_raw = attributes.get("storage", "")
            if storage_raw:
                instance_storage = parse_storage_info(storage_raw)

            # Debug: collect info about instances with storage
            if instance_storage > 0:
                debug_info.append({
                    "instance_type": attributes.get("instanceType", "unknown"),
                    "vcpus": instance_vcpus,
                    "ram_gb": instance_ram,
                    "storage_raw": storage_raw,
                    "storage_parsed": instance_storage
                })

            # Match CPU and RAM specs (allow instances that meet or exceed requirements)
            cpu_match = instance_vcpus >= vcpus
            ram_match = instance_ram >= ram_gb
            
            # Storage matching logic
            storage_match = True
            if storage_gb > 0:
                # If user requests storage, instance must have at least that much
                # OR be EBS-only (where you can attach any size EBS volume)
                storage_match = (instance_storage >= storage_gb) or (instance_storage == 0)

            if cpu_match and ram_match and storage_match:
                terms = data["terms"]["OnDemand"]
                for term_val in terms.values():
                    for price_dim in term_val["priceDimensions"].values():
                        # Handle different currency formats and convert to USD
                        price_per_unit = price_dim.get("pricePerUnit", {})
                        price_usd = 0.0
                        original_currency = "USD"
                        original_price = "0"
                        
                        if "USD" in price_per_unit:
                            price_usd = float(price_per_unit["USD"])
                            original_price = price_per_unit["USD"]
                        elif price_per_unit:
                            # Convert from other currency to USD
                            currency = list(price_per_unit.keys())[0]
                            price_str = list(price_per_unit.values())[0]
                            price_usd = convert_to_usd(price_str, currency)
                            original_currency = currency
                            original_price = price_str
                        else:
                            continue  # Skip if no price available
                        
                        # Skip if price is 0 or empty
                        if not price_usd or price_usd == 0:
                            continue
                            
                        region = attributes["location"]
                        
                        storage_type = "EBS-only" if instance_storage == 0 else f"{instance_storage}GB Instance Store"

                        # Calculate how much "over-spec" this instance is
                        cpu_ratio = instance_vcpus / vcpus
                        ram_ratio = instance_ram / ram_gb
                        over_spec_score = cpu_ratio + ram_ratio  # Lower is better

                        best_matches.append({
                            "provider": "AWS",
                            "region": region,
                            "instance_type": attributes["instanceType"],
                            "price_per_hour_usd": round(price_usd, 6),
                            "original_price": original_price,
                            "original_currency": original_currency,
                            "storage_type": storage_type,
                            "instance_storage_gb": instance_storage,
                            "actual_vcpus": instance_vcpus,
                            "actual_ram_gb": instance_ram,
                            "over_spec_score": round(over_spec_score, 2),
                            "storage_raw": storage_raw  # Add raw storage for debugging
                        })

    # Sort by over-spec score first (closest to requirements), then by price
    best_matches.sort(key=lambda x: (x["over_spec_score"], float(x["price_per_hour_usd"])))

    # Ensure all price_per_hour_usd are rounded to 4 decimals in the output
    for match in best_matches:
        match["price_per_hour_usd"] = round(match.get("price_per_hour_usd", 0), 4)

    return {
        "requested_specs": {
            "vcpus": vcpus, "ram_gb": ram_gb, 
            "storage": storage, "storage_gb": storage_gb, "duration": duration
        },
        "best_matches": best_matches[:10],  # Limit results
        "total_matches": len(best_matches),
        "debug_instances_with_storage": debug_info[:5] if debug_info else "No instances with storage found"
    }

@app.get("/")
def root():
    return {"message": "AWS Pricing API is running"}

@app.get("/currency/rates")
def get_currency_rates():
    """Get current currency conversion rates"""
    return {
        "rates": CURRENCY_TO_USD,
        "note": "Rates show how much USD you get for 1 unit of foreign currency"
    }

@app.post("/currency/update")
def update_currency_rates():
    """Update currency rates with live data"""
    global CURRENCY_TO_USD
    try:
        live_rates = get_live_exchange_rates()
        CURRENCY_TO_USD.update(live_rates)
        return {
            "message": "Currency rates updated successfully",
            "rates": CURRENCY_TO_USD
        }
    except Exception as e:
        return {
            "message": "Failed to update rates, using cached rates",
            "error": str(e),
            "rates": CURRENCY_TO_USD
        }

@app.get("/debug/instances")
def debug_instances(vcpus: int = None, ram_gb: int = None):
    """Debug endpoint to see what instances are available"""
    if not client:
        raise HTTPException(status_code=500, detail="AWS client not initialized")
    
    response = client.get_products(
        ServiceCode="AmazonEC2",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ],
        MaxResults=100
    )
    
    instances_with_storage = []
    all_specs = set()
    
    for price_item in response["PriceList"]:
        data = json.loads(price_item)
        attributes = data["product"]["attributes"]
        
        if "vcpu" in attributes and "memory" in attributes:
            instance_vcpus = int(attributes["vcpu"])
            instance_ram = float(attributes["memory"].split()[0])
            storage_raw = attributes.get("storage", "")
            instance_storage = parse_storage_info(storage_raw) if storage_raw else 0
            
            # Collect all CPU/RAM combinations
            all_specs.add((instance_vcpus, instance_ram))
            
            # Only show instances with storage > 0
            if instance_storage > 0:
                instances_with_storage.append({
                    "instance_type": attributes.get("instanceType", "unknown"),
                    "vcpus": instance_vcpus,
                    "ram_gb": instance_ram,
                    "storage_raw": storage_raw,
                    "storage_gb": instance_storage,
                    "region": attributes.get("location", "unknown")
                })
    
    # Filter by requested specs if provided
    if vcpus is not None and ram_gb is not None:
        instances_with_storage = [i for i in instances_with_storage 
                                if i["vcpus"] == vcpus and i["ram_gb"] == ram_gb]
    
    return {
        "instances_with_storage": instances_with_storage[:20],
        "total_with_storage": len(instances_with_storage),
        "available_cpu_ram_combos": sorted(list(all_specs))[:20]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
