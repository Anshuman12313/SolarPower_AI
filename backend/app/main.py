"""FastAPI application.  Run from the backend folder:  uvicorn app.main:app --reload --port 8000"""
import io
from typing import List

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .service import ModelNotReady, SolarService

app = FastAPI(title="SolarPower AI API", version="1.0.0")
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
service = SolarService()


class Inputs(BaseModel):
    irradiance: float = Field(ge=0, le=1200)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    wind_speed: float = Field(ge=0, le=25)
    cloud_cover: float = Field(ge=0, le=100)
    hour: float = Field(ge=0, le=23)


class PredictRequest(BaseModel):
    model: str
    inputs: Inputs


class WhatIfRequest(BaseModel):
    model: str
    base: Inputs
    variable: str
    points: int = Field(default=40, ge=5, le=200)


class Scenario(BaseModel):
    name: str
    inputs: Inputs


class ScenarioRequest(BaseModel):
    model: str
    scenarios: List[Scenario]


def run(func, *args, **kwargs):
    """Call a service function and convert errors into clean HTTP responses."""
    try:
        return func(*args, **kwargs)
    except ModelNotReady as err:
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))
    except Exception as err:  # unexpected problem: do not leak a stack trace to the browser
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {err}")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/features")
def features():
    return service.feature_info()


@app.get("/api/models")
def models():
    return run(service.model_list)


@app.get("/api/metrics")
def metrics():
    return run(service.metrics)


@app.get("/api/importance")
def importance():
    return run(service.importance)


@app.get("/api/dataset-info")
def dataset_info():
    return run(service.dataset_info)


@app.post("/api/predict")
def predict(req: PredictRequest):
    return run(service.predict, req.model, req.inputs.model_dump())


@app.post("/api/whatif")
def whatif(req: WhatIfRequest):
    return run(service.whatif, req.model, req.base.model_dump(), req.variable, req.points)


@app.post("/api/scenarios")
def scenarios(req: ScenarioRequest):
    items = [{"name": s.name, "inputs": s.inputs.model_dump()} for s in req.scenarios]
    return run(service.scenarios, req.model, items)


@app.post("/api/predict-batch")
async def predict_batch(model: str = Form(...), file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Please upload a .csv file.")
    try:
        df = pd.read_csv(io.BytesIO(await file.read()))
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read the CSV file.")
    result = run(service.predict_batch, model, df)
    return {"rows": result.astype(object).where(result.notna(), None).to_dict("records"),
            "count": int(len(result))}


@app.get("/api/viz/scatter")
def viz_scatter(x: str = "irradiance"):
    return run(service.scatter, x)


@app.get("/api/viz/hourly")
def viz_hourly():
    return run(service.hourly)


@app.get("/api/viz/correlation")
def viz_correlation():
    return run(service.correlation)


@app.get("/api/actual-vs-predicted")
def actual_vs_predicted(model: str):
    return run(service.actual_vs_predicted, model)
