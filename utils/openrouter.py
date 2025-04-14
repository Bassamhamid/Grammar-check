import requests
import json
from config import Config

def query_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": Config.SITE_URL,
        "X-Title": Config.SITE_TITLE
    }

    data = {
        "model": Config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(data)
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
