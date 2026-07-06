from fastapi import FastAPI
from fastapi.responses import JSONResponse
import random, time

app = FastAPI()
STATE = {"latency_multiplier": 1.0, "error_rate": 0.0}

@app.post("/predict")
async def predict(payload: dict):
    time.sleep(0.05 * STATE["latency_multiplier"])
    if random.random() < STATE["error_rate"]:
        return JSONResponse(status_code=500, content={"error": "internal_error"})
    return {"prediction": random.random()}

@app.post("/_inject/{scenario}")
async def inject(scenario: str):
    if scenario == "latency_spike":
        STATE["latency_multiplier"] = 15.0
    elif scenario == "reset":
        STATE["latency_multiplier"] = 1.0
        STATE["error_rate"] = 0.0
    return {"status": "injected", "scenario": scenario}
