import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")
NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"

if not NEBIUS_API_KEY:
    raise ValueError("NEBIUS_API_KEY is not set in the environment variables.")

nebius_client = AsyncOpenAI(
    base_url=NEBIUS_BASE_URL,
    api_key=NEBIUS_API_KEY,
)

# 3-Tier NVIDIA Nemotron Hierarchy (Override in .env if exact Nebius slugs differ)
MODEL_TIERS = {
    "NANO": os.getenv("NEMOTRON_NANO_MODEL", "nvidia/Nemotron-3-Nano-30B-A3B"),
    "SUPER": os.getenv("NEMOTRON_SUPER_MODEL", "nvidia/Nemotron-3-Super-120B"),
    "ULTRA": os.getenv("NEMOTRON_ULTRA_MODEL", "nvidia/Nemotron-4-340B-Instruct"),
}

# Approximate cost per 1M tokens (USD) on Token Factory for telemetry calculation
MODEL_PRICING_PER_1M = {
    MODEL_TIERS["NANO"]: {"input": 0.10, "output": 0.30},
    MODEL_TIERS["SUPER"]: {"input": 0.30, "output": 0.90},
    MODEL_TIERS["ULTRA"]: {"input": 1.20, "output": 3.60},
}