def restart_pod(pod_name: str) -> str:
    """Restart a specified Kubernetes pod."""
    return f"Action executed: restarted pod {pod_name} successfully"

def rollback_model(model_id: str) -> str:
    """Roll back the serving model deployment to a specified stable ID."""
    return f"Action executed: rolled back model to {model_id} successfully"

def rebalance_queue(queue_name: str) -> str:
    """Rebalance the batch workload queue."""
    return f"Action executed: rebalanced queue {queue_name} successfully"
