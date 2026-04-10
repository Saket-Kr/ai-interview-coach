import os
from pydantic import BaseModel


class Config(BaseModel):
    llm_base_url: str = os.getenv(
        "INTERVIEW_ANALYZER_LLM_URL", "http://localhost:8040/v1"
    )
    llm_api_key: str = os.getenv(
        "INTERVIEW_ANALYZER_LLM_API_KEY", ""
    )
    llm_model: str = os.getenv(
        "INTERVIEW_ANALYZER_LLM_MODEL", "Qwen/Qwen3-235B-A22B-FP8"
    )
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    hf_token: str | None = os.getenv("HF_TOKEN", None)
    max_tokens: int = 4096
    temperature: float = 0.3
