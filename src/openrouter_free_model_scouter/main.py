from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api.endpoints import router as api_router
import os

app = FastAPI(title="OpenRouter Free Model Scouter")

app.include_router(api_router, prefix="/api")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
