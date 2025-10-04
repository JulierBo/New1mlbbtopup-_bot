import os
import logging

logger = logging.getLogger(__name__)

# Get bot token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set!")
    raise ValueError("BOT_TOKEN environment variable is required")

# Bot configuration
BOT_USERNAME = os.getenv("BOT_USERNAME", "MyTelegramBot")

# Admin configuration
ADMIN_ID = 6437656033
ADMIN_GROUP_ID = -1002897101139

# Payment configuration
WAVE_NUMBER = "09123456789"  # Default Wave number
KPAY_NUMBER = "09123456789"  # Default KPay number

# Product prices (in MMK)
PRICES = {
    "1gb": 500,
    "2gb": 900,
    "5gb": 2000,
    "10gb": 3500,
    "unlimited": 5000
}

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Validate token format (basic check)
if not BOT_TOKEN.count(":") == 1:
    logger.warning("BOT_TOKEN format might be incorrect. Expected format: 'bot_id:bot_secret'")

logger.info(f"Bot configuration loaded successfully for {BOT_USERNAME}")
logger.info(f"Admin ID: {ADMIN_ID}, Admin Group: {ADMIN_GROUP_ID}")
