import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import datasets
import json
import uuid
from dataclasses import dataclass

st.set_page_config(layout="wide")

ALL_METHODS = ["ours", "gligen", "layoutgpt", "llmgrounded", "stablediffusion"]
caption_col = "caption"


class TwoAFC:
	def __init__(self, data):
		self.data = data
		inds = list(range(len(data)))


def load_data():
	with st.spinner("Loading ..."):
		# data = datasets.load_dataset("shariqfarooq/cs323_densepred_depth", streaming=True, split='test', keep_in_memory=True)
		data = datasets.load_dataset("shariqfarooq/cs323_densepred_depth", split='test', keep_in_memory=True)
		# data = data.shuffle(buffer_size=10)
	return iter(data)

def get_state(*args):
	out = [getattr(st.session_state, arg) for arg in args]
	if len(out) == 1:
		return out[0]
	else:
		return out

def set_state(**kwargs):
	for key, value in kwargs.items():
		setattr(st.session_state, key, value)


def make_checkboxes_exclusive(selected_key):
	for key, value in st.session_state.items():
		if key != selected_key and key.startswith("checkbox_") and value:
			st.session_state[key] = False

def clear_checkboxes():
	for key, value in st.session_state.items():
		if key.startswith("checkbox_"):
			st.session_state[key] = False

def submit_button_label():
	if any(st.session_state[f"checkbox_{method}"] for method in ALL_METHODS):
		return "Submit"
	else:
		return "I'm not sure"


def preference_ui(idd, prompt, method2image):
	st.title("Select your preference")
	# with st.form("my_form"):
	st.write("Which image do you prefer?")
	cols = st.columns(len(method2image))
	for col, (method, image) in zip(cols, method2image.items()):
		with col:
			st.checkbox("", key=f"checkbox_{method}", on_change=make_checkboxes_exclusive, kwargs=dict(selected_key=f"checkbox_{method}"))
			st.image(image, caption=method, width=300)

	st.button(submit_button_label(), on_click=on_submit, kwargs=dict(idd=idd))


def update_data():
	with st.spinner("Fetching row ..."):
		row = next(get_state("data"))
		set_state(row=row)

def on_submit(idd):
	update_data()
	# upload 
	for method in method2image.keys():
		if st.session_state[f"checkbox_{method}"]:
			upload_preference(idd, method)
	clear_checkboxes()

def get_current_set():
	if get_state("row") is None:
		update_data()
	
	row = get_state("row")
	st.write(row)
	# idd = row["id"]
	idd = str(uuid.uuid4())
	method2image = {method: row[method] for method in ALL_METHODS}
	return idd, method2image

def upload_preference(idd, method):
	db : firestore.Client
	db, user_id = get_state("db", "user_id")
	db.collection("preferences").add({
		"user_id": user_id,
		"method": method,
		"entry_id": idd
	})
	

def display_preferences():
	db, user_id = get_state("db", "user_id")
	preferences = db.collection("preferences").where("user_id", "==", user_id).stream()
	# preferences = db.collection("preferences").stream()
	for pref in preferences:
		st.write(pref.to_dict())


if not hasattr(st.session_state, "user_id"):
	key_dict = json.loads(st.secrets["textkey"])
	creds = service_account.Credentials.from_service_account_info(key_dict)
	db = firestore.Client(credentials=creds)
	set_state(db=db, data=load_data(), user_id=str(uuid.uuid4()), row=None)


st.write(f"Hello world {get_state('user_id')}")
idd, method2image = get_current_set()
st.write(idd)
preference_ui(idd, "Which image do you prefer?", method2image)
display_preferences()
st.write(st.session_state)