"""Medic tools — execute remediation actions against the simulator."""

import json
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("aegis.medic.tools")

SIMULATOR_URL = "http://localhost:8100"

# Audit log of all actions taken
ACTION_LOG: list[dict] = []


def _log_action(action_type: str, target: str, result: dict) -> None:
    """Record every remediation action for audit trail."""
    entry = {
        "action": action_type,
        "target": target,
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ACTION_LOG.append(entry)
    logger.info("ACTION: %s on %s → %s", action_type, target, result.get("status", "unknown"))


def restart_pod(pod_name: str) -> str:
    """Restart a specified Kubernetes pod by resetting the simulator service.

    This simulates a pod restart by calling the simulator's reset endpoint,
    which restores all metrics to baseline values.
    """
    try:
        resp = httpx.post(f"{SIMULATOR_URL}/_inject/reset", timeout=10.0)
        resp.raise_for_status()
        result = resp.json()
        result["action"] = "restart_pod"
        result["target"] = pod_name
        _log_action("restart_pod", pod_name, result)
        return json.dumps({
            "status": "success",
            "action": "restart_pod",
            "target": pod_name,
            "message": f"Pod {pod_name} restarted successfully. Metrics reset to baseline.",
            "simulator_response": result,
        }, indent=2)
    except httpx.HTTPError as exc:
        error_result = {"status": "failed", "error": str(exc)}
        _log_action("restart_pod", pod_name, error_result)
        return json.dumps({
            "status": "failed",
            "action": "restart_pod",
            "target": pod_name,
            "error": f"Failed to restart pod: {exc}",
        }, indent=2)


def rollback_model(model_id: str) -> str:
    """Roll back the serving model deployment to a specified stable version.

    Resets the simulator state (simulating a model rollback) and records
    the rollback in the deploy history.
    """
    try:
        resp = httpx.post(f"{SIMULATOR_URL}/_inject/reset", timeout=10.0)
        resp.raise_for_status()
        result = resp.json()
        result["action"] = "rollback_model"
        result["target"] = model_id
        _log_action("rollback_model", model_id, result)
        return json.dumps({
            "status": "success",
            "action": "rollback_model",
            "target": model_id,
            "message": f"Model rolled back to {model_id}. All metrics restored to baseline.",
            "simulator_response": result,
        }, indent=2)
    except httpx.HTTPError as exc:
        error_result = {"status": "failed", "error": str(exc)}
        _log_action("rollback_model", model_id, error_result)
        return json.dumps({
            "status": "failed",
            "action": "rollback_model",
            "target": model_id,
            "error": f"Failed to rollback model: {exc}",
        }, indent=2)


def rebalance_queue(queue_name: str) -> str:
    """Rebalance the batch workload queue.

    Resets the simulator state (simulating workload redistribution) to
    restore normal throughput and latency.
    """
    try:
        resp = httpx.post(f"{SIMULATOR_URL}/_inject/reset", timeout=10.0)
        resp.raise_for_status()
        result = resp.json()
        result["action"] = "rebalance_queue"
        result["target"] = queue_name
        _log_action("rebalance_queue", queue_name, result)
        return json.dumps({
            "status": "success",
            "action": "rebalance_queue",
            "target": queue_name,
            "message": f"Queue {queue_name} rebalanced successfully.",
            "simulator_response": result,
        }, indent=2)
    except httpx.HTTPError as exc:
        error_result = {"status": "failed", "error": str(exc)}
        _log_action("rebalance_queue", queue_name, error_result)
        return json.dumps({
            "status": "failed",
            "action": "rebalance_queue",
            "target": queue_name,
            "error": f"Failed to rebalance queue: {exc}",
        }, indent=2)


def get_action_log() -> list[dict]:
    """Return the full audit log of remediation actions (not an LLM tool)."""
    return list(ACTION_LOG)


def execute_remediation(command_str: str) -> str:
    """Parse and execute a remediation command string."""
    try:
        # e.g. restart_pod(mock_inference)
        if "(" not in command_str or not command_str.endswith(")"):
            return f"Error: Invalid command format: {command_str}"

        name, args_str = command_str.split("(", 1)
        args_str = args_str.rsplit(")", 1)[0].strip()

        # Clean arguments
        args = [arg.strip().strip("'\"") for arg in args_str.split(",") if arg.strip()]

        if name == "restart_pod":
            pod_name = args[0] if args else "unknown"
            return restart_pod(pod_name)
        elif name == "rollback_model":
            model_id = args[0] if args else "unknown"
            return rollback_model(model_id)
        elif name == "rebalance_queue":
            queue_name = args[0] if args else "unknown"
            return rebalance_queue(queue_name)
        elif name == "manual_intervention":
            return "Manual intervention requested."
        else:
            return f"Error: Unknown command: {name}"
    except Exception as e:
        return f"Error executing command {command_str}: {e}"

