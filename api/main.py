"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from api.routes import cars, health

app = FastAPI(
    title="CarBot API",
    description="API for car scraping and enrichment platform",
    version="0.1.0",
    debug=settings.debug,
)

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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CarBot API",
        "version": "0.1.0",
        "docs": "/docs",
    }

