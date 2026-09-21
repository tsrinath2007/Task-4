from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json, glob, os

app = FastAPI(title="Sentinel Fraud Investigation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/cases")
def get_cases():
    files = sorted(glob.glob("cases/generated/HHG-*.json"))
    cases = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            cases.append(json.load(fp))
    return cases

@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    path = f"cases/generated/{case_id}.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    return {"error": "not found"}

@app.get("/api/summary")
def get_summary():
    path = "cases/generated/benchmark_summary.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    return {}

# Run with: uvicorn ui.backend:app --port 8000
