import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ELECTRICITYMAP_API_URL = "https://api.electricitymap.org/v3/carbon-intensity/latest"

class CarbonIntensityError(Exception):
    pass

def get_mock_carbon_intensity(zone):
    """
    Provide mock carbon intensity data when API is not available
    Based on typical regional carbon intensities
    """
    mock_data = {
        # Country codes (most reliable for electricityMap)
        "US": {"carbon_intensity": 400, "fossil_fuel_percentage": 60},      # United States
        "CA": {"carbon_intensity": 120, "fossil_fuel_percentage": 20},      # Canada (hydro heavy)
        "DE": {"carbon_intensity": 450, "fossil_fuel_percentage": 50},      # Germany
        "IE": {"carbon_intensity": 350, "fossil_fuel_percentage": 45},      # Ireland
        "GB": {"carbon_intensity": 250, "fossil_fuel_percentage": 40},      # Great Britain
        "FR": {"carbon_intensity": 60, "fossil_fuel_percentage": 10},       # France (nuclear heavy)
        "NL": {"carbon_intensity": 380, "fossil_fuel_percentage": 52},      # Netherlands
        "BE": {"carbon_intensity": 200, "fossil_fuel_percentage": 35},      # Belgium
        "SG": {"carbon_intensity": 420, "fossil_fuel_percentage": 95},      # Singapore
        "HK": {"carbon_intensity": 480, "fossil_fuel_percentage": 90},      # Hong Kong
        "JP": {"carbon_intensity": 350, "fossil_fuel_percentage": 75},      # Japan
        "KR": {"carbon_intensity": 450, "fossil_fuel_percentage": 70},      # South Korea
        "IN": {"carbon_intensity": 650, "fossil_fuel_percentage": 80},      # India
        "AU": {"carbon_intensity": 500, "fossil_fuel_percentage": 75},      # Australia
        "TW": {"carbon_intensity": 550, "fossil_fuel_percentage": 85},      # Taiwan
        "ZA": {"carbon_intensity": 750, "fossil_fuel_percentage": 85},      # South Africa
    }
    
    data = mock_data.get(zone, {"carbon_intensity": 400, "fossil_fuel_percentage": 60})
    return {
        "carbon_intensity": data["carbon_intensity"],
        "renewable_percentage": data["fossil_fuel_percentage"],
        "zone": zone,
        "data_source": "mock"
    }

def get_carbon_intensity(zone):
    """
    Fetch carbon intensity and renewable percentage for a given electricityMap zone.
    Falls back to mock data if API is not available.
    Returns a dict: { 'carbon_intensity': int (gCO2eq/kWh), 'renewable_percentage': float, 'zone': str }
    """
    api_key = os.getenv("ELECTRICITYMAP_API_KEY")
    if not api_key:
        print("Warning: ELECTRICITYMAP_API_KEY not set, using mock data")
        return get_mock_carbon_intensity(zone)
    
    # Try different header formats for electricityMap API
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"zone": zone}
    
    try:
        resp = requests.get(ELECTRICITYMAP_API_URL, headers=headers, params=params, timeout=30)
        
        # If Bearer token fails, try auth-token format
        if resp.status_code == 401:
            headers = {"auth-token": api_key}
            resp = requests.get(ELECTRICITYMAP_API_URL, headers=headers, params=params, timeout=30)
        
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "carbon_intensity": data.get("carbonIntensity"),
            "renewable_percentage": data.get("fossilFuelPercentage"),
            "zone": zone,
            "data_source": "electricityMap"
        }
    except Exception as e:
        print(f"Warning: electricityMap API failed for zone {zone}: {e}")
        print("Using mock carbon intensity data")
        return get_mock_carbon_intensity(zone)
