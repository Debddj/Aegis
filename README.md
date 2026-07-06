# Aegis

Aegis is a multi-agent system that sits on top of an ML production stack (model-serving + GPU infra + data pipelines) and closes the loop between detecting a problem and resolving it — autonomously where it's safe to, and with a crisp human-approval handoff where it isn't.

## Agent Architecture

1. **Sentry (Monitoring Agent)**: Continuously ingests metrics and flags anomalies using statistical baselining.
2. **Sleuth (Diagnostic Agent)**: Correlates signals across services and time windows to produce root-cause hypotheses with confidence scores.
3. **Medic (Remediation Agent)**: Proposes fixes, classifies them by risk tier, and either executes them directly or requests human approval.
4. **Scribe (Reporting Agent)**: Automatically writes detailed incident postmortems.

## Project Structure

See the directories for:
- `agents/`: Core agent logic (ADK-based)
- `backend/`: FastAPI + gRPC service layer
- `simulator/`: Failure-injection harness & mock services
- `frontend/`: React/TS dashboard
- `infra/`: Docker compose and container configurations
