import os

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = "meta-llama/llama-4-maverick:free"
    
    # Channel Configuration
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # بدون @
    CHANNEL_LINK = os.getenv("CHANNEL_LINK")         # رابط القناة
    
    # Usage Limits
    CHAR_LIMIT = 120
    REQUEST_LIMIT = 3
    RESET_HOURS = 20
    
    # Webhook
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.environ.get("PORT", "10000"))
    
    # App Info
    SITE_URL = os.getenv("SITE_URL", "")
    SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Bot")
