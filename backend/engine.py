#!/usr/bin/env python3
"""
Simple function-based cloud pricing retrieval
This provides direct access to pricing functions without web server dependencies
"""

import json
import sys
from typing import Union
import carbon_intensity

def add_carbon_emissions_to_instance(instance, utilization: float = 0.5):
    """Add carbon emissions data to an instance, with optional utilization factor"""
    region = instance.get("region", "")
    # Map cloud region to electricityMap zone using standard country/region codes
    zone = get_electricitymap_zone(region)
    try:
        ci = carbon_intensity.get_carbon_intensity(zone)
        vcpus = instance.get("vcpus", 1)
        ram_gb = instance.get("ram_gb", 1)
        # Fixed Estimated values
        cpu_watts_per_vcpu = 15.0
        memory_watts_per_gb = 1.5
        # Power calculation
        max_power_watts = (vcpus * cpu_watts_per_vcpu) + (ram_gb * memory_watts_per_gb)
        idle_power_watts = max_power_watts * 0.35
        actual_power_watts = idle_power_watts + utilization * (max_power_watts - idle_power_watts)
        kwh = actual_power_watts / 1000.0  # for 1 hour
        co2_grams = ci["carbon_intensity"] * kwh if ci["carbon_intensity"] else None
        instance["carbon_emissions"] = {
            "co2_grams_per_hour": round(co2_grams, 2) if co2_grams else None,
            "carbon_intensity_region": region,
            "carbon_intensity_value_g_per_kwh": ci["carbon_intensity"] if ci and "carbon_intensity" in ci else None,
            "renewable_energy_percentage": 100 - ci["renewable_percentage"] if ci["renewable_percentage"] is not None else None,
            "emission_source": "electricityMap",
            "zone_used": zone,
            "power_draw_kwh": round(kwh, 4),
            "power_calculation": {
                "max_power_watts": round(max_power_watts, 2),
                "idle_power_watts": round(idle_power_watts, 2),
                "actual_power_watts": round(actual_power_watts, 2),
                "cpu_watts_per_vcpu": cpu_watts_per_vcpu,
                "memory_watts_per_gb": memory_watts_per_gb,
                "utilization": utilization
            }
        }
    except Exception as e:
        instance["carbon_emissions"] = {
            "co2_grams_per_hour": None,
            "carbon_intensity_region": region,
            "renewable_energy_percentage": None,
            "emission_source": "electricityMap",
            "zone_used": zone,
            "error": str(e)
        }
    return instance

def get_electricitymap_zone(region):
    """Map cloud provider regions to valid electricityMap zones (country codes work best)"""
    
    # Load region-to-zone mapping from YAML file
    import os
    import yaml
    mapping_path = os.path.join(os.path.dirname(__file__), "region_to_zone.yaml")
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            region_to_zone = yaml.safe_load(f)
    except Exception:
        region_to_zone = {}

    # Direct lookup first
    if region in region_to_zone:
        return region_to_zone[region]
    
    # Fallback pattern matching using country codes (now modular via YAML)
    region_lower = region.lower()
    fallback_path = os.path.join(os.path.dirname(__file__), "region_fallback_keywords.yaml")
    try:
        with open(fallback_path, "r", encoding="utf-8") as f:
            fallback_keywords = yaml.safe_load(f)
    except Exception:
        fallback_keywords = {}

    for country_code, keywords in fallback_keywords.items():
        if any(keyword in region_lower for keyword in keywords):
            return country_code

    # Default fallbacks using country codes
    if region.startswith("us"):
        return "US"
    elif region.startswith("eu"):
        return "DE"
    else:
        return "US"  # Ultimate fallback

