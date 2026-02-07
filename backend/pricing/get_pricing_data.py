#!/usr/bin/env python3
"""
Standalone script to get unified cloud pricing data as JSON output
This script provides direct pricing information from AWS, Azure, and GCP
without requiring a web server.
"""

import json
import sys
import re
from datetime import datetime
from typing import Union, Dict, Any, List

# Import the pricing functions
try:
    import pricing.aws_pricing as aws_pricing
    AWS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AWS pricing module not available: {e}")
    AWS_AVAILABLE = False

try:
    import pricing.azure_pricing as azure_pricing  
    AZURE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Azure pricing module not available: {e}")
    AZURE_AVAILABLE = False

try:
    import pricing.google_pricing as google_pricing
    GCP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: GCP pricing module not available: {e}")
    GCP_AVAILABLE = False

def parse_user_storage_input(storage_input: Union[str, int]) -> int:
    """Parse user storage input and convert to GB"""
    if isinstance(storage_input, int):
        return storage_input
    
    if not storage_input or storage_input == "0":
        return 0
    
    storage_str = str(storage_input).lower().replace(" ", "")
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(gb|tb|g|t)?$', storage_str)
    
    if not match:
        raise ValueError(f"Invalid storage format: {storage_input}")
    
    number = float(match.group(1))
    unit = match.group(2) or 'gb'
    
    if unit in ['tb', 't']:
        return int(number * 1000)
    elif unit in ['gb', 'g']:
        return int(number)
    else:
        return int(number)

def get_unified_cloud_pricing(
    vcpus: int,
    ram_gb: int,
    os: str = "linux",
    storage: Union[str, int] = 0,
    duration: str = "on_demand",
    limit_per_provider: int = 10
) -> Dict[str, Any]:
    """
    Get compute instance pricing from all available cloud providers
    in a unified JSON format.
    
    Parameters:
    - vcpus: Number of virtual CPUs required
    - ram_gb: Amount of RAM in GB required  
    - os: Operating system ("linux" or "windows")
    - storage: Storage requirement (e.g., "250gb", "1tb", or 0 for no specific requirement)
    - duration: Pricing duration ("on_demand" for now)
    - limit_per_provider: Maximum number of results per provider (default: 10)
    
    Returns:
    - Unified dictionary with pricing data from all providers
    """
    
    # Validate inputs
    if vcpus <= 0 or ram_gb <= 0:
        raise ValueError("vcpus and ram_gb must be positive integers")
    
    if os.lower() not in ['linux', 'windows', 'win']:
        raise ValueError("os must be 'linux' or 'windows'")
    
    # Parse storage
    storage_gb = parse_user_storage_input(storage)
    
    # Prepare the response structure
    unified_response = {
        "request_metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "requested_specs": {
                "vcpus": vcpus,
                "ram_gb": ram_gb,
                "os": os.lower(),
                "storage": storage,
                "storage_gb": storage_gb,
                "duration": duration,
                "limit_per_provider": limit_per_provider
            }
        },
        "providers": {
            "aws": {
                "status": "unavailable" if not AWS_AVAILABLE else "success",
                "instances": [],
                "total_matches": 0,
                "error": None if AWS_AVAILABLE else "AWS module not available"
            },
            "azure": {
                "status": "unavailable" if not AZURE_AVAILABLE else "success", 
                "instances": [],
                "total_matches": 0,
                "error": None if AZURE_AVAILABLE else "Azure module not available"
            },
            "gcp": {
                "status": "unavailable" if not GCP_AVAILABLE else "success",
                "instances": [],
                "total_matches": 0,
                "error": None if GCP_AVAILABLE else "GCP module not available"
            }
        },
        "summary": {
            "total_instances_found": 0,
            "cheapest_overall": None,
            "providers_with_data": []
        }
    }
    
    # Fetch AWS pricing
    if AWS_AVAILABLE:
        try:
            result = aws_pricing.get_aws_price(vcpus, ram_gb, os, storage, duration)
            
            instances = []
            for match in result.get("best_matches", [])[:limit_per_provider]:
                instances.append({
                    "instance_type": match.get("instance_type"),
                    "region": match.get("region"),
                    "price_per_hour_usd": round(match.get("price_per_hour_usd", 0), 4),
                    "vcpus": match.get("actual_vcpus"),
                    "ram_gb": match.get("actual_ram_gb"),
                    "storage_type": match.get("storage_type"),
                    "storage_gb": match.get("instance_storage_gb", 0),
                    "over_spec_score": match.get("over_spec_score"),
                    "currency": match.get("original_currency", "USD"),
                    "pricing_model": "On-Demand"
                })
            
            unified_response["providers"]["aws"]["instances"] = instances
            unified_response["providers"]["aws"]["total_matches"] = result.get("total_matches", 0)
            
        except Exception as e:
            unified_response["providers"]["aws"]["status"] = "error"
            unified_response["providers"]["aws"]["error"] = str(e)
    
    # Fetch Azure pricing
    if AZURE_AVAILABLE:
        try:
            result = azure_pricing.get_azure_price(vcpus, ram_gb, os, storage, duration)
            
            instances = []
            for match in result.get("best_matches", [])[:limit_per_provider]:
                instances.append({
                    "instance_type": match.get("instance_type"),
                    "region": match.get("region"),
                    "price_per_hour_usd": round(match.get("price_per_hour_usd", 0), 4),
                    "vcpus": match.get("actual_vcpus"),
                    "ram_gb": match.get("actual_ram_gb"),
                    "storage_type": match.get("storage_type"),
                    "storage_gb": match.get("instance_storage_gb", 0),
                    "over_spec_score": match.get("over_spec_score"),
                    "currency": match.get("original_currency", "USD"),
                    "pricing_model": match.get("pricing_type", "Standard")
                })
            
            unified_response["providers"]["azure"]["instances"] = instances
            unified_response["providers"]["azure"]["total_matches"] = result.get("total_matches", 0)
            
        except Exception as e:
            unified_response["providers"]["azure"]["status"] = "error"
            unified_response["providers"]["azure"]["error"] = str(e)
    
    # Fetch GCP pricing
    if GCP_AVAILABLE:
        try:
            result = google_pricing.get_gcp_price(vcpus, ram_gb, os, storage, duration)
            
            instances = []
            for match in result.get("best_matches", [])[:limit_per_provider]:
                instances.append({
                    "instance_type": match.get("instance_type"),
                    "region": match.get("region"),
                    "price_per_hour_usd": round(match.get("price_per_hour_usd", 0), 4),
                    "vcpus": match.get("actual_vcpus"),
                    "ram_gb": match.get("actual_ram_gb"),
                    "storage_type": match.get("storage_type"),
                    "storage_gb": match.get("instance_storage_gb", 0),
                    "over_spec_score": match.get("over_spec_score"),
                    "currency": match.get("original_currency", "USD"),
                    "pricing_model": "Standard",
                    "machine_family": match.get("machine_family", "Unknown")
                })
            
            unified_response["providers"]["gcp"]["instances"] = instances
            unified_response["providers"]["gcp"]["total_matches"] = result.get("total_matches", 0)
            
        except Exception as e:
            unified_response["providers"]["gcp"]["status"] = "error"
            unified_response["providers"]["gcp"]["error"] = str(e)
    
    # Calculate summary statistics
    all_instances = []
    providers_with_data = []
    
    for provider_name, provider_data in unified_response["providers"].items():
        if provider_data["status"] == "success" and provider_data["instances"]:
            providers_with_data.append(provider_name.upper())
            for instance in provider_data["instances"]:
                instance["provider"] = provider_name.upper()
                all_instances.append(instance)
    
    # Find cheapest overall option
    if all_instances:
        cheapest = min(all_instances, key=lambda x: x["price_per_hour_usd"])
        unified_response["summary"]["cheapest_overall"] = {
            "provider": cheapest["provider"],
            "instance_type": cheapest["instance_type"],
            "region": cheapest["region"],
            "price_per_hour_usd": round(cheapest["price_per_hour_usd"], 4),
            "vcpus": cheapest["vcpus"],
            "ram_gb": cheapest["ram_gb"]
        }
    
    unified_response["summary"]["total_instances_found"] = len(all_instances)
    unified_response["summary"]["providers_with_data"] = providers_with_data
    
    return unified_response

