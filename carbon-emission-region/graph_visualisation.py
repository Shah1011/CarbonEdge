#!/usr/bin/env python3
"""
Carbon Emission Visualization Script
Creates line graphs showing carbon intensity changes over time from CSV files
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import argparse
import seaborn as sns

def read_carbon_data(csv_file_path):
    """
    Read carbon emission data from CSV file
    
    Args:
        csv_file_path: Path to the CSV file
    
    Returns:
        DataFrame with carbon intensity data
    """
    try:
        df = pd.read_csv(csv_file_path)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        return df
    except Exception as e:
        print(f"Error reading {csv_file_path}: {e}")
        return None

def create_line_graph(df, region, provider=None, save_path=None, show_plot=True):
    """
    Create a line graph of carbon intensity over time (yearly averages)
    
    Args:
        df: DataFrame with carbon intensity data
        region: Region name for the title
        provider: Provider name (optional)
        save_path: Path to save the graph (optional)
        show_plot: Whether to display the plot
    """
    plt.figure(figsize=(10, 6))
    
    # Extract year and month from timestamp and calculate monthly averages
    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month
    df['year_month'] = df['timestamp'].dt.to_period('M')
    monthly_avg = df.groupby('year_month')['carbon_intensity'].mean().reset_index()
    
    # Filter for years 2021-2025
    monthly_avg = monthly_avg[
        (monthly_avg['year_month'].dt.year >= 2021) & 
        (monthly_avg['year_month'].dt.year <= 2025)
    ]
    
    # Convert period to timestamp for plotting
    monthly_avg['date'] = monthly_avg['year_month'].dt.to_timestamp()
    
    # Create the line plot with markers
    plt.plot(monthly_avg['date'], monthly_avg['carbon_intensity'], 
             linewidth=2, marker='o', markersize=4, color='steelblue', alpha=0.8)
    
    # Formatting
    title = f"Monthly Average Carbon Intensity"
    if provider:
        title += f" - {provider.upper()}"
    title += f" - {region}"
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Carbon Intensity (gCO₂eq/kWh)', fontsize=12)
    
    # Format x-axis to show years
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    plt.gca().xaxis.set_major_locator(mdates.YearLocator())
    plt.gca().xaxis.set_minor_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=0)
    
    # Set Y-axis range
    plt.ylim(200, 700)
    
    # Add grid
    plt.grid(True, alpha=0.3)
    
    # Add statistics text box
    mean_ci = monthly_avg['carbon_intensity'].mean()
    min_ci = monthly_avg['carbon_intensity'].min()
    max_ci = monthly_avg['carbon_intensity'].max()
    
    stats_text = f'Mean: {mean_ci:.1f}\nMin: {min_ci:.1f}\nMax: {max_ci:.1f}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Graph saved to: {save_path}")
    
    # Show plot
    if show_plot:
        plt.show()
    
    plt.close()

def create_multiple_regions_graph(csv_files, save_path=None, show_plot=True):
    """
    Create a line graph comparing multiple regions (yearly averages)
    
    Args:
        csv_files: List of (csv_path, region_name) tuples
        save_path: Path to save the graph (optional)
        show_plot: Whether to display the plot
    """
    plt.figure(figsize=(12, 8))
    
    colors = plt.cm.Set3(range(len(csv_files)))
    
    for i, (csv_path, region_name) in enumerate(csv_files):
        df = read_carbon_data(csv_path)
        if df is not None:
            # Extract year and month from timestamp and calculate monthly averages
            df['year'] = df['timestamp'].dt.year
            df['month'] = df['timestamp'].dt.month
            df['year_month'] = df['timestamp'].dt.to_period('M')
            monthly_avg = df.groupby('year_month')['carbon_intensity'].mean().reset_index()
            
            # Filter for years 2021-2025
            monthly_avg = monthly_avg[
                (monthly_avg['year_month'].dt.year >= 2021) & 
                (monthly_avg['year_month'].dt.year <= 2025)
            ]
            
            # Convert period to timestamp for plotting
            monthly_avg['date'] = monthly_avg['year_month'].dt.to_timestamp()
            
            plt.plot(monthly_avg['date'], monthly_avg['carbon_intensity'], 
                    linewidth=2, marker='o', markersize=3, label=region_name, 
                    color=colors[i], alpha=0.8)
    
    plt.title('Monthly Average Carbon Intensity Comparison Across Regions', fontsize=16, fontweight='bold')
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Carbon Intensity (gCO₂eq/kWh)', fontsize=12)
    
    # Format x-axis to show years
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    plt.gca().xaxis.set_major_locator(mdates.YearLocator())
    plt.xticks(rotation=0)
    
    # Set Y-axis range
    plt.ylim(200, 700)
    
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Comparison graph saved to: {save_path}")
    
    # Show plot
    if show_plot:
        plt.show()
    
    plt.close()

def main():
    """Main function to handle command line arguments and create graphs"""
    parser = argparse.ArgumentParser(description='Create carbon intensity visualization graphs')
    parser.add_argument('csv_file', help='Path to CSV file or directory containing CSV files')
    parser.add_argument('--region', help='Region name for single file mode')
    parser.add_argument('--provider', help='Provider name (aws, azure, gcp)')
    parser.add_argument('--save', help='Path to save the graph')
    parser.add_argument('--compare', action='store_true', help='Compare multiple regions')
    parser.add_argument('--no-show', action='store_true', help='Don\'t display the plot')
    
    args = parser.parse_args()
    
    show_plot = not args.no_show
    
    if os.path.isfile(args.csv_file):
        # Single file mode
        df = read_carbon_data(args.csv_file)
        if df is not None:
            region = args.region or os.path.splitext(os.path.basename(args.csv_file))[0]
            create_line_graph(df, region, args.provider, args.save, show_plot)
    
    elif os.path.isdir(args.csv_file):
        # Directory mode - compare multiple regions
        csv_files = []
        for filename in os.listdir(args.csv_file):
            if filename.endswith('.csv'):
                csv_path = os.path.join(args.csv_file, filename)
                region_name = os.path.splitext(filename)[0]
                csv_files.append((csv_path, region_name))
        
        if csv_files:
            if args.compare or len(csv_files) > 1:
                create_multiple_regions_graph(csv_files, args.save, show_plot)
            else:
                # Single file in directory
                csv_path, region_name = csv_files[0]
                df = read_carbon_data(csv_path)
                if df is not None:
                    create_line_graph(df, region_name, args.provider, args.save, show_plot)
        else:
            print("No CSV files found in the directory")
    else:
        print(f"Path not found: {args.csv_file}")

if __name__ == "__main__":
    # Add numpy import for trend line calculation
    import numpy as np
    main()
