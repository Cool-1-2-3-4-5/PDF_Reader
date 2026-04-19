import os
import googlemaps
from pprint import pprint
from dotenv import load_dotenv
load_dotenv()
MAPS_KEY = os.getenv('MAPS_KEY')
if not MAPS_KEY:
    # On Streamlit Cloud, load from environment variables set via Secrets
    import streamlit as st
    MAPS_KEY = st.secrets.get("MAPS_KEY")
maps_access = googlemaps.Client(MAPS_KEY)
print("HI")
results = maps_access.find_place(input = "AIRINC APPLIED INFORMATICS & RESEARCH INC.",input_type="textquery")
print(results)
details = maps_access.place(results['candidates'][0]['place_id'])
print("hhh")
print(details)
print(details['result']['international_phone_number'])
print(details['result']['website'])