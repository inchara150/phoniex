import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

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

    def get_forecast(self, zone_key: str, hours: int = 6) -> list:
        """Fetches forecasted carbon intensity for the next N hours."""
        import datetime
        fallback_forecast = [
            {
                "datetime": (datetime.datetime.utcnow() + datetime.timedelta(hours=i)).isoformat() + "Z",
                "carbonIntensity": self.historical_averages.get(zone_key, 300.0) * (0.7 if i == hours-1 else 1.0)
            }
            for i in range(hours)
        ]
        
        if not self.api_key:
            print(f"[⚠️] No Grid API key found. Using simulated forecast for {zone_key}.")
            return fallback_forecast

        url = "https://api.electricitymap.org/v3/carbon-intensity/forecast"
        headers = {"auth-token": self.api_key}
        params = {"zone": zone_key}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=3.0)
            response.raise_for_status()
            data = response.json()
            
            forecasts = data.get("forecast", [])
            if not forecasts:
                return fallback_forecast
                
            # Filter to just the next `hours` limit
            return forecasts[:hours]
            
        except Exception as e:
            print(f"[⚠️] Forecast API failure: {e}. Falling back to simulation.")
            return fallback_forecast