def get_cloud_pricing_json(vcpus: int, ram_gb: int, storage: Union[str, int] = 0, utilization: float = 0.5):
    """
    Get pricing from all cloud providers and return as clean JSON
    
    Args:
        vcpus: Number of vCPUs required
        ram_gb: RAM in GB required
        storage: Storage requirement (e.g., "100gb", "1tb", or 0)
    
    Returns:
        Dictionary with pricing data from all providers
    """
    
    # Import individual pricing modules
    try:
        import pricing.aws_pricing as aws_pricing
        aws_available = True
    except ImportError:
        aws_available = False
    
    try:
        import pricing.azure_pricing as azure_pricing
        azure_available = True
    except ImportError:
        azure_available = False
        
    try:
        import pricing.google_pricing as google_pricing
        gcp_available = True
    except ImportError:
        gcp_available = False
    
    results = {
        "request": {
            "vcpus": vcpus,
            "ram_gb": ram_gb,
            "storage": storage
        },
        "aws": {
            "available": aws_available,
            "instances": []
        },
        "azure": {
            "available": azure_available,
            "instances": []
        },
        "gcp": {
            "available": gcp_available,
            "instances": []
        }
    }
    
    # Get AWS pricing
    if aws_available:
        try:
            aws_result = aws_pricing.get_aws_price(vcpus, ram_gb, storage)
            for match in aws_result.get("best_matches", [])[:10]:
                instance = {
                    "provider": "AWS",
                    "instance_type": match.get("instance_type"),
                    "region": match.get("region"),
                    "price_usd_per_hour": match.get("price_per_hour_usd"),
                    "vcpus": match.get("actual_vcpus"),
                    "ram_gb": match.get("actual_ram_gb"),
                    "storage_type": match.get("storage_type"),
                    "storage_gb": match.get("instance_storage_gb", 0),
                    "attached_storage_gb": storage if storage else 0
                }
                # Add carbon emissions data
                instance = add_carbon_emissions_to_instance(instance, utilization=utilization)
                results["aws"]["instances"].append(instance)
        except Exception as e:
            results["aws"]["error"] = str(e)
    
    # Get Azure pricing
    if azure_available:
        try:
            azure_result = azure_pricing.get_azure_price(vcpus, ram_gb, storage)
            for match in azure_result.get("best_matches", [])[:10]:
                instance = {
                    "provider": "Azure",
                    "instance_type": match.get("instance_type"),
                    "region": match.get("region"),
                    "price_usd_per_hour": match.get("price_per_hour_usd"),
                    "vcpus": match.get("actual_vcpus"),
                    "ram_gb": match.get("actual_ram_gb"),
                    "storage_type": match.get("storage_type"),
                    "storage_gb": match.get("instance_storage_gb", 0),
                    "attached_storage_gb": storage if storage else 0
                }
                # Add carbon emissions data
                instance = add_carbon_emissions_to_instance(instance, utilization=utilization)
                results["azure"]["instances"].append(instance)
        except Exception as e:
            results["azure"]["error"] = str(e)
    
    # Get GCP pricing
    if gcp_available:
        try:
            gcp_result = google_pricing.get_gcp_price(vcpus, ram_gb, storage)
            for match in gcp_result.get("best_matches", [])[:10]:
                instance = {
                    "provider": "GCP",
                    "instance_type": match.get("instance_type"),
                    "region": match.get("region"),
                    "price_usd_per_hour": match.get("price_per_hour_usd"),
                    "vcpus": match.get("actual_vcpus"),
                    "ram_gb": match.get("actual_ram_gb"),
                    "storage_type": match.get("storage_type"),
                    "storage_gb": match.get("instance_storage_gb", 0),
                    "attached_storage_gb": storage if storage else 0,
                    "machine_family": match.get("machine_family", "")
                }
                # Add carbon emissions data
                instance = add_carbon_emissions_to_instance(instance, utilization=utilization)
                results["gcp"]["instances"].append(instance)
        except Exception as e:
            results["gcp"]["error"] = str(e)
    
    return results

def example_usage():
    """Example of how to use the pricing function"""
    
    print("Getting pricing for 2 vCPUs, 8GB RAM, Linux, 100GB storage...")
    
    pricing_data = get_cloud_pricing_json(
        vcpus=2,
        ram_gb=8,
        # os removed
        storage="100gb"
    )
    
    # Print as formatted JSON
    print(json.dumps(pricing_data, indent=2))
    
    # Example of accessing specific data
    print("\nSummary:")
    for provider in ["aws", "azure", "gcp"]:
        provider_data = pricing_data[provider]
        if provider_data["available"] and provider_data["instances"]:
            cheapest = min(provider_data["instances"], key=lambda x: x["price_usd_per_hour"])
            print(f"{provider.upper()}: {cheapest['instance_type']} - ${cheapest['price_usd_per_hour']:.4f}/hour")
        else:
            print(f"{provider.upper()}: No data available")

if __name__ == "__main__":
    # Allow command line usage
    if len(sys.argv) == 5:
        vcpus = int(sys.argv[1])
        ram_gb = int(sys.argv[2])
        storage = sys.argv[3]
        result = get_cloud_pricing_json(vcpus, ram_gb, storage)
        print(json.dumps(result, indent=2))
    else:
        example_usage()