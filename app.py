import os
from pathlib import Path

import requests
import streamlit as st

import cron_manager
import fw_core
from get_tokens import AuthError, authenticate
from schedule import ScheduleError, expand_week, next_monday, parse_schedule, rule_times_utc, validate_names

LOCAL_TZ = "Europe/Skopje"
SCHEDULE_FILE = Path(os.environ.get("FW_SCHEDULE_FILE", "schedule.yaml"))

EXAMPLE_SCHEDULE = """timezone: Europe/Skopje
profile: Default Profile
subjects:
  - name: WP
    slots:
      - {lab: Lab 1, day: mon, from: "10:00", to: "12:00"}
      - {lab: [Lab 2, Lab 3], day: wed, from: "14:00", to: "16:00"}
"""


@st.cache_data(ttl=300)
def load_reference_data():
    return fw_core.fetch_labs(), fw_core.fetch_profiles()


def generate_request(firewall_rule_name, selected_profile, selected_labs, start_date, start_time, end_date, end_time):
    time_from = fw_core.local_to_utc_iso(start_date, start_time, LOCAL_TZ)
    time_to = fw_core.local_to_utc_iso(end_date, end_time, LOCAL_TZ)
    return [
        fw_core.build_payload(firewall_rule_name, lab_data[lab], profile_data.get(selected_profile), time_from, time_to)
        for lab in selected_labs
    ]


# Streamlit app

st.title("Lab and Profile Selection")

try:
    lab_data, profile_data = load_reference_data()
except requests.RequestException:
    st.error("Could not load labs/profiles. fw.finki.ukim.mk might not be available")
    st.stop()

tab_once, tab_weekly = st.tabs(["One-off rule", "Weekly schedule"])

with tab_once:
    with st.form("FW rule", clear_on_submit=True):
        st.subheader("Authentication")
        username = st.text_input("CAS Username")
        password = st.text_input("CAS Password", type="password")

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

        # Date and time inputs (local time, converted to UTC when building the request)
        st.subheader("Select Time Range")
        start_date = st.date_input("Start Date")
        start_time = st.time_input("Start Time")
        end_date = st.date_input("End Date")
        end_time = st.time_input("End Time")

        submitted = st.form_submit_button("Submit")
        if submitted:
            all_requests = generate_request(
                firewall_rule_name=firewall_rule_name, selected_profile=selected_profile,
                selected_labs=selected_labs,
                start_date=start_date, start_time=start_time, end_date=end_date, end_time=end_time
            )

            try:
                token, cookie = authenticate(username, password)
            except AuthError:
                st.error("Wrong username or password")
            except requests.RequestException:
                st.error("Request failed. fw.finki.ukim.mk might not be available")
            else:
                try:
                    for r in all_requests:
                        fw_core.create_reservation(token, cookie, r)
                    st.success("FW rules created successfully")
                except requests.RequestException as e:
                    st.error(f"Request failed: {e}")

with tab_weekly:
    st.caption(
        f"Schedule file: `{SCHEDULE_FILE}`. The cron job reads `FW_USERNAME` / `FW_PASSWORD` "
        "from the server environment; credentials are never stored here."
    )

    with st.expander("Valid lab names"):
        st.code("\n".join(lab_data))
    with st.expander("Valid profile names"):
        st.code("\n".join(profile_data))

    current = SCHEDULE_FILE.read_text() if SCHEDULE_FILE.exists() else EXAMPLE_SCHEDULE
    text = st.text_area("schedule.yaml", current, height=300)

    if st.button("Save schedule"):
        try:
            parse_schedule(text)
        except Exception as e:
            st.error(f"Invalid schedule: {e}")
        else:
            SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            SCHEDULE_FILE.write_text(text)
            st.success("Saved")

    st.subheader("Preview: next week")
    try:
        rules = expand_week(parse_schedule(text), next_monday())
    except Exception as e:
        st.error(f"Invalid schedule: {e}")
    else:
        errors = validate_names(rules, lab_data, profile_data)
        for err in errors:
            st.error(err)
        st.table([
            {"rule": r.name, "lab": r.lab, "profile": r.profile,
             "from (UTC)": rule_times_utc(r)[0], "to (UTC)": rule_times_utc(r)[1]}
            for r in rules
        ])

    st.subheader("Cron")
    cron_expr = st.text_input("Cron expression", cron_manager.DEFAULT_CRON)
    col_install, col_remove = st.columns(2)
    try:
        if col_install.button("Install / update cron"):
            cron_manager.install_cron(SCHEDULE_FILE, cron_expr)
        if col_remove.button("Remove cron"):
            cron_manager.uninstall_cron()
        st.code(cron_manager.show_cron() or "no cron installed")
    except Exception as e:
        st.error(f"Could not manage cron: {e}")
