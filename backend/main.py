from fastapi import FastAPI
from backend.api import routes_incidents, routes_agents, routes_metrics

app = FastAPI(title="Aegis API")
app.include_router(routes_incidents.router, prefix="/incidents")
app.include_router(routes_agents.router, prefix="/agents")
app.include_router(routes_metrics.router, prefix="/metrics")

@app.get("/health")
def health():
    return {"status": "ok"}
