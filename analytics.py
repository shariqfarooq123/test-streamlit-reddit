import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import datasets
import json
import uuid
import random
import pandas as pd

st.set_page_config(layout="wide")

ALL_METHODS = ["ours", "gligen", "layoutgpt", "llmgrounded", "stablediffusion"]
caption_col = "caption"
CURRENT_2AFC_KEY = "curr_2afc"
USER_PREFFERENCES_COLLECTION = "userpreferences"


def get_state(*args):
	out = [getattr(st.session_state, arg) for arg in args]
	if len(out) == 1:
		return out[0]
	else:
		return out

def set_state(**kwargs):
	for key, value in kwargs.items():
		setattr(st.session_state, key, value)


if not hasattr(st.session_state, "user_id"):
    key_dict = json.loads(st.secrets["textkey"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds)
    # fetch user preferences data
    data = db.collection(USER_PREFFERENCES_COLLECTION).get()
    df = pd.DataFrame([doc.to_dict() for doc in data])
    set_state(df=df)
	
# Get queue sizes
max_queue_size = db.collection(f"study/max").get()





