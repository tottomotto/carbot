"""FastAPI application entry point."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from config.settings import settings
from api.routes import cars, health, ml

app = FastAPI(
    title="CarBot API",
    description="API for car scraping and enrichment platform",
    version="0.1.0",
    debug=settings.debug,
)

# Setup templates
templates = Jinja2Templates(directory="api/templates")

# Setup static files for images
app.mount("/images", StaticFiles(directory="scraped_images/images"), name="images")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(cars.router, prefix="/api/v1/cars", tags=["cars"])
app.include_router(ml.router, prefix="/api/v1/ml", tags=["ml"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - serves the web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/ml", response_class=HTMLResponse)
async def ml_dashboard(request: Request):
    """ML Dashboard endpoint - serves the ML analytics interface."""
    return templates.TemplateResponse("ml_dashboard.html", {"request": request})


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "message": "CarBot API",
        "version": "0.1.0",
        "docs": "/docs",
        "web_interface": "/",
    }

