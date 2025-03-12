import os
import dotenv

dotenv.load_dotenv()

TENOR_KEY = os.getenv("TB_TENOR_KEY")
TOKEN = os.getenv("TB_TG_TOKEN")
