from agents.memory.schemas import RiskTier

REVERSIBLE_LOW_RISK = {"restart_pod", "rebalance_queue"}
NEEDS_APPROVAL = {"rollback_model", "scale_down_cluster", "delete_resource"}

def classify_risk(action_command: str) -> RiskTier:
    action_type = action_command.split("(")[0]
    if action_type in REVERSIBLE_LOW_RISK:
        return RiskTier.LOW
    if action_type in NEEDS_APPROVAL:
        return RiskTier.HIGH
    return RiskTier.MEDIUM
