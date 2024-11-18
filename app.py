from datetime import timedelta, datetime

import streamlit as st
import requests
import json

# Fetch lab data
labs_response = requests.get("http://fw.finki.ukim.mk/data/rest/lab")
lab_data = {}
for lab in json.loads(labs_response.content):
	lab_data[lab['name']] = lab

# Fetch profile data
profiles_response = requests.get("http://fw.finki.ukim.mk/data/rest/firewall_profile")
profile_data = {}
for profile in json.loads(profiles_response.content):
	profile_data[profile['name']] = profile


def generate_request(firewall_rule_name, selected_profile, selected_labs, start_date, start_time, end_date, end_time):
	result = []
	for lab in selected_labs:
		request = {}
		request['name'] = firewall_rule_name
		request['lab'] = lab_data[lab]
		request['firewallProfile'] = profile_data.get(selected_profile)
		request['timeFrom'] = f"{start_date}T{start_time}.000Z"
		request['timeTo'] = f"{end_date}T{end_time}.000Z"
		result.append(request)
	return result


# Streamlit app
st.title("Lab and Profile Selection")

st.subheader("Authentication")

token = st.text_input("Enter the Authorization header")
cookie = st.text_input("Enter the Cookie header")

st.subheader("Firewall Rule Name")
firewall_rule_name = st.text_input("Enter the Firewall Rule Name")

# Lab checkboxes
st.subheader("Select Labs")
selected_labs = []
for lab_name in lab_data.keys():
	if st.checkbox(lab_name):
		selected_labs.append(lab_name)

# Profile dropdown
st.subheader("Select a Profile")
profile_options = list(profile_data.keys())
selected_profile = st.selectbox("Choose a profile", profile_options)

# Date and time inputs
st.subheader("Select Time Range")
start_date = st.date_input("Start Date")
start_time = st.time_input("Start Time")

current_datetime = datetime.combine(datetime.today(), start_time)

# Subtract one hour
new_datetime = current_datetime - timedelta(hours=1)

# Extract the time part if needed
start_time = new_datetime.time()

end_date = st.date_input("End Date")
end_time = st.time_input("End Time")

current_datetime = datetime.combine(datetime.today(), end_time)
new_datetime = current_datetime - timedelta(hours=1)
end_time = new_datetime.time()




if st.button("Generate Request"):
	all_requests = generate_request(
		firewall_rule_name=firewall_rule_name, selected_profile=selected_profile, selected_labs=selected_labs,
		start_date=start_date, start_time=start_time, end_date=end_date, end_time=end_time
	)
	# st.write("JSONs to send", json.dumps(all_requests))

	for r in all_requests:
		print(json.dumps(r))
		response = requests.post("http://fw.finki.ukim.mk/data/rest/reservation", json=r, headers={
			"Authorization": token,
			"Cookie": cookie
		})
		print(response.content, response.status_code)
