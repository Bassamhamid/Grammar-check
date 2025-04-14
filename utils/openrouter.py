import requests
import json
from config import Config
from utils.limits import limiter

async def validate_user_api(api_key: str) -> bool:
    """التحقق من صحة API المقدم من المستخدم"""
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def query_openrouter(prompt: str, user_id: int = None) -> str:
    # استخدام API الشخصي إذا كان متاحاً
    if user_id and limiter.is_premium_user(user_id):
        api_key = limiter.premium_users[user_id]['api_key']
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
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
        json=data
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
