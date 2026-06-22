import os
from dotenv import load_dotenv

# Resolve the absolute path to the root directory containing the .env file
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT_DIR, ".env")

# Load environment variables from the .env file
load_dotenv(ENV_PATH)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError(
        "Critical Configuration Error: GOOGLE_API_KEY is not set or is missing in the .env file. "
        "Please check your .env file at " + ENV_PATH
    )
