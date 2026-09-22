from grid_api import GridCarbonAPI

class PhoenixScheduler:
    def __init__(self, local_zone: str = "IN-KA", cloud_zone: str = "US-CAL-BANC"):
        # 1. Normalization Constants (The theoretical maximums)
        self.MAX_LATENCY_S = 60.0
        self.MAX_ENERGY_KWH = 0.010
        self.MAX_CARBON_G = 5.0
        self.MAX_COST_USD = 0.05
        
        # Store geographical zones for the API
        self.local_zone = local_zone
        self.cloud_zone = cloud_zone
        self.grid_api = GridCarbonAPI()
        
        # 2. Dynamic Weight Matrix [w_L, w_E, w_M, w_C, w_A]
        self.WEIGHTS = {
            "critical": [0.60, 0.05, 0.05, 0.00, 0.30],
            "high":     [0.30, 0.10, 0.10, 0.10, 0.40],
            "medium":   [0.20, 0.20, 0.20, 0.20, 0.20],
            "low":      [0.05, 0.20, 0.40, 0.25, 0.10]
        }

        # 3. Hardware / Model Telemetry Profiles
        self.PROFILES = {
            "local_edge":  {"latency": 15.0, "power_kw": 0.350, "cost": 0.00},
            "cloud_heavy": {"latency": 4.0,  "power_kw": 0.150, "cost": 0.02}
        }

        # 4. Historical Accuracy Database (A_m) for Bug Classes
        self.ACCURACY = {
            "db_deadlock": {"local_edge": 0.25, "cloud_heavy": 0.95},
            "syntax":      {"local_edge": 0.99, "cloud_heavy": 0.99},
            "algorithm":   {"local_edge": 0.85, "cloud_heavy": 0.95},
            "formatting":  {"local_edge": 0.99, "cloud_heavy": 0.99},
            "KeyError":    {"local_edge": 0.90, "cloud_heavy": 0.99} # Added for KeyError tests
        }

        # 5. Dynamic Model Routing Matrix
        self.MODEL_MATRIX = {
            "syntax":      {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
            "db_deadlock": {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "claude-3-5-sonnet-20240620"},
            "algorithm":   {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
            "formatting":  {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"},
            "KeyError":    {"local_edge": "qwen2.5-coder:7b", "cloud_heavy": "gemini-3.6-flash"}
        }

    def _calculate_score(self, route: str, severity: str, bug_type: str, grid_intensity: float) -> tuple:
        """Calculates the normalized dot product penalty score (Lower is better)."""
        weights = self.WEIGHTS.get(severity, self.WEIGHTS["medium"])
        profile = self.PROFILES[route]
        
        # Calculate raw variables
        energy_kwh = profile["power_kw"] * (profile["latency"] / 3600.0)
        carbon_g = energy_kwh * grid_intensity
        accuracy_map = self.ACCURACY.get(bug_type, self.ACCURACY["algorithm"])
        base_accuracy = accuracy_map.get(route, 0.5)
        
        # --- ADAPTIVE WEIGHT LEARNING ---
        from weights_db import get_learned_accuracy
        learned_accuracy = get_learned_accuracy(bug_type, route)
        if learned_accuracy is not None:
            # Blend the static assumption with the real world historical data (70% weight to real data)
            accuracy = (base_accuracy * 0.3) + (learned_accuracy * 0.7)
            print(f"  [🧠 LEARNING] Adjusted accuracy for {bug_type}/{route}: {base_accuracy:.2f} -> {accuracy:.2f}")
        else:
            accuracy = base_accuracy

        # Normalize to [0, 1] space (X_m vector)
        penalties = [
            min(profile["latency"] / self.MAX_LATENCY_S, 1.0),   # L_m
            min(energy_kwh / self.MAX_ENERGY_KWH, 1.0),          # E_m
            min(carbon_g / self.MAX_CARBON_G, 1.0),              # M_m
            min(profile["cost"] / self.MAX_COST_USD, 1.0),       # C_m
            1.0 - accuracy                                       # A_m (Inaccuracy Penalty)
        ]

        # Calculate Dot Product
        final_score = sum(w * p for w, p in zip(weights, penalties))
        return round(final_score, 4), carbon_g

    def evaluate_task(
        self,
        severity: str = "high",
        bug_type: str = "algorithm",
        complexity: str = "medium",
        local_grid: float = None,
        cloud_grid: float = None
    ) -> dict:
        """Evaluates incident conditions using live grid telemetry or overrides."""
        
        # Check offline resilience status: block cloud APIs (Gemini) when internet is disconnected
        try:
            from connectivity_manager import connectivity_manager
            is_offline = not connectivity_manager.is_online()
        except Exception:
            is_offline = False

        if is_offline:
            print("\n[OFFLINE RESILIENCE] Internet disconnected. Cloud APIs (Gemini) are strictly DISABLED.")
            print("  [OFFLINE MODE] Forcing 100% Local Edge routing with qwen2.5-coder:7b.")
            return {
                "route": "local_edge",
                "selected_model": "qwen2.5-coder:7b",
                "metrics": {
                    "local_score": 0.05,
                    "cloud_score": 999.0,
                    "local_emissions_gCO2": 0.90,
                    "cloud_emissions_gCO2": 0.0,
                    "local_grid": local_grid or 350.0,
                    "cloud_grid": 0.0,
                    "offline_mode": True
                },
            }

        if local_grid is None:
            print(f"\n[🌱 TELEMETRY] Fetching live grid carbon intensity...")
            local_grid = self.grid_api.get_intensity(self.local_zone)
        if cloud_grid is None:
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
                    "selected_model": "none",
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
        
        # Get dynamic model mapping based on bug_type
        model_map = self.MODEL_MATRIX.get(bug_type, self.MODEL_MATRIX["algorithm"])
        selected_model = model_map.get(selected_route, "qwen2.5-coder:7b")
        
        print(f"  🎯 Route selected: {selected_route} | Model: {selected_model}")
        
        return {
            "route": selected_route,
            "selected_model": selected_model,
            "metrics": {
                "local_score": local_score,
                "cloud_score": cloud_score,
                "local_emissions_gCO2": local_carbon,
                "cloud_emissions_gCO2": cloud_carbon,
                "local_grid": local_grid,
                "cloud_grid": cloud_grid
            },
        }