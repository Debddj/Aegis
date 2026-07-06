def fetch_recent_metrics(service_name: str) -> str:
    """Fetch recent latency, throughput, and error metrics for a service."""
    return f"Mock metrics for {service_name}: latency=350ms, cpu=85%, error_rate=0.01"

def compute_baseline_deviation(metric_name: str, current_value: float) -> str:
    """Compute the deviation of a metric from its historical baseline."""
    return f"Metric {metric_name} with value {current_value} deviates by +300% from baseline"
