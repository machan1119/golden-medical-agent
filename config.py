import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Composio API
    COMPOSIO_API_KEY: str = os.getenv("COMPOSIO_API_KEY", "")

    # Google Sheets API
    GOOGLE_SHEETS_CREDENTIALS_JSON: str = os.getenv(
        "GOOGLE_SHEETS_CREDENTIALS_JSON", ""
    )
    # JotForm API (optional)
    JOTFORM_API_KEY: str = os.getenv("JOTFORM_API_KEY", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # STT
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")


settings = Settings()
