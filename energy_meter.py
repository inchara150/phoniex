import psutil
import time
from contextlib import contextmanager

# Thermal Design Power (TDP) for a standard laptop/desktop CPU in Watts.
# We use this as a baseline to convert CPU utilization percentage into Watts.
CPU_TDP_WATTS = 65.0 

@contextmanager
def measure_energy():
    """
    Context manager that measures CPU usage and time to estimate energy in Joules.
    Yields a dictionary that gets populated with 'energy_j' and 'duration_s' upon exit.
    """
    # Initialize CPU percent tracking (call it once to start the measurement period)
    psutil.cpu_percent(interval=None)
    start_time = time.time()
    
    metrics = {"energy_j": 0.0, "duration_s": 0.0, "cpu_percent": 0.0}
    
    try:
        yield metrics
    finally:
        duration = time.time() - start_time
        # Get average CPU usage over the duration
        cpu_usage_pct = psutil.cpu_percent(interval=None)
        
        # If it's a very fast operation, cpu_usage_pct might be 0, so we default to a small baseline
        if cpu_usage_pct <= 0:
            cpu_usage_pct = 5.0
            
        # Energy (Joules) = Power (Watts) * Time (Seconds)
        # We scale the TDP by the CPU utilization percentage.
        power_watts = (cpu_usage_pct / 100.0) * CPU_TDP_WATTS
        
        metrics["duration_s"] = duration
        metrics["cpu_percent"] = cpu_usage_pct
        metrics["energy_j"] = power_watts * duration
