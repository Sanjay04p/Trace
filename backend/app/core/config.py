import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Nebius Token Factory uses an OpenAI-compatible API
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")
NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"

if not NEBIUS_API_KEY:
    raise ValueError("NEBIUS_API_KEY is not set in the environment variables.")

# We use AsyncOpenAI to prevent blocking FastAPI's event loop during model generation
nebius_client = AsyncOpenAI(
    base_url=NEBIUS_BASE_URL,
    api_key=NEBIUS_API_KEY,
)

# Define the primary NVIDIA model for the hackathon
# We will use Nemotron for complex pedagogical reasoning
PRIMARY_MODEL = "nvidia/Nemotron-4-340B-Instruct" 
FAST_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct" # For quick syntax routing if needed