import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


class AuthError(Exception):
	pass


def authenticate(username, password):
	# Step 1: Initialize session and fetch login page
	login_url = "https://cas.finki.ukim.mk/cas/login"
	service_url = "http://fw.finki.ukim.mk/cas/login"
	session = requests.Session()
	response = session.get(login_url, params={"service": service_url}, timeout=15)

	# Step 2: Parse hidden fields from the login page
	soup = BeautifulSoup(response.text, "html.parser")
	form_data = {inp["name"]: inp["value"] for inp in soup.find_all("input", {"type": "hidden"})}
	form_data["username"] = username
	form_data["password"] = password

	# Step 3: Submit login form
	post_response = session.post(login_url, data=form_data, allow_redirects=False, timeout=15)

	# Step 4: Follow redirects to validate ticket
	redirect_location = post_response.headers.get("Location", "")
	if not redirect_location:
		raise AuthError("Login failed. No redirection found.")

	parsed_url = urlparse(redirect_location)
	ticket = parse_qs(parsed_url.query).get("ticket", [None])[0]
	if not ticket:
		raise AuthError("Failed to obtain CAS ticket.")

	validation_url = f"{service_url}?ticket={ticket}"
	session.get(validation_url, allow_redirects=False, timeout=15)

	# Step 5: Fetch Bearer token from JavaScript logic or API
	src_js_url = "http://fw.finki.ukim.mk/app/dist/src.js"
	src_js_response = session.get(src_js_url, timeout=15)
	token = None
	if src_js_response.status_code == 200:
		js_content = src_js_response.text

		# Extract the token line starting with 'Bearer'
		if "Bearer" in js_content:
			start_idx = js_content.find("Bearer")
			end_idx = js_content.find("';", start_idx)  # Look for the end of the token string
			if end_idx != -1:
				token = js_content[start_idx:end_idx]
	if not token:
		raise AuthError("Bearer token not found in fw.finki.ukim.mk JavaScript.")

	# Step 6: Extract cookies from the session
	cookies = session.cookies.get_dict()
	if "JSESSIONID" not in cookies:
		raise AuthError("No JSESSIONID cookie received.")

	return token, f"NG_TRANSLATE_LANG_KEY=%22en%22; JSESSIONID={cookies['JSESSIONID']}"
