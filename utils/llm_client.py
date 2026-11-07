import time
from google import genai
from google.genai import types


def generate_with_retry(
    api_key: str,
    model_name: str,
    contents: str,
    config: types.GenerateContentConfig,
    max_retries: int = 4,
):
    """
    Calls Gemini with exponential backoff and automatic fallback models
    if Google servers return 503 (High Demand) or 429 (Rate Limit).
    """
    client = genai.Client(api_key=api_key)

    # Fallback chain if the primary model has a 503 demand spike
    fallback_models = [
        model_name,
        "gemini-2.0-flash",
        "gemini-flash-latest",
    ]
    # Remove duplicates while preserving order
    models_to_try = list(dict.fromkeys(fallback_models))

    last_error = None
    for current_model in models_to_try:
        for attempt in range(max_retries):
            try:
                return client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                last_error = e
                err_str = str(e).upper()
                # Retry on 503 Unavailable, 429 Quota/Burst, or 500 Internal Error
                if any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "OVERLOADED"]):
                    wait_time = (2 ** attempt) + 1  # 2s, 3s, 5s, 9s
                    time.sleep(wait_time)
                    continue
                # If model name itself is 404 invalid, break inner loop and try next fallback model
                if "404" in err_str or "NOT_FOUND" in err_str:
                    break
                raise e

    raise last_error