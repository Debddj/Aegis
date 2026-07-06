"""Tests for Medic risk policy classification."""

import pytest
from agents.medic.risk_policy import classify_risk
from agents.memory.schemas import RiskTier


class TestClassifyRisk:
    """Verify that commands are classified into the correct risk tiers."""

    def test_restart_pod_is_low_risk(self):
        assert classify_risk("restart_pod(inference-svc-3)") == RiskTier.LOW

    def test_rebalance_queue_is_low_risk(self):
        assert classify_risk("rebalance_queue(batch-queue)") == RiskTier.LOW

    def test_rollback_model_is_high_risk(self):
        assert classify_risk("rollback_model(model-v1)") == RiskTier.HIGH

    def test_scale_down_cluster_is_high_risk(self):
        assert classify_risk("scale_down_cluster(gpu-pool-1)") == RiskTier.HIGH

    def test_delete_resource_is_high_risk(self):
        assert classify_risk("delete_resource(old-checkpoint)") == RiskTier.HIGH

    def test_unknown_command_is_medium_risk(self):
        assert classify_risk("some_unknown_action(target)") == RiskTier.MEDIUM

    def test_manual_intervention_is_medium_risk(self):
        assert classify_risk("manual_intervention()") == RiskTier.MEDIUM

    def test_empty_command_is_medium_risk(self):
        """Commands that don't match any known pattern default to MEDIUM."""
        assert classify_risk("") == RiskTier.MEDIUM

    def test_command_with_complex_args(self):
        """Ensure parsing works with multi-argument commands."""
        assert classify_risk("restart_pod(ns=prod, pod=inference-svc-3-xyz)") == RiskTier.LOW
