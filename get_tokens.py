import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


def authenticate(username, password):
	# Step 1: Initialize session and fetch login page
	login_url = "https://cas.finki.ukim.mk/cas/login"
	service_url = "http://fw.finki.ukim.mk/cas/login"
	session = requests.Session()
	response = session.get(login_url, params={"service": service_url})

	# Step 2: Parse hidden fields from the login page
	soup = BeautifulSoup(response.text, "html.parser")
	form_data = {inp["name"]: inp["value"] for inp in soup.find_all("input", {"type": "hidden"})}
	form_data["username"] = username  # Replace with your credentials
	form_data["password"] = password  # Replace with your credentials

	# Step 3: Submit login form
	post_response = session.post(login_url, data=form_data, allow_redirects=False)

	# Step 4: Follow redirects to validate ticket
	redirect_location = post_response.headers.get("Location", "")
	if not redirect_location:
		print("Login failed. No redirection found.")
		exit()

	parsed_url = urlparse(redirect_location)
	ticket = parse_qs(parsed_url.query).get("ticket", [None])[0]
	if not ticket:
		print("Failed to obtain CAS ticket.")
		exit()

	validation_url = f"{service_url}?ticket={ticket}"
	validation_response = session.get(validation_url, allow_redirects=False)

	# Step 5: Fetch Bearer token from JavaScript logic or API
	src_js_url = "http://fw.finki.ukim.mk/app/dist/src.js"
	src_js_response = session.get(src_js_url)
	token = None
	if src_js_response.status_code == 200:
		js_content = src_js_response.text
		print("Fetched JavaScript logic. Analyzing for token...")

		# Extract the token line starting with 'Bearer'
		if "Bearer" in js_content:
			start_idx = js_content.find("Bearer")
			end_idx = js_content.find("';", start_idx)  # Look for the end of the token string
			if end_idx != -1:
				token = js_content[start_idx:end_idx]
				print(f"Extracted Token: {token}")
			else:
				print("Failed to find the end of the token.")
		else:
			print("Token not found in JavaScript logic.")

	# Step 6: Extract cookies from the session
	cookies = session.cookies.get_dict()
	print(f"Extracted Cookies: {cookies}")


	return token, f"NG_TRANSLATE_LANG_KEY=%22en%22; JSESSIONID={cookies['JSESSIONID']}"
