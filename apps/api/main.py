import os
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from apps.api.config import settings
from apps.api.routes import incidents
from db.database import engine, Base, get_db
from db.seed import seed_demo_data

# Create DB Tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="SIH 26143 — AI-Powered Oil Spill Investigation & Attribution Platform API"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Automatically seed the demo incident if clean checkout
    try:
        seed_demo_data()
    except Exception as e:
        print(f"Startup seed notice: {e}")

# Health Check Endpoints (PRD Section 10 / Phase 0)
@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "SIH-26143 API",
        "version": "1.0.0",
        "timestamp": os.getenv("CURRENT_TIME", "2026-09-04T16:00:00Z")
    }

@app.get("/health/db", status_code=status.HTTP_200_OK, tags=["Health"])
def health_db_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "HEALTHY", "database": "CONNECTED"}
    except Exception as e:
        return {"status": "UNHEALTHY", "database": str(e)}

@app.get("/health/redis", status_code=status.HTTP_200_OK, tags=["Health"])
def health_redis_check():
    return {"status": "HEALTHY", "redis": "MOCK_LOCAL_STANDBY"}

# Include Incidents Router
app.include_router(incidents.router, prefix="/api/v1", tags=["Investigation"])
app.include_router(incidents.router, prefix="", tags=["Investigation-Root"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
