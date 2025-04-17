from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
TIMEZONE = os.getenv("TZ", "Europe/Moscow")
DOMAIN = os.getenv("DOMAIN")
USE_WEBHOOK = os.getenv("USE_WEBHOOK")
PORT = int(os.getenv("PORT"))