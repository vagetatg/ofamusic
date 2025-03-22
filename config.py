from os import getenv

from dotenv import load_dotenv

load_dotenv()

API_ID = int(getenv("API_ID", None))
API_HASH = getenv("API_HASH", None)

TOKEN = getenv("TOKEN", None)

STRING = getenv("STRING", None)
STRING2 = getenv("STRING2", None)
STRING3 = getenv("STRING3", None)
STRING4 = getenv("STRING4", None)
STRING5 = getenv("STRING5", None)
STRING6 = getenv("STRING6", None)
STRING7 = getenv("STRING7", None)
STRING8 = getenv("STRING8", None)
STRING9 = getenv("STRING9", None)
STRING10 = getenv("STRING10", None)

SESSION_STRINGS = [
    STRING,
    STRING2,
    STRING3,
    STRING4,
    STRING5,
    STRING6,
    STRING7,
    STRING8,
    STRING9,
    STRING10,
]

OWNER_ID = int(getenv("OWNER_ID", 5938660179))
MONGO_URI = getenv("MONGO_URI", None)
DOWNLOADS_DIR = getenv("DOWNLOADS_DIR", "database/music")
API_URL = getenv("API_URL", None)
API_KEY = getenv("API_KEY", None)
PROXY_URL = getenv("PROXY_URL", None)
YOUTUBE_IMG_URL = "https://te.legra.ph/file/6298d377ad3eb46711644.jpg"
