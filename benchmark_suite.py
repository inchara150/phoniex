import math

class AdvancedPhoenixScheduler:
    def __init__(self):
        # 1. Normalization Constants (The theoretical maximums)
        self.MAX_LATENCY_S = 60.0
        self.MAX_ENERGY_KWH = 0.010
        self.MAX_CARBON_G = 5.0
        self.MAX_COST_USD = 0.05
        
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
            "formatting":  {"local_edge": 0.99, "cloud_heavy": 0.99}
        }

    def _calculate_score(self, route: str, severity: str, bug_type: str, grid_intensity: float) -> dict:
        """Calculates the normalized dot product penalty score (Lower is better)."""
        weights = self.WEIGHTS[severity]
        profile = self.PROFILES[route]
        
        # Calculate raw variables
        energy_kwh = profile["power_kw"] * (profile["latency"] / 3600.0)
        carbon_g = energy_kwh * grid_intensity
        accuracy = self.ACCURACY[bug_type][route]

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

    def evaluate_task(self, severity: str, bug_type: str, local_grid: float, cloud_grid: float) -> str:
        local_score, local_carbon = self._calculate_score("local_edge", severity, bug_type, local_grid)
        cloud_score, cloud_carbon = self._calculate_score("cloud_heavy", severity, bug_type, cloud_grid)
        
        # Debug trace
        print(f"    ↳ Local Score: {local_score:.4f} ({local_carbon:.4f}g CO2)")
        print(f"    ↳ Cloud Score: {cloud_score:.4f} ({cloud_carbon:.4f}g CO2)")

        # Temporal Shifting Logic (Delay Queue)
        # If severity is low, and the absolute carbon penalty of the best route is still terrible (> 0.25 threshold)
        weights = self.WEIGHTS[severity]
        if severity == "low":
            best_carbon_g = min(local_carbon, cloud_carbon)
            normalized_carbon_penalty = min(best_carbon_g / self.MAX_CARBON_G, 1.0)
            if normalized_carbon_penalty * weights[2] > 0.15: 
                return "delay"

        return "local_edge" if local_score <= cloud_score else "cloud_heavy"


# ==========================================
# BENCHMARK SUITE RUNNER
# ==========================================
if __name__ == "__main__":
    scheduler = AdvancedPhoenixScheduler()

    benchmarks = [
        {
            "id": "TEST-01",
            "desc": "SQLAlchemy Concurrency Deadlock",
            "severity": "critical", "bug_type": "db_deadlock",
            "local_grid": 480, "cloud_grid": 450,
            "expected": "cloud_heavy"
        },
        {
            "id": "TEST-02",
            "desc": "Flask Route SyntaxError",
            "severity": "high", "bug_type": "syntax",
            "local_grid": 120, "cloud_grid": 450,
            "expected": "local_edge"
        },
        {
            "id": "TEST-03",
            "desc": "Matrix Operation IndexError",
            "severity": "medium", "bug_type": "algorithm",
            "local_grid": 450, "cloud_grid": 110,
            "expected": "cloud_heavy"
        },
        {
            "id": "TEST-04",
            "desc": "PEP8 Docstring Compliance",
            "severity": "low", "bug_type": "formatting",
            "local_grid": 480, "cloud_grid": 450,
            "expected": "delay"
        }
    ]

    print("📊 PHOENIX SCHEDULER BENCHMARK MATRIX 📊\n")
    
    passed = 0
    for test in benchmarks:
        print(f"[{test['id']}] {test['desc']}")
        print(f"  Severity: {test['severity'].upper()} | Local Grid: {test['local_grid']}g | Cloud Grid: {test['cloud_grid']}g")
        
        result = scheduler.evaluate_task(
            test["severity"], test["bug_type"], test["local_grid"], test["cloud_grid"]
        )
        
        status = "✅ PASS" if result == test["expected"] else "❌ FAIL"
        print(f"  Outcome: {result} (Expected: {test['expected']}) -> {status}\n")
        
        if result == test["expected"]:
            passed += 1
            
    print("=" * 45)
    print(f"BENCHMARK RESULTS: {passed}/{len(benchmarks)} PASSED")
    print("=" * 45)