import os
from dotenv import load_dotenv

# Load env variables from the root .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
