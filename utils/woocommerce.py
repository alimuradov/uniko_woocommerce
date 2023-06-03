from woocommerce import API
from dotenv import load_dotenv
import os

api_url = os.getenv("API_URL")
woocommerce_ck = os.getenv("WOO_KEY")
woocommerce_cs = os.getenv("WOO_SECRET_KOD")

wcapi = API(
    url=api_url,
    consumer_key=woocommerce_ck,
    consumer_secret=woocommerce_cs,
    wp_api=True,
    version="wc/v3",
    timeout=20 # the default is 5, increase to whatever works for you.
)