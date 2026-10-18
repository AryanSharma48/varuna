import os
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from apps.api.config import settings
from apps.api.routes import incidents, reports
from db.database import engine, Base, get_db
from db.seed import seed_demo_data



app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="VARUNA — Automated Sentinel-1 Oil Spill Detection, Backtracking & AIS Vessel Attribution Platform API"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Safely initialize tables and demo seed
    try:
        Base.metadata.create_all(bind=engine)
        seed_demo_data()
    except Exception as e:
        print(f"Startup database initialization notice: {e}")

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "VARUNA API",
        "version": "1.0.0",
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

# Include Incidents & Reports Routers
app.include_router(incidents.router, prefix="/api/v1", tags=["Investigation"])
app.include_router(incidents.router, prefix="", tags=["Investigation-Root"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
app.include_router(reports.router, prefix="", tags=["Reports-Root"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
