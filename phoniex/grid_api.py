import os
import requests
from typing import Optional

class GridCarbonAPI:
    def __init__(self, api_key: Optional[str] = None):
        # Fallback to environment variable if not passed directly
        self.api_key = api_key or os.getenv("ELECTRICITY_MAPS_KEY")
        self.base_url = "https://api.electricitymap.org/v3/carbon-intensity/latest"
        
        # Fallback averages (gCO2eq/kWh) if the API fails
        self.historical_averages = {
            "US-CAL-BANC": 220.0, # California (Cloud default)
            "IN-KA": 450.0,       # Karnataka (Local default example)
            "FR": 60.0,           # France (Nuclear-heavy)
            "DE": 400.0,          # Germany (Coal/Wind mix)
        }

    def get_intensity(self, zone_key: str) -> float:
        """Fetches live carbon intensity for a specific grid zone."""
        if not self.api_key:
            print(f"⚠️ No Grid API key found. Using historical average for {zone_key}.")
            return self.historical_averages.get(zone_key, 300.0)

        headers = {"auth-token": self.api_key}
        params = {"zone": zone_key}

        try:
            response = requests.get(self.base_url, headers=headers, params=params, timeout=3.0)
            response.raise_for_status()
            data = response.json()
            
            intensity = data.get("carbonIntensity")
            if intensity is not None:
                return float(intensity)
                
            raise ValueError("Malformed response structure from grid API.")
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Grid API network failure: {e}. Falling back to historical data.")
            return self.historical_averages.get(zone_key, 300.0)