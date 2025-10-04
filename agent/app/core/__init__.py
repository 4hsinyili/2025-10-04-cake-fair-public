import logging
import random

from google.adk.models.lite_llm import LiteLlm

from app.context import get_current_request
from app.setting import setting


def load_open_router_model(model_name: str | None = None) -> LiteLlm:
    request = get_current_request()
    default_models = [
        "microsoft/mai-ds-r1:free",
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-4-maverick:free",
        "deepseek/deepseek-chat-v3.1:free",
    ]
    avail_models = getattr(request.app.state, "avail_models", default_models) if request else default_models
    random.shuffle(avail_models)  # 隨機打亂模型列表，增加嘗試的多樣性
    for avail_model in avail_models:
        try:
            print(f"Trying to load model: {avail_model}")
            lite_model = LiteLlm(
                # Specify the OpenRouter model using 'openrouter/' prefix
                model=f"openrouter/{model_name or avail_model}",
                # Explicitly provide the API key from environment variables
                api_key=setting.openrouter.API_KEY,
                # Explicitly provide the OpenRouter API base URL
                api_base=setting.openrouter.API_BASE,
            )
            return lite_model
        except Exception as e:
            print(f"Failed to load model {avail_model}: {e}")
            avail_models.remove(avail_model)
            request.app.state.avail_models = avail_models
    raise ValueError("No available models could be loaded.")