def main():
    """Main function to run the pricing comparison"""
    print("🌟 Cloud Pricing Unified Data Fetcher")
    print("=" * 50)
    
    # Example usage scenarios
    test_scenarios = [
        {
            "name": "Small Linux instance",
            "vcpus": 2,
            "ram_gb": 8,
            "os": "linux",
            "storage": "100gb"
        },
        {
            "name": "Medium Linux instance", 
            "vcpus": 4,
            "ram_gb": 16,
            "os": "linux",
            "storage": "250gb"
        },
        {
            "name": "Small Windows instance",
            "vcpus": 2,
            "ram_gb": 8,
            "os": "windows",
            "storage": "0"
        },
        {
            "name": "Large Linux instance",
            "vcpus": 8,
            "ram_gb": 32,
            "os": "linux",
            "storage": "500gb"
        }
    ]
    
    all_results = {}
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📊 Test {i}: {scenario['name']}")
        print("-" * 30)
        
        try:
            # Remove 'name' from scenario for the API call
            params = {k: v for k, v in scenario.items() if k != 'name'}
            
            print(f"Specs: {params['vcpus']} vCPUs, {params['ram_gb']}GB RAM, {params['os']}, {params['storage']} storage")
            
            # Get pricing data
            results = get_unified_cloud_pricing(**params)
            
            # Store results
            all_results[f"scenario_{i}"] = {
                "description": scenario['name'],
                "parameters": params,
                "results": results
            }
            
            # Print summary
            print(f"Total instances found: {results['summary']['total_instances_found']}")
            
            if results['summary']['cheapest_overall']:
                cheapest = results['summary']['cheapest_overall']
                print(f"💰 Cheapest: {cheapest['provider']} {cheapest['instance_type']} in {cheapest['region']} - ${cheapest['price_per_hour_usd']:.4f}/hour")
            
            providers_with_data = results['summary']['providers_with_data']
            if providers_with_data:
                print(f"📈 Data from: {', '.join(providers_with_data)}")
            else:
                print("❌ No pricing data available")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            all_results[f"scenario_{i}"] = {
                "description": scenario['name'],
                "parameters": params,
                "error": str(e)
            }
    
    # Save all results to a JSON file
    output_file = "unified_cloud_pricing_results.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n📁 All results saved to: {output_file}")
    except Exception as e:
        print(f"\n❌ Failed to save results: {e}")
    
    print(f"\n✨ Done! Check {output_file} for complete JSON output.")
    
    # Also print one complete example as JSON to stdout
    if all_results:
        first_scenario = list(all_results.values())[0]
        if 'results' in first_scenario:
            print(f"\n📋 Sample JSON output for '{first_scenario['description']}':")
            print(json.dumps(first_scenario['results'], indent=2))

if __name__ == "__main__":
    main()