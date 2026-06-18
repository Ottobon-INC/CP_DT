import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.settings import settings

from app.database.session import Base, engine
from app.models import TwinInactivityState
from app.schedulers.digital_twin_scheduler import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print(f"Starting {settings.APP_NAME} in environment: {settings.APP_ENV}")
    
    # Database is managed remotely via Supabase REST API; direct table auto-creation is disabled.
    print("Remote database connection configured via Supabase REST client.")
            
    # Start the periodic background scheduler
    start_scheduler()
    
    yield
    
    # Shutdown logic
    shutdown_scheduler()
    print(f"Shutting down {settings.APP_NAME}...")



app = FastAPI(
    title=settings.APP_NAME,
    description="Digital Twin Backend Orchestrator built with FastAPI & LangGraph",
    version="0.1.0",
    lifespan=lifespan
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(api_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development"
    )

