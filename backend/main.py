#!/usr/bin/env python3
"""
Command-line interface for cloud pricing data
Usage: python pricing_cli.py --vcpus 4 --ram 16 --os linux --storage 100gb
"""

import argparse
import json
import sys
from engine import get_cloud_pricing_json 

def main():
    parser = argparse.ArgumentParser(
        description="Get compute instance pricing from AWS, Azure, and Google Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pricing_cli.py --vcpus 2 --ram 8 --os linux --storage 100gb
  python pricing_cli.py --vcpus 4 --ram 16 --os windows --storage 0
  python pricing_cli.py --vcpus 8 --ram 32 --os linux --storage 1tb --output pricing.json
  python pricing_cli.py --vcpus 2 --ram 4 --os linux --storage 250gb --summary
        """
    )
    
    # Required arguments
    parser.add_argument('--vcpus', type=int, required=True,
                      help='Number of virtual CPUs required (e.g., 2, 4, 8)')
    
    parser.add_argument('--ram', type=int, required=True,
                      help='Amount of RAM in GB required (e.g., 8, 16, 32)')
    
    # Optional arguments
    parser.add_argument('--os', type=str, default='linux', choices=['linux', 'windows'],
                      help='Operating system (default: linux)')
    
    parser.add_argument('--storage', type=str, default='0',
                      help='Storage requirement (e.g., "100gb", "1tb", "0" for none)')
    
    parser.add_argument('--output', '-o', type=str,
                      help='Output file to save JSON results (default: print to stdout)')
    
    parser.add_argument('--summary', action='store_true',
                      help='Show only a summary instead of full JSON output')
    
    parser.add_argument('--cheapest', action='store_true',
                      help='Show only the cheapest option from each provider')
    
    parser.add_argument('--utilization', type=float, default=0.5,
                      help='CPU utilization factor (0 to 1, default: 0.5)')

    args = parser.parse_args()

    if not (0 <= args.utilization <= 1):
        print('Error: --utilization must be between 0 and 1.', file=sys.stderr)
        sys.exit(1)

    try:
        # Get pricing data
        print(f"Fetching pricing for {args.vcpus} vCPUs, {args.ram}GB RAM, {args.os}, {args.storage} storage...", 
              file=sys.stderr)

        pricing_data = get_cloud_pricing_json(
            vcpus=args.vcpus,
            ram_gb=args.ram,
            os=args.os,
            storage=args.storage,
            utilization=args.utilization
        )
        
        if args.summary or args.cheapest:
            # Print summary instead of full JSON
            print(f"\n Pricing Summary for {args.vcpus} vCPUs, {args.ram}GB RAM, {args.os}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            
            for provider in ["aws", "azure", "gcp"]:
                provider_data = pricing_data[provider]
                provider_name = provider.upper()
                
                if not provider_data["available"]:
                    print(f"{provider_name}: Not available", file=sys.stderr)
                elif "error" in provider_data:
                    print(f"{provider_name}: Error - {provider_data['error']}", file=sys.stderr)
                elif not provider_data["instances"]:
                    print(f"{provider_name}: No matching instances found", file=sys.stderr)
                else:
                    instances = provider_data["instances"]
                    if args.cheapest:
                        cheapest = min(instances, key=lambda x: x["price_usd_per_hour"])
                        print(f"{provider_name}: {cheapest['instance_type']} in {cheapest['region']}", file=sys.stderr)
                        print(f"         ${cheapest['price_usd_per_hour']:.4f}/hour ({cheapest['vcpus']} vCPUs, {cheapest['ram_gb']}GB RAM)", file=sys.stderr)
                        # Show carbon emissions if available
                        if 'carbon_emissions' in cheapest and cheapest['carbon_emissions'].get('co2_grams_per_hour'):
                            co2 = cheapest['carbon_emissions']['co2_grams_per_hour']
                            print(f"          {co2:.1f}g CO2/hour", file=sys.stderr)
                    else:
                        top_3 = sorted(instances, key=lambda x: x["price_usd_per_hour"])[:3]
                        print(f"{provider_name}: {len(instances)} instances found", file=sys.stderr)
                        for i, instance in enumerate(top_3, 1):
                            line = f"  {i}. {instance['instance_type']} in {instance['region']} - ${instance['price_usd_per_hour']:.4f}/hour"
                            # Add carbon info if available
                            if 'carbon_emissions' in instance and instance['carbon_emissions'].get('co2_grams_per_hour'):
                                co2 = instance['carbon_emissions']['co2_grams_per_hour']
                                line += f" ( {co2:.1f}g CO2/h)"
                            print(line, file=sys.stderr)
            
            # Find and display overall cheapest
            all_instances = []
            for provider in ["aws", "azure", "gcp"]:
                if pricing_data[provider]["available"] and pricing_data[provider]["instances"]:
                    for instance in pricing_data[provider]["instances"]:
                        all_instances.append(instance)
            
            if all_instances:
                overall_cheapest = min(all_instances, key=lambda x: x["price_usd_per_hour"])
                print(f"\n CHEAPEST OVERALL:", file=sys.stderr)
                print(f"   {overall_cheapest['provider']} {overall_cheapest['instance_type']} in {overall_cheapest['region']}", file=sys.stderr)
                print(f"   ${overall_cheapest['price_usd_per_hour']:.4f}/hour ({overall_cheapest['vcpus']} vCPUs, {overall_cheapest['ram_gb']}GB RAM)", file=sys.stderr)
                
                # Show carbon emissions if available
                if 'carbon_emissions' in overall_cheapest and overall_cheapest['carbon_emissions'].get('co2_grams_per_hour'):
                    co2 = overall_cheapest['carbon_emissions']['co2_grams_per_hour']
                    renewable = overall_cheapest['carbon_emissions'].get('renewable_energy_percentage')
                    print(f"    {co2:.1f}g CO2/hour", file=sys.stderr)
                    if renewable is not None:
                        print(f"    {renewable:.1f}% renewable energy", file=sys.stderr)
                
                # Output just the cheapest as JSON for easy parsing
                cheapest_json = {
                    "cheapest_option": {
                        "provider": overall_cheapest['provider'],
                        "instance_type": overall_cheapest['instance_type'],
                        "region": overall_cheapest['region'],
                        "price_usd_per_hour": overall_cheapest['price_usd_per_hour'],
                        "vcpus": overall_cheapest['vcpus'],
                        "ram_gb": overall_cheapest['ram_gb'],
                        "storage_type": overall_cheapest['storage_type']
                    }
                }
                
                # Include carbon emissions in JSON output if available
                if 'carbon_emissions' in overall_cheapest:
                    cheapest_json["cheapest_option"]["carbon_emissions"] = overall_cheapest['carbon_emissions']
                
                print(json.dumps(cheapest_json, indent=2))
            else:
                print("❌ No pricing data available from any provider", file=sys.stderr)
                sys.exit(1)
                
        else:
            # Output full JSON
            output_json = json.dumps(pricing_data, indent=2)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output_json)
                print(f"Results saved to {args.output}", file=sys.stderr)
            else:
                print(output_json)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()