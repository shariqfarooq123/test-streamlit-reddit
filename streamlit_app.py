import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import datasets
import json
import uuid
import random

st.set_page_config(layout="wide")

ALL_METHODS = ["ours", "gligen", "layoutgpt", "llmgrounded", "stablediffusion"]
caption_col = "caption"
CURRENT_2AFC_KEY = "curr_2afc"
USER_PREFFERENCES_COLLECTION = "userpreferences"




def load_data():
	with st.spinner("Loading ..."):
		data = datasets.load_dataset('shariqfarooq/USYllmblue', split='train')
	return data

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

def submit_button_label(methods):
	if any(st.session_state[f"checkbox_{method}"] for method in methods):
		return "Submit"
	else:
		return "I'm not sure"

def preference_ui(twoafc_dict):
	twoafc_data = load_2afc_data(twoafc_dict)
	st.title("Select your preference")
	st.write()
	st.info(twoafc_data['caption'])
	cols = st.columns(2)
	method1_image = twoafc_data['method1']
	method2_image = twoafc_data['method2']
	method1_name = twoafc_data['method1_name']
	method2_name = twoafc_data['method2_name']

	method2image = {method1_name: method1_image, method2_name: method2_image}
	items = list(method2image.items())
	random.shuffle(items)
	for col, (method, image) in zip(cols, items):
		with col:
			st.checkbox("", key=f"checkbox_{method}", on_change=make_checkboxes_exclusive, kwargs=dict(selected_key=f"checkbox_{method}"))
			st.image(image)

	st.button(submit_button_label(method2image.keys()), on_click=on_submit, kwargs=dict(twoafc_dict=twoafc_dict))


def update_data():
	with st.spinner("Fetching ..."):
		curr_twoafc = get_next_2afc()
		set_state(**{CURRENT_2AFC_KEY: curr_twoafc})


def on_submit(twoafc_dict):
	# upload 
	methods = [twoafc_dict['method1'], twoafc_dict['method2']]
	for method in methods:
		if st.session_state[f"checkbox_{method}"]:
			ref = twoafc_dict.pop('ref')
			upload_preference(twoafc_dict, method)
			# delete the element from the queue
			ref.reference.delete()
			set_state(done_so_far=get_state("done_so_far") + 1)
	clear_checkboxes()
	# update count
	update_data()

def get_current_set():
	if not hasattr(st.session_state, CURRENT_2AFC_KEY) or get_state(CURRENT_2AFC_KEY) is None:
		update_data()
	return get_state(CURRENT_2AFC_KEY)

def upload_preference(twoafc_dict, chosen_method):
	db : firestore.Client
	db, user_id = get_state("db", "user_id")
	col = db.collection(USER_PREFFERENCES_COLLECTION)
	col.add({'user_id': user_id, 'chosen': chosen_method, **twoafc_dict})

def get_next_2afc():
	db : firestore.Client
	db, user_id = get_state("db", "user_id")
	# get number of max queues to check
	max_queues = db.collection("study").document("max_queues").get().to_dict()["value"]
	# get the non-empty queue
	queue_no = 0
	while True:
		queue_name = f"2afc-{queue_no}"
		queue_ref = db.collection(f"study/queues/{queue_name}")
		# check if queue is empty
		if len(queue_ref.limit(1).get()) > 0:
			break
		queue_no += 1

		if queue_no >= max_queues:
			return None
	
	# debug with queue debug queue
	# queue_name = f"2afc-debug"
	queue_ref = db.collection(f"study/queues/{queue_name}")
	
	# get the first element of the queue
	# we are using firestore as a queue
	# twoafc_doc = next(queue_ref.limit(1).stream())

	# get a random element of the queue
	choices = queue_ref.limit(10).get()
	if len(choices) == 0:
		return None
	twoafc_doc = random.choice(choices)
	twoafc_dict = twoafc_doc.to_dict()
	twoafc_dict['ref'] = twoafc_doc
	# delete the element from the queue
	# twoafc_doc.delete()
	# return the element
	return twoafc_dict

def load_2afc_data(twoafc_dict):
	data = get_state("data")
	row = data[twoafc_dict["idx"]]
	return dict(
		id=twoafc_dict["id"],
		method1=row[twoafc_dict["method1"]],
		method2=row[twoafc_dict["method2"]],
		method1_name=twoafc_dict["method1"],
		method2_name=twoafc_dict["method2"],
		caption=row[caption_col]
	)

	

def display_preferences():
	# debug only
	db, user_id = get_state("db", "user_id")
	preferences = db.collection(USER_PREFFERENCES_COLLECTION).where("user_id", "==", user_id).stream()
	# preferences = db.collection("preferences").stream()
	for pref in preferences:
		st.write(pref.to_dict())

def count_to_emoji(count):
	if count == 0:
		# sad face
		return "😞"
	elif count <= 3:
		# neutral face
		return "😐"
	elif count <= 6:
		# slightly smiling face
		return "🙂"
	elif count <= 9:
		# smiling face with smiling eyes
		return "😊"
	elif count <= 12:
		# hug face
		return "🤗"
	elif count <= 15:
		# bronze medal
		return "🥉"
	elif count < 18:
		# silver medal
		return "🥈"
	elif count >= 18:
		# gold medal
		return "🥇"






if not hasattr(st.session_state, "user_id"):
	key_dict = json.loads(st.secrets["textkey"])
	creds = service_account.Credentials.from_service_account_info(key_dict)
	db = firestore.Client(credentials=creds)
	set_state(db=db, data=load_data(), user_id=str(uuid.uuid4()), row=None, done_so_far=0)


st.title("Welcome! Thank you for participating in our study.")
"""
## Instructions
#### Select the image (by clicking the checkbox above it) that most accurately represents the provided textual description (in blue). 
Image quality is not a factor to consider. Please thoroughly examine the image before making your selection. Your task is to identify the image that, in your judgment, aligns most closely with the provided description. It may be possible that few objects in the descriptions may not be present in any of the images. In that case choose the image that according to you has the maximum information encompassing the text. 

Click 'Submit' to submit your response. If you are unsure, click 'I'm not sure'.

Please submit as many responses as you can. Thank you for your time!
"""
twoafc_dict = get_current_set()
preference_ui(twoafc_dict)
count = get_state("done_so_far")
st.write(f"You've submitted {count} response(s) {count_to_emoji(count)}")

