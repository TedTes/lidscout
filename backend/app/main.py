"""
Main FastAPI application.
Entry point for the backend service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.businesses import router as businesses_router

# Create FastAPI app
app = FastAPI(
    title="Business Scraper API",
    description="API for scraping and searching business information",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(businesses_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Business Scraper API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)