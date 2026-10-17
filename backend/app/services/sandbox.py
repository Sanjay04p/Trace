import httpx
import logging
from typing import List, Dict, Any
from app.core.config import NEBIUS_API_KEY, NEBIUS_BASE_URL

logger = logging.getLogger(__name__)

# Assuming Nebius provides a sandbox endpoint within their v1 API structure.
# Adjust the specific endpoint path based on the official Nebius Sandbox documentation.
SANDBOX_ENDPOINT = f"{NEBIUS_BASE_URL.rstrip('/')}/sandbox/execute"

async def execute_in_sandbox(user_code: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executes the user's code against a set of test cases in the Nebius secure sandbox.
    
    Args:
        user_code: The Python code submitted by the learner.
        test_cases: A list of dictionaries containing 'input' and 'expected_output'.
        
    Returns:
        A dictionary containing the execution results, including pass/fail status,
        stdout, and stderr traces for the diagnostician agent.
    """
    headers = {
        "Authorization": f"Bearer {NEBIUS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "language": "python",
        "code": user_code,
        "test_cases": test_cases,
        "timeout": 5.0 # Strict timeout to prevent infinite loops (e.g., bad while loops in two-pointer problems)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SANDBOX_ENDPOINT, 
                json=payload, 
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            
            # Expected response structure: 
            # {
            #   "status": "completed" | "error" | "timeout",
            #   "results": [{"input": "...", "passed": True/False, "actual_output": "...", "stderr": "..."}]
            # }
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Sandbox API error: {e.response.text}")
        return {"status": "api_error", "error": e.response.text}
    except Exception as e:
        logger.error(f"Execution failure: {str(e)}")
        return {"status": "internal_error", "error": str(e)}