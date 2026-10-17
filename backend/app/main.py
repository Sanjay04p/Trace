from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import nebius_client, PRIMARY_MODEL
from app.api.routes import router as swarm_router
app = FastAPI(
    title="AlgoMentor Swarm API",
    description="Backend for the Nebius x NVIDIA Hackathon project",
    version="1.0.0"
)

# Configure CORS to allow your React frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(swarm_router)

@app.get("/health")
async def health_check():
    """Verify backend is running and Nebius connection is active."""
    try:
        # Quick ping to the Nebius models endpoint to verify authentication
        models = await nebius_client.models.list()
        return {
            "status": "healthy", 
            "nebius_connected": True,
            "primary_model_configured": PRIMARY_MODEL
        }
    except Exception as e:
         return {"status": "degraded", "error": str(e)}

# Run this file locally using: uvicorn app.main:app --reload