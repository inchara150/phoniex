# Add this import to the top of shedule.py
from grid_api import GridCarbonAPI

class PhoenixScheduler:
    def __init__(self, local_zone: str = "IN-KA", cloud_zone: str = "US-CAL-BANC"):
        # Existing initialization code...
        self.MAX_LATENCY_S = 60.0
        self.MAX_ENERGY_KWH = 0.010
        self.MAX_CARBON_G = 5.0
        self.MAX_COST_USD = 0.05
        
        # Store geographical zones for the API
        self.local_zone = local_zone
        self.cloud_zone = cloud_zone
        self.grid_api = GridCarbonAPI()
        
        # [Keep your existing WEIGHTS, PROFILES, and ACCURACY dictionaries here]

    # [Keep your existing _calculate_score method here]

    def evaluate_task(
        self,
        severity: str = "high",
        bug_type: str = "algorithm",
        complexity: str = "medium",
    ) -> dict:
        """Evaluates incident conditions using live grid telemetry."""
        
        # Fetch LIVE grid conditions
        print(f"\n[🌍 TELEMETRY] Fetching live grid carbon intensity...")
        local_grid = self.grid_api.get_intensity(self.local_zone)
        cloud_grid = self.grid_api.get_intensity(self.cloud_zone)
        
        print(f"  ↳ Local Grid ({self.local_zone}): {local_grid} gCO2/kWh")
        print(f"  ↳ Cloud Grid ({self.cloud_zone}): {cloud_grid} gCO2/kWh")

        local_score, local_carbon = self._calculate_score(
            "local_edge", severity, bug_type, local_grid
        )
        cloud_score, cloud_carbon = self._calculate_score(
            "cloud_heavy", severity, bug_type, cloud_grid
        )

        # Off-peak delay shifting criteria
        if severity == "low":
            best_carbon = min(local_carbon, cloud_carbon)
            norm_carbon = min(best_carbon / self.MAX_CARBON_G, 1.0)
            if norm_carbon * self.WEIGHTS["low"][2] > 0.15:
                return {
                    "route": "delay",
                    "metrics": {
                        "local_score": local_score,
                        "cloud_score": cloud_score,
                        "local_emissions_gCO2": local_carbon,
                        "cloud_emissions_gCO2": cloud_carbon,
                        "local_grid": local_grid,
                        "cloud_grid": cloud_grid
                    },
                }

        selected_route = "local_edge" if local_score <= cloud_score else "cloud_heavy"
        return {
            "route": selected_route,
            "metrics": {
                "local_score": local_score,
                "cloud_score": cloud_score,
                "local_emissions_gCO2": local_carbon,
                "cloud_emissions_gCO2": cloud_carbon,
                "local_grid": local_grid,
                "cloud_grid": cloud_grid
            },
        }