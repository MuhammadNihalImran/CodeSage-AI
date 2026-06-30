import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from agent.orchestrator import OrchestratorAgent
from db.supabase_client import create_session

# Define project-specific directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
log_file_path = os.path.join(LOGS_DIR, "agent_activity.log")
IS_VERCEL = "VERCEL" in os.environ

# Setup built-in python logging for agent activities
activity_logger = logging.getLogger("agent_activity")
activity_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')

if IS_VERCEL:
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    activity_logger.addHandler(sh)
else:
    os.makedirs(LOGS_DIR, exist_ok=True)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    activity_logger.addHandler(file_handler)


app = FastAPI(title="AI Code Mentor Agent")

# Configure CORS origins, allowing local dev and production frontend from environment
allowed_origins = [
    "http://localhost:5173",
]
prod_frontend = os.environ.get("PRODUCTION_FRONTEND_URL")
if prod_frontend:
    allowed_origins.append(prod_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


agent = OrchestratorAgent()


class CodeAnalysisRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user requesting analysis")
    session_id: str | None = Field(None, description="The session ID. A new one will be created if omitted.")
    code: str = Field(..., description="The code snippet to analyze")
    language: str = Field("python", description="The programming language of the code")

@app.get("/health")
def health_check():
    """Health check endpoint to verify the server status.
    
    Returns:
        dict: A dictionary indicating status is ok.
    """
    return {"status": "ok"}

@app.get("/mode")
def get_mode():
    """Returns whether the application is running in mock mode or live mode."""
    use_mock = os.environ.get("USE_MOCK_RESPONSES", "").lower() == "true"
    return {"use_mock": use_mock}


@app.post("/analyze")
async def analyze_code(request: CodeAnalysisRequest):
    """Analyze a code snippet using multiple concurrent sub-agents and store state in Supabase.
    
    Returns:
        dict: The combined analyzed results and synthesis.
    """
    code_length = len(request.code)
    try:
        session_id = request.session_id
        if not session_id:
            session_id = create_session(request.user_id)
            
        result = await agent.run_full_pipeline(
            user_id=request.user_id,
            session_id=session_id,
            code=request.code,
            language=request.language
        )
        # Add session_id to return payload so client can reuse it
        result["session_id"] = session_id
        return result
    except Exception as e:
        activity_logger.info(f"Orchestrator -> Pipeline Failure. Code length: {code_length}. Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
