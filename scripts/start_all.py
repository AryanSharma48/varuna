import sys
import os
import subprocess
import uvicorn

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.seed import seed_demo_data

def main():
    print("=" * 65)
    print("VARUNA -- STARTING MARITIME INVESTIGATION PLATFORM BACKEND")
    print("=" * 65)
    
    # 1. Seed database
    print("\n[1/2] Ensuring database tables and demo incident are seeded...")
    seed_demo_data()
    
    # 2. Start Uvicorn Server
    print("\n[2/2] Starting FastAPI API server at http://127.0.0.1:8000 ...")
    print("Swagger Documentation available at: http://127.0.0.1:8000/docs")
    print("Health Status available at: http://127.0.0.1:8000/health")
    print("=" * 65 + "\n")
    
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
