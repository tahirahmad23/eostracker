"""
FastAPI Web Application - Main Entry Point
Integrates all modules into a complete web application
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
import os

# Import route modules
from web.routes import public, auth, dashboard, api, subscription
from alerts.scheduler import start_scheduler, stop_scheduler
# Create FastAPI app
app = FastAPI(
    title="EOS Tracker Platform",
    description="End-of-Support tracking for network infrastructure",
    version="1.0.0"
)

# Add session middleware for flash messages
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Include route modules
app.include_router(public.router, tags=["Public"])
app.include_router(auth.router, tags=["Authentication"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(api.router, prefix="/api", tags=["API"])
app.include_router(subscription.router, tags=["Subscription"])

@app.on_event("startup")
async def startup():
    start_scheduler()
   
@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
